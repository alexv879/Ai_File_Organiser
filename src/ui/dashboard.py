"""
FastAPI Dashboard Module

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module provides a web-based dashboard for the Private AI File Organiser.
The dashboard includes:
- File inbox (pending files)
- Statistics and time saved
- Settings and configuration
- License management

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict
from time import time
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ..config import get_config
from ..core.db_manager import DatabaseManager
from ..core.classifier import FileClassifier
from ..core.actions import ActionManager
from ..core.duplicates import DuplicateFinder
from ..core.watcher import FolderWatcher
from ..ai.ollama_client import OllamaClient
from ..license.validator import LicenseValidator


# Rate limiting (HIGH-5 FIX)
_rate_limit_cache = defaultdict(list)
_RATE_LIMIT_WINDOW = 60  # seconds
_MAX_REQUESTS_PER_WINDOW = 10  # max deep analyze requests per window


def _check_rate_limit(ip: str) -> bool:
    """
    Check if IP is within rate limit for deep analyze endpoint.

    Args:
        ip: Client IP address

    Returns:
        bool: True if within limit, False if rate limit exceeded
    """
    now = time()

    # Clean old entries outside the window
    _rate_limit_cache[ip] = [t for t in _rate_limit_cache[ip] if now - t < _RATE_LIMIT_WINDOW]

    # Check limit
    if len(_rate_limit_cache[ip]) >= _MAX_REQUESTS_PER_WINDOW:
        return False

    # Record this request
    _rate_limit_cache[ip].append(now)
    return True


# Pydantic models for API requests/responses
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


# Initialize FastAPI app
app = FastAPI(
    title="AI File Organiser Dashboard",
    description="Web dashboard for Private AI File Organiser",
    version="1.0.0"
)

# Global application state
class AppState:
    """Application state container."""
    def __init__(self):
        self.config = get_config()
        self.db = DatabaseManager()
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

        # Initialize watcher (but don't start yet)
        self.watcher = FolderWatcher(
            folders=self.config.watched_folders,
            callback=self.on_file_detected,
            config=self.config
        )

    def on_file_detected(self, file_path: str):
        """
        Callback when watcher detects a new file.

        Args:
            file_path (str): Path to detected file
        """
        # Classify the file
        if self.classifier is None:
            print(f"Warning: Classifier not initialized, skipping file: {file_path}")
            return

        classification = self.classifier.classify(file_path)

        # Add to pending files
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


# ==================== HTML Templates ====================

def get_dashboard_html() -> str:
    """Generate dashboard HTML."""
    template_path = Path(__file__).parent / "templates" / "dashboard.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


# ==================== API Endpoints ====================

@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Serve dashboard HTML."""
    return get_dashboard_html()


@app.get("/api/stats")
def get_stats():
    """Get statistics."""
    return state.db.get_stats('all')


@app.get("/api/pending-files")
def get_pending_files():
    """Get pending files for review."""
    return [
        {
            'file_path': item['file_path'],
            'filename': Path(item['file_path']).name,
            'classification': item['classification']
        }
        for item in state.pending_files
    ]


@app.post("/api/files/approve")
def approve_file(request: FileActionRequest):
    """Approve and execute file action."""
    if state.action_manager is None:
        raise HTTPException(status_code=500, detail="Action manager not initialized")

    # Find file in pending
    file_item = None
    for item in state.pending_files:
        if item['file_path'] == request.file_path:
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
def reject_file(request: FileActionRequest):
    """Reject file action."""
    # Remove from pending
    state.pending_files = [
        item for item in state.pending_files
        if item['file_path'] != request.file_path
    ]

    return {'success': True, 'message': 'File rejected'}


@app.get("/api/history")
def get_history():
    """Get recent file operation history."""
    return state.db.get_recent_logs(50)


@app.get("/api/search")
def search_files(q: Optional[str] = None, category: Optional[str] = None, limit: int = 100):
    """Search moved/renamed files in the history log.

    Params:
        q: substring to search filename/old_path/new_path
        category: optional category filter
        limit: max results
    """
    if state.db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    results = state.db.search_logs(query=q, category=category, limit=limit)  # type: ignore
    return results


@app.get("/api/duplicates/scan")
def scan_duplicates():
    """Scan for duplicate files."""
    if state.duplicate_finder is None:
        raise HTTPException(status_code=500, detail="Duplicate finder not initialized")

    duplicates = []

    for folder in state.config.watched_folders:
        folder_dups = state.duplicate_finder.find_duplicates_in_directory(folder, recursive=True)
        duplicates.extend(folder_dups)

    # Apply safety filtering to avoid presenting application/game files for deletion
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


@app.get("/api/license/status")
def get_license_status():
    """Get license status."""
    if state.license_validator is None:
        raise HTTPException(status_code=500, detail="License validator not initialized")

    return state.license_validator.check_license_status()


