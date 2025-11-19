"""
Secure FastAPI Dashboard with Authentication

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.

This is the secure version of the dashboard with JWT authentication,
rate limiting, HTTPS support, and CORS protection.
"""

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict
from time import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.security import get_security_settings
from src.ui.auth import (
    get_current_user,
    require_admin,
    create_access_token,
    User,
    LoginResponse,
    validate_password_strength
)
from src.core.user_manager import get_user_manager
from src.config import get_config
from src.core.db_manager import DatabaseManager
from src.core.classifier import FileClassifier
from src.core.actions import ActionManager
from src.core.duplicates import DuplicateFinder
from src.core.watcher import FolderWatcher
from src.ai.ollama_client import OllamaClient
from src.license.validator import LicenseValidator

# Security settings
security_settings = get_security_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="AI File Organizer Dashboard (Secure)",
    description="Secure web dashboard with JWT authentication",
    version="2.0.0",
    docs_url="/api/docs" if security_settings.debug else None,
    redoc_url="/api/redoc" if security_settings.debug else None,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
if security_settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=security_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=security_settings.allowed_methods,
        allow_headers=["*"],
    )

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.aifileorganizer.com"]
)


# ==================== Request Models ====================

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class FileActionRequest(BaseModel):
    file_path: str
    action: str  # 'approve', 'reject', 'custom'
    custom_path: Optional[str] = None


class LicenseActivationRequest(BaseModel):
    license_key: str


class SettingsUpdateRequest(BaseModel):
    auto_mode: Optional[bool] = None
    dry_run: Optional[bool] = None
    enable_ai: Optional[bool] = None


class DeepAnalyzeRequest(BaseModel):
    file_path: str


# ==================== Application State ====================

class AppState:
    """Application state container."""

    def __init__(self):
        self.config = get_config()
        self.db = DatabaseManager()
        self.user_manager = get_user_manager()
        self.ollama = None
        self.classifier = None
        self.action_manager = None
        self.duplicate_finder = None
        self.watcher = None
        self.license_validator = None
        self.pending_files: List[Dict[str, Any]] = []

        self._initialize()

    def _initialize(self):
        """Initialize all components."""
        # Initialize Ollama client
        self.ollama = OllamaClient(
            base_url=self.config.ollama_base_url,
            model=self.config.ollama_model,
            timeout=self.config.get('ollama_timeout', 30)
        )

        # Initialize classifier
        ollama_client = self.ollama if self.ollama.is_available() else None
        self.classifier = FileClassifier(self.config, ollama_client)

        # Initialize action manager
        self.action_manager = ActionManager(self.config, self.db)

        # Initialize duplicate finder
        self.duplicate_finder = DuplicateFinder(self.config, self.db)

        # Initialize license validator
        self.license_validator = LicenseValidator(self.config, self.db)

        # Initialize watcher
        self.watcher = FolderWatcher(
            folders=self.config.watched_folders,
            callback=self.on_file_detected,
            config=self.config
        )

        # Create default admin user if none exists
        self._create_default_admin()

    def _create_default_admin(self):
        """Create default admin user if no users exist."""
        users = self.user_manager.list_users()
        if not users:
            try:
                # Create default admin (user MUST change this password)
                self.user_manager.create_user(
                    username="admin",
                    email="admin@localhost",
                    password="ChangeMe123!",
                    is_admin=True
                )
                print("⚠️  DEFAULT ADMIN CREATED: username='admin', password='ChangeMe123!'")
                print("⚠️  PLEASE LOGIN AND CHANGE THE PASSWORD IMMEDIATELY!")
            except Exception as e:
                print(f"Warning: Could not create default admin: {e}")

    def on_file_detected(self, file_path: str):
        """Callback when watcher detects a new file."""
        if self.classifier is None:
            return

        classification = self.classifier.classify(file_path)
        self.pending_files.append({
            'file_path': file_path,
            'classification': classification,
            'detected_at': Path(file_path).stat().st_mtime
        })

    def start_watcher(self):
        """Start the folder watcher."""
        if self.watcher and not self.watcher._running:
            self.watcher.start(background=True)

    def stop_watcher(self):
        """Stop the folder watcher."""
        if self.watcher and self.watcher._running:
            self.watcher.stop()


