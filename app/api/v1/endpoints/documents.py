from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
import os
import uuid
import asyncio
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.cache import cache
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse, DocumentList
from app.services.export_service import ExportService
from app.tasks.document_processing import process_document_task
from app.api.v1.endpoints.websocket import manager

logger = logging.getLogger(__name__)
router = APIRouter()

# 文件上传进度跟踪
upload_progress = {}

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传文档"""
    try:
        # 验证文件类型
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in settings.allowed_file_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_extension}。支持的类型: {', '.join(settings.allowed_file_types)}"
            )
        
        # 验证文件大小
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制: {file.size / (1024*1024):.1f}MB > {settings.max_file_size / (1024*1024):.1f}MB"
            )
        
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"{file_id}.{file_extension}"
        
        # 确保上传目录存在
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, unique_filename)
        
        # 创建文档记录
        document_data = DocumentCreate(
            title=title,
            description=description or "",
            file_path=file_path,
            file_name=file.filename,
            file_size=file.size or 0,
            file_type=file_extension,
            tags=tags.split(',') if tags else [],
            user_id=current_user.id
        )
        
        # 保存到数据库
        document = Document(**document_data.dict())
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # 初始化上传进度
        upload_progress[file_id] = {
            "status": "uploading",
            "progress": 0,
            "document_id": document.id,
            "user_id": str(current_user.id),
            "start_time": datetime.now().isoformat()
        }
        
        # 异步保存文件
        background_tasks.add_task(
            save_uploaded_file,
            file,
            file_path,
            file_id,
            document.id,
            str(current_user.id)
        )
        
        # 启动文档处理任务
        background_tasks.add_task(
            process_document_task.delay,
            document.id
        )
        
        logger.info(f"文档上传开始: {document.id}, 文件: {file.filename}")
        
        return DocumentResponse.from_orm(document)
        
    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")

async def save_uploaded_file(
    file: UploadFile,
    file_path: str,
    file_id: str,
    document_id: int,
    user_id: str
):
    """异步保存上传的文件"""
    try:
        chunk_size = 1024 * 1024  # 1MB chunks
        total_size = file.size or 0
        uploaded_size = 0
        
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                buffer.write(chunk)
                uploaded_size += len(chunk)
                
                # 更新进度
                if total_size > 0:
                    progress = int((uploaded_size / total_size) * 100)
                    upload_progress[file_id]["progress"] = progress
                    
                    # 通过WebSocket发送进度更新
                    await manager.send_to_user(user_id, {
                        "type": "file_progress",
                        "file_id": file_id,
                        "document_id": document_id,
                        "progress": progress,
                        "status": "uploading",
                        "uploaded_size": uploaded_size,
                        "total_size": total_size,
                        "timestamp": datetime.now().isoformat()
                    })
        
        # 上传完成
        upload_progress[file_id]["status"] = "completed"
        upload_progress[file_id]["progress"] = 100
        upload_progress[file_id]["completed_time"] = datetime.now().isoformat()
        
        # 发送完成通知
        await manager.send_to_user(user_id, {
            "type": "file_progress",
            "file_id": file_id,
            "document_id": document_id,
            "progress": 100,
            "status": "completed",
            "message": "文件上传完成",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"文件保存完成: {file_path}")
        
    except Exception as e:
        # 上传失败
        upload_progress[file_id]["status"] = "failed"
        upload_progress[file_id]["error"] = str(e)
        
        # 发送错误通知
        await manager.send_to_user(user_id, {
            "type": "file_progress",
            "file_id": file_id,
            "document_id": document_id,
            "progress": 0,
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        
        logger.error(f"文件保存失败: {e}")

@router.get("/upload/progress/{file_id}")
async def get_upload_progress(file_id: str):
    """获取文件上传进度"""
    if file_id not in upload_progress:
        raise HTTPException(status_code=404, detail="文件ID不存在")
    
    return upload_progress[file_id]

@router.get("/upload/progress")
async def get_all_upload_progress(current_user: User = Depends(get_current_user)):
    """获取当前用户的所有上传进度"""
    user_progress = {}
    for file_id, progress in upload_progress.items():
        if progress.get("user_id") == str(current_user.id):
            user_progress[file_id] = progress
    
    return user_progress

@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    tags: Optional[str] = None,
    file_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文档列表（支持搜索和过滤）"""
    try:
        query = db.query(Document).filter(Document.user_id == current_user.id)
        
        # 搜索功能
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (Document.title.ilike(search_filter)) |
                (Document.description.ilike(search_filter)) |
                (Document.tags.any(lambda tag: tag.ilike(search_filter)))
            )
        
        # 标签过滤
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            for tag in tag_list:
                query = query.filter(Document.tags.any(lambda t: t.ilike(f"%{tag}%")))
        
        # 文件类型过滤
        if file_type:
            query = query.filter(Document.file_type == file_type)
        
        # 分页
        total = query.count()
        documents = query.offset(skip).limit(limit).all()
        
        # 缓存结果
        cache_key = f"documents:user:{current_user.id}:search:{search}:tags:{tags}:type:{file_type}:skip:{skip}:limit:{limit}"
        cache.set(cache_key, {
            "documents": [doc.to_dict() for doc in documents],
            "total": total,
            "timestamp": datetime.now().isoformat()
        }, ttl=300)
        
        return documents
        
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个文档"""
    try:
        # 尝试从缓存获取
        cache_key = f"document:{document_id}:user:{current_user.id}"
        cached_doc = cache.get(cache_key)
        
        if cached_doc:
            return DocumentResponse(**cached_doc)
        
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 缓存结果
        cache.set(cache_key, document.to_dict(), ttl=600)
        
        return DocumentResponse.from_orm(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文档失败: {str(e)}")

@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新文档"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 更新字段
        for field, value in document_update.dict(exclude_unset=True).items():
            setattr(document, field, value)
        
        document.updated_at = datetime.now()
        db.commit()
        db.refresh(document)
        
        # 清除相关缓存
        cache.clear_pattern(f"document:{document_id}:*")
        cache.clear_pattern(f"documents:user:{current_user.id}:*")
        
        return DocumentResponse.from_orm(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新文档失败: {str(e)}")

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除文档"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 删除物理文件
        if document.file_path and os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # 删除数据库记录
        db.delete(document)
        db.commit()
        
        # 清除相关缓存
        cache.clear_pattern(f"document:{document_id}:*")
        cache.clear_pattern(f"documents:user:{current_user.id}:*")
        
        return {"message": "文档删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")

@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载文档"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        if not os.path.exists(document.file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        def file_generator():
            with open(document.file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        return StreamingResponse(
            file_generator(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={document.file_name}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载文档失败: {str(e)}")

@router.get("/stats/summary")
async def get_document_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取文档统计信息"""
    try:
        # 尝试从缓存获取
        cache_key = f"stats:user:{current_user.id}"
        cached_stats = cache.get(cache_key)
        
        if cached_stats:
            return cached_stats
        
        # 计算统计信息
        total_documents = db.query(Document).filter(Document.user_id == current_user.id).count()
        
        # 按文件类型统计
        type_stats = db.query(Document.file_type, db.func.count(Document.id)).filter(
            Document.user_id == current_user.id
        ).group_by(Document.file_type).all()
        
        # 按标签统计
        tag_stats = {}
        documents = db.query(Document).filter(Document.user_id == current_user.id).all()
        for doc in documents:
            for tag in doc.tags:
                tag_stats[tag] = tag_stats.get(tag, 0) + 1
        
        # 总文件大小
        total_size = sum(doc.file_size for doc in documents)
        
        stats = {
            "total_documents": total_documents,
            "total_size": total_size,
            "file_types": dict(type_stats),
            "top_tags": dict(sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)[:10]),
            "last_updated": datetime.now().isoformat()
        }
        
        # 缓存结果
        cache.set(cache_key, stats, ttl=1800)  # 30分钟
        
        return stats
        
    except Exception as e:
        logger.error(f"获取文档统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文档统计失败: {str(e)}")
