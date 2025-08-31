import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import time
from enum import Enum

# AI SDK imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)

class AIProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

@dataclass
class AIResponse:
    """AI响应标准格式"""
    content: str
    provider: str
    model: str
    tokens_used: int
    response_time: float
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class CircuitBreakerState:
    """熔断器状态"""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    status: AIProviderStatus = AIProviderStatus.HEALTHY
    consecutive_successes: int = 0

class CircuitBreaker:
    """AI服务熔断器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState()
    
    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        if self.state.status == AIProviderStatus.HEALTHY:
            return True
        
        if self.state.status == AIProviderStatus.UNAVAILABLE:
            # 检查是否可以尝试恢复
            if (self.state.last_failure_time and 
                datetime.now() - self.state.last_failure_time > timedelta(seconds=self.recovery_timeout)):
                self.state.status = AIProviderStatus.DEGRADED
                return True
            return False
        
        # DEGRADED状态，允许部分请求通过
        return True
    
    def record_success(self):
        """记录成功请求"""
        self.state.consecutive_successes += 1
        self.state.failure_count = 0
        
        if self.state.consecutive_successes >= 3:
            self.state.status = AIProviderStatus.HEALTHY
            self.state.consecutive_successes = 0
    
    def record_failure(self):
        """记录失败请求"""
        self.state.failure_count += 1
        self.state.consecutive_successes = 0
        self.state.last_failure_time = datetime.now()
        
        if self.state.failure_count >= self.failure_threshold:
            self.state.status = AIProviderStatus.UNAVAILABLE

class RetryConfig:
    """重试配置"""
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def get_delay(self, attempt: int) -> float:
        """计算重试延迟（指数退避）"""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)

async def retry_with_backoff(
    func: Callable,
    retry_config: RetryConfig,
    *args,
    **kwargs
) -> Any:
    """带指数退避的重试装饰器"""
    last_exception = None
    
    for attempt in range(retry_config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt == retry_config.max_retries:
                break
            
            delay = retry_config.get_delay(attempt)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
            await asyncio.sleep(delay)
    
    raise last_exception

class OptimizedAIProvider(ABC):
    """优化的AI服务提供商抽象基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.circuit_breaker = CircuitBreaker()
        self.retry_config = RetryConfig()
        self._request_history = []
        self._max_history_size = 100
    
    @abstractmethod
    async def _generate_text_impl(self, prompt: str, **kwargs) -> AIResponse:
        """实际的文本生成实现"""
        pass
    
    async def generate_text(self, prompt: str, **kwargs) -> AIResponse:
        """生成文本内容（带熔断和重试）"""
        if not self.circuit_breaker.can_execute():
            raise Exception(f"AI provider {self.name} is currently unavailable")
        
        start_time = time.time()
        
        try:
            response = await retry_with_backoff(
                self._generate_text_impl,
                self.retry_config,
                prompt,
                **kwargs
            )
            
            self.circuit_breaker.record_success()
            self._record_request(response.response_time, True)
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            self.circuit_breaker.record_failure()
            self._record_request(response_time, False)
            
            # 返回失败响应而不是抛出异常
            return AIResponse(
                content="",
                provider=self.name,
                model="unknown",
                tokens_used=0,
                response_time=response_time,
                success=False,
                error=str(e)
            )
    
    def _record_request(self, response_time: float, success: bool):
        """记录请求历史"""
        self._request_history.append({
            "timestamp": datetime.now(),
            "response_time": response_time,
            "success": success
        })
        
        # 保持历史记录大小
        if len(self._request_history) > self._max_history_size:
            self._request_history.pop(0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        if not self._request_history:
            return {
                "status": self.circuit_breaker.state.status.value,
                "total_requests": 0,
                "success_rate": 0,
                "avg_response_time": 0
            }
        
        recent_requests = [
            req for req in self._request_history
            if datetime.now() - req["timestamp"] < timedelta(minutes=5)
        ]
        
        total_requests = len(recent_requests)
        successful_requests = sum(1 for req in recent_requests if req["success"])
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        avg_response_time = sum(req["response_time"] for req in recent_requests) / total_requests if total_requests > 0 else 0
        
        return {
            "status": self.circuit_breaker.state.status.value,
            "total_requests": total_requests,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "failure_count": self.circuit_breaker.state.failure_count,
            "consecutive_successes": self.circuit_breaker.state.consecutive_successes
        }

class OptimizedGeminiProvider(OptimizedAIProvider):
    """优化的Google Gemini提供商"""
    
    def __init__(self):
        super().__init__("gemini")
        
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai包未安装")
        
        if not settings.gemini_api_key:
            raise ValueError("Gemini API密钥未配置")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.generation_config = genai.types.GenerationConfig(
            max_output_tokens=settings.gemini_max_tokens,
            temperature=settings.gemini_temperature,
        )
        logger.info(f"Optimized Gemini provider initialized: {settings.gemini_model}")
    
    async def _generate_text_impl(self, prompt: str, **kwargs) -> AIResponse:
        """Gemini文本生成实现"""
        start_time = time.time()
        
        # 合并自定义配置
        config = self.generation_config
        if kwargs:
            config_dict = {
                'max_output_tokens': kwargs.get('max_tokens', settings.gemini_max_tokens),
                'temperature': kwargs.get('temperature', settings.gemini_temperature),
            }
            config = genai.types.GenerationConfig(**config_dict)
        
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt,
            generation_config=config
        )
        
        if not response.text:
            raise ValueError("Gemini返回空响应")
        
        response_time = time.time() - start_time
        
        return AIResponse(
            content=response.text.strip(),
            provider="gemini",
            model=settings.gemini_model,
            tokens_used=response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0,
            response_time=response_time,
            success=True
        )