# Create global app state
state = AppState()


# ==================== Security Headers Middleware ====================

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    if security_settings.enable_security_headers:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' http://localhost:11434;"
        )

    return response


# ==================== Authentication Endpoints ====================

@app.post("/api/auth/register", response_model=User)
@limiter.limit("5/hour")  # Strict rate limit on registration
async def register(request: Request, register_data: RegisterRequest):
    """Register a new user."""
    try:
        # Validate password strength
        strength = validate_password_strength(register_data.password)
        if not strength.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Password does not meet requirements", "errors": strength.errors}
            )

        # Create user
        success = state.user_manager.create_user(
            username=register_data.username,
            email=register_data.email,
            password=register_data.password,
            is_admin=False
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )

        # Get the created user
        user = state.user_manager.get_user(register_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User created but could not be retrieved"
            )

        return user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/api/auth/login", response_model=LoginResponse)
@limiter.limit("10/minute")  # Rate limit login attempts
async def login(request: Request, login_data: LoginRequest):
    """Authenticate user and return JWT token."""
    # Get client IP for audit logging
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Authenticate user
    user = state.user_manager.authenticate_user(
        username=login_data.username,
        password=login_data.password,
        ip_address=client_ip,
        user_agent=user_agent
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    from datetime import timedelta
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=security_settings.jwt_expiry_minutes)
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=security_settings.jwt_expiry_minutes * 60,
        user=user
    )


