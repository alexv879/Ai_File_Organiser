# Technical Implementation Plan
## AI File Organizer 2.0 - Detailed Development Guide

**Version:** 1.0
**Date:** January 2025
**Status:** Ready for Implementation

---

## Overview

This document provides detailed technical specifications and implementation guides for transforming the AI File Organizer according to the strategy outlined in `TRANSFORMATION_STRATEGY_2025.md`.

---

## Phase 1: Foundation & Security (Weeks 1-8)

### 1.1 Dashboard Security Hardening

#### Current State Analysis
**File:** `/src/ui/dashboard.py`
**Issues:**
- No authentication (anyone can access)
- HTTP only (no HTTPS)
- No rate limiting
- No CSRF protection

#### Implementation Steps

**Step 1: Add Environment Configuration**

Create `/src/config/security.py`:

```python
"""Security configuration for web dashboard."""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class SecuritySettings(BaseSettings):
    """Security settings from environment variables."""

    # JWT Settings
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 30

    # API Keys
    clerk_secret_key: Optional[str] = Field(None, env="CLERK_SECRET_KEY")
    clerk_publishable_key: Optional[str] = Field(None, env="CLERK_PUBLISHABLE_KEY")

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "https://yourdomain.com"]

    # HTTPS
    ssl_cert_file: Optional[str] = Field(None, env="SSL_CERT_FILE")
    ssl_key_file: Optional[str] = Field(None, env="SSL_KEY_FILE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


security_settings = SecuritySettings()
```

**Step 2: Install Dependencies**

Update `requirements.txt`:
```txt
# Add these packages
python-jose[cryptography]>=3.3.0  # JWT handling
passlib[bcrypt]>=1.7.4           # Password hashing
slowapi>=0.1.9                    # Rate limiting
python-multipart>=0.0.9          # Form parsing
```

**Step 3: Create Authentication Middleware**

Create `/src/ui/auth.py`:

```python
"""Authentication and authorization for dashboard."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.config.security import security_settings

logger = logging.getLogger(__name__)
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    """User model."""
    username: str
    email: str
    is_active: bool = True
    is_admin: bool = False


class TokenData(BaseModel):
    """JWT token payload."""
    username: Optional[str] = None
    exp: Optional[datetime] = None


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=security_settings.jwt_expiry_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        security_settings.jwt_secret_key,
        algorithm=security_settings.jwt_algorithm
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            security_settings.jwt_secret_key,
            algorithms=[security_settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username, exp=payload.get("exp"))
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception

    # TODO: Fetch user from database
    # For now, return mock user
    user = User(username=token_data.username, email=f"{token_data.username}@example.com")

    if user is None:
        raise credentials_exception

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
```

**Step 4: Update Dashboard with Authentication**

Update `/src/ui/dashboard.py`:

```python
"""Enhanced secure dashboard."""

import logging
from datetime import timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel

from src.ui.auth import (
    get_current_user,
    require_admin,
    create_access_token,
    verify_password,
    User
)
from src.config.security import security_settings

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# FastAPI app
app = FastAPI(
    title="AI File Organizer Dashboard",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# HTTPS redirect (production)
if security_settings.ssl_cert_file:
    app.add_middleware(HTTPSRedirectMiddleware)

# Trusted host
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
)


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str = "bearer"
    user: User


@app.post("/api/auth/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, login_data: LoginRequest):
    """Authenticate user and return JWT token."""
    # TODO: Verify against database
    # For now, mock authentication
    if login_data.username != "admin" or login_data.password != "changeme":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": login_data.username},
        expires_delta=timedelta(minutes=security_settings.jwt_expiry_minutes)
    )

    user = User(username=login_data.username, email=f"{login_data.username}@example.com", is_admin=True)

    return LoginResponse(access_token=access_token, user=user)


@app.get("/api/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user


@app.get("/api/files/inbox")
@limiter.limit("30/minute")
async def get_inbox(request: Request, current_user: User = Depends(get_current_user)):
    """Get files in inbox - requires authentication."""
    # Existing inbox logic with auth
    pass


@app.post("/api/files/organize")
@limiter.limit("10/minute")
async def organize_files(request: Request, current_user: User = Depends(get_current_user)):
    """Organize files - requires authentication."""
    # Existing organize logic with auth
    pass


@app.get("/api/admin/stats")
async def get_admin_stats(admin_user: User = Depends(require_admin)):
    """Admin-only endpoint."""
    return {"stats": "sensitive data"}


@app.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Public health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        ssl_keyfile=security_settings.ssl_key_file,
        ssl_certfile=security_settings.ssl_cert_file,
    )
```

