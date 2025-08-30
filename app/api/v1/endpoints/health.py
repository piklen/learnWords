from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
import time
from typing import Dict, Any

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """基础健康检查"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """详细健康检查"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "services": {}
    }
    
    # Check database
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        health_status["services"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Check external services
    health_status["services"]["openai"] = {
        "status": "configured" if settings.openai_api_key else "not_configured"
    }
    
    health_status["services"]["aws"] = {
        "status": "configured" if settings.aws_access_key_id else "not_configured"
    }
    
    return health_status

@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """就绪状态检查（用于Kubernetes等）"""
    try:
        # Check database
        db = next(get_db())
        db.execute(text("SELECT 1"))
        
        # Check Redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )

@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """存活状态检查（用于Kubernetes等）"""
    return {"status": "alive"}

@router.get("/metrics")
async def get_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取系统指标（需要认证）"""
    
    # Basic metrics
    metrics = {
        "timestamp": time.time(),
        "system": {
            "debug_mode": settings.debug,
            "max_file_size": settings.max_file_size,
            "max_workers": settings.max_workers
        }
    }
    
    # Database metrics
    try:
        # Count users
        user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        metrics["database"] = {
            "users": user_count
        }
        
        # Count documents
        doc_count = db.execute(text("SELECT COUNT(*) FROM documents")).scalar()
        metrics["database"]["documents"] = doc_count
        
        # Count lesson plans
        lp_count = db.execute(text("SELECT COUNT(*) FROM lesson_plans")).scalar()
        metrics["database"]["lesson_plans"] = lp_count
        
    except Exception as e:
        metrics["database"] = {"error": str(e)}
    
    return metrics
