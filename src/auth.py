"""
User Authentication and Authorization System

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module provides user authentication, password hashing, role-based permissions,
and session management for the AI File Organiser.

NOTICE: This software is proprietary and confidential. Unauthorized copying,
modification, distribution, or use is strictly prohibited.
See LICENSE.txt for full terms and conditions.

Version: 1.0.0
Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import hashlib
import secrets
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import bcrypt
import jwt
from functools import wraps


class UserRole(Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class Permission(Enum):
    """System permissions."""
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    DELETE_FILES = "delete_files"
    SCAN_DUPLICATES = "scan_duplicates"
    MANAGE_USERS = "manage_users"
    VIEW_LOGS = "view_logs"
    CONFIGURE_SYSTEM = "configure_system"


@dataclass
class User:
    """User account information."""
    username: str
    password_hash: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    permissions: List[Permission] = field(default_factory=list)
    session_token: Optional[str] = None
    token_expires: Optional[datetime] = None

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        if self.role == UserRole.ADMIN:
            return True
        return permission in self.permissions

    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.has_permission(p) for p in permissions)

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for storage."""
        return {
            'username': self.username,
            'password_hash': self.password_hash,
            'role': self.role.value,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'permissions': [p.value for p in self.permissions],
            'session_token': self.session_token,
            'token_expires': self.token_expires.isoformat() if self.token_expires else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary."""
        return cls(
            username=data['username'],
            password_hash=data['password_hash'],
            role=UserRole(data['role']),
            created_at=datetime.fromisoformat(data['created_at']),
            last_login=datetime.fromisoformat(data['last_login']) if data.get('last_login') else None,
            is_active=data.get('is_active', True),
            permissions=[Permission(p) for p in data.get('permissions', [])],
            session_token=data.get('session_token'),
            token_expires=datetime.fromisoformat(data['token_expires']) if data.get('token_expires') else None
        )


class AuthManager:
    """
    User authentication and authorization manager.
    """

    def __init__(self, users_file: Optional[str] = None, jwt_secret: Optional[str] = None):
        """
        Initialize authentication manager.

        Args:
            users_file: Path to users database file
            jwt_secret: Secret key for JWT tokens
        """
        if users_file is None:
            self.users_file = Path(__file__).parent.parent / "data" / "users.json"
        else:
            self.users_file = Path(users_file)

        self.jwt_secret = jwt_secret or self._generate_jwt_secret()
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, User] = {}

        # Ensure data directory exists
        self.users_file.parent.mkdir(parents=True, exist_ok=True)

        self.load_users()

        # Create default admin user if no users exist
        if not self.users:
            self._create_default_admin()

    def _generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret."""
        return secrets.token_hex(32)

    def _create_default_admin(self) -> None:
        """Create default admin user."""
        admin_user = User(
            username="admin",
            password_hash=self._hash_password("admin123"),
            role=UserRole.ADMIN,
            created_at=datetime.now(),
            permissions=[Permission.CONFIGURE_SYSTEM, Permission.MANAGE_USERS]
        )
        self.users["admin"] = admin_user
        self.save_users()

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def load_users(self) -> None:
        """Load users from file."""
        if not self.users_file.exists():
            return

        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)

            for username, user_data in users_data.items():
                self.users[username] = User.from_dict(user_data)

        except Exception as e:
            print(f"Error loading users: {e}")

    def save_users(self) -> None:
        """Save users to file."""
        users_data = {}
        for username, user in self.users.items():
            users_data[username] = user.to_dict()

        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, indent=2)
        except Exception as e:
            print(f"Error saving users: {e}")

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user.

        Args:
            username: Username to authenticate
            password: Password to verify

        Returns:
            User object if authentication successful, None otherwise
        """
        user = self.users.get(username)
        if not user or not user.is_active:
            return None

        if not self._verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login = datetime.now()
        self.save_users()

        return user

    def create_session(self, user: User) -> str:
        """
        Create a session token for a user.

        Args:
            user: User to create session for

        Returns:
            JWT session token
        """
        expires = datetime.now() + timedelta(hours=24)
        token_data = {
            'username': user.username,
            'role': user.role.value,
            'exp': expires.timestamp(),
            'iat': datetime.now().timestamp()
        }

        token = jwt.encode(token_data, self.jwt_secret, algorithm='HS256')

        # Store session
        user.session_token = token
        user.token_expires = expires
        self.sessions[token] = user
        self.save_users()

        return token

    def validate_session(self, token: str) -> Optional[User]:
        """
        Validate a session token.

        Args:
            token: JWT session token

        Returns:
            User object if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            username = payload['username']

            user = self.users.get(username)
            if not user or not user.is_active:
                return None

            # Check if token matches stored token
            if user.session_token != token:
                return None

            # Check expiration
            if user.token_expires and datetime.now() > user.token_expires:
                return None

            return user

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def invalidate_session(self, token: str) -> None:
        """
        Invalidate a session token.

        Args:
            token: Session token to invalidate
        """
        user = self.sessions.pop(token, None)
        if user:
            user.session_token = None
            user.token_expires = None
            self.save_users()

    def create_user(self, username: str, password: str, role: UserRole = UserRole.USER,
                   permissions: Optional[List[Permission]] = None) -> bool:
        """
        Create a new user account.

        Args:
            username: Unique username
            password: User password
            role: User role
            permissions: Additional permissions

        Returns:
            True if user created successfully, False otherwise
        """
        if username in self.users:
            return False

        if permissions is None:
            permissions = []

        user = User(
            username=username,
            password_hash=self._hash_password(password),
            role=role,
            created_at=datetime.now(),
            permissions=permissions
        )

        self.users[username] = user
        self.save_users()
        return True

    def delete_user(self, username: str) -> bool:
        """
        Delete a user account.

        Args:
            username: Username to delete

        Returns:
            True if user deleted, False otherwise
        """
        if username not in self.users:
            return False

        # Prevent deleting the last admin
        user = self.users[username]
        if user.role == UserRole.ADMIN:
            admin_count = sum(1 for u in self.users.values()
                            if u.role == UserRole.ADMIN and u.is_active)
            if admin_count <= 1:
                return False

        # Invalidate sessions
        if user.session_token:
            self.invalidate_session(user.session_token)

        del self.users[username]
        self.save_users()
        return True

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """
        Change a user's password.

        Args:
            username: Username
            old_password: Current password
            new_password: New password

        Returns:
            True if password changed, False otherwise
        """
        user = self.authenticate(username, old_password)
        if not user:
            return False

        user.password_hash = self._hash_password(new_password)
        self.save_users()
        return True

    def update_user_permissions(self, username: str, permissions: List[Permission]) -> bool:
        """
        Update a user's permissions.

        Args:
            username: Username to update
            permissions: New permissions list

        Returns:
            True if updated, False otherwise
        """
        user = self.users.get(username)
        if not user:
            return False

        user.permissions = permissions
        self.save_users()
        return True

    def get_user(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return self.users.get(username)

    def list_users(self) -> List[User]:
        """Get all users."""
        return list(self.users.values())

    def require_permission(self, permission: Permission):
        """
        Decorator to require a specific permission.

        Args:
            permission: Required permission

        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract user from kwargs or first argument
                user = kwargs.get('user') or (args[0] if args else None)

                if not isinstance(user, User):
                    raise ValueError("User object required")

                if not user.has_permission(permission):
                    raise PermissionError(f"Permission denied: {permission.value}")

                return func(*args, **kwargs)
            return wrapper
        return decorator

    def require_any_permission(self, permissions: List[Permission]):
        """
        Decorator to require any of the specified permissions.

        Args:
            permissions: List of permissions (user needs at least one)

        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                user = kwargs.get('user') or (args[0] if args else None)

                if not isinstance(user, User):
                    raise ValueError("User object required")

                if not user.has_any_permission(permissions):
                    raise PermissionError(f"Permission denied: any of {[p.value for p in permissions]}")

                return func(*args, **kwargs)
            return wrapper
        return decorator

    def check_ip_access(self, ip_address: str, allowed_ips: Optional[List[str]] = None) -> bool:
        """
        Check if IP address is allowed access.

        Args:
            ip_address: Client IP address
            allowed_ips: List of allowed IP patterns (supports wildcards)

        Returns:
            True if access allowed, False otherwise
        """
        if not allowed_ips:
            return True

        from fnmatch import fnmatch
        return any(fnmatch(ip_address, pattern) for pattern in allowed_ips)


# Global authentication manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager(users_file: Optional[str] = None) -> AuthManager:
    """Get or create global authentication manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager(users_file)
    return _auth_manager


# Default role permissions
DEFAULT_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.READ_FILES,
        Permission.WRITE_FILES,
        Permission.DELETE_FILES,
        Permission.SCAN_DUPLICATES,
        Permission.MANAGE_USERS,
        Permission.VIEW_LOGS,
        Permission.CONFIGURE_SYSTEM
    ],
    UserRole.USER: [
        Permission.READ_FILES,
        Permission.WRITE_FILES,
        Permission.SCAN_DUPLICATES,
        Permission.VIEW_LOGS
    ],
    UserRole.GUEST: [
        Permission.READ_FILES
    ]
}


if __name__ == "__main__":
    # Test authentication system
    auth = get_auth_manager()

    # Test default admin login
    user = auth.authenticate("admin", "admin123")
    if user:
        print(f"Login successful: {user.username} ({user.role.value})")

        # Create session
        token = auth.create_session(user)
        print(f"Session created: {token[:20]}...")

        # Validate session
        validated_user = auth.validate_session(token)
        if validated_user:
            print(f"Session validated: {validated_user.username}")

        # Test permissions
        print(f"Has admin permission: {user.has_permission(Permission.MANAGE_USERS)}")
        print(f"Has read permission: {user.has_permission(Permission.READ_FILES)}")

    else:
        print("Login failed")

    # Create test user
    success = auth.create_user("testuser", "password123", UserRole.USER)
    if success:
        print("Test user created")

        # Test login
        test_user = auth.authenticate("testuser", "password123")
        if test_user:
            print(f"Test user login: {test_user.username} ({test_user.role.value})")
            print(f"Test user permissions: {[p.value for p in test_user.permissions]}")