**Step 5: Create User Database Schema**

Create `/src/core/user_manager.py`:

```python
"""User management with SQLite."""

import logging
import sqlite3
from datetime import datetime
from typing import Optional
from pathlib import Path

from src.ui.auth import get_password_hash, verify_password

logger = logging.getLogger(__name__)


class UserManager:
    """Manage users in SQLite database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize user database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    is_admin BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            conn.commit()

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        is_admin: bool = False
    ) -> bool:
        """Create new user."""
        try:
            hashed_password = get_password_hash(password)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO users (username, email, hashed_password, is_admin)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, email, hashed_password, is_admin)
                )
                conn.commit()
            logger.info(f"Created user: {username}")
            return True
        except sqlite3.IntegrityError:
            logger.error(f"User already exists: {username}")
            return False

    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user and return user data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username,)
            )
            user = cursor.fetchone()

            if user and verify_password(password, user["hashed_password"]):
                # Update last login
                conn.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.utcnow(), user["id"])
                )
                conn.commit()

                return {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "is_admin": bool(user["is_admin"])
                }

        return None

    def get_user(self, username: str) -> Optional[dict]:
        """Get user by username."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, username, email, is_active, is_admin FROM users WHERE username = ?",
                (username,)
            )
            user = cursor.fetchone()

            if user:
                return dict(user)

        return None
```

**Step 6: Generate Self-Signed Certificate for Development**

Create `/scripts/setup/generate_ssl_cert.sh`:

```bash
#!/bin/bash
# Generate self-signed SSL certificate for local development

CERT_DIR="./data/ssl"
mkdir -p "$CERT_DIR"

openssl req -x509 -newkey rsa:4096 -nodes \
  -out "$CERT_DIR/cert.pem" \
  -keyout "$CERT_DIR/key.pem" \
  -days 365 \
  -subj "/CN=localhost/O=AI File Organizer/C=US"

echo "✓ SSL certificate generated at $CERT_DIR"
echo "  Certificate: $CERT_DIR/cert.pem"
echo "  Private Key: $CERT_DIR/key.pem"
```

**Step 7: Create Environment Template**

Create `/.env.example`:

```bash
# Security Settings
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
CLERK_SECRET_KEY=sk_test_xxxxx
CLERK_PUBLISHABLE_KEY=pk_test_xxxxx

# SSL (for local development)
SSL_CERT_FILE=./data/ssl/cert.pem
SSL_KEY_FILE=./data/ssl/key.pem

# Database
DATABASE_ENCRYPTION_KEY=your-database-encryption-key

# API Keys (optional)
OPENAI_API_KEY=sk-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Environment
ENVIRONMENT=development  # or production
DEBUG=true
```

---

### 1.2 Database Encryption with SQLCipher

#### Installation

Update `requirements.txt`:
```txt
pysqlcipher3>=1.2.0  # SQLCipher Python bindings
```

#### Implementation

Create `/src/core/encrypted_db.py`:

