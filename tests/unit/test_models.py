"""
Unit tests for database models
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.document import Document, DocumentStatus
from app.models.lesson_plan import LessonPlan, LessonPlanStatus
from app.models.user import User
from tests.factories import DocumentFactory, LessonPlanFactory, UserFactory


class TestUserModel:
    """Test User model"""
    
    @pytest.mark.unit
    def test_create_user(self, db_session):
        """Test creating a user"""
        user = UserFactory.build()
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email is not None
        assert user.username is not None
        assert user.is_active is True
        assert user.is_verified is False
    
    @pytest.mark.unit
    def test_user_email_uniqueness(self, db_session):
        """Test that user email must be unique"""
        email = "test@example.com"
        
        user1 = UserFactory.build(email=email)
        db_session.add(user1)
        db_session.commit()
        
        user2 = UserFactory.build(email=email)
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    @pytest.mark.unit
    def test_user_username_uniqueness(self, db_session):
        """Test that username must be unique"""
        username = "testuser"
        
        user1 = UserFactory.build(username=username)
        db_session.add(user1)
        db_session.commit()
        
        user2 = UserFactory.build(username=username)
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    @pytest.mark.unit
    def test_user_relationships(self, db_session):
        """Test user relationships with documents and lesson plans"""
        user = UserFactory.create(session=db_session)
        
        # Create documents for the user
        documents = DocumentFactory.create_batch(2, session=db_session, user_id=user.id)
        
        # Create lesson plans for the user
        lesson_plans = LessonPlanFactory.create_batch(
            2, session=db_session, user_id=user.id, document_id=documents[0].id
        )
        
        db_session.commit()
        
        # Test relationships
        assert len(user.documents) == 2
        assert len(user.lesson_plans) == 2
        assert all(doc.user_id == user.id for doc in user.documents)
        assert all(lp.user_id == user.id for lp in user.lesson_plans)


class TestDocumentModel:
    """Test Document model"""
    
    @pytest.mark.unit
    def test_create_document(self, db_session, test_user):
        """Test creating a document"""
        document = DocumentFactory.build(user_id=test_user.id)
        db_session.add(document)
        db_session.commit()
        
        assert document.id is not None
        assert document.title is not None
        assert document.filename is not None
        assert document.user_id == test_user.id
        assert document.status in [status.value for status in DocumentStatus]
    
    @pytest.mark.unit
    def test_document_status_enum(self, db_session, test_user):
        """Test document status enumeration"""
        document = DocumentFactory.build(
            user_id=test_user.id,
            status=DocumentStatus.UPLOADING
        )
        db_session.add(document)
        db_session.commit()
        
        assert document.status == DocumentStatus.UPLOADING.value
        
        # Update status
        document.status = DocumentStatus.PROCESSED
        db_session.commit()
        
        assert document.status == DocumentStatus.PROCESSED.value
    
    @pytest.mark.unit
    def test_document_user_relationship(self, db_session, test_user):
        """Test document-user relationship"""
        document = DocumentFactory.create(session=db_session, user_id=test_user.id)
        db_session.commit()
        
        assert document.user.id == test_user.id
        assert document.user.email == test_user.email


class TestLessonPlanModel:
    """Test LessonPlan model"""
    
    @pytest.mark.unit
    def test_create_lesson_plan(self, db_session, test_user, test_document):
        """Test creating a lesson plan"""
        lesson_plan = LessonPlanFactory.build(
            user_id=test_user.id,
            document_id=test_document.id
        )
        db_session.add(lesson_plan)
        db_session.commit()
        
        assert lesson_plan.id is not None
        assert lesson_plan.title is not None
        assert lesson_plan.user_id == test_user.id
        assert lesson_plan.document_id == test_document.id
        assert lesson_plan.status in [status.value for status in LessonPlanStatus]
    
    @pytest.mark.unit
    def test_lesson_plan_status_enum(self, db_session, test_user, test_document):
        """Test lesson plan status enumeration"""
        lesson_plan = LessonPlanFactory.build(
            user_id=test_user.id,
            document_id=test_document.id,
            status=LessonPlanStatus.PENDING
        )
        db_session.add(lesson_plan)
        db_session.commit()
        
        assert lesson_plan.status == LessonPlanStatus.PENDING.value
        
        # Update status
        lesson_plan.status = LessonPlanStatus.GENERATING
        db_session.commit()
        
        assert lesson_plan.status == LessonPlanStatus.GENERATING.value
    
    @pytest.mark.unit
    def test_lesson_plan_relationships(self, db_session, test_user, test_document):
        """Test lesson plan relationships"""
        lesson_plan = LessonPlanFactory.create(
            session=db_session,
            user_id=test_user.id,
            document_id=test_document.id
        )
        db_session.commit()
        
        assert lesson_plan.user.id == test_user.id
        assert lesson_plan.document.id == test_document.id
        assert lesson_plan.user.email == test_user.email
        assert lesson_plan.document.title == test_document.title
    
    @pytest.mark.unit
    def test_lesson_plan_json_fields(self, db_session, test_user, test_document):
        """Test JSON field handling"""
        learning_objectives = ["目标1", "目标2", "目标3"]
        activities = ["活动1", "活动2"]
        
        lesson_plan = LessonPlanFactory.build(
            user_id=test_user.id,
            document_id=test_document.id,
            learning_objectives=learning_objectives,
            activities=activities
        )
        db_session.add(lesson_plan)
        db_session.commit()
        
        # Refresh from database
        db_session.refresh(lesson_plan)
        
        assert lesson_plan.learning_objectives == learning_objectives
        assert lesson_plan.activities == activities
        assert isinstance(lesson_plan.learning_objectives, list)
        assert isinstance(lesson_plan.activities, list)


class TestModelConstraints:
    """Test model constraints and validations"""
    
    @pytest.mark.unit
    def test_user_required_fields(self, db_session):
        """Test user required fields"""
        # Test missing email
        with pytest.raises(IntegrityError):
            user = User(username="testuser", hashed_password="hashed")
            db_session.add(user)
            db_session.commit()
        
        db_session.rollback()
        
        # Test missing username
        with pytest.raises(IntegrityError):
            user = User(email="test@example.com", hashed_password="hashed")
            db_session.add(user)
            db_session.commit()
    
    @pytest.mark.unit
    def test_document_required_fields(self, db_session, test_user):
        """Test document required fields"""
        # Test missing title
        with pytest.raises(IntegrityError):
            document = Document(
                filename="test.pdf",
                user_id=test_user.id
            )
            db_session.add(document)
            db_session.commit()
    
    @pytest.mark.unit
    def test_foreign_key_constraints(self, db_session):
        """Test foreign key constraints"""
        # Test invalid user_id in document
        with pytest.raises(IntegrityError):
            document = DocumentFactory.build(user_id=99999)  # Non-existent user
            db_session.add(document)
            db_session.commit()
