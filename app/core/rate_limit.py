import time
import logging
from typing import Optional, Callable, Dict, Any
from functools import wraps
from fastapi import HTTPException, Request, status
from app.core.cache import cache
from app.core.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """API限流器"""
    
    def __init__(self):
        self.rate_limit_per_minute = settings.rate_limit_per_minute
        self.default_window = 60  # 默认时间窗口（秒）
    
    def _get_client_identifier(self, request: Request) -> str:
        """获取客户端标识符"""
        # 优先使用用户ID（如果已认证）
        if hasattr(request.state, 'user') and request.state.user:
            return f"user:{request.state.user.id}"
        
        # 使用IP地址
        client_ip = request.client.host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _get_rate_limit_key(self, identifier: str, endpoint: str) -> str:
        """生成限流键"""
        return f"rate_limit:{identifier}:{endpoint}"
    
    def _check_rate_limit(self, identifier: str, endpoint: str, max_requests: int, window: int) -> bool:
        """检查是否超过限流"""
        try:
            key = self._get_rate_limit_key(identifier, endpoint)
            current_time = int(time.time())
            
            # 获取当前时间窗口的请求次数
            window_start = current_time - (current_time % window)
            window_key = f"{key}:{window_start}"
            
            # 从缓存获取当前窗口的请求次数
            current_requests = cache.get(window_key) or 0
            
            if current_requests >= max_requests:
                return False
            
            # 增加请求计数
            cache.set(window_key, current_requests + 1, ttl=window)
            
            return True
            
        except Exception as e:
            logger.error(f"检查限流失败: {e}")
            # 限流检查失败时，允许请求通过
            return True
    
    def _get_remaining_requests(self, identifier: str, endpoint: str, max_requests: int, window: int) -> int:
        """获取剩余请求次数"""
        try:
            key = self._get_rate_limit_key(identifier, endpoint)
            current_time = int(time.time())
            window_start = current_time - (current_time % window)
            window_key = f"{key}:{window_start}"
            
            current_requests = cache.get(window_key) or 0
            return max(0, max_requests - current_requests)
            
        except Exception as e:
            logger.error(f"获取剩余请求次数失败: {e}")
            return max_requests
    
    def _get_reset_time(self, identifier: str, endpoint: str, window: int) -> int:
        """获取限流重置时间"""
        current_time = int(time.time())
        window_start = current_time - (current_time % window)
        return window_start + window
    
    def rate_limit(
        self,
        requests_per_minute: Optional[int] = None,
        window: Optional[int] = None,
        endpoint: Optional[str] = None
    ):
        """限流装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 获取请求对象
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                
                if not request:
                    # 如果没有找到请求对象，跳过限流检查
                    return await func(*args, **kwargs)
                
                # 获取限流参数
                max_requests = requests_per_minute or self.rate_limit_per_minute
                time_window = window or self.default_window
                endpoint_name = endpoint or f"{func.__module__}.{func.__name__}"
                
                # 获取客户端标识符
                identifier = self._get_client_identifier(request)
                
                # 检查限流
                if not self._check_rate_limit(identifier, endpoint_name, max_requests, time_window):
                    # 计算剩余请求次数和重置时间
                    remaining = self._get_remaining_requests(identifier, endpoint_name, max_requests, time_window)
                    reset_time = self._get_reset_time(identifier, endpoint_name, time_window)
                    
                    # 设置响应头
                    request.state.rate_limit_headers = {
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": str(remaining),
                        "X-RateLimit-Reset": str(reset_time),
                        "X-RateLimit-Window": str(time_window)
                    }
                    
                    # 抛出限流异常
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "请求过于频繁",
                            "message": f"每分钟最多允许 {max_requests} 次请求",
                            "remaining": remaining,
                            "reset_time": reset_time,
                            "retry_after": max(1, reset_time - int(time.time()))
                        }
                    )
                
                # 设置响应头
                remaining = self._get_remaining_requests(identifier, endpoint_name, max_requests, time_window)
                reset_time = self._get_reset_time(identifier, endpoint_name, time_window)
                
                request.state.rate_limit_headers = {
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                    "X-RateLimit-Window": str(time_window)
                }
                
                # 执行原函数
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def get_rate_limit_info(self, identifier: str, endpoint: str) -> Dict[str, Any]:
        """获取限流信息"""
        try:
            key = self._get_rate_limit_key(identifier, endpoint)
            current_time = int(time.time())
            window_start = current_time - (current_time % self.default_window)
            window_key = f"{key}:{window_start}"
            
            current_requests = cache.get(window_key) or 0
            remaining = max(0, self.rate_limit_per_minute - current_requests)
            reset_time = window_start + self.default_window
            
            return {
                "limit": self.rate_limit_per_minute,
                "remaining": remaining,
                "reset_time": reset_time,
                "current_requests": current_requests,
                "window": self.default_window
            }
            
        except Exception as e:
            logger.error(f"获取限流信息失败: {e}")
            return {
                "limit": self.rate_limit_per_minute,
                "remaining": self.rate_limit_per_minute,
                "reset_time": int(time.time()) + self.default_window,
                "current_requests": 0,
                "window": self.default_window
            }
    
    def reset_rate_limit(self, identifier: str, endpoint: str) -> bool:
        """重置限流计数"""
        try:
            key = self._get_rate_limit_key(identifier, endpoint)
            current_time = int(time.time())
            window_start = current_time - (current_time % self.default_window)
            window_key = f"{key}:{window_start}"
            
            cache.delete(window_key)
            return True
            
        except Exception as e:
            logger.error(f"重置限流失败: {e}")
            return False
    
    def get_all_rate_limits(self, identifier: str) -> Dict[str, Any]:
        """获取用户的所有限流信息"""
        try:
            # 这里可以实现获取所有端点的限流信息
            # 由于Redis键的复杂性，这里返回基本信息
            return {
                "identifier": identifier,
                "global_limit": self.rate_limit_per_minute,
                "window": self.default_window,
                "message": "使用具体端点获取详细限流信息"
            }
            
        except Exception as e:
            logger.error(f"获取所有限流信息失败: {e}")
            return {}

# 全局限流器实例
rate_limiter = RateLimiter()

# 便捷的限流装饰器
def rate_limit(requests_per_minute: Optional[int] = None, window: Optional[int] = None, endpoint: Optional[str] = None):
    """便捷的限流装饰器"""
    return rate_limiter.rate_limit(requests_per_minute, window, endpoint)

# 不同级别的限流装饰器
def strict_rate_limit(func: Callable) -> Callable:
    """严格限流：每分钟30次请求"""
    return rate_limit(30, 60)(func)

def moderate_rate_limit(func: Callable) -> Callable:
    """中等限流：每分钟60次请求"""
    return rate_limit(60, 60)(func)

def lenient_rate_limit(func: Callable) -> Callable:
    """宽松限流：每分钟120次请求"""
    return rate_limit(120, 60)(func)

def burst_rate_limit(func: Callable) -> Callable:
    """突发限流：每分钟300次请求"""
    return rate_limit(300, 60)(func)
