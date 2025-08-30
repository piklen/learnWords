import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio

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

class AIProvider(ABC):
    """AI服务提供商抽象基类"""
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本内容"""
        pass
    
    @abstractmethod
    async def analyze_document(self, content: str, **kwargs) -> Dict[str, Any]:
        """分析文档内容"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass

class GeminiProvider(AIProvider):
    """Google Gemini API提供商"""
    
    def __init__(self):
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
        logger.info(f"Gemini提供商初始化成功，模型: {settings.gemini_model}")
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """使用Gemini生成文本"""
        try:
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
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini文本生成失败: {str(e)}")
            raise
    
    async def analyze_document(self, content: str, **kwargs) -> Dict[str, Any]:
        """使用Gemini分析文档"""
        analysis_prompt = f"""
        请分析以下文档内容，提取关键信息：

        文档内容：
        {content}

        请提供以下分析：
        1. 主要主题和概念
        2. 内容结构分析
        3. 适合的教学年级
        4. 建议的教学重点
        5. 可能的教学活动

        请以JSON格式返回分析结果。
        """
        
        try:
            response_text = await self.generate_text(analysis_prompt, **kwargs)
            
            # 尝试解析JSON响应
            import json
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # 如果不是JSON格式，返回原始文本
                analysis = {
                    "raw_analysis": response_text,
                    "parsed": False
                }
            
            return {
                "provider": "gemini",
                "model": settings.gemini_model,
                "analysis": analysis,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Gemini文档分析失败: {str(e)}")
            return {
                "provider": "gemini",
                "error": str(e),
                "success": False
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取Gemini模型信息"""
        return {
            "provider": "gemini",
            "model": settings.gemini_model,
            "max_tokens": settings.gemini_max_tokens,
            "temperature": settings.gemini_temperature,
            "available": True
        }

class OpenAIProvider(AIProvider):
    """OpenAI API提供商"""
    
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("openai包未安装")
        
        if not settings.openai_api_key:
            raise ValueError("OpenAI API密钥未配置")
        
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        logger.info(f"OpenAI提供商初始化成功，模型: {settings.openai_model}")
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """使用OpenAI生成文本"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get('max_tokens', settings.openai_max_tokens),
                temperature=kwargs.get('temperature', settings.openai_temperature)
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("OpenAI返回空响应")
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI文本生成失败: {str(e)}")
            raise
    
    async def analyze_document(self, content: str, **kwargs) -> Dict[str, Any]:
        """使用OpenAI分析文档"""
        analysis_prompt = f"""
        请分析以下文档内容，提取关键信息：

        文档内容：
        {content}

        请提供以下分析：
        1. 主要主题和概念
        2. 内容结构分析
        3. 适合的教学年级
        4. 建议的教学重点
        5. 可能的教学活动

        请以JSON格式返回分析结果。
        """
        
        try:
            response_text = await self.generate_text(analysis_prompt, **kwargs)
            
            import json
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                analysis = {
                    "raw_analysis": response_text,
                    "parsed": False
                }
            
            return {
                "provider": "openai",
                "model": settings.openai_model,
                "analysis": analysis,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"OpenAI文档分析失败: {str(e)}")
            return {
                "provider": "openai",
                "error": str(e),
                "success": False
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取OpenAI模型信息"""
        return {
            "provider": "openai",
            "model": settings.openai_model,
            "max_tokens": settings.openai_max_tokens,
            "temperature": settings.openai_temperature,
            "available": True
        }

class AnthropicProvider(AIProvider):
    """Anthropic Claude API提供商"""
    
    def __init__(self):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic包未安装")
        
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API密钥未配置")
        
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        logger.info(f"Anthropic提供商初始化成功，模型: {settings.anthropic_model}")
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """使用Claude生成文本"""
        try:
            response = await self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=kwargs.get('max_tokens', settings.anthropic_max_tokens),
                temperature=kwargs.get('temperature', settings.anthropic_temperature),
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response.content or not response.content[0].text:
                raise ValueError("Anthropic返回空响应")
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Anthropic文本生成失败: {str(e)}")
            raise
    
    async def analyze_document(self, content: str, **kwargs) -> Dict[str, Any]:
        """使用Claude分析文档"""
        analysis_prompt = f"""
        请分析以下文档内容，提取关键信息：

        文档内容：
        {content}

        请提供以下分析：
        1. 主要主题和概念
        2. 内容结构分析
        3. 适合的教学年级
        4. 建议的教学重点
        5. 可能的教学活动

        请以JSON格式返回分析结果。
        """
        
        try:
            response_text = await self.generate_text(analysis_prompt, **kwargs)
            
            import json
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                analysis = {
                    "raw_analysis": response_text,
                    "parsed": False
                }
            
            return {
                "provider": "anthropic",
                "model": settings.anthropic_model,
                "analysis": analysis,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Anthropic文档分析失败: {str(e)}")
            return {
                "provider": "anthropic",
                "error": str(e),
                "success": False
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取Anthropic模型信息"""
        return {
            "provider": "anthropic",
            "model": settings.anthropic_model,
            "max_tokens": settings.anthropic_max_tokens,
            "temperature": settings.anthropic_temperature,
            "available": True
        }

class AIService:
    """统一AI服务管理器"""
    
    def __init__(self):
        self.providers: Dict[str, AIProvider] = {}
        self.current_provider: Optional[AIProvider] = None
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化可用的AI提供商"""
        # 尝试初始化Gemini
        if GEMINI_AVAILABLE and settings.gemini_api_key:
            try:
                self.providers["gemini"] = GeminiProvider()
                logger.info("Gemini提供商已加载")
            except Exception as e:
                logger.warning(f"Gemini提供商初始化失败: {str(e)}")
        
        # 尝试初始化OpenAI
        if OPENAI_AVAILABLE and settings.openai_api_key:
            try:
                self.providers["openai"] = OpenAIProvider()
                logger.info("OpenAI提供商已加载")
            except Exception as e:
                logger.warning(f"OpenAI提供商初始化失败: {str(e)}")
        
        # 尝试初始化Anthropic
        if ANTHROPIC_AVAILABLE and settings.anthropic_api_key:
            try:
                self.providers["anthropic"] = AnthropicProvider()
                logger.info("Anthropic提供商已加载")
            except Exception as e:
                logger.warning(f"Anthropic提供商初始化失败: {str(e)}")
        
        # 设置当前提供商
        if settings.ai_provider in self.providers:
            self.current_provider = self.providers[settings.ai_provider]
            logger.info(f"当前AI提供商: {settings.ai_provider}")
        elif self.providers:
            # 如果配置的提供商不可用，使用第一个可用的
            provider_name = list(self.providers.keys())[0]
            self.current_provider = self.providers[provider_name]
            logger.warning(f"配置的提供商不可用，使用: {provider_name}")
        else:
            logger.error("没有可用的AI提供商")
    
    def get_available_providers(self) -> List[str]:
        """获取可用的提供商列表"""
        return list(self.providers.keys())
    
    def switch_provider(self, provider_name: str) -> bool:
        """切换AI提供商"""
        if provider_name in self.providers:
            self.current_provider = self.providers[provider_name]
            logger.info(f"已切换到提供商: {provider_name}")
            return True
        else:
            logger.error(f"提供商不可用: {provider_name}")
            return False
    
    async def generate_text(self, prompt: str, provider: str = None, **kwargs) -> str:
        """生成文本内容"""
        if provider and provider in self.providers:
            selected_provider = self.providers[provider]
        else:
            selected_provider = self.current_provider
        
        if not selected_provider:
            raise ValueError("没有可用的AI提供商")
        
        return await selected_provider.generate_text(prompt, **kwargs)
    
    async def analyze_document(self, content: str, provider: str = None, **kwargs) -> Dict[str, Any]:
        """分析文档内容"""
        if provider and provider in self.providers:
            selected_provider = self.providers[provider]
        else:
            selected_provider = self.current_provider
        
        if not selected_provider:
            raise ValueError("没有可用的AI提供商")
        
        return await selected_provider.analyze_document(content, **kwargs)
    
    def get_provider_info(self, provider_name: str = None) -> Dict[str, Any]:
        """获取提供商信息"""
        if provider_name:
            if provider_name in self.providers:
                return self.providers[provider_name].get_model_info()
            else:
                return {"provider": provider_name, "available": False, "error": "提供商不可用"}
        else:
            # 返回所有提供商信息
            info = {}
            for name, provider in self.providers.items():
                info[name] = provider.get_model_info()
            
            # 添加不可用的提供商信息
            all_providers = ["gemini", "openai", "anthropic"]
            for provider in all_providers:
                if provider not in info:
                    info[provider] = {
                        "provider": provider,
                        "available": False,
                        "error": "未配置或依赖包未安装"
                    }
            
            return info
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        results = {}
        
        for name, provider in self.providers.items():
            try:
                # 使用简单的提示词测试
                test_prompt = "请回答：1+1等于几？"
                response = await provider.generate_text(test_prompt, max_tokens=50)
                results[name] = {
                    "status": "healthy",
                    "response_length": len(response),
                    "model_info": provider.get_model_info()
                }
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "model_info": provider.get_model_info()
                }
        
        return {
            "current_provider": settings.ai_provider,
            "providers": results,
            "total_available": len(self.providers)
        }

# 全局AI服务实例
ai_service = AIService()
