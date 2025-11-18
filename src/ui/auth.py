"""Authentication and authorization for the web dashboard.

This module provides JWT-based authentication with secure password hashing,
token management, and user verification for the FastAPI dashboard.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

from src.config.security import get_security_settings

logger = logging.getLogger(__name__)

# Security settings
settings = get_security_settings()

# HTTP Bearer token scheme
security = HTTPBearer()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    """User model for authenticated users."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    is_active: bool = True
    is_admin: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserInDB(User):
    """User model with hashed password (for database storage)."""

    hashed_password: str


class TokenData(BaseModel):
    """JWT token payload data."""

    username: Optional[str] = None
    exp: Optional[datetime] = None
    token_type: str = "access"


class LoginResponse(BaseModel):
    """Response model for successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class PasswordStrength(BaseModel):
    """Password strength validation result."""

    is_valid: bool
    errors: list[str] = []
    score: int = 0  # 0-5 scale


def validate_password_strength(password: str) -> PasswordStrength:
    """Validate password against security policy.

    Args:
        password: Password to validate

    Returns:
        PasswordStrength: Validation result with errors if any

    Example:
        >>> result = validate_password_strength("weak")
        >>> print(result.is_valid)
        False
        >>> print(result.errors)
        ['Password must be at least 12 characters']
    """
    errors = []
    score = 0

    # Length check
    if len(password) < settings.min_password_length:
        errors.append(f"Password must be at least {settings.min_password_length} characters")
    else:
        score += 1

    # Character requirements
    if settings.require_uppercase and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    else:
        score += 1

    if settings.require_lowercase and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    else:
        score += 1

    if settings.require_numbers and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    else:
        score += 1

    if settings.require_special:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            errors.append("Password must contain at least one special character")
        else:
            score += 1

    # Common password check (basic)
    common_passwords = ["password", "123456", "qwerty", "admin", "letmein"]
    if password.lower() in common_passwords:
        errors.append("Password is too common")
        score = 0

    is_valid = len(errors) == 0

    return PasswordStrength(is_valid=is_valid, errors=errors, score=score if is_valid else 0)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token.

    Args:
        data: Payload data to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        str: Encoded JWT token

    Example:
        >>> token = create_access_token({"sub": "johndoe"})
        >>> print(len(token) > 0)
        True
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiry_minutes)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    logger.debug(f"Created access token for {data.get('sub')}, expires at {expire}")

    return encoded_jwt


def create_refresh_token(username: str) -> str:
    """Create JWT refresh token with longer expiration.

    Args:
        username: Username for token

    Returns:
        str: Encoded JWT refresh token
    """
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_expiry_days)

    to_encode = {
        "sub": username,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    logger.debug(f"Created refresh token for {username}, expires at {expire}")

    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password

    Returns:
        bool: True if password matches

    Example:
        >>> hashed = get_password_hash("secret123")
        >>> verify_password("secret123", hashed)
        True
        >>> verify_password("wrong", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Bcrypt hashed password

    Example:
        >>> hash1 = get_password_hash("mypassword")
        >>> hash2 = get_password_hash("mypassword")
        >>> hash1 != hash2  # Different salts
        True
    """
    return pwd_context.hash(password)


def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData: Decoded token data

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        username: str = payload.get("sub")
        exp: int = payload.get("exp")
        token_type: str = payload.get("type", "access")

        if username is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception

        # Convert exp to datetime
        exp_datetime = datetime.fromtimestamp(exp) if exp else None

        token_data = TokenData(
            username=username,
            exp=exp_datetime,
            token_type=token_type
        )

        logger.debug(f"Successfully decoded token for {username}")
        return token_data

    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> User:
    """Get current authenticated user from JWT token.

    This function extracts and validates the JWT token from the
    Authorization header and returns the authenticated user.

    Args:
        credentials: HTTP Bearer credentials from header

    Returns:
        User: Authenticated user object

    Raises:
        HTTPException: If token is invalid, expired, or user not found

    Example:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user": user.username}
    """
    token_data = decode_token(credentials.credentials)

    # TODO: Fetch user from database using UserManager
    # For now, return a mock user for development
    # In production, this should query the database:
    #
    # from src.core.user_manager import get_user_manager
    # user_manager = get_user_manager()
    # user = user_manager.get_user(token_data.username)
    # if user is None:
    #     raise HTTPException(status_code=404, detail="User not found")
    # return User(**user)

    user = User(
        username=token_data.username,
        email=f"{token_data.username}@example.com",
        is_active=True,
        is_admin=False
    )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role for endpoint access.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Admin user object

    Raises:
        HTTPException: If user is not an admin

    Example:
        @app.get("/admin/users")
        async def list_users(admin: User = Depends(require_admin)):
            return {"message": "Admin access granted"}
    """
    if not current_user.is_admin:
        logger.warning(f"User {current_user.username} attempted admin access without permission")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    logger.debug(f"Admin access granted to {current_user.username}")
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise.

    Useful for endpoints that work for both authenticated and
    anonymous users but provide extra features when authenticated.

    Args:
        credentials: Optional HTTP Bearer credentials

    Returns:
        Optional[User]: User if authenticated, None otherwise

    Example:
        @app.get("/public")
        async def public_route(user: Optional[User] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user.username}"}
            return {"message": "Hello anonymous"}
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
