"""
Test data factories using Factory Boy
"""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from factory.fuzzy import FuzzyChoice, FuzzyInteger, FuzzyText

from app.models.document import Document, DocumentStatus
from app.models.lesson_plan import LessonPlan, LessonPlanStatus
from app.models.user import User


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with common configuration"""
    
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"


class UserFactory(BaseFactory):
    """Factory for User model"""
    
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    full_name = factory.Faker("name")
    hashed_password = factory.LazyFunction(
        lambda: "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "secret"
    )
    is_active = True
    is_verified = False


class DocumentFactory(BaseFactory):
    """Factory for Document model"""
    
    class Meta:
        model = Document
    
    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("text", max_nb_chars=200)
    filename = factory.Faker("file_name", extension="pdf")
    file_path = factory.LazyAttribute(lambda obj: f"uploads/{obj.filename}")
    file_size = FuzzyInteger(1024, 10485760)  # 1KB to 10MB
    mime_type = "application/pdf"
    status = FuzzyChoice([status.value for status in DocumentStatus])
    ocr_text = factory.Faker("text", max_nb_chars=1000)
    structured_content = factory.LazyFunction(lambda: {
        "title": factory.Faker("sentence").generate(),
        "sections": [
            {
                "heading": factory.Faker("sentence", nb_words=3).generate(),
                "content": factory.Faker("paragraph").generate(),
            }
            for _ in range(3)
        ],
    })
    processing_error = None
    user_id = factory.SubFactory(UserFactory)


class LessonPlanFactory(BaseFactory):
    """Factory for LessonPlan model"""
    
    class Meta:
        model = LessonPlan
    
    title = factory.Faker("sentence", nb_words=6)
    grade_level = FuzzyChoice(["小学", "初中", "高中", "大学"])
    subject = FuzzyChoice(["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理"])
    duration_minutes = FuzzyChoice([40, 45, 50, 90])
    learning_objectives = factory.List([
        factory.Faker("sentence") for _ in range(3)
    ])
    pedagogical_style = FuzzyChoice(["讲授式", "启发式", "讨论式", "实验式", "混合式"])
    activities = factory.List([
        factory.Faker("sentence") for _ in range(2)
    ])
    assessment_methods = factory.List([
        factory.Faker("word") for _ in range(2)
    ])
    differentiation_strategies = factory.List([
        factory.Faker("sentence") for _ in range(2)
    ])
    content = factory.Faker("text", max_nb_chars=2000)
    content_markdown = factory.LazyAttribute(lambda obj: f"# {obj.title}\n\n{obj.content}")
    status = FuzzyChoice([status.value for status in LessonPlanStatus])
    generation_error = None
    user_id = factory.SubFactory(UserFactory)
    document_id = factory.SubFactory(DocumentFactory)


# Utility functions for creating test data
def create_test_user(**kwargs):
    """Create a test user with optional overrides"""
    return UserFactory.create(**kwargs)


def create_test_document(user=None, **kwargs):
    """Create a test document with optional user and overrides"""
    if user:
        kwargs["user_id"] = user.id
    return DocumentFactory.create(**kwargs)


def create_test_lesson_plan(user=None, document=None, **kwargs):
    """Create a test lesson plan with optional user, document and overrides"""
    if user:
        kwargs["user_id"] = user.id
    if document:
        kwargs["document_id"] = document.id
    return LessonPlanFactory.create(**kwargs)


# Batch creation helpers
def create_multiple_users(count=5, **kwargs):
    """Create multiple test users"""
    return UserFactory.create_batch(count, **kwargs)


def create_multiple_documents(count=3, user=None, **kwargs):
    """Create multiple test documents"""
    if user:
        kwargs["user_id"] = user.id
    return DocumentFactory.create_batch(count, **kwargs)


def create_multiple_lesson_plans(count=3, user=None, document=None, **kwargs):
    """Create multiple test lesson plans"""
    if user:
        kwargs["user_id"] = user.id
    if document:
        kwargs["document_id"] = document.id
    return LessonPlanFactory.create_batch(count, **kwargs)
