from pydantic_settings import BaseSettings
from pydantic import validator, Field
from typing import Optional, List, Dict, Any
import secrets
import os
from functools import lru_cache

class DatabaseSettings(BaseSettings):
    """数据库配置"""
    # 主数据库
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/lesson_planner",
        description="主数据库连接URL"
    )
    
    # 读副本数据库（可选）
    read_replica_database_url: Optional[str] = Field(
        default=None,
        description="读副本数据库连接URL"
    )
    
    # 连接池配置
    db_pool_size: int = Field(default=20, ge=5, le=100)
    db_max_overflow: int = Field(default=30, ge=10, le=200)
    db_pool_recycle: int = Field(default=3600, ge=300, le=7200)
    db_pool_timeout: int = Field(default=30, ge=5, le=60)
    
    # 查询超时
    db_statement_timeout: int = Field(default=30, ge=5, le=300)
    db_lock_timeout: int = Field(default=10, ge=1, le=60)

class RedisSettings(BaseSettings):
    """Redis配置"""
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis连接URL"
    )
    
    # Redis连接池配置
    redis_pool_size: int = Field(default=20, ge=5, le=100)
    redis_timeout: int = Field(default=5, ge=1, le=30)
    redis_retry_on_timeout: bool = True
    
    # 密码（生产环境）
    redis_password: Optional[str] = None

class AISettings(BaseSettings):
    """AI服务配置"""
    # 主要AI提供商
    ai_provider: str = Field(default="gemini", description="主要AI服务提供商")
    
    # Google Gemini
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    gemini_max_tokens: int = Field(default=2048, ge=100, le=8192)
    gemini_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    gemini_timeout: int = Field(default=60, ge=10, le=300)
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_max_tokens: int = Field(default=2000, ge=100, le=4000)
    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    openai_timeout: int = Field(default=60, ge=10, le=300)
    
    # Anthropic Claude
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    anthropic_max_tokens: int = Field(default=2000, ge=100, le=4000)
    anthropic_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    anthropic_timeout: int = Field(default=60, ge=10, le=300)
    
    # AI服务容错配置
    ai_retry_attempts: int = Field(default=3, ge=1, le=10)
    ai_retry_delay: float = Field(default=1.0, ge=0.1, le=10.0)
    ai_circuit_breaker_threshold: int = Field(default=5, ge=1, le=20)
    ai_circuit_breaker_timeout: int = Field(default=60, ge=30, le=300)

class StorageSettings(BaseSettings):
    """存储配置"""
    storage_backend: str = Field(default="r2", description="存储后端类型")
    
    # Cloudflare R2
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_bucket_name: Optional[str] = None
    r2_account_id: Optional[str] = None
    r2_endpoint_url: Optional[str] = None
    r2_public_domain: Optional[str] = None
    
    # AWS S3
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_s3_bucket: Optional[str] = None
    
    # 本地存储
    local_storage_path: str = "uploads"
    
    # 文件上传限制
    max_file_size: int = Field(default=50 * 1024 * 1024, ge=1024*1024, le=500*1024*1024)
    allowed_file_types: List[str] = ["pdf", "png", "jpg", "jpeg", "docx", "txt"]

class SecuritySettings(BaseSettings):
    """安全配置"""
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    
    # 密码策略
    password_min_length: int = Field(default=8, ge=6, le=128)
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_special: bool = False
    
    # 会话配置
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "strict"

class CacheSettings(BaseSettings):
    """缓存配置"""
    cache_ttl: int = Field(default=3600, ge=60, le=86400)
    cache_max_local_size: int = Field(default=1000, ge=100, le=10000)
    
    # 缓存策略
    ai_response_cache_ttl: int = Field(default=3600, ge=300, le=86400)
    document_processing_cache_ttl: int = Field(default=86400, ge=3600, le=604800)
    user_session_cache_ttl: int = Field(default=1800, ge=300, le=7200)

class TaskSettings(BaseSettings):
    """任务处理配置"""
    # Celery配置
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    
    # Worker配置
    worker_concurrency: int = Field(default=2, ge=1, le=20)
    max_workers: int = Field(default=4, ge=1, le=50)
    
    # 任务超时
    task_time_limit: int = Field(default=1800, ge=300, le=7200)  # 30分钟
    task_soft_time_limit: int = Field(default=1500, ge=240, le=6600)  # 25分钟
    
    # 重试配置
    task_max_retries: int = Field(default=3, ge=0, le=10)
    task_default_retry_delay: int = Field(default=60, ge=10, le=300)

