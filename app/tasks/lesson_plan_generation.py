import json
from typing import Dict, Any
from celery import current_task
import asyncio

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.lesson_plan import LessonPlan, LessonPlanStatus
from app.models.document import Document
from app.services.prompt_engine import PromptEngine

@celery_app.task(bind=True)
def generate_lesson_plan_task(self, lesson_plan_id: int):
    """生成教案的异步任务"""
    db = SessionLocal()
    
    try:
        # Get lesson plan
        lesson_plan = db.query(LessonPlan).filter(LessonPlan.id == lesson_plan_id).first()
        if not lesson_plan:
            current_task.update_state(state='FAILURE', meta={'error': 'Lesson plan not found'})
            return
        
        # Get associated document
        document = db.query(Document).filter(Document.id == lesson_plan.document_id).first()
        if not document or document.status != "structured":
            lesson_plan.status = LessonPlanStatus.FAILED
            lesson_plan.generation_error = "Document not ready for lesson plan generation"
            db.commit()
            current_task.update_state(state='FAILURE', meta={'error': 'Document not ready'})
            return
        
        # Initialize prompt engine
        prompt_engine = PromptEngine()
        
        # Generate lesson plan using AI service
        try:
            generated_content = asyncio.run(prompt_engine.generate_lesson_plan(
                structured_content=document.structured_content,
                user_requirements={
                    "grade_level": lesson_plan.grade_level,
                    "subject": lesson_plan.subject,
                    "duration_minutes": lesson_plan.duration_minutes,
                    "learning_objectives": lesson_plan.learning_objectives,
                    "pedagogical_style": lesson_plan.pedagogical_style,
                    "activities": lesson_plan.activities,
                    "assessment_methods": lesson_plan.assessment_methods,
                    "differentiation_strategies": lesson_plan.differentiation_strategies
                }
            ))
            
            # Update lesson plan
            lesson_plan.title = extract_title(generated_content)
            lesson_plan.content = generated_content
            lesson_plan.content_markdown = generated_content  # For now, same as content
            lesson_plan.status = LessonPlanStatus.COMPLETED
            
        except Exception as e:
            lesson_plan.status = LessonPlanStatus.FAILED
            lesson_plan.generation_error = f"AI API error: {str(e)}"
            db.commit()
            current_task.update_state(state='FAILURE', meta={'error': str(e)})
            return
        
        db.commit()
        current_task.update_state(state='SUCCESS')
        
    except Exception as e:
        if lesson_plan:
            lesson_plan.status = LessonPlanStatus.FAILED
            lesson_plan.generation_error = str(e)
            db.commit()
        current_task.update_state(state='FAILURE', meta={'error': str(e)})
    finally:
        db.close()

def extract_title(content: str) -> str:
    """从生成的内容中提取标题"""
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            return line[:100]  # Limit title length
    return "教案"
