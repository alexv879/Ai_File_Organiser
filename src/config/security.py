"""Security configuration for web dashboard and APIs.

This module provides centralized security configuration management
including JWT settings, API keys, rate limiting, CORS, and HTTPS settings.
"""

from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import secrets


class SecuritySettings(BaseSettings):
    """Security settings loaded from environment variables.

    All sensitive configuration should be stored in environment variables
    or a .env file, never committed to version control.
    """

    # JWT Settings
    jwt_secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    jwt_expiry_minutes: int = Field(
        default=30,
        description="JWT token expiry in minutes"
    )
    jwt_refresh_expiry_days: int = Field(
        default=7,
        description="Refresh token expiry in days"
    )

    # API Keys for cloud services
    clerk_secret_key: Optional[str] = Field(
        default=None,
        env="CLERK_SECRET_KEY",
        description="Clerk authentication secret key"
    )
    clerk_publishable_key: Optional[str] = Field(
        default=None,
        env="CLERK_PUBLISHABLE_KEY",
        description="Clerk authentication publishable key"
    )

    # Rate Limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting"
    )
    rate_limit_per_minute: int = Field(
        default=60,
        description="Maximum requests per minute per IP"
    )
    rate_limit_per_hour: int = Field(
        default=1000,
        description="Maximum requests per hour per IP"
    )

    # CORS Settings
    cors_enabled: bool = Field(
        default=True,
        description="Enable CORS middleware"
    )
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed origins for CORS"
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods"
    )

    # HTTPS/TLS Settings
    ssl_enabled: bool = Field(
        default=False,
        description="Enable HTTPS (requires cert and key files)"
    )
    ssl_cert_file: Optional[str] = Field(
        default=None,
        env="SSL_CERT_FILE",
        description="Path to SSL certificate file"
    )
    ssl_key_file: Optional[str] = Field(
        default=None,
        env="SSL_KEY_FILE",
        description="Path to SSL private key file"
    )

    # Database Encryption
    database_encryption_key: Optional[str] = Field(
        default=None,
        env="DATABASE_ENCRYPTION_KEY",
        description="Encryption key for SQLCipher"
    )
    database_encryption_enabled: bool = Field(
        default=False,
        description="Enable database encryption with SQLCipher"
    )

    # Session Settings
    session_cookie_name: str = Field(
        default="aifo_session",
        description="Session cookie name"
    )
    session_cookie_secure: bool = Field(
        default=False,
        description="Require HTTPS for session cookies"
    )
    session_cookie_httponly: bool = Field(
        default=True,
        description="Prevent JavaScript access to session cookies"
    )
    session_cookie_samesite: str = Field(
        default="lax",
        description="SameSite cookie attribute (strict/lax/none)"
    )

    # Security Headers
    enable_security_headers: bool = Field(
        default=True,
        description="Enable security headers (CSP, HSTS, etc.)"
    )

    # Password Policy
    min_password_length: int = Field(
        default=12,
        description="Minimum password length"
    )
    require_uppercase: bool = Field(
        default=True,
        description="Require uppercase letters in passwords"
    )
    require_lowercase: bool = Field(
        default=True,
        description="Require lowercase letters in passwords"
    )
    require_numbers: bool = Field(
        default=True,
        description="Require numbers in passwords"
    )
    require_special: bool = Field(
        default=True,
        description="Require special characters in passwords"
    )

    # Environment
    environment: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Environment name (development/staging/production)"
    )
    debug: bool = Field(
        default=False,
        env="DEBUG",
        description="Debug mode"
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        allowed = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed:
            raise ValueError(f"JWT algorithm must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    def validate_ssl_config(self) -> bool:
        """Validate SSL configuration."""
        if self.ssl_enabled:
            if not self.ssl_cert_file or not self.ssl_key_file:
                raise ValueError("SSL enabled but cert/key files not specified")
            # In a real app, verify files exist
        return True

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[SecuritySettings] = None


def get_security_settings() -> SecuritySettings:
    """Get security settings singleton.

    Returns:
        SecuritySettings: Security configuration instance

    Example:
        >>> from src.config.security import get_security_settings
        >>> settings = get_security_settings()
        >>> print(settings.jwt_expiry_minutes)
        30
    """
    global _settings
    if _settings is None:
        _settings = SecuritySettings()
    return _settings


# Export commonly used instance
security_settings = get_security_settings()