class MonitoringSettings(BaseSettings):
    """监控配置"""
    enable_metrics: bool = True
    metrics_collection_interval: int = Field(default=60, ge=10, le=300)
    metrics_retention_hours: int = Field(default=24, ge=1, le=168)
    
    # 告警阈值
    cpu_warning_threshold: float = Field(default=80.0, ge=50.0, le=95.0)
    cpu_critical_threshold: float = Field(default=90.0, ge=60.0, le=99.0)
    memory_warning_threshold: float = Field(default=80.0, ge=50.0, le=95.0)
    memory_critical_threshold: float = Field(default=90.0, ge=60.0, le=99.0)
    disk_warning_threshold: float = Field(default=85.0, ge=50.0, le=95.0)
    disk_critical_threshold: float = Field(default=95.0, ge=60.0, le=99.0)
    
    # 性能阈值
    response_time_warning: float = Field(default=2.0, ge=0.5, le=10.0)
    response_time_critical: float = Field(default=5.0, ge=1.0, le=30.0)
    error_rate_warning: float = Field(default=0.05, ge=0.01, le=0.5)
    error_rate_critical: float = Field(default=0.1, ge=0.02, le=0.8)

class ServerSettings(BaseSettings):
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = Field(default=18773, ge=1000, le=65535)
    
    # 环境配置
    debug: bool = False
    environment: str = Field(default="development", description="运行环境")
    
    # 网络配置
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    api_prefix: str = "/api/v1"
    
    # 限流配置
    rate_limit_per_minute: int = Field(default=100, ge=10, le=10000)
    rate_limit_burst: int = Field(default=200, ge=20, le=20000)
    
    # WebSocket配置
    websocket_ping_interval: int = Field(default=20, ge=5, le=120)
    websocket_ping_timeout: int = Field(default=20, ge=5, le=60)
    websocket_max_connections: int = Field(default=1000, ge=10, le=10000)

