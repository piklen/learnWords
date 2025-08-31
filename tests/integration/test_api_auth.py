"""
Integration tests for authentication API endpoints
"""

import pytest
from fastapi import status

from app.core.security import verify_password
from tests.factories import UserFactory


class TestAuthenticationAPI:
    """Test authentication endpoints"""
    
    @pytest.mark.integration
    async def test_register_user_success(self, async_client, db_session):
        """Test successful user registration"""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepassword123",
            "full_name": "New User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        assert "hashed_password" not in data  # Password should not be returned
    
    @pytest.mark.integration
    async def test_register_user_duplicate_email(self, async_client, test_user):
        """Test registration with duplicate email"""
        user_data = {
            "email": test_user.email,  # Use existing email
            "username": "differentuser",
            "password": "securepassword123",
            "full_name": "Different User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in response.json()["detail"]
    
    @pytest.mark.integration
    async def test_register_user_invalid_data(self, async_client):
        """Test registration with invalid data"""
        # Missing required fields
        user_data = {
            "email": "invalid-email",  # Invalid email format
            "password": "123"  # Too short password
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.integration
    async def test_login_success(self, async_client, db_session):
        """Test successful user login"""
        # Create a user with known password
        user = UserFactory.create(
            session=db_session,
            email="loginuser@example.com",
            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "secret"
        )
        db_session.commit()
        
        login_data = {
            "username": user.email,  # FastAPI OAuth2 uses username field for email
            "password": "secret"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,  # Form data for OAuth2
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
    
    @pytest.mark.integration
    async def test_login_invalid_credentials(self, async_client, test_user):
        """Test login with invalid credentials"""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email or password" in response.json()["detail"]
    
    @pytest.mark.integration
    async def test_login_nonexistent_user(self, async_client):
        """Test login with non-existent user"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "somepassword"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email or password" in response.json()["detail"]


class TestProtectedEndpoints:
    """Test protected endpoints requiring authentication"""
    
    @pytest.mark.integration
    async def test_protected_endpoint_without_token(self, async_client):
        """Test accessing protected endpoint without token"""
        response = await async_client.get("/api/v1/documents/")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.integration
    async def test_protected_endpoint_with_invalid_token(self, async_client):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = await async_client.get("/api/v1/documents/", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.integration
    async def test_protected_endpoint_with_valid_token(self, async_client, auth_headers):
        """Test accessing protected endpoint with valid token"""
        response = await async_client.get("/api/v1/documents/", headers=auth_headers)
        
        # Should not return 401, might return 200 or other status depending on implementation
        assert response.status_code != status.HTTP_401_UNAUTHORIZED


class TestTokenValidation:
    """Test token validation and security"""
    
    @pytest.mark.integration
    async def test_token_expiration(self, async_client, test_user):
        """Test token expiration handling"""
        from app.core.security import create_access_token
        from datetime import timedelta
        
        # Create an expired token
        expired_token = create_access_token(
            data={"sub": test_user.email},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await async_client.get("/api/v1/documents/", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.integration
    async def test_token_with_invalid_user(self, async_client):
        """Test token with non-existent user"""
        from app.core.security import create_access_token
        
        # Create token for non-existent user
        token = create_access_token(data={"sub": "nonexistent@example.com"})
        
        headers = {"Authorization": f"Bearer {token}"}
        response = await async_client.get("/api/v1/documents/", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.integration
    async def test_malformed_authorization_header(self, async_client):
        """Test malformed Authorization header"""
        test_cases = [
            {"Authorization": "invalid-format"},
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": "Basic dGVzdA=="},  # Wrong auth type
        ]
        
        for headers in test_cases:
            response = await async_client.get("/api/v1/documents/", headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordSecurity:
    """Test password security features"""
    
    @pytest.mark.unit
    def test_password_hashing(self):
        """Test password hashing functionality"""
        from app.core.security import get_password_hash, verify_password
        
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        
        # Hash should be different from original password
        assert hashed != password
        
        # Should be able to verify correct password
        assert verify_password(password, hashed) is True
        
        # Should reject incorrect password
        assert verify_password("wrongpassword", hashed) is False
    
    @pytest.mark.unit
    def test_password_hash_uniqueness(self):
        """Test that same password generates different hashes"""
        from app.core.security import get_password_hash
        
        password = "samepassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Same password should generate different hashes (due to salt)
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
