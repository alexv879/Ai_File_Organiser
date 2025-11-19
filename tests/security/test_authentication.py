"""Security tests for authentication system.

Tests the JWT authentication, password validation, and user management
security features implemented in Phase 1.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from src.ui.auth import (
    create_access_token,
    verify_password,
    get_password_hash,
    validate_password_strength,
    decode_token
)
from src.core.user_manager import UserManager
from src.config.security import get_security_settings


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "test_users.db"
    yield db_path
    shutil.rmtree(temp_dir)


@pytest.fixture
def user_manager(temp_db):
    """Create UserManager instance with temporary database."""
    return UserManager(temp_db)


class TestPasswordSecurity:
    """Test password hashing and validation."""

    def test_password_hashing(self):
        """Test that passwords are hashed securely."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are long
        assert hashed.startswith("$2b$")  # Bcrypt prefix

    def test_password_verification(self):
        """Test password verification."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

    def test_password_hash_uniqueness(self):
        """Test that same password produces different hashes (salt)."""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_password_strength_validation(self):
        """Test password strength requirements."""
        # Valid password
        result = validate_password_strength("ValidPass123!")
        assert result.is_valid is True
        assert len(result.errors) == 0

        # Too short
        result = validate_password_strength("Short1!")
        assert result.is_valid is False
        assert any("12 characters" in error for error in result.errors)

        # No uppercase
        result = validate_password_strength("lowercase123!")
        assert result.is_valid is False
        assert any("uppercase" in error for error in result.errors)

        # No numbers
        result = validate_password_strength("NoNumbers!")
        assert result.is_valid is False
        assert any("number" in error for error in result.errors)

        # No special characters
        result = validate_password_strength("NoSpecial123")
        assert result.is_valid is False
        assert any("special" in error for error in result.errors)

        # Common password
        result = validate_password_strength("password123!")
        assert result.is_valid is False
        assert any("common" in error for error in result.errors)


class TestJWTSecurity:
    """Test JWT token security."""

    def test_token_creation(self):
        """Test JWT token creation."""
        token = create_access_token({"sub": "testuser"})

        assert isinstance(token, str)
        assert len(token) > 100  # JWTs are long

    def test_token_expiration(self):
        """Test token expiration."""
        # Create token that expires in 1 second
        token = create_access_token(
            {"sub": "testuser"},
            expires_delta=timedelta(seconds=1)
        )

        # Should decode successfully immediately
        token_data = decode_token(token)
        assert token_data.username == "testuser"

        # Wait for expiration
        import time
        time.sleep(2)

        # Should raise exception after expiration
        with pytest.raises(Exception):
            decode_token(token)

    def test_token_payload(self):
        """Test token contains correct payload."""
        token = create_access_token({"sub": "testuser"})
        token_data = decode_token(token)

        assert token_data.username == "testuser"
        assert token_data.exp is not None
        assert token_data.token_type == "access"

    def test_token_tampering(self):
        """Test that tampered tokens are rejected."""
        token = create_access_token({"sub": "testuser"})

        # Tamper with token
        tampered = token[:-5] + "XXXXX"

        # Should raise exception
        with pytest.raises(Exception):
            decode_token(tampered)


class TestUserManagement:
    """Test user management security."""

    def test_create_user(self, user_manager):
        """Test user creation."""
        success = user_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="ValidPass123!"
        )

        assert success is True

        # Verify user exists
        user = user_manager.get_user("testuser")
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_duplicate_username(self, user_manager):
        """Test that duplicate usernames are rejected."""
        user_manager.create_user(
            username="testuser",
            email="test1@example.com",
            password="ValidPass123!"
        )

        # Try to create with same username
        with pytest.raises(ValueError, match="already exists"):
            user_manager.create_user(
                username="testuser",
                email="test2@example.com",
                password="ValidPass123!"
            )

    def test_duplicate_email(self, user_manager):
        """Test that duplicate emails are rejected."""
        user_manager.create_user(
            username="user1",
            email="test@example.com",
            password="ValidPass123!"
        )

        # Try to create with same email
        with pytest.raises(ValueError, match="already registered"):
            user_manager.create_user(
                username="user2",
                email="test@example.com",
                password="ValidPass123!"
            )

    def test_weak_password_rejected(self, user_manager):
        """Test that weak passwords are rejected."""
        with pytest.raises(ValueError, match="Password validation failed"):
            user_manager.create_user(
                username="testuser",
                email="test@example.com",
                password="weak"
            )

    def test_authentication_success(self, user_manager):
        """Test successful authentication."""
        user_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="ValidPass123!"
        )

        user = user_manager.authenticate_user("testuser", "ValidPass123!")
        assert user is not None
        assert user.username == "testuser"

    def test_authentication_failure(self, user_manager):
        """Test failed authentication."""
        user_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="ValidPass123!"
        )

        # Wrong password
        user = user_manager.authenticate_user("testuser", "WrongPass123!")
        assert user is None

        # Wrong username
        user = user_manager.authenticate_user("wronguser", "ValidPass123!")
        assert user is None

    def test_account_lockout(self, user_manager):
        """Test account lockout after failed attempts."""
        user_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="ValidPass123!"
        )

        # Try wrong password 5 times
        for _ in range(5):
            user_manager.authenticate_user("testuser", "WrongPass123!")

        # Account should be locked
        user = user_manager.authenticate_user("testuser", "ValidPass123!")
        assert user is None  # Locked even with correct password

    def test_case_insensitive_username(self, user_manager):
        """Test that usernames are case-insensitive."""
        user_manager.create_user(
            username="TestUser",
            email="test@example.com",
            password="ValidPass123!"
        )

        # Should authenticate with different case
        user = user_manager.authenticate_user("testuser", "ValidPass123!")
        assert user is not None

        user = user_manager.authenticate_user("TESTUSER", "ValidPass123!")
        assert user is not None

    def test_login_history(self, user_manager):
        """Test that login history is recorded."""
        user_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="ValidPass123!"
        )

        # Successful login
        user_manager.authenticate_user(
            "testuser",
            "ValidPass123!",
            ip_address="192.168.1.1",
            user_agent="Test Browser"
        )

        # Failed login
        user_manager.authenticate_user(
            "testuser",
            "WrongPass123!",
            ip_address="192.168.1.2",
            user_agent="Test Browser"
        )

        # Check history
        history = user_manager.get_login_history("testuser")
        assert len(history) == 2

        # Check successful login
        successful = [h for h in history if h["success"]]
        assert len(successful) == 1
        assert successful[0]["ip_address"] == "192.168.1.1"

        # Check failed login
        failed = [h for h in history if not h["success"]]
        assert len(failed) == 1
        assert failed[0]["ip_address"] == "192.168.1.2"


class TestSecuritySettings:
    """Test security settings."""

    def test_security_settings_loaded(self):
        """Test that security settings are loaded."""
        settings = get_security_settings()

        assert settings.jwt_algorithm in ["HS256", "HS384", "HS512"]
        assert settings.jwt_expiry_minutes > 0
        assert settings.min_password_length >= 12

    def test_production_mode_detection(self):
        """Test production mode detection."""
        settings = get_security_settings()

        # Should not be production in test environment
        assert settings.is_production is False
        assert settings.is_development is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
