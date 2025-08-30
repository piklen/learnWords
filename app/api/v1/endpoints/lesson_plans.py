from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.lesson_plan import LessonPlan, LessonPlanStatus
from app.schemas.lesson_plan import LessonPlanCreate, LessonPlanResponse
from app.tasks.lesson_plan_generation import generate_lesson_plan_task

router = APIRouter()

@router.post("/", response_model=LessonPlanResponse)
def create_lesson_plan(
    lesson_plan: LessonPlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """创建教案生成任务"""
    # Verify document exists and belongs to user
    document = db.query(Document).filter(
        Document.id == lesson_plan.document_id,
        Document.user_id == current_user.id,
        Document.status == "structured"  # Only process structured documents
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or not ready for lesson plan generation"
        )
    
    # Create lesson plan record
    db_lesson_plan = LessonPlan(
        user_id=current_user.id,
        document_id=lesson_plan.document_id,
        grade_level=lesson_plan.grade_level,
        subject=lesson_plan.subject,
        duration_minutes=lesson_plan.duration_minutes,
        learning_objectives=lesson_plan.learning_objectives,
        pedagogical_style=lesson_plan.pedagogical_style,
        activities=lesson_plan.activities,
        assessment_methods=lesson_plan.assessment_methods,
        differentiation_strategies=lesson_plan.differentiation_strategies,
        status=LessonPlanStatus.GENERATING
    )
    
    db.add(db_lesson_plan)
    db.commit()
    db.refresh(db_lesson_plan)
    
    # Trigger async generation
    generate_lesson_plan_task.delay(db_lesson_plan.id)
    
    return db_lesson_plan

@router.get("/", response_model=List[LessonPlanResponse])
def list_lesson_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取用户教案列表"""
    lesson_plans = db.query(LessonPlan).filter(LessonPlan.user_id == current_user.id).all()
    return lesson_plans

@router.get("/{lesson_plan_id}", response_model=LessonPlanResponse)
def get_lesson_plan(
    lesson_plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """获取特定教案详情"""
    lesson_plan = db.query(LessonPlan).filter(
        LessonPlan.id == lesson_plan_id,
        LessonPlan.user_id == current_user.id
    ).first()
    
    if not lesson_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson plan not found"
        )
    
    return lesson_plan

@router.post("/{lesson_plan_id}/regenerate")
def regenerate_lesson_plan(
    lesson_plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """重新生成教案"""
    lesson_plan = db.query(LessonPlan).filter(
        LessonPlan.id == lesson_plan_id,
        LessonPlan.user_id == current_user.id
    ).first()
    
    if not lesson_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson plan not found"
        )
    
    # Reset status and trigger regeneration
    lesson_plan.status = LessonPlanStatus.GENERATING
    lesson_plan.generation_error = None
    db.commit()
    
    # Trigger async regeneration
    generate_lesson_plan_task.delay(lesson_plan.id)
    
    return {"message": "Lesson plan regeneration started", "lesson_plan_id": lesson_plan_id}
