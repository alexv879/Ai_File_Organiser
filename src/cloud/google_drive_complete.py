"""Google Drive integration via Google Drive API v3.

Complete implementation using google-auth and google-api-python-client.

Installation:
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

API Documentation: https://developers.google.com/drive/api/v3/reference
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import logging
import io

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from google.auth.transport.requests import Request
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logging.warning("Google Drive packages not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

from .base import CloudStorageProvider, CloudFile, CloudFolder, SyncStatus

logger = logging.getLogger(__name__)


class GoogleDriveProvider(CloudStorageProvider):
    """Google Drive cloud storage provider using Google Drive API v3.

    Requires google-auth and google-api-python-client packages.
    Scopes: https://www.googleapis.com/auth/drive
    """

    SCOPES = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/userinfo.email'
    ]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None
    ):
        """Initialize Google Drive provider."""
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google Drive integration requires google packages. "
                "Install with: pip install google-auth google-auth-oauthlib "
                "google-auth-httplib2 google-api-python-client"
            )

        super().__init__(client_id, client_secret, redirect_uri, access_token, refresh_token)

        self.credentials = None
        self.service = None

        if access_token and refresh_token:
            self._init_from_tokens(access_token, refresh_token)

    def _init_from_tokens(self, access_token: str, refresh_token: str):
        """Initialize credentials from existing tokens."""
        self.credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES
        )
        self.service = build('drive', 'v3', credentials=self.credentials)

    def get_authorization_url(self) -> str:
        """Get OAuth authorization URL."""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        return auth_url

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )

        flow.fetch_token(code=code)
        self.credentials = flow.credentials
        self.service = build('drive', 'v3', credentials=self.credentials)

        self.access_token = self.credentials.token
        self.refresh_token = self.credentials.refresh_token

        return {
            "access_token": self.credentials.token,
            "refresh_token": self.credentials.refresh_token,
            "expires_in": 3600
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self.credentials:
            raise ValueError("No credentials available")

        self.credentials.refresh(Request())
        self.access_token = self.credentials.token

        return {
            "access_token": self.credentials.token,
            "expires_in": 3600
        }

    def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information."""
        self.ensure_authenticated()

        about = self.service.about().get(fields='user,storageQuota').execute()

        return {
            "displayName": about['user'].get('displayName'),
            "email": about['user'].get('emailAddress'),
            "quota": about.get('storageQuota', {})
        }

    def get_quota(self) -> Dict[str, int]:
        """Get storage quota information."""
        self.ensure_authenticated()

        about = self.service.about().get(fields='storageQuota').execute()
        quota = about.get('storageQuota', {})

        total = int(quota.get('limit', 0))
        used = int(quota.get('usage', 0))

        return {
            "total": total,
            "used": used,
            "remaining": total - used
        }

    def _parse_file_metadata(self, item: Dict[str, Any]) -> CloudFile:
        """Parse Google Drive file to CloudFile."""
        file_id = item['id']
        name = item['name']
        size = int(item.get('size', 0))
        is_folder = item.get('mimeType') == 'application/vnd.google-apps.folder'

        modified_time = datetime.fromisoformat(
            item.get('modifiedTime', '').replace('Z', '+00:00')
        )
        created_time = datetime.fromisoformat(
            item.get('createdTime', '').replace('Z', '+00:00')
        )

        mime_type = item.get('mimeType')
        md5_hash = item.get('md5Checksum')

        parent_id = item.get('parents', [None])[0]
        path = f"/{name}"  # Simplified path

        return CloudFile(
            id=file_id,
            name=name,
            path=path,
            size=size,
            modified_time=modified_time,
            created_time=created_time,
            is_folder=is_folder,
            mime_type=mime_type,
            md5_hash=md5_hash,
            parent_id=parent_id,
            sync_status=SyncStatus.SYNCED,
            metadata=item
        )

    def list_files(
        self,
        folder_id: Optional[str] = None,
        recursive: bool = False
    ) -> List[CloudFile]:
        """List files in a folder."""
        self.ensure_authenticated()

        if folder_id:
            query = f"'{folder_id}' in parents and trashed=false"
        else:
            query = "'root' in parents and trashed=false"

        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, size, createdTime, modifiedTime, md5Checksum, parents)',
            pageSize=1000
        ).execute()

        files = [self._parse_file_metadata(item) for item in results.get('files', [])]

        if recursive:
            for file in files[:]:
                if file.is_folder:
                    files.extend(self.list_files(file.id, recursive=True))

        return files

    def get_file_metadata(self, file_id: str) -> CloudFile:
        """Get file metadata."""
        self.ensure_authenticated()

        file = self.service.files().get(
            fileId=file_id,
            fields='id, name, mimeType, size, createdTime, modifiedTime, md5Checksum, parents'
        ).execute()

        return self._parse_file_metadata(file)

    def download_file(
        self,
        file_id: str,
        local_path: Path,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """Download file from Google Drive."""
        self.ensure_authenticated()

        request = self.service.files().get_media(fileId=file_id)

        local_path.parent.mkdir(parents=True, exist_ok=True)

        fh = io.FileIO(str(local_path), 'wb')
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

            if progress_callback and status:
                progress_callback(
                    int(status.progress() * status.total_size),
                    status.total_size
                )

        logger.info(f"Downloaded file to {local_path}")
        return True

    def upload_file(
        self,
        local_path: Path,
        cloud_folder_id: Optional[str] = None,
        cloud_filename: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> CloudFile:
        """Upload file to Google Drive."""
        self.ensure_authenticated()

        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        filename = cloud_filename or local_path.name

        file_metadata = {
            'name': filename
        }

        if cloud_folder_id:
            file_metadata['parents'] = [cloud_folder_id]

        media = MediaFileUpload(
            str(local_path),
            resumable=True
        )

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, mimeType, size, createdTime, modifiedTime, md5Checksum, parents'
        ).execute()

        logger.info(f"Uploaded {filename} to Google Drive")
        return self._parse_file_metadata(file)

    def create_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None
    ) -> CloudFolder:
        """Create new folder in Google Drive."""
        self.ensure_authenticated()

        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]

        folder = self.service.files().create(
            body=file_metadata,
            fields='id, name, createdTime, modifiedTime, parents'
        ).execute()

        return CloudFolder(
            id=folder['id'],
            name=folder['name'],
            path=f"/{folder['name']}",
            parent_id=folder.get('parents', [None])[0],
            created_time=datetime.fromisoformat(folder.get('createdTime', '').replace('Z', '+00:00')),
            metadata=folder
        )

    def move_file(self, file_id: str, destination_folder_id: str) -> CloudFile:
        """Move file to different folder."""
        self.ensure_authenticated()

        # Get current parents
        file = self.service.files().get(
            fileId=file_id,
            fields='parents'
        ).execute()

        previous_parents = ','.join(file.get('parents', []))

        # Move file
        file = self.service.files().update(
            fileId=file_id,
            addParents=destination_folder_id,
            removeParents=previous_parents,
            fields='id, name, mimeType, size, createdTime, modifiedTime, md5Checksum, parents'
        ).execute()

        return self._parse_file_metadata(file)

    def rename_file(self, file_id: str, new_name: str) -> CloudFile:
        """Rename file."""
        self.ensure_authenticated()

        file = self.service.files().update(
            fileId=file_id,
            body={'name': new_name},
            fields='id, name, mimeType, size, createdTime, modifiedTime, md5Checksum, parents'
        ).execute()

        return self._parse_file_metadata(file)

    def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """Delete file (moves to trash unless permanent=True)."""
        self.ensure_authenticated()

        if permanent:
            self.service.files().delete(fileId=file_id).execute()
        else:
            self.service.files().update(
                fileId=file_id,
                body={'trashed': True}
            ).execute()

        logger.info(f"Deleted file {file_id} ({'permanent' if permanent else 'to trash'})")
        return True

    def search_files(
        self,
        query: str,
        folder_id: Optional[str] = None
    ) -> List[CloudFile]:
        """Search for files."""
        self.ensure_authenticated()

        search_query = f"name contains '{query}' and trashed=false"
        if folder_id:
            search_query += f" and '{folder_id}' in parents"

        results = self.service.files().list(
            q=search_query,
            spaces='drive',
            fields='files(id, name, mimeType, size, createdTime, modifiedTime, md5Checksum, parents)',
            pageSize=100
        ).execute()

        return [self._parse_file_metadata(item) for item in results.get('files', [])]
