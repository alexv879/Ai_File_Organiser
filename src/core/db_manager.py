"""
Database Management Module

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module handles all database operations for the Private AI File Organiser.
It uses SQLite for local storage of file logs, statistics, license info, and duplicate tracking.

Tables:
    - files_log: Records all file operations
    - duplicates: Tracks duplicate file hashes
    - license: Stores license validation status
    - stats: Aggregated statistics (daily, weekly, monthly)

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
import threading
import queue
import time


class ConnectionPool:
    """
    Thread-safe SQLite connection pool for improved performance.

    Maintains a pool of reusable database connections to reduce connection overhead.
    """

    def __init__(self, db_path: str, max_connections: int = 10, timeout: float = 30.0):
        """
        Initialize the connection pool.

        Args:
            db_path (str): Path to the SQLite database file
            max_connections (int): Maximum number of connections in the pool
            timeout (float): Timeout for acquiring connections from the pool
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._active_connections = 0

        # Pre-populate the pool with initial connections
        for _ in range(min(3, max_connections)):  # Start with 3 connections
            self._create_connection()

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimized settings."""
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance between performance and safety
        conn.execute("PRAGMA cache_size=10000")  # Increase cache size (10MB)
        conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a connection from the pool.

        Returns:
            sqlite3.Connection: Database connection

        Raises:
            queue.Empty: If no connection is available within timeout
        """
        try:
            return self._pool.get(timeout=self.timeout)
        except queue.Empty:
            with self._lock:
                if self._active_connections < self.max_connections:
                    self._active_connections += 1
                    return self._create_connection()
                else:
                    raise queue.Empty("Connection pool exhausted")

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """
        Return a connection to the pool.

        Args:
            conn (sqlite3.Connection): Connection to return
        """
        try:
            # Test if connection is still valid
            conn.execute("SELECT 1").fetchone()
            self._pool.put_nowait(conn)
        except (sqlite3.Error, queue.Full):
            # Connection is invalid or pool is full, close it
            try:
                conn.close()
            except:
                pass
            with self._lock:
                self._active_connections = max(0, self._active_connections - 1)

    def close_all(self) -> None:
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except queue.Empty:
                break

        with self._lock:
            self._active_connections = 0


