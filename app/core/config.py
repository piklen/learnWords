from pydantic_settings import BaseSettings
from pydantic import validator
from typing import Optional, List
import secrets

class Settings(BaseSettings):
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 6773
    
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/lesson_planner"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Cloudflare R2 Configuration
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_bucket_name: Optional[str] = None
    r2_account_id: Optional[str] = None
    r2_endpoint_url: Optional[str] = None  # 格式: https://{account_id}.r2.cloudflarestorage.com
    r2_public_domain: Optional[str] = None  # 自定义域名（可选）
    
    # 存储配置
    storage_backend: str = "r2"  # 可选: "r2", "s3", "local"
    
    # AWS S3 Configuration (备用)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_s3_bucket: Optional[str] = None
    
    # AI API Configuration
    # Google Gemini API
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"  # 或 "gemini-1.5-pro"
    gemini_max_tokens: int = 2048
    gemini_temperature: float = 0.7
    
    # OpenAI API (可选)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.7
    
    # Anthropic Claude API (可选)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    anthropic_max_tokens: int = 2000
    anthropic_temperature: float = 0.7
    
    # AI服务提供商选择
    ai_provider: str = "gemini"  # 可选: "gemini", "openai", "anthropic"
    
    # Security
    secret_key: str = secrets.token_urlsafe(32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # App Configuration
    debug: bool = True
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    api_prefix: str = "/api/v1"
    
    # File Upload
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_file_types: List[str] = ["pdf", "png", "jpg", "jpeg"]
    
    # Task Processing
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    max_workers: int = 4
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    
    # Cache Configuration
    cache_ttl: int = 3600  # 1 hour
    
    # WebSocket Configuration
    websocket_ping_interval: int = 20
    websocket_ping_timeout: int = 20
    
    @validator("celery_broker_url", "celery_result_backend", pre=True, always=True)
    def set_celery_urls(cls, v, values):
        if v is None:
            return values.get("redis_url")
        return v
    
    @validator("allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
