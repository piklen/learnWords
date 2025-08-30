from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class LessonPlanStatus(str, enum.Enum):
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class LessonPlan(Base):
    __tablename__ = "lesson_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Generation parameters
    grade_level = Column(String)
    subject = Column(String)
    duration_minutes = Column(Integer)
    learning_objectives = Column(Text)
    pedagogical_style = Column(String)
    activities = Column(JSON)
    assessment_methods = Column(JSON)
    differentiation_strategies = Column(Text)
    
    # Generated content
    title = Column(String)
    content = Column(Text)
    content_markdown = Column(Text)
    
    # Status and metadata
    status = Column(Enum(LessonPlanStatus), default=LessonPlanStatus.GENERATING)
    generation_error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="lesson_plans")
    document = relationship("Document", back_populates="lesson_plans")