class OptimizedAIService:
    """优化的AI服务管理器"""
    
    def __init__(self):
        self.providers: Dict[str, OptimizedAIProvider] = {}
        self.provider_weights: Dict[str, float] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化AI提供商"""
        # 初始化Gemini
        if GEMINI_AVAILABLE and settings.gemini_api_key:
            try:
                self.providers["gemini"] = OptimizedGeminiProvider()
                self.provider_weights["gemini"] = 1.0
                logger.info("Optimized Gemini provider loaded")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}")
        
        # TODO: 添加其他优化的提供商
        
        if not self.providers:
            logger.error("No AI providers available")
    
    def _select_provider(self, preferred_provider: Optional[str] = None) -> Optional[OptimizedAIProvider]:
        """智能选择AI提供商"""
        if preferred_provider and preferred_provider in self.providers:
            provider = self.providers[preferred_provider]
            if provider.circuit_breaker.can_execute():
                return provider
        
        # 基于权重和健康状态选择提供商
        available_providers = [
            (name, provider) for name, provider in self.providers.items()
            if provider.circuit_breaker.can_execute()
        ]
        
        if not available_providers:
            return None
        
        # 简单策略：选择第一个可用的提供商
        # TODO: 实现更复杂的负载均衡策略
        return available_providers[0][1]
    
    async def generate_text(self, prompt: str, preferred_provider: str = None, **kwargs) -> AIResponse:
        """生成文本内容"""
        provider = self._select_provider(preferred_provider)
        
        if not provider:
            return AIResponse(
                content="",
                provider="none",
                model="none",
                tokens_used=0,
                response_time=0,
                success=False,
                error="No available AI providers"
            )
        
        return await provider.generate_text(prompt, **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        results = {}
        
        for name, provider in self.providers.items():
            try:
                # 使用简单的测试提示词
                test_response = await provider.generate_text("测试", max_tokens=10)
                results[name] = {
                    "status": "healthy" if test_response.success else "unhealthy",
                    "metrics": provider.get_metrics(),
                    "test_response_time": test_response.response_time
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "metrics": provider.get_metrics()
                }
        
        return {
            "providers": results,
            "total_available": len([p for p in results.values() if p.get("status") == "healthy"])
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有提供商的指标"""
        return {
            name: provider.get_metrics()
            for name, provider in self.providers.items()
        }

# 全局优化的AI服务实例
ai_service = OptimizedAIService()