class OptimizedSettings(BaseSettings):
    """优化的配置管理"""
    
    # 子配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    ai: AISettings = Field(default_factory=AISettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    tasks: TaskSettings = Field(default_factory=TaskSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_nested_delimiter = "__"
        
        # 环境变量映射
        fields = {
            # 数据库
            "database.database_url": {"env": "DATABASE_URL"},
            "database.read_replica_database_url": {"env": "READ_REPLICA_DATABASE_URL"},
            
            # Redis
            "redis.redis_url": {"env": "REDIS_URL"},
            "redis.redis_password": {"env": "REDIS_PASSWORD"},
            
            # AI配置
            "ai.ai_provider": {"env": "AI_PROVIDER"},
            "ai.gemini_api_key": {"env": "GEMINI_API_KEY"},
            "ai.gemini_model": {"env": "GEMINI_MODEL"},
            "ai.openai_api_key": {"env": "OPENAI_API_KEY"},
            "ai.anthropic_api_key": {"env": "ANTHROPIC_API_KEY"},
            
            # 存储
            "storage.storage_backend": {"env": "STORAGE_BACKEND"},
            "storage.r2_access_key_id": {"env": "R2_ACCESS_KEY_ID"},
            "storage.r2_secret_access_key": {"env": "R2_SECRET_ACCESS_KEY"},
            "storage.r2_bucket_name": {"env": "R2_BUCKET_NAME"},
            "storage.r2_account_id": {"env": "R2_ACCOUNT_ID"},
            
            # 安全
            "security.secret_key": {"env": "SECRET_KEY"},
            
            # 服务器
            "server.host": {"env": "HOST"},
            "server.port": {"env": "PORT"},
            "server.debug": {"env": "DEBUG"},
            "server.environment": {"env": "ENVIRONMENT"},
        }
    
    @validator("server.allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("storage.allowed_file_types", pre=True)
    def parse_allowed_file_types(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @validator("tasks.celery_broker_url", "tasks.celery_result_backend", pre=True, always=True)
    def set_celery_urls(cls, v, values):
        if v is None:
            redis_settings = values.get("redis", RedisSettings())
            return redis_settings.redis_url
        return v
    
    def get_database_url(self, use_read_replica: bool = False) -> str:
        """获取数据库连接URL"""
        if use_read_replica and self.database.read_replica_database_url:
            return self.database.read_replica_database_url
        return self.database.database_url
    
    def get_ai_config(self, provider: str = None) -> Dict[str, Any]:
        """获取AI服务配置"""
        provider = provider or self.ai.ai_provider
        
        if provider == "gemini":
            return {
                "api_key": self.ai.gemini_api_key,
                "model": self.ai.gemini_model,
                "max_tokens": self.ai.gemini_max_tokens,
                "temperature": self.ai.gemini_temperature,
                "timeout": self.ai.gemini_timeout
            }
        elif provider == "openai":
            return {
                "api_key": self.ai.openai_api_key,
                "model": self.ai.openai_model,
                "max_tokens": self.ai.openai_max_tokens,
                "temperature": self.ai.openai_temperature,
                "timeout": self.ai.openai_timeout
            }
        elif provider == "anthropic":
            return {
                "api_key": self.ai.anthropic_api_key,
                "model": self.ai.anthropic_model,
                "max_tokens": self.ai.anthropic_max_tokens,
                "temperature": self.ai.anthropic_temperature,
                "timeout": self.ai.anthropic_timeout
            }
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置"""
        if self.storage.storage_backend == "r2":
            return {
                "backend": "r2",
                "access_key_id": self.storage.r2_access_key_id,
                "secret_access_key": self.storage.r2_secret_access_key,
                "bucket_name": self.storage.r2_bucket_name,
                "account_id": self.storage.r2_account_id,
                "endpoint_url": self.storage.r2_endpoint_url,
                "public_domain": self.storage.r2_public_domain
            }
        elif self.storage.storage_backend == "s3":
            return {
                "backend": "s3",
                "access_key_id": self.storage.aws_access_key_id,
                "secret_access_key": self.storage.aws_secret_access_key,
                "bucket_name": self.storage.aws_s3_bucket,
                "region": self.storage.aws_region
            }
        else:
            return {
                "backend": "local",
                "storage_path": self.storage.local_storage_path
            }
    
    def is_production(self) -> bool:
        """检查是否为生产环境"""
        return self.server.environment.lower() == "production"
    
    def validate_required_settings(self) -> List[str]:
        """验证必需的配置项"""
        missing = []
        
        # 检查AI配置
        if self.ai.ai_provider == "gemini" and not self.ai.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        elif self.ai.ai_provider == "openai" and not self.ai.openai_api_key:
            missing.append("OPENAI_API_KEY")
        elif self.ai.ai_provider == "anthropic" and not self.ai.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        
        # 检查存储配置
        if self.storage.storage_backend == "r2":
            if not all([self.storage.r2_access_key_id, self.storage.r2_secret_access_key,
                       self.storage.r2_bucket_name, self.storage.r2_account_id]):
                missing.append("R2 storage configuration")
        elif self.storage.storage_backend == "s3":
            if not all([self.storage.aws_access_key_id, self.storage.aws_secret_access_key,
                       self.storage.aws_s3_bucket]):
                missing.append("S3 storage configuration")
        
        # 生产环境检查
        if self.is_production():
            if self.security.secret_key == secrets.token_urlsafe(32):
                missing.append("SECRET_KEY (production)")
        
        return missing

@lru_cache()
def get_settings() -> OptimizedSettings:
    """获取配置实例（缓存）"""
    return OptimizedSettings()

# 全局配置实例
settings = get_settings()

# 向后兼容的旧设置属性
# 这样可以平滑迁移现有代码
def __getattr__(name: str):
    """向后兼容的属性访问"""
    setting_mappings = {
        # 数据库
        "database_url": settings.database.database_url,
        
        # Redis
        "redis_url": settings.redis.redis_url,
        
        # AI
        "gemini_api_key": settings.ai.gemini_api_key,
        "gemini_model": settings.ai.gemini_model,
        "gemini_max_tokens": settings.ai.gemini_max_tokens,
        "gemini_temperature": settings.ai.gemini_temperature,
        "openai_api_key": settings.ai.openai_api_key,
        "anthropic_api_key": settings.ai.anthropic_api_key,
        "ai_provider": settings.ai.ai_provider,
        
        # 存储
        "storage_backend": settings.storage.storage_backend,
        "r2_access_key_id": settings.storage.r2_access_key_id,
        "r2_secret_access_key": settings.storage.r2_secret_access_key,
        "r2_bucket_name": settings.storage.r2_bucket_name,
        "r2_account_id": settings.storage.r2_account_id,
        "max_file_size": settings.storage.max_file_size,
        "allowed_file_types": settings.storage.allowed_file_types,
        
        # 安全
        "secret_key": settings.security.secret_key,
        "access_token_expire_minutes": settings.security.access_token_expire_minutes,
        
        # 服务器
        "host": settings.server.host,
        "port": settings.server.port,
        "debug": settings.server.debug,
        "allowed_hosts": settings.server.allowed_hosts,
        "api_prefix": settings.server.api_prefix,
        
        # 缓存
        "cache_ttl": settings.cache.cache_ttl,
        
        # 其他
        "max_workers": settings.tasks.max_workers,
        "rate_limit_per_minute": settings.server.rate_limit_per_minute,
        "websocket_ping_interval": settings.server.websocket_ping_interval,
        "websocket_ping_timeout": settings.server.websocket_ping_timeout,
    }
    
    if name in setting_mappings:
        return setting_mappings[name]
    
    raise AttributeError(f"'{__name__}' has no attribute '{name}'")
