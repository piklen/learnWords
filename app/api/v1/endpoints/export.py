from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
import logging
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.cache import cache
from app.models.user import User
from app.models.document import Document
from app.models.lesson_plan import LessonPlan
from app.schemas.document import DocumentResponse
from app.schemas.lesson_plan import LessonPlanResponse
from app.services.export_service import export_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/formats")
async def get_supported_formats():
    """获取支持的导出格式"""
    return {
        "supported_formats": export_service.get_supported_formats(),
        "description": "支持的导出格式包括JSON、CSV、XML、PDF、Word和ZIP"
    }

@router.get("/documents")
async def export_documents(
    format: str = Query(..., description="导出格式"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    tags: Optional[str] = Query(None, description="标签过滤"),
    file_type: Optional[str] = Query(None, description="文件类型过滤"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """导出文档"""
    try:
        # 验证导出格式
        if not export_service.validate_export_format(format):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的导出格式: {format}。支持的格式: {', '.join(export_service.get_supported_formats())}"
            )
        
        # 构建查询
        query = db.query(Document).filter(Document.user_id == current_user.id)
        
        # 应用过滤条件
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (Document.title.ilike(search_filter)) |
                (Document.description.ilike(search_filter)) |
                (Document.tags.any(lambda tag: tag.ilike(search_filter)))
            )
        
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            for tag in tag_list:
                query = query.filter(Document.tags.any(lambda t: t.ilike(f"%{tag}%")))
        
        if file_type:
            query = query.filter(Document.file_type == file_type)
        
        # 获取文档
        documents = query.all()
        
        if not documents:
            raise HTTPException(status_code=404, detail="没有找到符合条件的文档")
        
        # 转换为字典格式
        documents_data = []
        for doc in documents:
            doc_dict = doc.to_dict()
            # 处理特殊字段
            if "created_at" in doc_dict and doc_dict["created_at"]:
                doc_dict["created_at"] = doc_dict["created_at"].isoformat()
            if "updated_at" in doc_dict and doc_dict["updated_at"]:
                doc_dict["updated_at"] = doc_dict["updated_at"].isoformat()
            documents_data.append(doc_dict)
        
        # 导出数据
        export_data = export_service.export_documents(documents_data, format)
        
        # 生成文件名
        filename = export_service.get_export_filename(format, f"documents_{len(documents)}")
        
        # 设置MIME类型
        mime_types = {
            "json": "application/json",
            "csv": "text/csv",
            "xml": "application/xml",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "zip": "application/zip"
        }
        
        # 记录导出日志
        logger.info(f"用户 {current_user.id} 导出了 {len(documents)} 个文档，格式: {format}")
        
        # 清除相关缓存
        cache.clear_pattern(f"documents:user:{current_user.id}:*")
        
        return StreamingResponse(
            iter([export_data]),
            media_type=mime_types.get(format, "application/octet-stream"),
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

@router.get("/lesson-plans")
async def export_lesson_plans(
    format: str = Query(..., description="导出格式"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    subject: Optional[str] = Query(None, description="学科过滤"),
    grade_level: Optional[str] = Query(None, description="年级过滤"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """导出教案"""
    try:
        # 验证导出格式
        if not export_service.validate_export_format(format):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的导出格式: {format}。支持的格式: {', '.join(export_service.get_supported_formats())}"
            )
        
        # 构建查询
        query = db.query(LessonPlan).filter(LessonPlan.user_id == current_user.id)
        
        # 应用过滤条件
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (LessonPlan.title.ilike(search_filter)) |
                (LessonPlan.content.ilike(search_filter)) |
                (LessonPlan.learning_objectives.ilike(search_filter))
            )
        
        if subject:
            query = query.filter(LessonPlan.subject == subject)
        
        if grade_level:
            query = query.filter(LessonPlan.grade_level == grade_level)
        
        # 获取教案
        lesson_plans = query.all()
        
        if not lesson_plans:
            raise HTTPException(status_code=404, detail="没有找到符合条件的教案")
        
        # 转换为字典格式
        lesson_plans_data = []
        for plan in lesson_plans:
            plan_dict = plan.to_dict()
            # 处理特殊字段
            if "created_at" in plan_dict and plan_dict["created_at"]:
                plan_dict["created_at"] = plan_dict["created_at"].isoformat()
            if "updated_at" in plan_dict and plan_dict["updated_at"]:
                plan_dict["updated_at"] = plan_dict["updated_at"].isoformat()
            lesson_plans_data.append(plan_dict)
        
        # 导出数据
        export_data = export_service.export_lesson_plans(lesson_plans_data, format)
        
        # 生成文件名
        filename = export_service.get_export_filename(format, f"lesson_plans_{len(lesson_plans)}")
        
        # 设置MIME类型
        mime_types = {
            "json": "application/json",
            "csv": "text/csv",
            "xml": "application/xml",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "zip": "application/zip"
        }
        
        # 记录导出日志
        logger.info(f"用户 {current_user.id} 导出了 {len(lesson_plans)} 个教案，格式: {format}")
        
        # 清除相关缓存
        cache.clear_pattern(f"lesson_plans:user:{current_user.id}:*")
        
        return StreamingResponse(
            iter([export_data]),
            media_type=mime_types.get(format, "application/octet-stream"),
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出教案失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

@router.get("/all")
async def export_all_data(
    format: str = Query(..., description="导出格式"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """导出所有数据（文档和教案）"""
    try:
        # 验证导出格式
        if not export_service.validate_export_format(format):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的导出格式: {format}。支持的格式: {', '.join(export_service.get_supported_formats())}"
            )
        
        # 获取所有数据
        documents = db.query(Document).filter(Document.user_id == current_user.id).all()
        lesson_plans = db.query(LessonPlan).filter(LessonPlan.user_id == current_user.id).all()
        
        if not documents and not lesson_plans:
            raise HTTPException(status_code=404, detail="没有找到任何数据")
        
        # 准备导出数据
        all_data = {
            "export_info": {
                "export_time": datetime.now().isoformat(),
                "user_id": current_user.id,
                "total_documents": len(documents),
                "total_lesson_plans": len(lesson_plans)
            },
            "documents": [],
            "lesson_plans": []
        }
        
        # 转换文档数据
        for doc in documents:
            doc_dict = doc.to_dict()
            if "created_at" in doc_dict and doc_dict["created_at"]:
                doc_dict["created_at"] = doc_dict["created_at"].isoformat()
            if "updated_at" in doc_dict and doc_dict["updated_at"]:
                doc_dict["updated_at"] = doc_dict["updated_at"].isoformat()
            all_data["documents"].append(doc_dict)
        
        # 转换教案数据
        for plan in lesson_plans:
            plan_dict = plan.to_dict()
            if "created_at" in plan_dict and plan_dict["created_at"]:
                plan_dict["created_at"] = plan_dict["created_at"].isoformat()
            if "updated_at" in plan_dict and plan_dict["updated_at"]:
                plan_dict["updated_at"] = plan_dict["updated_at"].isoformat()
            all_data["lesson_plans"].append(plan_dict)
        
        # 导出数据
        export_data = export_service.export_documents([all_data], format)
        
        # 生成文件名
        filename = export_service.get_export_filename(format, f"all_data_{len(documents)}_{len(lesson_plans)}")
        
        # 设置MIME类型
        mime_types = {
            "json": "application/json",
            "csv": "text/csv",
            "xml": "application/xml",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "zip": "application/zip"
        }
        
        # 记录导出日志
        logger.info(f"用户 {current_user.id} 导出了所有数据，文档: {len(documents)}, 教案: {len(lesson_plans)}, 格式: {format}")
        
        # 清除相关缓存
        cache.clear_pattern(f"*:user:{current_user.id}:*")
        
        return StreamingResponse(
            iter([export_data]),
            media_type=mime_types.get(format, "application/octet-stream"),
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出所有数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

@router.get("/stats")
async def get_export_stats(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """获取导出统计信息"""
    try:
        # 尝试从缓存获取
        cache_key = f"export_stats:user:{current_user.id}"
        cached_stats = cache.get(cache_key)
        
        if cached_stats:
            return cached_stats
        
        # 计算统计信息
        total_documents = db.query(Document).filter(Document.user_id == current_user.id).count()
        total_lesson_plans = db.query(LessonPlan).filter(LessonPlan.user_id == current_user.id).count()
        
        # 按文件类型统计文档
        doc_type_stats = db.query(Document.file_type, db.func.count(Document.id)).filter(
            Document.user_id == current_user.id
        ).group_by(Document.file_type).all()
        
        # 按学科统计教案
        subject_stats = db.query(LessonPlan.subject, db.func.count(LessonPlan.id)).filter(
            LessonPlan.user_id == current_user.id
        ).group_by(LessonPlan.subject).all()
        
        # 按年级统计教案
        grade_stats = db.query(LessonPlan.grade_level, db.func.count(LessonPlan.id)).filter(
            LessonPlan.user_id == current_user.id
        ).group_by(LessonPlan.grade_level).all()
        
        stats = {
            "total_documents": total_documents,
            "total_lesson_plans": total_lesson_plans,
            "document_types": dict(doc_type_stats),
            "subjects": dict(subject_stats),
            "grade_levels": dict(grade_stats),
            "supported_export_formats": export_service.get_supported_formats(),
            "last_updated": datetime.now().isoformat()
        }
        
        # 缓存结果
        cache.set(cache_key, stats, ttl=1800)  # 30分钟
        
        return stats
        
    except Exception as e:
        logger.error(f"获取导出统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")
