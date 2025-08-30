from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Any, List, Dict
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.models.lesson_plan import LessonPlan, LessonPlanStatus

router = APIRouter()

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """检查用户是否为管理员"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户未激活"
        )
    
    # 这里可以添加更复杂的管理员权限检查
    # 例如检查用户角色、权限等
    
    return current_user

@router.get("/dashboard", dependencies=[Depends(require_admin)])
async def get_admin_dashboard(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取管理后台仪表板数据"""
    
    # 用户统计
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    new_users_today = db.query(func.count(User.id)).filter(
        User.created_at >= datetime.utcnow().date()
    ).scalar()
    
    # 文档统计
    total_documents = db.query(func.count(Document.id)).scalar()
    documents_by_status = db.query(
        Document.status,
        func.count(Document.id)
    ).group_by(Document.status).all()
    
    # 教案统计
    total_lesson_plans = db.query(func.count(LessonPlan.id)).scalar()
    lesson_plans_by_status = db.query(
        LessonPlan.status,
        func.count(LessonPlan.id)
    ).group_by(LessonPlan.status).all()
    
    # 最近活动
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    recent_documents = db.query(Document).order_by(Document.created_at.desc()).limit(5).all()
    
    return {
        "timestamp": datetime.utcnow(),
        "users": {
            "total": total_users,
            "active": active_users,
            "new_today": new_users_today,
            "recent": [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "created_at": user.created_at
                }
                for user in recent_users
            ]
        },
        "documents": {
            "total": total_documents,
            "by_status": dict(documents_by_status),
            "recent": [
                {
                    "id": doc.id,
                    "filename": doc.original_filename,
                    "status": doc.status,
                    "created_at": doc.created_at
                }
                for doc in recent_documents
            ]
        },
        "lesson_plans": {
            "total": total_lesson_plans,
            "by_status": dict(lesson_plans_by_status)
        }
    }

@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """获取用户列表（管理员）"""
    
    users = db.query(User).offset(skip).limit(limit).all()
    
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        for user in users
    ]

@router.put("/users/{user_id}/status", dependencies=[Depends(require_admin)])
async def update_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """更新用户状态（管理员）"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )
    
    user.is_active = is_active
    db.commit()
    
    return {
        "message": f"用户状态已更新为 {'激活' if is_active else '停用'}",
        "user_id": user_id,
        "is_active": is_active
    }

@router.get("/documents", dependencies=[Depends(require_admin)])
async def list_all_documents(
    skip: int = 0,
    limit: int = 100,
    status: DocumentStatus = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """获取所有文档列表（管理员）"""
    
    query = db.query(Document)
    if status:
        query = query.filter(Document.status == status)
    
    documents = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": doc.id,
            "user_id": doc.user_id,
            "filename": doc.original_filename,
            "status": doc.status,
            "file_size": doc.file_size,
            "created_at": doc.created_at,
            "processing_error": doc.processing_error
        }
        for doc in documents
    ]

@router.post("/documents/{document_id}/retry", dependencies=[Depends(require_admin)])
async def retry_document_processing(
    document_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """重试文档处理（管理员）"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档未找到"
        )
    
    # 重置状态
    document.status = DocumentStatus.UPLOADED
    document.processing_error = None
    db.commit()
    
    # 重新触发处理
    from app.tasks.document_processing import process_document_task
    process_document_task.delay(document.id)
    
    return {
        "message": "文档处理已重新开始",
        "document_id": document_id
    }

@router.get("/system/health", dependencies=[Depends(require_admin)])
async def get_system_health(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取系统健康状态（管理员）"""
    
    # 数据库连接检查
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Redis连接检查
    try:
        import redis
        r = redis.from_url("redis://localhost:6379")
        r.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    # 系统资源使用
    import psutil
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "timestamp": datetime.utcnow(),
        "services": {
            "database": db_status,
            "redis": redis_status
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent
        }
    }
