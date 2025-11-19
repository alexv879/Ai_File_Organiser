"""Base classes for cloud storage providers.

This module defines the abstract interface that all cloud storage
providers must implement, ensuring consistent behavior across
OneDrive, Google Drive, Dropbox, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, BinaryIO
import logging

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """File synchronization status."""
    SYNCED = "synced"              # File is up-to-date in cloud
    PENDING = "pending"            # Upload/download pending
    DOWNLOADING = "downloading"    # Currently downloading
    UPLOADING = "uploading"        # Currently uploading
    CONFLICT = "conflict"          # Sync conflict detected
    ERROR = "error"                # Sync error occurred
    PLACEHOLDER = "placeholder"    # Local placeholder (file in cloud only)


@dataclass
class CloudFile:
    """Represents a file in cloud storage."""

    id: str                                # Cloud provider's file ID
    name: str                              # File name
    path: str                              # Full cloud path
    size: int                              # File size in bytes
    modified_time: datetime                 # Last modified timestamp
    created_time: datetime                  # Creation timestamp
    is_folder: bool = False                # Whether this is a folder
    mime_type: Optional[str] = None        # MIME type
    md5_hash: Optional[str] = None         # MD5 hash for integrity
    sha1_hash: Optional[str] = None        # SHA1 hash
    download_url: Optional[str] = None     # Temporary download URL
    parent_id: Optional[str] = None        # Parent folder ID
    sync_status: SyncStatus = SyncStatus.SYNCED
    local_path: Optional[Path] = None      # Local file path if synced
    metadata: Dict[str, Any] = None        # Additional provider-specific metadata

    def __post_init__(self):
        """Initialize metadata dict if None."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CloudFolder:
    """Represents a folder in cloud storage."""

    id: str                                # Cloud provider's folder ID
    name: str                              # Folder name
    path: str                              # Full cloud path
    parent_id: Optional[str] = None        # Parent folder ID
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    item_count: int = 0                    # Number of items in folder
    metadata: Dict[str, Any] = None        # Additional metadata

    def __post_init__(self):
        """Initialize metadata dict if None."""
        if self.metadata is None:
            self.metadata = {}