```python
"""Encrypted database manager using SQLCipher."""

import logging
from pathlib import Path
from typing import Any, Optional
from contextlib import contextmanager

try:
    from pysqlcipher3 import dbapi2 as sqlite
    SQLCIPHER_AVAILABLE = True
except ImportError:
    import sqlite3 as sqlite
    SQLCIPHER_AVAILABLE = False
    logging.warning("SQLCipher not available, falling back to standard SQLite")


logger = logging.getLogger(__name__)


class EncryptedDatabase:
    """Database manager with encryption support."""

    def __init__(self, db_path: Path, encryption_key: Optional[str] = None):
        self.db_path = db_path
        self.encryption_key = encryption_key
        self.encrypted = SQLCIPHER_AVAILABLE and encryption_key is not None

        if self.encrypted:
            logger.info(f"Using encrypted database at {db_path}")
        else:
            logger.warning(f"Using unencrypted database at {db_path}")

        self._init_database()

    def _init_database(self):
        """Initialize database with encryption."""
        with self.get_connection() as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")

            # Set secure settings
            if self.encrypted:
                conn.execute("PRAGMA cipher_page_size = 4096")
                conn.execute("PRAGMA kdf_iter = 64000")

            conn.commit()

    @contextmanager
    def get_connection(self):
        """Get database connection context manager."""
        conn = sqlite.connect(str(self.db_path))

        if self.encrypted and self.encryption_key:
            # Set encryption key
            conn.execute(f"PRAGMA key = '{self.encryption_key}'")

            # Verify database is accessible
            try:
                conn.execute("SELECT count(*) FROM sqlite_master")
            except sqlite.DatabaseError:
                raise ValueError("Invalid encryption key or corrupted database")

        try:
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute a query."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor

    def fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Fetch one result."""
        with self.get_connection() as conn:
            conn.row_factory = sqlite.Row
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        """Fetch all results."""
        with self.get_connection() as conn:
            conn.row_factory = sqlite.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


def migrate_to_encrypted(
    old_db_path: Path,
    new_db_path: Path,
    encryption_key: str
) -> bool:
    """Migrate existing database to encrypted version."""
    if not SQLCIPHER_AVAILABLE:
        logger.error("SQLCipher not available, cannot encrypt database")
        return False

    try:
        # Open old database
        old_conn = sqlite.connect(str(old_db_path))

        # Attach new encrypted database
        old_conn.execute(f"ATTACH DATABASE '{new_db_path}' AS encrypted KEY '{encryption_key}'")

        # Export schema and data
        old_conn.execute("SELECT sqlcipher_export('encrypted')")

        # Detach and close
        old_conn.execute("DETACH DATABASE encrypted")
        old_conn.close()

        logger.info(f"Successfully migrated database to encrypted version at {new_db_path}")
        return True

    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        return False
```

---

### 1.3 Improve Exception Handling

#### Pattern to Replace

**Bad (current):**
```python
try:
    # some operation
except Exception as e:
    logger.error(f"Error: {e}")
    return None
```

**Good (target):**
```python
from src.utils.error_handler import FileOperationError, ValidationError

try:
    # some operation
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
    raise FileOperationError(f"Cannot process missing file: {e}") from e
except PermissionError as e:
    logger.error(f"Permission denied: {e}")
    raise FileOperationError(f"Insufficient permissions: {e}") from e
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise ValidationError(f"Invalid input: {e}") from e
```

#### Custom Exception Hierarchy

Update `/src/utils/error_handler.py`:

```python
"""Custom exception hierarchy for better error handling."""


class AIFileOrganizerError(Exception):
    """Base exception for all application errors."""
    pass


class ConfigurationError(AIFileOrganizerError):
    """Configuration or settings related errors."""
    pass


class FileOperationError(AIFileOrganizerError):
    """File operation failures."""
    pass


class ClassificationError(AIFileOrganizerError):
    """AI classification failures."""
    pass


class ValidationError(AIFileOrganizerError):
    """Input validation failures."""
    pass


class DatabaseError(AIFileOrganizerError):
    """Database operation failures."""
    pass


class AuthenticationError(AIFileOrganizerError):
    """Authentication failures."""
    pass


class AuthorizationError(AIFileOrganizerError):
    """Authorization failures."""
    pass


class RateLimitError(AIFileOrganizerError):
    """Rate limit exceeded."""
    pass


class CloudStorageError(AIFileOrganizerError):
    """Cloud storage API errors."""
    pass


class SafetyViolationError(AIFileOrganizerError):
    """Safety guardian blocked operation."""
    pass
```

#### Systematic Replacement Script

Create `/scripts/improve_exception_handling.py`:

```python
"""Find and list files with generic exception handling."""

import re
from pathlib import Path


def find_generic_exceptions(file_path: Path) -> list[dict]:
    """Find generic exception handlers in a file."""
    issues = []

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        # Pattern: except Exception as e: (too generic)
        if re.search(r'except\s+Exception\s+as\s+\w+:', line):
            issues.append({
                'file': str(file_path),
                'line': i,
                'code': line.strip(),
                'severity': 'medium'
            })

        # Pattern: except: (bare except, worst)
        if re.search(r'except\s*:', line):
            issues.append({
                'file': str(file_path),
                'line': i,
                'code': line.strip(),
                'severity': 'high'
            })

    return issues


def main():
    """Scan codebase for exception handling issues."""
    src_dir = Path(__file__).parent.parent / 'src'
    all_issues = []

    for py_file in src_dir.rglob('*.py'):
        issues = find_generic_exceptions(py_file)
        all_issues.extend(issues)

    # Sort by severity
    all_issues.sort(key=lambda x: 0 if x['severity'] == 'high' else 1)

    print(f"Found {len(all_issues)} exception handling issues:\n")

    for issue in all_issues:
        print(f"[{issue['severity'].upper()}] {issue['file']}:{issue['line']}")
        print(f"  {issue['code']}\n")

    # Generate report
    with open('exception_handling_report.txt', 'w') as f:
        for issue in all_issues:
            f.write(f"{issue['file']}:{issue['line']} - {issue['code']}\n")

    print(f"✓ Report saved to exception_handling_report.txt")


if __name__ == "__main__":
    main()
```

---

### 1.4 Type Safety with mypy

#### Setup

Update `requirements.txt`:
```txt
mypy>=1.8.0
types-requests>=2.31.0
types-PyYAML>=6.0.0
```

Create `/mypy.ini`:

```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_any_generics = True
check_untyped_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
strict_equality = True
strict_optional = True

# Per-module options
[mypy-tests.*]
ignore_errors = True

[mypy-pysqlcipher3.*]
ignore_missing_imports = True

[mypy-watchdog.*]
ignore_missing_imports = True

[mypy-mutagen.*]
ignore_missing_imports = True
```

#### Add Type Hints Systematically

Create `/scripts/add_type_hints.py`:

```python
"""Generate type hint stubs for existing code."""

from pathlib import Path
import subprocess


def generate_stubs(src_dir: Path):
    """Generate type stubs using stubgen."""
    subprocess.run([
        "stubgen",
        "-p", "src",
        "-o", "stubs"
    ])


def run_mypy_incremental(src_dir: Path):
    """Run mypy on codebase."""
    result = subprocess.run([
        "mypy",
        str(src_dir),
        "--no-incremental"
    ], capture_output=True, text=True)

    print(result.stdout)
    print(result.stderr)

    # Count errors
    errors = result.stdout.count("error:")
    print(f"\nTotal errors: {errors}")


if __name__ == "__main__":
    src = Path(__file__).parent.parent / "src"
    run_mypy_incremental(src)
```

---

### 1.5 Testing Suite Expansion

#### Setup pytest with Coverage

Update `requirements.txt`:
```txt
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
pytest-mock>=3.11.1
pytest-xdist>=3.3.1  # Parallel testing
pytest-timeout>=2.1.0  # Timeout protection
```

Create `/pytest.ini`:

```ini
[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    --asyncio-mode=auto
    --timeout=30
    -n auto  # Parallel execution

markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    security: marks tests as security-related
```

#### Create Test Structure

```
tests/
├── unit/
│   ├── test_actions.py (existing)
│   ├── test_classifier.py (existing)
│   ├── test_ollama_client.py (existing)
│   ├── test_auth.py (new)
│   ├── test_user_manager.py (new)
│   ├── test_encrypted_db.py (new)
│   └── test_space_optimizer.py (new)
├── integration/
│   ├── test_full_organization_flow.py (new)
│   ├── test_dashboard_api.py (new)
│   └── test_cloud_storage.py (new)
├── security/
│   ├── test_safety_guardian.py (existing)
│   ├── test_authentication.py (new)
│   └── test_rate_limiting.py (new)
└── fixtures/
    ├── sample_files/
    └── conftest.py
```

#### Example Test: Authentication

Create `/tests/unit/test_auth.py`:

```python
"""Tests for authentication system."""

import pytest
from datetime import timedelta
from jose import jwt

from src.ui.auth import (
    create_access_token,
    verify_password,
    get_password_hash,
    get_current_user,
    User
)
from src.config.security import security_settings


def test_password_hashing():
    """Test password hashing and verification."""
    password = "TestPassword123!"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)


def test_create_access_token():
    """Test JWT token creation."""
    data = {"sub": "testuser"}
    token = create_access_token(data, expires_delta=timedelta(minutes=15))

    # Decode token
    payload = jwt.decode(
        token,
        security_settings.jwt_secret_key,
        algorithms=[security_settings.jwt_algorithm]
    )

    assert payload["sub"] == "testuser"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    """Test getting user from valid token."""
    # Create token
    token = create_access_token({"sub": "testuser"})

    # Mock credentials
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token
    )

    # Get user
    user = await get_current_user(credentials)

    assert user.username == "testuser"
    assert user.is_active


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test getting user from invalid token."""
    from fastapi.security import HTTPAuthorizationCredentials
    from fastapi import HTTPException

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid_token"
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials)

    assert exc_info.value.status_code == 401
```

