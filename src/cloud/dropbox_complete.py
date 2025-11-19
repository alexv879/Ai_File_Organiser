"""Dropbox integration via Dropbox API v2.

Complete implementation using dropbox package.

Installation:
    pip install dropbox

API Documentation: https://www.dropbox.com/developers/documentation/python
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import logging

try:
    import dropbox
    from dropbox.files import WriteMode
    from dropbox.oauth import DropboxOAuth2Flow
    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False
    logging.warning("Dropbox package not installed. Run: pip install dropbox")

from .base import CloudStorageProvider, CloudFile, CloudFolder, SyncStatus

logger = logging.getLogger(__name__)


class DropboxProvider(CloudStorageProvider):
    """Dropbox cloud storage provider using Dropbox API v2.

    Requires dropbox package.
    """

    AUTH_URL_TEMPLATE = "https://www.dropbox.com/oauth2/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&token_access_type=offline"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None
    ):
        """Initialize Dropbox provider."""
        if not DROPBOX_AVAILABLE:
            raise ImportError(
                "Dropbox integration requires dropbox package. "
                "Install with: pip install dropbox"
            )

        super().__init__(client_id, client_secret, redirect_uri, access_token, refresh_token)

        self.dbx = None

        if access_token:
            self.dbx = dropbox.Dropbox(access_token)

    def get_authorization_url(self) -> str:
        """Get OAuth authorization URL."""
        return self.AUTH_URL_TEMPLATE.format(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri
        )

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        import requests

        token_url = "https://api.dropboxapi.com/oauth2/token"

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri
        }

        response = requests.post(token_url, data=data)
        response.raise_for_status()

        tokens = response.json()
        self.access_token = tokens['access_token']
        self.refresh_token = tokens.get('refresh_token')

        self.dbx = dropbox.Dropbox(self.access_token)

        return tokens

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        import requests

        token_url = "https://api.dropboxapi.com/oauth2/token"

        data = {
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        response = requests.post(token_url, data=data)
        response.raise_for_status()

        tokens = response.json()
        self.access_token = tokens['access_token']

        self.dbx = dropbox.Dropbox(self.access_token)

        return tokens

    def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information."""
        self.ensure_authenticated()

        account = self.dbx.users_get_current_account()

        return {
            "displayName": account.name.display_name,
            "email": account.email,
            "account_id": account.account_id
        }

    def get_quota(self) -> Dict[str, int]:
        """Get storage quota information."""
        self.ensure_authenticated()

        space_usage = self.dbx.users_get_space_usage()

        total = space_usage.allocation.get_individual().allocated
        used = space_usage.used

        return {
            "total": total,
            "used": used,
            "remaining": total - used
        }

    def _parse_file_metadata(self, item) -> CloudFile:
        """Parse Dropbox file to CloudFile."""
        if isinstance(item, dropbox.files.FileMetadata):
            file_id = item.id
            name = item.name
            size = item.size
            is_folder = False
            modified_time = item.server_modified
            created_time = item.client_modified

            # Dropbox uses content_hash instead of md5
            md5_hash = item.content_hash if hasattr(item, 'content_hash') else None

            return CloudFile(
                id=file_id,
                name=name,
                path=item.path_display,
                size=size,
                modified_time=modified_time,
                created_time=created_time,
                is_folder=is_folder,
                mime_type=None,  # Dropbox doesn't provide MIME type
                md5_hash=md5_hash,
                parent_id=str(Path(item.path_display).parent),
                sync_status=SyncStatus.SYNCED
            )
        elif isinstance(item, dropbox.files.FolderMetadata):
            return CloudFile(
                id=item.id,
                name=item.name,
                path=item.path_display,
                size=0,
                modified_time=datetime.now(),
                created_time=datetime.now(),
                is_folder=True,
                parent_id=str(Path(item.path_display).parent),
                sync_status=SyncStatus.SYNCED
            )
        else:
            raise ValueError(f"Unknown metadata type: {type(item)}")

    def list_files(
        self,
        folder_id: Optional[str] = None,
        recursive: bool = False
    ) -> List[CloudFile]:
        """List files in a folder."""
        self.ensure_authenticated()

        path = folder_id or ""

        try:
            result = self.dbx.files_list_folder(path, recursive=recursive)
            files = [self._parse_file_metadata(entry) for entry in result.entries]

            # Handle pagination
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                files.extend([self._parse_file_metadata(entry) for entry in result.entries])

            return files

        except dropbox.exceptions.ApiError as e:
            logger.error(f"Error listing files: {e}")
            return []

    def get_file_metadata(self, file_id: str) -> CloudFile:
        """Get file metadata."""
        self.ensure_authenticated()

        metadata = self.dbx.files_get_metadata(file_id)
        return self._parse_file_metadata(metadata)

    def download_file(
        self,
        file_id: str,
        local_path: Path,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """Download file from Dropbox."""
        self.ensure_authenticated()

        local_path.parent.mkdir(parents=True, exist_ok=True)

        metadata, response = self.dbx.files_download(file_id)

        total_size = metadata.size
        downloaded = 0

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback:
                        progress_callback(downloaded, total_size)

        logger.info(f"Downloaded {metadata.name} to {local_path}")
        return True

    def upload_file(
        self,
        local_path: Path,
        cloud_folder_id: Optional[str] = None,
        cloud_filename: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> CloudFile:
        """Upload file to Dropbox."""
        self.ensure_authenticated()

        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        filename = cloud_filename or local_path.name

        if cloud_folder_id:
            cloud_path = f"{cloud_folder_id}/{filename}"
        else:
            cloud_path = f"/{filename}"

        file_size = local_path.stat().st_size

        # For small files (< 150MB), use simple upload
        if file_size < 150 * 1024 * 1024:
            with open(local_path, 'rb') as f:
                data = f.read()

            metadata = self.dbx.files_upload(
                data,
                cloud_path,
                mode=WriteMode('overwrite')
            )

        else:
            # For large files, use upload session
            chunk_size = 4 * 1024 * 1024  # 4MB chunks

            with open(local_path, 'rb') as f:
                # Start upload session
                upload_session_start = self.dbx.files_upload_session_start(
                    f.read(chunk_size)
                )

                cursor = dropbox.files.UploadSessionCursor(
                    session_id=upload_session_start.session_id,
                    offset=f.tell()
                )

                commit = dropbox.files.CommitInfo(path=cloud_path)

                # Upload chunks
                while f.tell() < file_size:
                    if (file_size - f.tell()) <= chunk_size:
                        # Last chunk
                        metadata = self.dbx.files_upload_session_finish(
                            f.read(chunk_size),
                            cursor,
                            commit
                        )
                    else:
                        self.dbx.files_upload_session_append_v2(
                            f.read(chunk_size),
                            cursor
                        )
                        cursor.offset = f.tell()

                    if progress_callback:
                        progress_callback(f.tell(), file_size)

        logger.info(f"Uploaded {filename} to Dropbox")
        return self._parse_file_metadata(metadata)

    def create_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None
    ) -> CloudFolder:
        """Create new folder in Dropbox."""
        self.ensure_authenticated()

        if parent_folder_id:
            folder_path = f"{parent_folder_id}/{folder_name}"
        else:
            folder_path = f"/{folder_name}"

        metadata = self.dbx.files_create_folder_v2(folder_path)

        return CloudFolder(
            id=metadata.metadata.id,
            name=metadata.metadata.name,
            path=metadata.metadata.path_display,
            parent_id=str(Path(metadata.metadata.path_display).parent),
            created_time=datetime.now(),
            metadata=metadata.metadata
        )

    def move_file(self, file_id: str, destination_folder_id: str) -> CloudFile:
        """Move file to different folder."""
        self.ensure_authenticated()

        # Get filename from file_id (path)
        filename = Path(file_id).name
        new_path = f"{destination_folder_id}/{filename}"

        metadata = self.dbx.files_move_v2(file_id, new_path)

        return self._parse_file_metadata(metadata.metadata)

    def rename_file(self, file_id: str, new_name: str) -> CloudFile:
        """Rename file."""
        self.ensure_authenticated()

        parent_path = str(Path(file_id).parent)
        new_path = f"{parent_path}/{new_name}"

        metadata = self.dbx.files_move_v2(file_id, new_path)

        return self._parse_file_metadata(metadata.metadata)

    def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """Delete file (always permanent in Dropbox, but can restore from trash)."""
        self.ensure_authenticated()

        self.dbx.files_delete_v2(file_id)

        logger.info(f"Deleted file {file_id}")
        return True

    def search_files(
        self,
        query: str,
        folder_id: Optional[str] = None
    ) -> List[CloudFile]:
        """Search for files."""
        self.ensure_authenticated()

        path = folder_id or ""

        result = self.dbx.files_search_v2(
            query,
            options=dropbox.files.SearchOptions(
                path=path,
                max_results=100
            )
        )

        files = []
        for match in result.matches:
            if hasattr(match, 'metadata') and hasattr(match.metadata, 'metadata'):
                files.append(self._parse_file_metadata(match.metadata.metadata))

        return files
