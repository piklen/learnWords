from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.lesson_plan import LessonPlanStatus

class LessonPlanBase(BaseModel):
    document_id: int
    grade_level: str
    subject: str
    duration_minutes: int
    learning_objectives: str
    pedagogical_style: str
    activities: List[str]
    assessment_methods: List[str]
    differentiation_strategies: Optional[str] = None

class LessonPlanCreate(LessonPlanBase):
    pass

class LessonPlanResponse(LessonPlanBase):
    id: int
    user_id: int
    title: Optional[str] = None
    content: Optional[str] = None
    content_markdown: Optional[str] = None
    status: LessonPlanStatus
    generation_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