class DatabaseManager:
    """
    Manages SQLite database operations for file tracking, statistics, and license management.

    Attributes:
        db_path (Path): Path to SQLite database file
        connection_pool (ConnectionPool): Connection pool for database operations
        _prepared_statements (dict): Cache of prepared statements for performance
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager and create tables if they don't exist.

        Args:
            db_path (str, optional): Path to database file. Defaults to data/database/organiser.db
        """
        if db_path is None:
            # Default to data/database/organiser.db in project root
            self.db_path = Path(__file__).parent.parent.parent / "data" / "database" / "organiser.db"
        else:
            self.db_path = Path(db_path)

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection pool
        self.connection_pool = ConnectionPool(str(self.db_path))

        # Cache for prepared statements
        self._prepared_statements = {}

        self._initialize_database()

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections using connection pool.

        Yields:
            sqlite3.Connection: Database connection from pool

        Example:
            >>> with db.get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT * FROM files_log")
        """
        conn = self.connection_pool.get_connection()
        try:
            yield conn
        finally:
            self.connection_pool.return_connection(conn)

    def _get_prepared_statement(self, sql: str) -> str:
        """
        Get or cache a prepared statement.

        Args:
            sql (str): SQL statement

        Returns:
            str: The SQL statement (cached for future use)
        """
        if sql not in self._prepared_statements:
            self._prepared_statements[sql] = sql
        return self._prepared_statements[sql]

    def execute_batch(self, operations: List[Tuple[str, Tuple]]) -> List[Any]:
        """
        Execute multiple database operations in a single transaction.

        Args:
            operations (List[Tuple[str, Tuple]]): List of (sql, params) tuples

        Returns:
            List[Any]: List of results from each operation
        """
        results = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN IMMEDIATE")
                for sql, params in operations:
                    prepared_sql = self._get_prepared_statement(sql)
                    cursor.execute(prepared_sql, params)
                    results.append(cursor.lastrowid or cursor.rowcount)
                conn.commit()
                return results
            except Exception as e:
                conn.rollback()
                raise e

    def bulk_log_actions(self, actions: List[Dict[str, Any]]) -> List[int]:
        """
        Bulk log multiple file actions efficiently.

        Args:
            actions (List[Dict]): List of action dictionaries

        Returns:
            List[int]: List of log IDs
        """
        operations = []
        stats_updates = []

        for action in actions:
            # Prepare log insert operation
            log_sql = """
                INSERT INTO files_log
                (filename, old_path, new_path, operation, time_saved, category, ai_suggested, user_approved,
                 raw_response, model_name, prompt_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            log_params = (
                action['filename'], action['old_path'], action.get('new_path'),
                action['operation'], action.get('time_saved', 0.0), action.get('category'),
                action.get('ai_suggested', False), action.get('user_approved', False),
                action.get('raw_response'), action.get('model_name'), action.get('prompt_hash')
            )
            operations.append((log_sql, log_params))

            # Prepare stats update operation
            today = datetime.now().date()
            stats_sql = """
                INSERT INTO stats (stat_date, files_organised, time_saved_minutes, ai_classifications)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(stat_date) DO UPDATE SET
                    files_organised = files_organised + 1,
                    time_saved_minutes = time_saved_minutes + ?,
                    ai_classifications = ai_classifications + ?
            """
            time_saved = action.get('time_saved', 0.0)
            ai_suggested = action.get('ai_suggested', False)
            stats_params = (today, time_saved, 1 if ai_suggested else 0, time_saved, 1 if ai_suggested else 0)
            operations.append((stats_sql, stats_params))

        # Execute all operations in batch
        results = self.execute_batch(operations)

        # Extract log IDs (every other result, starting from index 0)
        log_ids = []
        for i in range(0, len(results), 2):
            log_id = results[i]
            if log_id is None:
                raise RuntimeError("Failed to get log ID after batch insert")
            log_ids.append(log_id)

        return log_ids

    def _initialize_database(self) -> None:
        """
        Create database tables and indexes if they don't exist.
        Called automatically during initialization with performance optimizations.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Performance optimization pragmas
            cursor.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
            cursor.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
            cursor.execute("PRAGMA wal_autocheckpoint = 1000")  # Auto-checkpoint WAL
            cursor.execute("PRAGMA optimize")  # Run optimization

            # Files log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    old_path TEXT NOT NULL,
                    new_path TEXT,
                    operation TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    time_saved REAL DEFAULT 0.0,
                    category TEXT,
                    ai_suggested BOOLEAN DEFAULT 0,
                    user_approved BOOLEAN DEFAULT 0,
                    raw_response TEXT,
                    model_name TEXT,
                    prompt_hash TEXT
                )
            """)

            # Migration: Add new columns if they don't exist
            try:
                cursor.execute("ALTER TABLE files_log ADD COLUMN raw_response TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE files_log ADD COLUMN model_name TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE files_log ADD COLUMN prompt_hash TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Duplicates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS duplicates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_hash, file_path)
                )
            """)

            # License table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS license (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT UNIQUE NOT NULL,
                    activation_date DATETIME,
                    expiry_date DATETIME,
                    status TEXT DEFAULT 'unused',
                    last_verified DATETIME
                )
            """)

            # Statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stat_date DATE UNIQUE NOT NULL,
                    files_organised INTEGER DEFAULT 0,
                    time_saved_minutes REAL DEFAULT 0.0,
                    duplicates_removed INTEGER DEFAULT 0,
                    ai_classifications INTEGER DEFAULT 0
                )
            """)

            # Deferred queue for age-based moves
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS deferred_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    eligible_at DATETIME NOT NULL,
                    status TEXT DEFAULT 'queued', -- queued | processing | done | skipped | error
                    last_error TEXT
                )
                """
            )

            # Create comprehensive indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_timestamp ON files_log(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_category ON files_log(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_operation ON files_log(operation)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_ai_suggested ON files_log(ai_suggested)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_duplicates_hash ON duplicates(file_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_duplicates_path ON duplicates(file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_date ON stats(stat_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_deferred_status_eligible ON deferred_queue(status, eligible_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_deferred_eligible ON deferred_queue(eligible_at)")

            # Composite indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_timestamp_category ON files_log(timestamp, category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_operation_timestamp ON files_log(operation, timestamp)")

            conn.commit()

    # ==================== File Log Operations ====================

    def log_action(self, filename: str, old_path: str, new_path: Optional[str],
                   operation: str, time_saved: float = 0.0, category: Optional[str] = None,
                   ai_suggested: bool = False, user_approved: bool = False,
                   raw_response: Optional[str] = None, model_name: Optional[str] = None,
                   prompt_hash: Optional[str] = None) -> int:
        """
        Log a file operation to the database with atomic transaction support.

        Args:
            filename (str): Name of the file
            old_path (str): Original file path
            new_path (str, optional): New file path (if moved/renamed)
            operation (str): Type of operation (move, rename, delete, archive)
            time_saved (float): Estimated time saved in minutes
            category (str, optional): File category
            ai_suggested (bool): Whether AI suggested this action
            user_approved (bool): Whether user approved this action
            raw_response (str, optional): Raw LLM response for debugging
            model_name (str, optional): Name of the model used
            prompt_hash (str, optional): Hash of the prompt for traceability

        Returns:
            int: ID of the inserted log entry
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Start explicit transaction (HIGH #5 FIX)
                cursor.execute("BEGIN IMMEDIATE")

                # Insert log entry
                cursor.execute("""
                    INSERT INTO files_log
                    (filename, old_path, new_path, operation, time_saved, category, ai_suggested, user_approved,
                     raw_response, model_name, prompt_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (filename, old_path, new_path, operation, time_saved, category, ai_suggested, user_approved,
                      raw_response, model_name, prompt_hash))

                log_id = cursor.lastrowid
                if log_id is None:
                    raise RuntimeError("Failed to get log ID after insert")

                # Update daily stats
                today = datetime.now().date()
                cursor.execute("""
                    INSERT INTO stats (stat_date, files_organised, time_saved_minutes, ai_classifications)
                    VALUES (?, 1, ?, ?)
                    ON CONFLICT(stat_date) DO UPDATE SET
                        files_organised = files_organised + 1,
                        time_saved_minutes = time_saved_minutes + ?,
                        ai_classifications = ai_classifications + ?
                """, (today, time_saved, 1 if ai_suggested else 0, time_saved, 1 if ai_suggested else 0))

                # Commit transaction (HIGH #5 FIX)
                conn.commit()
                return log_id

            except Exception as e:
                # Rollback on any error (HIGH #5 FIX)
                conn.rollback()
                raise e

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve recent file operation logs with optimized query.

        Args:
            limit (int): Maximum number of logs to retrieve

        Returns:
            List[Dict]: List of log entries as dictionaries
        """
        sql = self._get_prepared_statement("""
            SELECT id, filename, old_path, new_path, operation, timestamp, time_saved, category,
                   ai_suggested, user_approved, model_name
            FROM files_log
            ORDER BY timestamp DESC
            LIMIT ?
        """)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def search_logs(self, query: Optional[str] = None, category: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search the files_log table by filename, old_path, new_path or category using optimized queries.

        Args:
            query (str, optional): Substring to search for in filename/paths
            category (str, optional): Category to filter by
            limit (int): Max results

        Returns:
            List[Dict]: Matching log entries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            where_clauses = []
            params: List[Any] = []

            if query:
                # Escape SQL LIKE wildcards (HIGH #3 FIX)
                escaped_query = query.replace('%', '\\%').replace('_', '\\_')
                like = f"%{escaped_query}%"
                where_clauses.append(
                    "(filename LIKE ? ESCAPE '\\' OR old_path LIKE ? ESCAPE '\\' OR new_path LIKE ? ESCAPE '\\')"
                )
                params.extend([like, like, like])

            if category:
                where_clauses.append("category = ?")
                params.append(category)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            sql = f"""
                SELECT id, filename, old_path, new_path, operation, timestamp, time_saved, category,
                       ai_suggested, user_approved, model_name
                FROM files_log
                WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT ?
            """

            prepared_sql = self._get_prepared_statement(sql)
            params.append(limit)

            cursor.execute(prepared_sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def undo_last_action(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the last action for undo functionality.

        Returns:
            Dict or None: Last action details or None if no actions exist
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM files_log
                WHERE operation IN ('move', 'rename')
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== Duplicate Operations ====================

    def add_duplicate(self, file_hash: str, file_path: str, file_size: int) -> bool:
        """
        Add a duplicate file entry.

        Args:
            file_hash (str): Hash of the file content
            file_path (str): Path to the file
            file_size (int): File size in bytes

        Returns:
            bool: True if added successfully, False if already exists
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO duplicates (file_hash, file_path, file_size)
                    VALUES (?, ?, ?)
                """, (file_hash, file_path, file_size))
                return True
        except sqlite3.IntegrityError:
            return False  # Duplicate entry already exists

    def get_duplicates(self) -> List[Dict[str, List[str]]]:
        """
        Get all sets of duplicate files grouped by hash with optimized query.

        Returns:
            List[Dict]: List of duplicate groups, each containing file paths
        """
        sql = self._get_prepared_statement("""
            SELECT file_hash, GROUP_CONCAT(file_path, '|') as paths, file_size
            FROM duplicates
            GROUP BY file_hash
            HAVING COUNT(*) > 1
            ORDER BY file_size DESC
        """)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)

            duplicates = []
            for row in cursor.fetchall():
                duplicates.append({
                    'hash': row['file_hash'],
                    'paths': row['paths'].split('|'),
                    'size': row['file_size']
                })

            return duplicates

    def remove_duplicate_entry(self, file_path: str) -> bool:
        """
        Remove a duplicate entry from tracking.

        Args:
            file_path (str): Path to the file to remove

        Returns:
            bool: True if removed successfully
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM duplicates WHERE file_path = ?", (file_path,))
            return cursor.rowcount > 0

    # ==================== License Operations ====================

    def store_license(self, license_key: str, expiry_date: datetime, status: str = 'active') -> bool:
        """
        Store or update license information.

        Args:
            license_key (str): The license key
            expiry_date (datetime): License expiration date
            status (str): License status (unused, active, expired)

        Returns:
            bool: True if stored successfully
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO license (license_key, activation_date, expiry_date, status, last_verified)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(license_key) DO UPDATE SET
                    expiry_date = ?,
                    status = ?,
                    last_verified = ?
            """, (license_key, datetime.now(), expiry_date, status, datetime.now(),
                  expiry_date, status, datetime.now()))

            return True

    def get_license_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current license status.

        Returns:
            Dict or None: License information or None if no license exists
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM license
                ORDER BY activation_date DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            if row:
                license_info = dict(row)
                # Check if expired
                if license_info['expiry_date']:
                    expiry = datetime.fromisoformat(license_info['expiry_date'])
                    if expiry < datetime.now():
                        license_info['status'] = 'expired'
                return license_info

            return None

    def is_license_valid(self) -> bool:
        """
        Check if current license is valid and not expired.

        Returns:
            bool: True if license is valid and active
        """
        license_info = self.get_license_status()
        if not license_info:
            return False

        if license_info['status'] != 'active':
            return False

        if license_info['expiry_date']:
            expiry = datetime.fromisoformat(license_info['expiry_date'])
            return expiry > datetime.now()

        return False

    # ==================== Statistics Operations ====================

    def get_stats(self, period: str = 'all') -> Dict[str, Any]:
        """
        Get aggregated statistics for a given period with optimized queries.

        Args:
            period (str): Time period ('today', 'week', 'month', 'all')

        Returns:
            Dict: Statistics including files organised, time saved, etc.
        """
        # Predefined queries for different periods
        queries = {
            'today': self._get_prepared_statement("""
                SELECT
                    SUM(files_organised) as total_files,
                    SUM(time_saved_minutes) as total_time_saved,
                    SUM(duplicates_removed) as total_duplicates,
                    SUM(ai_classifications) as total_ai_classifications
                FROM stats
                WHERE stat_date = date('now')
            """),
            'week': self._get_prepared_statement("""
                SELECT
                    SUM(files_organised) as total_files,
                    SUM(time_saved_minutes) as total_time_saved,
                    SUM(duplicates_removed) as total_duplicates,
                    SUM(ai_classifications) as total_ai_classifications
                FROM stats
                WHERE stat_date >= date('now', '-7 days')
            """),
            'month': self._get_prepared_statement("""
                SELECT
                    SUM(files_organised) as total_files,
                    SUM(time_saved_minutes) as total_time_saved,
                    SUM(duplicates_removed) as total_duplicates,
                    SUM(ai_classifications) as total_ai_classifications
                FROM stats
                WHERE stat_date >= date('now', '-30 days')
            """),
            'all': self._get_prepared_statement("""
                SELECT
                    SUM(files_organised) as total_files,
                    SUM(time_saved_minutes) as total_time_saved,
                    SUM(duplicates_removed) as total_duplicates,
                    SUM(ai_classifications) as total_ai_classifications
                FROM stats
            """)
        }

        sql = queries.get(period, queries['all'])

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)

            row = cursor.fetchone()
            return {
                'files_organised': row['total_files'] or 0,
                'time_saved_minutes': row['total_time_saved'] or 0.0,
                'time_saved_hours': round((row['total_time_saved'] or 0.0) / 60, 2),
                'duplicates_removed': row['total_duplicates'] or 0,
                'ai_classifications': row['total_ai_classifications'] or 0,
                'period': period
            }

    def update_duplicate_stats(self, count: int) -> None:
        """
        Update duplicate removal statistics for today.

        Args:
            count (int): Number of duplicates removed
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            today = datetime.now().date()
            cursor.execute("""
                INSERT INTO stats (stat_date, duplicates_removed)
                VALUES (?, ?)
                ON CONFLICT(stat_date) DO UPDATE SET
                    duplicates_removed = duplicates_removed + ?
            """, (today, count, count))

    # ==================== Deferred Queue Operations ====================

    def enqueue_deferred(self, file_path: str, eligible_at: datetime) -> int:
        """Add a file to the deferred processing queue."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO deferred_queue (file_path, eligible_at, status)
                VALUES (?, ?, 'queued')
                """,
                (file_path, eligible_at.isoformat())
            )
            item_id = cursor.lastrowid
            if item_id is None:
                raise RuntimeError("Failed to get item ID after insert")
            return item_id

    def fetch_due_deferred(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch queued items whose eligible_at has passed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, file_path, detected_at, eligible_at, status
                FROM deferred_queue
                WHERE status = 'queued' AND eligible_at <= datetime('now')
                ORDER BY eligible_at ASC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_deferred_status(self, item_id: int, status: str, error: str | None = None) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE deferred_queue SET status = ?, last_error = ? WHERE id = ?",
                (status, error, item_id)
            )

    def cleanup(self) -> None:
        """
        Clean up resources and close connection pool.
        Should be called when shutting down the application.
        """
        if hasattr(self, 'connection_pool'):
            self.connection_pool.close_all()
        self._prepared_statements.clear()

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during cleanup


if __name__ == "__main__":
    # Test database operations
    db = DatabaseManager()
    print("Database initialized successfully!")

    # Test logging an action
    log_id = db.log_action(
        filename="test_file.pdf",
        old_path="/home/user/Downloads/test_file.pdf",
        new_path="/home/user/Documents/PDFs/test_file.pdf",
        operation="move",
        time_saved=0.5,
        category="Documents",
        ai_suggested=True,
        user_approved=True
    )
    print(f"Logged action with ID: {log_id}")

    # Test retrieving stats
    stats = db.get_stats('today')
    print(f"Today's stats: {stats}")

    # Test license check
    is_valid = db.is_license_valid()
    print(f"License valid: {is_valid}")
