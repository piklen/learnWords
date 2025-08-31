"""
高性能API中间件
包含请求优化、响应压缩、速率限制等功能
"""

import asyncio
import gzip
import time
import json
import logging
from typing import Callable, Dict, Any, Optional, Set
from fastapi import Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis
from datetime import datetime, timedelta

from app.core.config_optimized import settings

logger = logging.getLogger(__name__)

class PerformanceMiddleware(BaseHTTPMiddleware):
    """高性能API中间件"""
    
    def __init__(
        self,
        app: ASGIApp,
        enable_compression: bool = True,
        enable_caching: bool = True,
        enable_rate_limiting: bool = True,
        compression_min_size: int = 1000,
        cache_ttl: int = 300
    ):
        super().__init__(app)
        self.enable_compression = enable_compression
        self.enable_caching = enable_caching
        self.enable_rate_limiting = enable_rate_limiting
        self.compression_min_size = compression_min_size
        self.cache_ttl = cache_ttl
        
        # Redis连接（用于缓存和限流）
        self.redis = None
        self._initialize_redis()
        
        # 缓存相关配置
        self.cacheable_methods = {"GET", "HEAD"}
        self.cache_exclude_paths = {"/health", "/metrics", "/ws"}
        
        # 压缩相关配置
        self.compressible_types = {
            "application/json",
            "application/javascript",
            "text/html",
            "text/plain",
            "text/css",
            "text/xml",
            "application/xml"
        }
        
        # 限流配置
        self.rate_limit_window = 60  # 1分钟窗口
        self.default_rate_limit = settings.server.rate_limit_per_minute
        
    def _initialize_redis(self):
        """初始化Redis连接"""
        try:
            self.redis = redis.Redis.from_url(
                settings.redis.redis_url,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Redis for performance middleware: {e}")
            self.redis = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求的主要逻辑"""
        start_time = time.time()
        
        # 获取客户端信息
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        try:
            # 1. 速率限制检查
            if self.enable_rate_limiting:
                rate_limit_result = await self._check_rate_limit(client_ip, request.url.path)
                if not rate_limit_result["allowed"]:
                    return self._create_rate_limit_response(rate_limit_result)
            
            # 2. 检查缓存
            if self.enable_caching and self._is_cacheable(request):
                cached_response = await self._get_cached_response(request)
                if cached_response:
                    await self._record_metrics(
                        request, None, time.time() - start_time, 
                        status="cache_hit", client_ip=client_ip
                    )
                    return cached_response
            
            # 3. 处理请求
            response = await call_next(request)
            
            # 4. 处理响应
            response = await self._process_response(request, response)
            
            # 5. 缓存响应
            if self.enable_caching and self._should_cache_response(request, response):
                await self._cache_response(request, response)
            
            # 6. 记录指标
            processing_time = time.time() - start_time
            await self._record_metrics(
                request, response, processing_time, 
                status="success", client_ip=client_ip
            )
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Performance middleware error: {e}")
            
            # 记录错误指标
            await self._record_metrics(
                request, None, processing_time, 
                status="error", client_ip=client_ip, error=str(e)
            )
            
            # 重新抛出异常
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _check_rate_limit(self, client_ip: str, path: str) -> Dict[str, Any]:
        """检查速率限制"""
        if not self.redis:
            return {"allowed": True, "remaining": self.default_rate_limit}
        
        try:
            # 使用滑动窗口算法
            now = int(time.time())
            window_start = now - self.rate_limit_window
            
            # Redis键
            key = f"rate_limit:{client_ip}:{path}"
            
            # 清理过期的请求记录
            await self.redis.zremrangebyscore(key, 0, window_start)
            
            # 获取当前窗口内的请求数
            current_requests = await self.redis.zcard(key)
            
            if current_requests >= self.default_rate_limit:
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": now + self.rate_limit_window
                }
            
            # 记录当前请求
            await self.redis.zadd(key, {str(now): now})
            await self.redis.expire(key, self.rate_limit_window * 2)  # 设置过期时间
            
            return {
                "allowed": True,
                "remaining": self.default_rate_limit - current_requests - 1
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return {"allowed": True, "remaining": self.default_rate_limit}
    
    def _create_rate_limit_response(self, rate_limit_result: Dict[str, Any]) -> Response:
        """创建速率限制响应"""
        headers = {
            "X-RateLimit-Limit": str(self.default_rate_limit),
            "X-RateLimit-Remaining": str(rate_limit_result.get("remaining", 0)),
            "X-RateLimit-Reset": str(rate_limit_result.get("reset_time", 0)),
            "Retry-After": str(self.rate_limit_window)
        }
        
        return Response(
            content=json.dumps({
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {self.default_rate_limit} per minute"
            }),
            status_code=429,
            headers=headers,
            media_type="application/json"
        )
    
    def _is_cacheable(self, request: Request) -> bool:
        """检查请求是否可缓存"""
        return (
            request.method in self.cacheable_methods and
            not any(path in str(request.url.path) for path in self.cache_exclude_paths) and
            not request.headers.get("cache-control", "").startswith("no-cache")
        )
    
    async def _get_cached_response(self, request: Request) -> Optional[Response]:
        """获取缓存的响应"""
        if not self.redis:
            return None
        
        try:
            cache_key = f"response_cache:{request.method}:{request.url}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return Response(
                    content=data["content"],
                    status_code=data["status_code"],
                    headers=data.get("headers", {}),
                    media_type=data.get("media_type", "application/json")
                )
                
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        
        return None
    
    def _should_cache_response(self, request: Request, response: Response) -> bool:
        """检查响应是否应该缓存"""
        return (
            self._is_cacheable(request) and
            200 <= response.status_code < 300 and
            not response.headers.get("cache-control", "").startswith("no-cache")
        )
    
    async def _cache_response(self, request: Request, response: Response):
        """缓存响应"""
        if not self.redis:
            return
        
        try:
            # 读取响应内容
            if hasattr(response, 'body'):
                content = response.body
            else:
                # 对于StreamingResponse，我们不缓存
                return
            
            cache_data = {
                "content": content.decode() if isinstance(content, bytes) else content,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "media_type": response.media_type,
                "cached_at": datetime.now().isoformat()
            }
            
            cache_key = f"response_cache:{request.method}:{request.url}"
            await self.redis.setex(
                cache_key, 
                self.cache_ttl, 
                json.dumps(cache_data)
            )
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    async def _process_response(self, request: Request, response: Response) -> Response:
        """处理响应（压缩等）"""
        if not self.enable_compression:
            return response
        
        # 检查是否应该压缩
        if not self._should_compress(request, response):
            return response
        
        try:
            # 获取响应内容
            if hasattr(response, 'body'):
                content = response.body
                if isinstance(content, str):
                    content = content.encode()
                
                # 检查内容大小
                if len(content) < self.compression_min_size:
                    return response
                
                # 压缩内容
                compressed_content = gzip.compress(content)
                
                # 创建新的响应
                new_response = Response(
                    content=compressed_content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                
                # 添加压缩头
                new_response.headers["content-encoding"] = "gzip"
                new_response.headers["content-length"] = str(len(compressed_content))
                
                return new_response
                
        except Exception as e:
            logger.error(f"Response compression error: {e}")
        
        return response
    
    def _should_compress(self, request: Request, response: Response) -> bool:
        """检查是否应该压缩响应"""
        # 检查客户端是否支持gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return False
        
        # 检查内容类型
        content_type = response.media_type or ""
        if not any(ct in content_type for ct in self.compressible_types):
            return False
        
        # 检查是否已经压缩
        if response.headers.get("content-encoding"):
            return False
        
        return True
    
    async def _record_metrics(
        self, 
        request: Request, 
        response: Optional[Response], 
        processing_time: float,
        status: str = "success",
        client_ip: str = "unknown",
        error: str = None
    ):
        """记录性能指标"""
        if not self.redis:
            return
        
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "method": request.method,
                "path": str(request.url.path),
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent", ""),
                "processing_time": processing_time,
                "status": status,
                "status_code": response.status_code if response else None,
                "content_length": response.headers.get("content-length") if response else None,
                "error": error
            }
            
            # 保存到Redis（时间序列）
            key = f"performance_metrics:{datetime.now().strftime('%Y%m%d%H')}"
            await self.redis.lpush(key, json.dumps(metrics))
            await self.redis.expire(key, 86400)  # 24小时过期
            
            # 更新实时统计
            await self._update_realtime_stats(metrics)
            
        except Exception as e:
            logger.error(f"Metrics recording error: {e}")
    
    async def _update_realtime_stats(self, metrics: Dict[str, Any]):
        """更新实时统计"""
        if not self.redis:
            return
        
        try:
            stats_key = "realtime_stats"
            
            # 获取当前统计
            current_stats = await self.redis.get(stats_key)
            stats = json.loads(current_stats) if current_stats else {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "cache_hits": 0,
                "avg_response_time": 0,
                "last_updated": None,
                "response_times": []
            }
            
            # 更新统计
            stats["total_requests"] += 1
            stats["last_updated"] = datetime.now().isoformat()
            
            if metrics["status"] == "success":
                stats["successful_requests"] += 1
            elif metrics["status"] == "error":
                stats["failed_requests"] += 1
            elif metrics["status"] == "cache_hit":
                stats["cache_hits"] += 1
                stats["successful_requests"] += 1
            
            # 更新响应时间
            stats["response_times"].append(metrics["processing_time"])
            if len(stats["response_times"]) > 100:  # 只保留最近100个
                stats["response_times"] = stats["response_times"][-100:]
            
            # 计算平均响应时间
            if stats["response_times"]:
                stats["avg_response_time"] = sum(stats["response_times"]) / len(stats["response_times"])
            
            # 保存统计
            await self.redis.setex(stats_key, 3600, json.dumps(stats))
            
        except Exception as e:
            logger.error(f"Realtime stats update error: {e}")


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """请求大小限制中间件"""
    
    def __init__(self, app: ASGIApp, max_size: int = 50 * 1024 * 1024):  # 50MB
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """检查请求大小"""
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    return Response(
                        content=json.dumps({
                            "error": "Request too large",
                            "message": f"Request size {size} exceeds maximum {self.max_size} bytes"
                        }),
                        status_code=413,
                        media_type="application/json"
                    )
            except ValueError:
                pass
        
        return await call_next(request)


class ResponseTimeHeaderMiddleware(BaseHTTPMiddleware):
    """响应时间头中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """添加响应时间到响应头"""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        response.headers["X-Timestamp"] = str(int(time.time()))
        
        return response


# 中间件工厂函数
def create_performance_middleware(app: ASGIApp) -> ASGIApp:
    """创建性能中间件链"""
    # 添加响应时间头
    app = ResponseTimeHeaderMiddleware(app)
    
    # 添加请求大小限制
    app = RequestSizeMiddleware(app, max_size=settings.storage.max_file_size)
    
    # 添加主要性能中间件
    app = PerformanceMiddleware(
        app,
        enable_compression=True,
        enable_caching=True,
        enable_rate_limiting=True
    )
    
    return app
