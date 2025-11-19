"""Cloud storage integrations for AI File Organizer.

This package provides unified interfaces for multiple cloud storage providers:
- Microsoft OneDrive (via Microsoft Graph API)
- Google Drive (via Google Drive API v3)
- Dropbox (via Dropbox API v2)

All integrations use OAuth 2.0 for authentication and provide:
- File upload/download
- Organization and folder management
- Space-saving features (placeholders)
- Two-way sync capabilities
"""

from .base import CloudStorageProvider, CloudFile, CloudFolder, SyncStatus
from .onedrive import OneDriveProvider
from .google_drive import GoogleDriveProvider
from .dropbox import DropboxProvider

__all__ = [
    'CloudStorageProvider',
    'CloudFile',
    'CloudFolder',
    'SyncStatus',
    'OneDriveProvider',
    'GoogleDriveProvider',
    'DropboxProvider',
]
