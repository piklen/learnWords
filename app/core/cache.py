import redis
import json
import pickle
from typing import Any, Optional, Union
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis缓存管理器"""
    
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """连接到Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=False,  # 保持二进制模式以支持pickle
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # 测试连接
            self.redis_client.ping()
            logger.info("✅ Redis缓存连接成功")
        except Exception as e:
            logger.error(f"❌ Redis缓存连接失败: {e}")
            self.redis_client = None
    
    def _serialize(self, value: Any) -> bytes:
        """序列化值"""
        try:
            return pickle.dumps(value)
        except Exception:
            return json.dumps(value, ensure_ascii=False).encode('utf-8')
    
    def _deserialize(self, value: bytes) -> Any:
        """反序列化值"""
        try:
            return pickle.loads(value)
        except Exception:
            try:
                return json.loads(value.decode('utf-8'))
            except Exception:
                return value.decode('utf-8')
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value is not None:
                return self._deserialize(value)
            return None
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        if not self.redis_client:
            return False
        
        try:
            serialized_value = self._serialize(value)
            ttl = ttl or settings.cache_ttl
            return self.redis_client.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"检查缓存键失败 {key}: {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """设置过期时间"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.expire(key, ttl))
        except Exception as e:
            logger.error(f"设置过期时间失败 {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的键"""
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"清除模式缓存失败 {pattern}: {e}")
            return 0
    
    def get_ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        if not self.redis_client:
            return -1
        
        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"获取TTL失败 {key}: {e}")
            return -1

# 全局缓存实例
cache = RedisCache()

# 缓存装饰器
def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存储到缓存
            cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