class CloudStorageProvider(ABC):
    """Abstract base class for cloud storage providers.

    All cloud storage integrations (OneDrive, Google Drive, Dropbox)
    must inherit from this class and implement all abstract methods.

    This ensures a consistent API across different providers, making
    it easy to switch between them or support multiple providers.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None
    ):
        """Initialize cloud storage provider.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: OAuth redirect URI
            access_token: Optional existing access token
            refresh_token: Optional existing refresh token
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @abstractmethod
    def get_authorization_url(self) -> str:
        """Get OAuth authorization URL for user to visit.

        Returns:
            str: Authorization URL

        Example:
            >>> provider = OneDriveProvider(...)
            >>> auth_url = provider.get_authorization_url()
            >>> print(f"Visit: {auth_url}")
        """
        pass

    @abstractmethod
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dict: Token response with access_token, refresh_token, etc.

        Example:
            >>> provider = OneDriveProvider(...)
            >>> tokens = provider.exchange_code_for_token(auth_code)
            >>> provider.access_token = tokens['access_token']
        """
        pass

    @abstractmethod
    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh the access token using refresh token.

        Returns:
            Dict: New token response

        Example:
            >>> provider = OneDriveProvider(...)
            >>> new_tokens = provider.refresh_access_token()
        """
        pass

    @abstractmethod
    def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information.

        Returns:
            Dict: User info (email, name, quota, etc.)

        Example:
            >>> provider = OneDriveProvider(...)
            >>> user = provider.get_user_info()
            >>> print(f"Email: {user['email']}")
        """
        pass

    @abstractmethod
    def get_quota(self) -> Dict[str, int]:
        """Get storage quota information.

        Returns:
            Dict: With keys 'total', 'used', 'remaining' (all in bytes)

        Example:
            >>> provider = OneDriveProvider(...)
            >>> quota = provider.get_quota()
            >>> print(f"Used: {quota['used']} / {quota['total']} bytes")
        """
        pass

    @abstractmethod
    def list_files(
        self,
        folder_id: Optional[str] = None,
        recursive: bool = False
    ) -> List[CloudFile]:
        """List files in a folder.

        Args:
            folder_id: Folder ID (None = root)
            recursive: List files recursively

        Returns:
            List[CloudFile]: List of files

        Example:
            >>> provider = OneDriveProvider(...)
            >>> files = provider.list_files()
            >>> for file in files:
            ...     print(file.name)
        """
        pass

    @abstractmethod
    def get_file_metadata(self, file_id: str) -> CloudFile:
        """Get file metadata.

        Args:
            file_id: File ID

        Returns:
            CloudFile: File metadata

        Example:
            >>> provider = OneDriveProvider(...)
            >>> file = provider.get_file_metadata("file123")
            >>> print(f"Size: {file.size} bytes")
        """
        pass

    @abstractmethod
    def download_file(
        self,
        file_id: str,
        local_path: Path,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """Download a file from cloud storage.

        Args:
            file_id: Cloud file ID
            local_path: Local path to save file
            progress_callback: Optional callback for progress (bytes_downloaded, total_bytes)

        Returns:
            bool: True if download successful

        Example:
            >>> def progress(downloaded, total):
            ...     print(f"Progress: {downloaded}/{total}")
            >>> provider.download_file("file123", Path("file.txt"), progress)
        """
        pass

    @abstractmethod
    def upload_file(
        self,
        local_path: Path,
        cloud_folder_id: Optional[str] = None,
        cloud_filename: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> CloudFile:
        """Upload a file to cloud storage.

        Args:
            local_path: Local file path
            cloud_folder_id: Destination folder ID (None = root)
            cloud_filename: Optional custom filename
            progress_callback: Optional progress callback

        Returns:
            CloudFile: Uploaded file metadata

        Example:
            >>> provider.upload_file(Path("file.txt"))
        """
        pass

    @abstractmethod
    def create_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None
    ) -> CloudFolder:
        """Create a new folder.

        Args:
            folder_name: Name of new folder
            parent_folder_id: Parent folder ID (None = root)

        Returns:
            CloudFolder: Created folder metadata

        Example:
            >>> folder = provider.create_folder("Documents")
            >>> print(folder.id)
        """
        pass

    @abstractmethod
    def move_file(
        self,
        file_id: str,
        destination_folder_id: str
    ) -> CloudFile:
        """Move a file to a different folder.

        Args:
            file_id: File ID to move
            destination_folder_id: Destination folder ID

        Returns:
            CloudFile: Updated file metadata

        Example:
            >>> provider.move_file("file123", "folder456")
        """
        pass

    @abstractmethod
    def rename_file(self, file_id: str, new_name: str) -> CloudFile:
        """Rename a file.

        Args:
            file_id: File ID
            new_name: New filename

        Returns:
            CloudFile: Updated file metadata

        Example:
            >>> provider.rename_file("file123", "newname.txt")
        """
        pass

    @abstractmethod
    def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """Delete a file.

        Args:
            file_id: File ID
            permanent: Permanently delete (vs trash)

        Returns:
            bool: True if deleted successfully

        Example:
            >>> provider.delete_file("file123")  # Move to trash
            >>> provider.delete_file("file123", permanent=True)  # Permanent
        """
        pass

    @abstractmethod
    def search_files(
        self,
        query: str,
        folder_id: Optional[str] = None
    ) -> List[CloudFile]:
        """Search for files.

        Args:
            query: Search query
            folder_id: Optional folder to search within

        Returns:
            List[CloudFile]: Matching files

        Example:
            >>> files = provider.search_files("contract")
            >>> for file in files:
            ...     print(file.name)
        """
        pass

    # Helper methods (implemented here, not abstract)

    def is_authenticated(self) -> bool:
        """Check if provider has valid access token.

        Returns:
            bool: True if authenticated
        """
        return self.access_token is not None

    def ensure_authenticated(self) -> None:
        """Ensure provider is authenticated, raise exception if not.

        Raises:
            ValueError: If not authenticated
        """
        if not self.is_authenticated():
            raise ValueError(
                f"{self.__class__.__name__} is not authenticated. "
                "Please complete OAuth flow first."
            )

    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            str: Formatted size (e.g., "1.5 MB")

        Example:
            >>> provider.format_size(1536000)
            '1.5 MB'
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
