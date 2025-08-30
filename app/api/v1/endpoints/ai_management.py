from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.services.ai_service import ai_service
from app.api.v1.endpoints.auth import get_current_user
from app.schemas.user import User

router = APIRouter()

class ProviderSwitchRequest(BaseModel):
    provider: str

class TextGenerationRequest(BaseModel):
    prompt: str
    provider: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

class DocumentAnalysisRequest(BaseModel):
    content: str
    provider: Optional[str] = None

@router.get("/providers", response_model=Dict[str, Any])
async def get_providers(current_user: User = Depends(get_current_user)):
    """获取所有AI提供商信息"""
    try:
        return ai_service.get_provider_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商信息失败: {str(e)}")

@router.get("/providers/available", response_model=List[str])
async def get_available_providers(current_user: User = Depends(get_current_user)):
    """获取可用的AI提供商列表"""
    try:
        return ai_service.get_available_providers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取可用提供商失败: {str(e)}")

@router.post("/providers/switch")
async def switch_provider(
    request: ProviderSwitchRequest,
    current_user: User = Depends(get_current_user)
):
    """切换AI提供商"""
    try:
        success = ai_service.switch_provider(request.provider)
        if not success:
            raise HTTPException(status_code=400, detail=f"提供商不可用: {request.provider}")
        
        return {
            "message": f"已切换到提供商: {request.provider}",
            "current_provider": request.provider,
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换提供商失败: {str(e)}")

@router.post("/generate", response_model=Dict[str, Any])
async def generate_text(
    request: TextGenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """使用AI生成文本"""
    try:
        kwargs = {}
        if request.max_tokens:
            kwargs['max_tokens'] = request.max_tokens
        if request.temperature is not None:
            kwargs['temperature'] = request.temperature
        
        response = await ai_service.generate_text(
            request.prompt,
            provider=request.provider,
            **kwargs
        )
        
        return {
            "text": response,
            "provider": request.provider or ai_service.current_provider.__class__.__name__.lower().replace('provider', ''),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本生成失败: {str(e)}")

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_document(
    request: DocumentAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """使用AI分析文档内容"""
    try:
        result = await ai_service.analyze_document(
            request.content,
            provider=request.provider
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档分析失败: {str(e)}")

@router.get("/health", response_model=Dict[str, Any])
async def health_check(current_user: User = Depends(get_current_user)):
    """AI服务健康检查"""
    try:
        return await ai_service.health_check()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")

@router.get("/models", response_model=Dict[str, Any])
async def get_model_info(current_user: User = Depends(get_current_user)):
    """获取当前使用的模型信息"""
    try:
        if not ai_service.current_provider:
            raise HTTPException(status_code=404, detail="没有可用的AI提供商")
        
        return ai_service.current_provider.get_model_info()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型信息失败: {str(e)}")