---

## Phase 2: Desktop App Modernization (Weeks 9-16)

### 2.1 Tauri Project Setup

#### Installation

```bash
# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Tauri CLI
cargo install tauri-cli

# Verify installation
cargo tauri --version
```

#### Project Structure

```
ai-file-organizer-desktop/
├── src-tauri/              # Rust backend
│   ├── src/
│   │   ├── main.rs        # Entry point
│   │   ├── commands.rs    # Tauri commands
│   │   ├── python_bridge.rs  # Python engine bridge
│   │   └── storage.rs     # Secure storage
│   ├── Cargo.toml
│   └── tauri.conf.json    # Tauri configuration
├── src/                   # React frontend
│   ├── components/
│   │   ├── Dashboard.tsx
│   │   ├── FileList.tsx
│   │   ├── Settings.tsx
│   │   └── OrganizeButton.tsx
│   ├── hooks/
│   │   ├── useFiles.ts
│   │   └── useSettings.ts
│   ├── lib/
│   │   ├── api.ts
│   │   └── types.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── tsconfig.json
```

#### Initial Tauri Setup

Create `/ai-file-organizer-desktop/src-tauri/tauri.conf.json`:

```json
{
  "build": {
    "beforeBuildCommand": "npm run build",
    "beforeDevCommand": "npm run dev",
    "devPath": "http://localhost:5173",
    "distDir": "../dist"
  },
  "package": {
    "productName": "AI File Organizer",
    "version": "2.0.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "fs": {
        "all": false,
        "readFile": true,
        "writeFile": true,
        "readDir": true,
        "copyFile": true,
        "createDir": true,
        "removeDir": true,
        "removeFile": true,
        "renameFile": true,
        "scope": ["$HOME/**", "$DOCUMENT/**", "$DOWNLOAD/**"]
      },
      "dialog": {
        "all": true
      },
      "shell": {
        "all": false,
        "execute": true,
        "sidecar": true,
        "scope": [
          {
            "name": "python-engine",
            "cmd": "python",
            "args": ["-m", "src.main"]
          }
        ]
      },
      "http": {
        "all": true,
        "scope": ["http://localhost:11434/**"]
      },
      "notification": {
        "all": true
      }
    },
    "bundle": {
      "active": true,
      "category": "Utility",
      "copyright": "Copyright © 2025",
      "deb": {
        "depends": []
      },
      "externalBin": [],
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/128x128@2x.png",
        "icons/icon.icns",
        "icons/icon.ico"
      ],
      "identifier": "com.aifileorganizer.app",
      "longDescription": "AI-powered file organization tool",
      "macOS": {
        "entitlements": null,
        "exceptionDomain": "",
        "frameworks": [],
        "providerShortName": null,
        "signingIdentity": null
      },
      "resources": [],
      "shortDescription": "AI File Organizer",
      "targets": "all",
      "windows": {
        "certificateThumbprint": null,
        "digestAlgorithm": "sha256",
        "timestampUrl": ""
      }
    },
    "security": {
      "csp": "default-src 'self'; connect-src 'self' http://localhost:11434; style-src 'self' 'unsafe-inline'; script-src 'self'"
    },
    "updater": {
      "active": true,
      "endpoints": [
        "https://releases.aifileorganizer.com/{{target}}/{{current_version}}"
      ],
      "dialog": true,
      "pubkey": ""
    },
    "windows": [
      {
        "fullscreen": false,
        "height": 800,
        "resizable": true,
        "title": "AI File Organizer",
        "width": 1200,
        "minWidth": 800,
        "minHeight": 600
      }
    ],
    "systemTray": {
      "iconPath": "icons/icon.png",
      "iconAsTemplate": true
    }
  }
}
```

[Continuing in next message due to length...]

