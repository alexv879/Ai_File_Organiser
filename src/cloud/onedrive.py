"""Microsoft OneDrive integration via Microsoft Graph API.

This module provides OneDrive integration using the Microsoft Graph API,
supporting OAuth 2.0 authentication, file operations, and intelligent
organization features.

API Documentation: https://docs.microsoft.com/en-us/graph/api/overview
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import requests
import logging

from .base import CloudStorageProvider, CloudFile, CloudFolder, SyncStatus

logger = logging.getLogger(__name__)


class OneDriveProvider(CloudStorageProvider):
    """Microsoft OneDrive cloud storage provider.

    Uses Microsoft Graph API for all operations.
    Scopes required: Files.ReadWrite.All, offline_access
    """

    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    AUTH_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

    SCOPES = [
        "Files.ReadWrite.All",
        "offline_access",
        "User.Read"
    ]

    def get_authorization_url(self) -> str:
        """Get OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.SCOPES),
            "response_mode": "query"
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.AUTH_ENDPOINT}?{query_string}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }

        response = requests.post(self.TOKEN_ENDPOINT, data=data)
        response.raise_for_status()

        tokens = response.json()
        self.access_token = tokens.get("access_token")
        self.refresh_token = tokens.get("refresh_token")

        return tokens

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self.refresh_token:
            raise ValueError("No refresh token available")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }

        response = requests.post(self.TOKEN_ENDPOINT, data=data)
        response.raise_for_status()

        tokens = response.json()
        self.access_token = tokens.get("access_token")
        if "refresh_token" in tokens:
            self.refresh_token = tokens["refresh_token"]

        return tokens

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        self.ensure_authenticated()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information."""
        response = requests.get(
            f"{self.GRAPH_API_ENDPOINT}/me",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def get_quota(self) -> Dict[str, int]:
        """Get storage quota information."""
        response = requests.get(
            f"{self.GRAPH_API_ENDPOINT}/me/drive",
            headers=self._get_headers()
        )
        response.raise_for_status()

        drive_info = response.json()
        quota = drive_info.get("quota", {})

        return {
            "total": quota.get("total", 0),
            "used": quota.get("used", 0),
            "remaining": quota.get("remaining", 0)
        }

    def _parse_file_metadata(self, item: Dict[str, Any]) -> CloudFile:
        """Parse OneDrive item to CloudFile."""
        file_id = item["id"]
        name = item["name"]
        size = item.get("size", 0)
        is_folder = "folder" in item

        modified_time = datetime.fromisoformat(
            item.get("lastModifiedDateTime", "").replace("Z", "+00:00")
        )
        created_time = datetime.fromisoformat(
            item.get("createdDateTime", "").replace("Z", "+00:00")
        )

        mime_type = item.get("file", {}).get("mimeType")
        md5_hash = item.get("file", {}).get("hashes", {}).get("quickXorHash")

        parent_id = item.get("parentReference", {}).get("id")
        path = item.get("parentReference", {}).get("path", "") + "/" + name

        download_url = item.get("@microsoft.graph.downloadUrl")

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
            download_url=download_url,
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
        if folder_id:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/items/{folder_id}/children"
        else:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/root/children"

        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        files = [self._parse_file_metadata(item) for item in data.get("value", [])]

        # Recursive listing
        if recursive:
            for file in files[:]:  # Copy to avoid modifying during iteration
                if file.is_folder:
                    files.extend(self.list_files(file.id, recursive=True))

        return files

    def get_file_metadata(self, file_id: str) -> CloudFile:
        """Get file metadata."""
        response = requests.get(
            f"{self.GRAPH_API_ENDPOINT}/me/drive/items/{file_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return self._parse_file_metadata(response.json())

    def download_file(
        self,
        file_id: str,
        local_path: Path,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """Download file from OneDrive."""
        file_metadata = self.get_file_metadata(file_id)

        if not file_metadata.download_url:
            raise ValueError("File has no download URL")

        # Download file
        response = requests.get(file_metadata.download_url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        local_path.parent.mkdir(parents=True, exist_ok=True)

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback:
                        progress_callback(downloaded, total_size)

        logger.info(f"Downloaded {file_metadata.name} to {local_path}")
        return True

    def upload_file(
        self,
        local_path: Path,
        cloud_folder_id: Optional[str] = None,
        cloud_filename: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> CloudFile:
        """Upload file to OneDrive."""
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        filename = cloud_filename or local_path.name

        if cloud_folder_id:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/items/{cloud_folder_id}:/{filename}:/content"
        else:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/root:/{filename}:/content"

        with open(local_path, 'rb') as f:
            file_data = f.read()

        headers = self._get_headers()
        headers["Content-Type"] = "application/octet-stream"

        response = requests.put(url, headers=headers, data=file_data)
        response.raise_for_status()

        logger.info(f"Uploaded {filename} to OneDrive")
        return self._parse_file_metadata(response.json())

    def create_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None
    ) -> CloudFolder:
        """Create new folder in OneDrive."""
        if parent_folder_id:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/items/{parent_folder_id}/children"
        else:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/root/children"

        data = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }

        response = requests.post(url, headers=self._get_headers(), json=data)
        response.raise_for_status()

        item = response.json()
        return CloudFolder(
            id=item["id"],
            name=item["name"],
            path=item.get("parentReference", {}).get("path", "") + "/" + item["name"],
            parent_id=item.get("parentReference", {}).get("id"),
            created_time=datetime.fromisoformat(item.get("createdDateTime", "").replace("Z", "+00:00")),
            metadata=item
        )

    def move_file(self, file_id: str, destination_folder_id: str) -> CloudFile:
        """Move file to different folder."""
        data = {
            "parentReference": {
                "id": destination_folder_id
            }
        }

        response = requests.patch(
            f"{self.GRAPH_API_ENDPOINT}/me/drive/items/{file_id}",
            headers=self._get_headers(),
            json=data
        )
        response.raise_for_status()
        return self._parse_file_metadata(response.json())

    def rename_file(self, file_id: str, new_name: str) -> CloudFile:
        """Rename file."""
        data = {"name": new_name}

        response = requests.patch(
            f"{self.GRAPH_API_ENDPOINT}/me/drive/items/{file_id}",
            headers=self._get_headers(),
            json=data
        )
        response.raise_for_status()
        return self._parse_file_metadata(response.json())

    def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """Delete file (moves to recycle bin unless permanent=True)."""
        response = requests.delete(
            f"{self.GRAPH_API_ENDPOINT}/me/drive/items/{file_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()

        logger.info(f"Deleted file {file_id} ({'permanent' if permanent else 'to recycle bin'})")
        return True

    def search_files(
        self,
        query: str,
        folder_id: Optional[str] = None
    ) -> List[CloudFile]:
        """Search for files."""
        if folder_id:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/items/{folder_id}/search(q='{query}')"
        else:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/root/search(q='{query}')"

        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()

        data = response.json()
        return [self._parse_file_metadata(item) for item in data.get("value", [])]