@app.post("/api/license/activate")
def activate_license(request: LicenseActivationRequest):
    """Activate license."""
    if state.license_validator is None:
        raise HTTPException(status_code=500, detail="License validator not initialized")

    result = state.license_validator.activate_license(request.license_key)
    return result


@app.post("/api/files/deep-analyze")
def deep_analyze_file(request: DeepAnalyzeRequest, req: Request):
    """
    Perform deep agent analysis on a file.

    This endpoint uses the AgentAnalyzer to perform multi-step reasoning
    and return a detailed classification plan with evidence. The analysis
    is non-destructive and respects all folder policies and blacklists.

    Security: Validates file is in watched folders or pending list to prevent
    path traversal attacks and unauthorized file access. Rate limited to prevent
    DOS attacks.

    Args:
        request: Contains file_path to analyze
        req: FastAPI Request object for rate limiting

    Returns:
        Dict: Agent analysis result with category, suggested_path, evidence, etc.
    """
    if state.classifier is None:
        raise HTTPException(status_code=500, detail="Classifier not initialized")

    # Rate limit check (HIGH-5 FIX)
    client_ip = req.client.host if req.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {_MAX_REQUESTS_PER_WINDOW} requests per {_RATE_LIMIT_WINDOW} seconds."
        )

    file_path = request.file_path

    # Validate file exists
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Validate file is in watched folders or pending list (HIGH-7 FIX)
    file_path_obj = Path(file_path).resolve()

    # Check if in pending files
    is_pending = any(
        Path(item['file_path']).resolve() == file_path_obj
        for item in state.pending_files
    )

    # Check if in watched folders
    is_watched = False
    for watched in state.config.watched_folders:
        watched_path = Path(watched).expanduser().resolve()
        try:
            if os.path.commonpath([str(file_path_obj), str(watched_path)]) == str(watched_path):
                is_watched = True
                break
        except ValueError:
            # Different drives on Windows - skip
            continue

    if not is_pending and not is_watched:
        raise HTTPException(
            status_code=403,
            detail="File not in watched folders or pending list"
        )

    # Check blacklist (defense in depth)
    blacklist = getattr(state.config, 'path_blacklist', []) or []
    for blacklisted in blacklist:
        try:
            blacklisted_resolved = Path(blacklisted).expanduser().resolve()
            if os.path.commonpath([str(file_path_obj), str(blacklisted_resolved)]) == str(blacklisted_resolved):
                raise HTTPException(
                    status_code=403,
                    detail="File is in blacklisted location"
                )
        except (ValueError, OSError):
            # Different drives on Windows - skip
            continue

    # Perform deep analysis using classifier with deep_analysis=True
    try:
        result = state.classifier.classify(str(file_path_obj), deep_analysis=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deep analysis failed: {str(e)}")


@app.post("/api/settings")
def update_settings(request: SettingsUpdateRequest):
    """Update settings."""
    if request.auto_mode is not None:
        state.config.update('auto_mode', request.auto_mode)

    if request.dry_run is not None:
        state.config.update('dry_run', request.dry_run)
        if state.action_manager is not None:
            state.action_manager.set_dry_run(request.dry_run)

    if request.enable_ai is not None:
        state.config.update('classification.enable_ai', request.enable_ai)

    state.config.save()

    return {'success': True, 'message': 'Settings updated'}


@app.post("/api/watcher/start")
def start_watcher():
    """Start folder watcher."""
    state.start_watcher()
    return {'success': True, 'message': 'Watcher started'}


@app.post("/api/watcher/stop")
def stop_watcher():
    """Stop folder watcher."""
    state.stop_watcher()
    return {'success': True, 'message': 'Watcher stopped'}


def run_dashboard(host: str = "127.0.0.1", port: int = 5000):
    """
    Run the dashboard server (LOCAL ONLY - PRIVACY PROTECTED).

    SECURITY: This dashboard is LOCKED to localhost (127.0.0.1) only.
    It cannot be accessed from the network to protect your privacy.

    Args:
        host (str): Host to bind to (FORCED to 127.0.0.1 for security)
        port (int): Port to listen on
    """
    import uvicorn

    # SECURITY: Force localhost-only access for privacy
    # This prevents network access and protects user data
    if host != "127.0.0.1" and host != "localhost":
        print("⚠️  WARNING: For privacy protection, dashboard is LOCKED to localhost only!")
        print("   Changing host to 127.0.0.1 (local access only)")
        host = "127.0.0.1"

    print(f"""
    ============================================
    AI File Organiser - Dashboard
    🔒 PRIVACY PROTECTED - LOCAL ACCESS ONLY
    ============================================

    Dashboard: http://127.0.0.1:{port}

    ✅ Secure: Only accessible from this computer
    🔒 Private: No network exposure
    🛡️  Protected: Your files stay private

    Press Ctrl+C to stop
    ============================================
    """)

    # Force localhost binding for security
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    run_dashboard()
