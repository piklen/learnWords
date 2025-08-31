import asyncio
import json
import pickle
import hashlib
import logging
from typing import Any, Optional, Dict, List, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import wraps
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: datetime
    ttl: int
    hit_count: int = 0
    last_accessed: Optional[datetime] = None

class CacheStrategy:
    """缓存策略枚举"""
    LRU = "lru"  # 最近最少使用
    TTL = "ttl"  # 基于时间
    LFU = "lfu"  # 最少使用频率

class OptimizedRedisCache:
    """优化的Redis缓存系统"""
    
    def __init__(self):
        self.redis_pool = None
        self.default_ttl = settings.cache_ttl
        self.key_prefix = "learnwords:cache:"
        self.stats_key = "learnwords:cache:stats"
        self._local_cache = {}  # 本地缓存层
        self._local_cache_max_size = 1000
        
    async def initialize(self):
        """初始化Redis连接池"""
        try:
            self.redis_pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis = redis.Redis(connection_pool=self.redis_pool)
            
            # 测试连接
            await self.redis.ping()
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self.redis = None
    
    def _make_key(self, key: str, namespace: str = None) -> str:
        """生成缓存键"""
        if namespace:
            return f"{self.key_prefix}{namespace}:{key}"
        return f"{self.key_prefix}{key}"
    
    def _hash_complex_key(self, key: Any) -> str:
        """为复杂对象生成哈希键"""
        if isinstance(key, (str, int, float)):
            return str(key)
        
        # 对复杂对象进行哈希
        try:
            key_str = json.dumps(key, sort_keys=True, default=str)
            return hashlib.md5(key_str.encode()).hexdigest()
        except Exception:
            # 如果序列化失败，使用字符串表示
            return hashlib.md5(str(key).encode()).hexdigest()
    
    async def get(self, key: str, namespace: str = None, default: Any = None) -> Any:
        """获取缓存值"""
        cache_key = self._make_key(key, namespace)
        
        # 首先检查本地缓存
        if cache_key in self._local_cache:
            entry = self._local_cache[cache_key]
            if datetime.now() - entry.created_at < timedelta(seconds=entry.ttl):
                entry.hit_count += 1
                entry.last_accessed = datetime.now()
                await self._update_stats("local_hit")
                return entry.value
            else:
                # 本地缓存过期
                del self._local_cache[cache_key]
        
        # 检查Redis缓存
        if self.redis:
            try:
                data = await self.redis.get(cache_key)
                if data:
                    try:
                        value = pickle.loads(data)
                        # 添加到本地缓存
                        await self._add_to_local_cache(cache_key, value, self.default_ttl)
                        await self._update_stats("redis_hit")
                        return value
                    except (pickle.PickleError, TypeError):
                        # 尝试JSON解析
                        try:
                            value = json.loads(data)
                            await self._add_to_local_cache(cache_key, value, self.default_ttl)
                            await self._update_stats("redis_hit")
                            return value
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to deserialize cache value for key: {cache_key}")
            except Exception as e:
                logger.error(f"Redis get error for key {cache_key}: {e}")
        
        await self._update_stats("miss")
        return default
    
    async def set(self, key: str, value: Any, ttl: int = None, namespace: str = None) -> bool:
        """设置缓存值"""
        cache_key = self._make_key(key, namespace)
        ttl = ttl or self.default_ttl
        
        # 添加到本地缓存
        await self._add_to_local_cache(cache_key, value, ttl)
        
        # 保存到Redis
        if self.redis:
            try:
                # 尝试使用pickle序列化，更高效
                try:
                    serialized_value = pickle.dumps(value)
                except (pickle.PickleError, TypeError):
                    # 回退到JSON
                    serialized_value = json.dumps(value, default=str)
                
                await self.redis.setex(cache_key, ttl, serialized_value)
                await self._update_stats("set")
                return True
                
            except Exception as e:
                logger.error(f"Redis set error for key {cache_key}: {e}")
        
        return False
    
    async def delete(self, key: str, namespace: str = None) -> bool:
        """删除缓存值"""
        cache_key = self._make_key(key, namespace)
        
        # 从本地缓存删除
        if cache_key in self._local_cache:
            del self._local_cache[cache_key]
        
        # 从Redis删除
        if self.redis:
            try:
                result = await self.redis.delete(cache_key)
                await self._update_stats("delete")
                return bool(result)
            except Exception as e:
                logger.error(f"Redis delete error for key {cache_key}: {e}")
        
        return False
    
    async def exists(self, key: str, namespace: str = None) -> bool:
        """检查键是否存在"""
        cache_key = self._make_key(key, namespace)
        
        # 检查本地缓存
        if cache_key in self._local_cache:
            entry = self._local_cache[cache_key]
            if datetime.now() - entry.created_at < timedelta(seconds=entry.ttl):
                return True
            else:
                del self._local_cache[cache_key]
        
        # 检查Redis
        if self.redis:
            try:
                return bool(await self.redis.exists(cache_key))
            except Exception as e:
                logger.error(f"Redis exists error for key {cache_key}: {e}")
        
        return False
    
    async def clear_namespace(self, namespace: str) -> int:
        """清除命名空间下的所有缓存"""
        if not self.redis:
            return 0
        
        try:
            pattern = self._make_key("*", namespace)
            keys = await self.redis.keys(pattern)
            
            if keys:
                # 从本地缓存删除
                for key in keys:
                    if key in self._local_cache:
                        del self._local_cache[key]
                
                # 从Redis删除
                deleted = await self.redis.delete(*keys)
                await self._update_stats("clear")
                return deleted
                
        except Exception as e:
            logger.error(f"Redis clear namespace error for {namespace}: {e}")
        
        return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self.redis:
            return {"error": "Redis not available"}
        
        try:
            stats_data = await self.redis.get(self.stats_key)
            stats = json.loads(stats_data) if stats_data else {}
            
            # 添加本地缓存统计
            stats["local_cache_size"] = len(self._local_cache)
            stats["local_cache_max_size"] = self._local_cache_max_size
            
            # 计算命中率
            total_hits = stats.get("local_hit", 0) + stats.get("redis_hit", 0)
            total_requests = total_hits + stats.get("miss", 0)
            stats["hit_rate"] = total_hits / total_requests if total_requests > 0 else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    async def _add_to_local_cache(self, key: str, value: Any, ttl: int):
        """添加到本地缓存"""
        # 如果本地缓存已满，删除最旧的条目
        if len(self._local_cache) >= self._local_cache_max_size:
            oldest_key = min(
                self._local_cache.keys(),
                key=lambda k: self._local_cache[k].last_accessed or self._local_cache[k].created_at
            )
            del self._local_cache[oldest_key]
        
        self._local_cache[key] = CacheEntry(
            value=value,
            created_at=datetime.now(),
            ttl=ttl,
            last_accessed=datetime.now()
        )
    
    async def _update_stats(self, operation: str):
        """更新缓存统计"""
        if not self.redis:
            return
        
        try:
            stats_data = await self.redis.get(self.stats_key)
            stats = json.loads(stats_data) if stats_data else {}
            
            stats[operation] = stats.get(operation, 0) + 1
            stats["last_updated"] = datetime.now().isoformat()
            
            await self.redis.setex(self.stats_key, 86400, json.dumps(stats))
            
        except Exception as e:
            logger.error(f"Failed to update cache stats: {e}")

def cache_result(
    ttl: int = None,
    namespace: str = None,
    key_func: Callable = None
):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 基于函数名和参数生成键
                args_str = "_".join(str(arg) for arg in args)
                kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{func.__name__}_{args_str}_{kwargs_str}"
            
            cache_key = cache._hash_complex_key(cache_key)
            
            # 尝试从缓存获取
            cached_result = await cache.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl, namespace)
            
            return result
        
        return wrapper
    return decorator

# 全局缓存实例
cache = OptimizedRedisCache()

# AI响应缓存专用装饰器
def cache_ai_response(ttl: int = 3600):
    """AI响应缓存装饰器"""
    return cache_result(ttl=ttl, namespace="ai_responses")

# 文档处理结果缓存装饰器
def cache_document_processing(ttl: int = 86400):
    """文档处理结果缓存装饰器"""
    return cache_result(ttl=ttl, namespace="document_processing")
