"""User management with secure SQLite storage.

This module handles user authentication, registration, and management
with secure password hashing and database integration.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from contextlib import contextmanager

from src.ui.auth import (
    get_password_hash,
    verify_password,
    validate_password_strength,
    User,
    UserInDB
)

logger = logging.getLogger(__name__)


class UserManager:
    """Manage users in SQLite database with secure practices."""

    def __init__(self, db_path: Path):
        """Initialize user manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
        logger.info(f"User manager initialized with database at {db_path}")

    def _init_database(self):
        """Initialize user database schema with security best practices."""
        with self._get_connection() as conn:
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    hashed_password TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1 NOT NULL,
                    is_admin BOOLEAN DEFAULT 0 NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    last_login TIMESTAMP,
                    failed_login_attempts INTEGER DEFAULT 0 NOT NULL,
                    locked_until TIMESTAMP,
                    CONSTRAINT chk_username_length CHECK (length(username) >= 3),
                    CONSTRAINT chk_email_format CHECK (email LIKE '%_@_%._%')
                )
            """)

            # Login history table for audit
            conn.execute("""
                CREATE TABLE IF NOT EXISTS login_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_login_history_user_id ON login_history(user_id)
            """)

            conn.commit()
            logger.debug("User database schema initialized")

    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        is_admin: bool = False
    ) -> bool:
        """Create new user with password validation.

        Args:
            username: Unique username (3-50 characters)
            email: Valid email address
            password: Password meeting security policy
            is_admin: Whether user has admin privileges

        Returns:
            bool: True if user created successfully

        Raises:
            ValueError: If username/email exists or password too weak

        Example:
            >>> um = UserManager(Path("users.db"))
            >>> um.create_user("john", "john@example.com", "SecurePass123!")
            True
        """
        # Validate password strength
        strength = validate_password_strength(password)
        if not strength.is_valid:
            error_msg = "; ".join(strength.errors)
            logger.warning(f"Password validation failed for {username}: {error_msg}")
            raise ValueError(f"Password validation failed: {error_msg}")

        # Hash password
        hashed_password = get_password_hash(password)

        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO users (username, email, hashed_password, is_admin)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username.lower(), email.lower(), hashed_password, is_admin)
                )
                conn.commit()

            logger.info(f"Created user: {username} (admin={is_admin})")
            return True

        except sqlite3.IntegrityError as e:
            logger.error(f"Failed to create user {username}: {e}")
            if "username" in str(e).lower():
                raise ValueError(f"Username '{username}' already exists")
            elif "email" in str(e).lower():
                raise ValueError(f"Email '{email}' already registered")
            else:
                raise ValueError("User creation failed: integrity constraint violation")

    def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[User]:
        """Authenticate user with account lockout protection.

        Args:
            username: Username or email
            password: Plain text password
            ip_address: Optional IP address for logging
            user_agent: Optional user agent for logging

        Returns:
            Optional[User]: User object if authentication successful, None otherwise

        Example:
            >>> um = UserManager(Path("users.db"))
            >>> user = um.authenticate_user("john", "SecurePass123!")
            >>> print(user.username if user else "Login failed")
            john
        """
        with self._get_connection() as conn:
            # Find user by username or email
            cursor = conn.execute(
                """
                SELECT * FROM users
                WHERE (username = ? OR email = ?)
                AND is_active = 1
                """,
                (username.lower(), username.lower())
            )
            user_row = cursor.fetchone()

            # User not found
            if not user_row:
                logger.warning(f"Authentication failed: user '{username}' not found")
                return None

            user_dict = dict(user_row)
            user_id = user_dict["id"]

            # Check if account is locked
            if user_dict["locked_until"]:
                locked_until = datetime.fromisoformat(user_dict["locked_until"])
                if datetime.utcnow() < locked_until:
                    logger.warning(f"Account locked for user {username} until {locked_until}")
                    return None
                else:
                    # Unlock account
                    conn.execute(
                        """
                        UPDATE users
                        SET locked_until = NULL, failed_login_attempts = 0
                        WHERE id = ?
                        """,
                        (user_id,)
                    )
                    conn.commit()

            # Verify password
            if verify_password(password, user_dict["hashed_password"]):
                # Successful login
                conn.execute(
                    """
                    UPDATE users
                    SET last_login = ?, failed_login_attempts = 0
                    WHERE id = ?
                    """,
                    (datetime.utcnow(), user_id)
                )

                # Log successful login
                conn.execute(
                    """
                    INSERT INTO login_history (user_id, ip_address, user_agent, success)
                    VALUES (?, ?, ?, 1)
                    """,
                    (user_id, ip_address, user_agent)
                )

                conn.commit()

                logger.info(f"Successful authentication for user {username}")

                return User(
                    username=user_dict["username"],
                    email=user_dict["email"],
                    is_active=bool(user_dict["is_active"]),
                    is_admin=bool(user_dict["is_admin"]),
                    created_at=datetime.fromisoformat(user_dict["created_at"]),
                    last_login=datetime.utcnow()
                )

            else:
                # Failed login
                failed_attempts = user_dict["failed_login_attempts"] + 1

                # Lock account after 5 failed attempts
                locked_until = None
                if failed_attempts >= 5:
                    locked_until = datetime.utcnow().replace(minute=datetime.utcnow().minute + 30)
                    logger.warning(f"Account locked for user {username} after {failed_attempts} failed attempts")

                conn.execute(
                    """
                    UPDATE users
                    SET failed_login_attempts = ?, locked_until = ?
                    WHERE id = ?
                    """,
                    (failed_attempts, locked_until, user_id)
                )

                # Log failed login
                conn.execute(
                    """
                    INSERT INTO login_history (user_id, ip_address, user_agent, success)
                    VALUES (?, ?, ?, 0)
                    """,
                    (user_id, ip_address, user_agent)
                )

                conn.commit()

                logger.warning(f"Authentication failed for user {username} ({failed_attempts} attempts)")
                return None

    def get_user(self, username: str) -> Optional[User]:
        """Get user by username.

        Args:
            username: Username to lookup

        Returns:
            Optional[User]: User object if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, username, email, is_active, is_admin, created_at, last_login
                FROM users
                WHERE username = ?
                """,
                (username.lower(),)
            )
            user_row = cursor.fetchone()

            if user_row:
                user_dict = dict(user_row)
                return User(
                    username=user_dict["username"],
                    email=user_dict["email"],
                    is_active=bool(user_dict["is_active"]),
                    is_admin=bool(user_dict["is_admin"]),
                    created_at=datetime.fromisoformat(user_dict["created_at"]) if user_dict["created_at"] else None,
                    last_login=datetime.fromisoformat(user_dict["last_login"]) if user_dict["last_login"] else None
                )

            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address.

        Args:
            email: Email address to lookup

        Returns:
            Optional[User]: User object if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, username, email, is_active, is_admin, created_at, last_login
                FROM users
                WHERE email = ?
                """,
                (email.lower(),)
            )
            user_row = cursor.fetchone()

            if user_row:
                user_dict = dict(user_row)
                return User(**user_dict)

            return None

    def update_password(self, username: str, new_password: str) -> bool:
        """Update user password.

        Args:
            username: Username
            new_password: New password (must meet security policy)

        Returns:
            bool: True if password updated successfully

        Raises:
            ValueError: If password validation fails
        """
        # Validate password strength
        strength = validate_password_strength(new_password)
        if not strength.is_valid:
            error_msg = "; ".join(strength.errors)
            raise ValueError(f"Password validation failed: {error_msg}")

        hashed_password = get_password_hash(new_password)

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE users
                SET hashed_password = ?
                WHERE username = ?
                """,
                (hashed_password, username.lower())
            )
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Password updated for user {username}")
                return True

            logger.warning(f"Failed to update password: user {username} not found")
            return False

    def deactivate_user(self, username: str) -> bool:
        """Deactivate user account.

        Args:
            username: Username to deactivate

        Returns:
            bool: True if user deactivated successfully
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE users
                SET is_active = 0
                WHERE username = ?
                """,
                (username.lower(),)
            )
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Deactivated user {username}")
                return True

            return False

    def list_users(self, include_inactive: bool = False) -> List[User]:
        """List all users.

        Args:
            include_inactive: Include deactivated users

        Returns:
            List[User]: List of user objects
        """
        with self._get_connection() as conn:
            query = """
                SELECT id, username, email, is_active, is_admin, created_at, last_login
                FROM users
            """
            if not include_inactive:
                query += " WHERE is_active = 1"

            query += " ORDER BY created_at DESC"

            cursor = conn.execute(query)
            users = []

            for row in cursor.fetchall():
                user_dict = dict(row)
                users.append(User(
                    username=user_dict["username"],
                    email=user_dict["email"],
                    is_active=bool(user_dict["is_active"]),
                    is_admin=bool(user_dict["is_admin"]),
                    created_at=datetime.fromisoformat(user_dict["created_at"]) if user_dict["created_at"] else None,
                    last_login=datetime.fromisoformat(user_dict["last_login"]) if user_dict["last_login"] else None
                ))

            return users

    def get_login_history(self, username: str, limit: int = 10) -> List[Dict]:
        """Get login history for user.

        Args:
            username: Username to get history for
            limit: Maximum number of records to return

        Returns:
            List[Dict]: Login history records
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT lh.login_time, lh.ip_address, lh.user_agent, lh.success
                FROM login_history lh
                JOIN users u ON lh.user_id = u.id
                WHERE u.username = ?
                ORDER BY lh.login_time DESC
                LIMIT ?
                """,
                (username.lower(), limit)
            )

            return [dict(row) for row in cursor.fetchall()]


# Global user manager instance
_user_manager: Optional[UserManager] = None


def get_user_manager(db_path: Optional[Path] = None) -> UserManager:
    """Get user manager singleton.

    Args:
        db_path: Optional database path (uses default if not specified)

    Returns:
        UserManager: User manager instance
    """
    global _user_manager

    if _user_manager is None:
        if db_path is None:
            # Use default path
            from pathlib import Path
            db_path = Path.home() / ".aifo" / "users.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)

        _user_manager = UserManager(db_path)

    return _user_manager