@app.get("/api/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return current_user


@app.post("/api/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should delete token)."""
    # In a stateless JWT system, logout is handled client-side by deleting the token
    # For additional security, you could implement a token blacklist here
    return {"message": "Logged out successfully"}


# ==================== File Organization Endpoints (Protected) ====================

@app.get("/api/stats")
@limiter.limit("30/minute")
async def get_stats(request: Request, current_user: User = Depends(get_current_user)):
    """Get statistics (requires authentication)."""
    return state.db.get_stats('all')


@app.get("/api/pending-files")
@limiter.limit("30/minute")
async def get_pending_files(request: Request, current_user: User = Depends(get_current_user)):
    """Get pending files for review (requires authentication)."""
    return [
        {
            'file_path': item['file_path'],
            'filename': Path(item['file_path']).name,
            'classification': item['classification']
        }
        for item in state.pending_files
    ]


@app.post("/api/files/approve")
@limiter.limit("60/minute")
async def approve_file(
    request: Request,
    file_request: FileActionRequest,
    current_user: User = Depends(get_current_user)
):
    """Approve and execute file action (requires authentication)."""
    if state.action_manager is None:
        raise HTTPException(status_code=500, detail="Action manager not initialized")

    # Find file in pending
    file_item = None
    for item in state.pending_files:
        if item['file_path'] == file_request.file_path:
            file_item = item
            break

    if not file_item:
        raise HTTPException(status_code=404, detail="File not found in pending list")

    # Execute action
    result = state.action_manager.execute(
        file_path=file_item['file_path'],
        classification=file_item['classification'],
        user_approved=True
    )

    # Remove from pending
    state.pending_files.remove(file_item)

    return result


@app.post("/api/files/reject")
@limiter.limit("60/minute")
async def reject_file(
    request: Request,
    file_request: FileActionRequest,
    current_user: User = Depends(get_current_user)
):
    """Reject file action (requires authentication)."""
    state.pending_files = [
        item for item in state.pending_files
        if item['file_path'] != file_request.file_path
    ]
    return {'success': True, 'message': 'File rejected'}


@app.get("/api/history")
@limiter.limit("30/minute")
async def get_history(request: Request, current_user: User = Depends(get_current_user)):
    """Get recent file operation history (requires authentication)."""
    return state.db.get_recent_logs(50)


@app.get("/api/search")
@limiter.limit("60/minute")
async def search_files(
    request: Request,
    current_user: User = Depends(get_current_user),
    q: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
):
    """Search moved/renamed files (requires authentication)."""
    if state.db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    results = state.db.search_logs(query=q, category=category, limit=limit)
    return results


@app.get("/api/duplicates/scan")
@limiter.limit("10/hour")  # CPU-intensive operation
async def scan_duplicates(request: Request, current_user: User = Depends(get_current_user)):
    """Scan for duplicate files (requires authentication)."""
    if state.duplicate_finder is None:
        raise HTTPException(status_code=500, detail="Duplicate finder not initialized")

    duplicates = []
    for folder in state.config.watched_folders:
        folder_dups = state.duplicate_finder.find_duplicates_in_directory(folder, recursive=True)
        duplicates.extend(folder_dups)

    safe_groups, protected_groups, protected_files = state.duplicate_finder.filter_protected_duplicates(duplicates)
    summary = state.duplicate_finder.get_duplicate_summary(safe_groups)

    return {
        'groups': safe_groups,
        'summary': summary,
        'protected': {
            'protected_groups': protected_groups,
            'protected_files': protected_files
        }
    }


@app.post("/api/files/deep-analyze")
@limiter.limit("10/minute")
async def deep_analyze_file(
    request: Request,
    analyze_request: DeepAnalyzeRequest,
    current_user: User = Depends(get_current_user)
):
    """Perform deep AI analysis on a file (requires authentication)."""
    if state.classifier is None:
        raise HTTPException(status_code=500, detail="Classifier not initialized")

    file_path = analyze_request.file_path

    # Validate file exists
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Security validation
    file_path_obj = Path(file_path).resolve()

    # Check if in pending or watched folders
    is_pending = any(
        Path(item['file_path']).resolve() == file_path_obj
        for item in state.pending_files
    )

    is_watched = False
    for watched in state.config.watched_folders:
        watched_path = Path(watched).expanduser().resolve()
        try:
            if os.path.commonpath([str(file_path_obj), str(watched_path)]) == str(watched_path):
                is_watched = True
                break
        except ValueError:
            continue

    if not is_pending and not is_watched:
        raise HTTPException(
            status_code=403,
            detail="File not in watched folders or pending list"
        )

    # Perform analysis
    try:
        result = state.classifier.classify(str(file_path_obj), deep_analysis=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deep analysis failed: {str(e)}")


# ==================== Settings Endpoints (Protected) ====================

@app.post("/api/settings")
@limiter.limit("30/minute")
async def update_settings(
    request: Request,
    settings_request: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update settings (requires authentication)."""
    if settings_request.auto_mode is not None:
        state.config.update('auto_mode', settings_request.auto_mode)

    if settings_request.dry_run is not None:
        state.config.update('dry_run', settings_request.dry_run)
        if state.action_manager is not None:
            state.action_manager.set_dry_run(settings_request.dry_run)

    if settings_request.enable_ai is not None:
        state.config.update('classification.enable_ai', settings_request.enable_ai)

    state.config.save()
    return {'success': True, 'message': 'Settings updated'}


@app.post("/api/watcher/start")
@limiter.limit("10/minute")
async def start_watcher(request: Request, current_user: User = Depends(get_current_user)):
    """Start folder watcher (requires authentication)."""
    state.start_watcher()
    return {'success': True, 'message': 'Watcher started'}


@app.post("/api/watcher/stop")
@limiter.limit("10/minute")
async def stop_watcher(request: Request, current_user: User = Depends(get_current_user)):
    """Stop folder watcher (requires authentication)."""
    state.stop_watcher()
    return {'success': True, 'message': 'Watcher stopped'}


# ==================== Admin Endpoints (Admin Only) ====================

@app.get("/api/admin/users")
@limiter.limit("30/minute")
async def list_users(request: Request, admin_user: User = Depends(require_admin)):
    """List all users (admin only)."""
    users = state.user_manager.list_users(include_inactive=True)
    return users


@app.post("/api/admin/users/{username}/deactivate")
@limiter.limit("10/minute")
async def deactivate_user(
    request: Request,
    username: str,
    admin_user: User = Depends(require_admin)
):
    """Deactivate a user (admin only)."""
    if username == admin_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    success = state.user_manager.deactivate_user(username)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"User {username} deactivated"}


@app.get("/api/admin/stats/detailed")
@limiter.limit("30/minute")
async def get_detailed_stats(request: Request, admin_user: User = Depends(require_admin)):
    """Get detailed system statistics (admin only)."""
    return {
        "users": {
            "total": len(state.user_manager.list_users(include_inactive=True)),
            "active": len(state.user_manager.list_users(include_inactive=False)),
        },
        "files": state.db.get_stats('all'),
        "pending": len(state.pending_files),
        "watcher_running": state.watcher._running if state.watcher else False
    }


# ==================== License Endpoints ====================

@app.get("/api/license/status")
@limiter.limit("30/minute")
async def get_license_status(request: Request, current_user: User = Depends(get_current_user)):
    """Get license status (requires authentication)."""
    if state.license_validator is None:
        raise HTTPException(status_code=500, detail="License validator not initialized")

    return state.license_validator.check_license_status()


@app.post("/api/license/activate")
@limiter.limit("5/hour")
async def activate_license(
    request: Request,
    license_request: LicenseActivationRequest,
    current_user: User = Depends(get_current_user)
):
    """Activate license (requires authentication)."""
    if state.license_validator is None:
        raise HTTPException(status_code=500, detail="License validator not initialized")

    result = state.license_validator.activate_license(license_request.license_key)
    return result


# ==================== Health Check (Public) ====================

@app.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Public health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "authentication": "enabled"
    }


# ==================== Frontend (Public) ====================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve dashboard HTML (login page if not authenticated)."""
    template_path = Path(__file__).parent / "templates" / "dashboard_secure.html"

    # If template doesn't exist yet, return simple message
    if not template_path.exists():
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI File Organizer - Secure Dashboard</title>
        </head>
        <body>
            <h1>AI File Organizer 2.0 - Secure Dashboard</h1>
            <p>Please use the API endpoints at <code>/api/*</code></p>
            <p>API Documentation: <a href="/api/docs">/api/docs</a></p>
            <p>Login endpoint: <code>POST /api/auth/login</code></p>
        </body>
        </html>
        """)

    with open(template_path, 'r', encoding='utf-8') as f:
        return HTMLResponse(content=f.read())


# ==================== Run Function ====================

def run_secure_dashboard(host: str = "127.0.0.1", port: int = 8000):
    """
    Run the secure dashboard server with HTTPS.

    Args:
        host: Host to bind to
        port: Port to listen on
    """
    import uvicorn

    # Production: require HTTPS
    ssl_keyfile = security_settings.ssl_key_file if security_settings.ssl_enabled else None
    ssl_certfile = security_settings.ssl_cert_file if security_settings.ssl_enabled else None

    print(f"""
    ============================================
    AI File Organizer 2.0 - Secure Dashboard
    🔒 AUTHENTICATION ENABLED
    ============================================

    Dashboard: {'https' if ssl_keyfile else 'http'}://{host}:{port}
    API Docs: {'https' if ssl_keyfile else 'http'}://{host}:{port}/api/docs

    ✅ JWT Authentication: Enabled
    🔒 Rate Limiting: Enabled
    🛡️  CORS Protection: {'Enabled' if security_settings.cors_enabled else 'Disabled'}
    🔐 HTTPS: {'Enabled' if ssl_keyfile else 'Disabled (Development)'}

    Default Admin:
      Username: admin
      Password: ChangeMe123!
      ⚠️  CHANGE PASSWORD IMMEDIATELY!

    Press Ctrl+C to stop
    ============================================
    """)

    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        log_level="info"
    )


if __name__ == "__main__":
    run_secure_dashboard()
