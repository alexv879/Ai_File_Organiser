"""
File Watcher Module

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module monitors specified directories for new or modified files using
the watchdog library (cross-platform filesystem events monitoring).

Reference: watchdog library for filesystem event monitoring
Reference: inotify (Linux), FSEvents (macOS), ReadDirectoryChangesW (Windows)

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import time
import threading
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Callable, Optional, TYPE_CHECKING
from queue import Queue

# Watchdog for filesystem monitoring
# Reference: watchdog library for cross-platform file system events
try:
    from watchdog.observers import Observer  # type: ignore
    from watchdog.events import FileSystemEventHandler, FileSystemEvent  # type: ignore
    WATCHDOG_SUPPORT = True
except ImportError:
    # Fallback types for when watchdog is not installed
    if TYPE_CHECKING:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler, FileSystemEvent
    else:
        Observer = None  # type: ignore
        FileSystemEventHandler = object  # type: ignore
        FileSystemEvent = object  # type: ignore
    WATCHDOG_SUPPORT = False

# Alternative: watchfiles (Rust-based, faster)
try:
    import watchfiles  # type: ignore
    WATCHFILES_SUPPORT = True
except ImportError:
    WATCHFILES_SUPPORT = False


class FileEventHandler(FileSystemEventHandler):
    """
    Custom event handler for file system changes.

    This handler filters and processes file creation and modification events,
    adding relevant files to a processing queue.

    Attributes:
        callback (Callable): Function to call when a file event occurs
        file_queue (Queue): Queue for detected files
        ignored_extensions (set): File extensions to ignore
        ignored_patterns (set): Filename patterns to ignore
    """

    def __init__(self, callback: Optional[Callable] = None, file_queue: Optional[Queue] = None, blacklist: Optional[List[str]] = None, max_queue_size: int = 1000):
        """
        Initialize file event handler.

        Args:
            callback (Callable, optional): Function to call with file path when event occurs
            file_queue (Queue, optional): Queue to add detected files to
            blacklist (List[str], optional): List of paths to ignore
            max_queue_size (int): Maximum queue size to prevent memory leak (HIGH #4 FIX)
        """
        super().__init__()
        self.callback = callback
        self.file_queue = file_queue or Queue(maxsize=max_queue_size)  # Add maxsize (HIGH #4 FIX)
        # Optional list of path prefixes to ignore
        self.blacklist = [str(Path(p).expanduser().resolve()) for p in (blacklist or [])]

        # Ignore temporary and system files
        self.ignored_extensions = {
            '.tmp', '.temp', '.crdownload', '.part', '.partial',
            '.download', '.cache', '.lock', '.swp', '.~'
        }

        self.ignored_patterns = {
            '.DS_Store', 'Thumbs.db', 'desktop.ini', '.gitkeep',
            '.git', '.svn', '__pycache__', 'node_modules'
        }

    def _should_process(self, path: str) -> bool:
        """
        Determine if a file should be processed.

        Args:
            path (str): File path

        Returns:
            bool: True if file should be processed, False if should be ignored
        """
        file_path = Path(path)

        # Ignore directories
        if file_path.is_dir():
            return False

        # Ignore files in ignored patterns
        if file_path.name in self.ignored_patterns:
            return False

        # Ignore hidden files (starting with .)
        if file_path.name.startswith('.'):
            return False

        # Ignore files with ignored extensions
        if file_path.suffix.lower() in self.ignored_extensions:
            return False

        # Ignore very small files (likely incomplete or empty)
        try:
            if file_path.stat().st_size < 100:  # Less than 100 bytes
                return False
        except OSError:
            return False

        # Ignore files under any blacklisted path
        try:
            resolved = str(file_path.resolve())
            for b in self.blacklist:
                try:
                    # Use commonpath to determine ancestry; handle different drives
                    if os.path.commonpath([resolved, b]) == b:
                        return False
                except Exception:
                    # If commonpath fails (different drives), try simple prefix compare
                    if resolved.lower().startswith(b.lower()):
                        return False
        except Exception:
            pass

        return True

    def on_created(self, event: FileSystemEvent):
        """
        Handle file creation events.

        Args:
            event (FileSystemEvent): File system event
        """
        src_path = event.src_path
        if isinstance(src_path, (bytes, bytearray, memoryview)):
            src_path = bytes(src_path).decode()
        if not event.is_directory and self._should_process(src_path):
            # Wait for file to stabilize (check both time and size)
            file_path = Path(src_path)

            try:
                # Initial check
                old_size = file_path.stat().st_size
                time.sleep(0.5)

                # Re-check file still exists and is stable
                if file_path.exists():
                    new_size = file_path.stat().st_size

                    # If file is still growing, wait a bit more
                    if new_size != old_size:
                        time.sleep(1)
                        # Final check
                        if file_path.exists():
                            self._process_file(src_path)
                    else:
                        # File size is stable
                        self._process_file(src_path)
            except OSError:
                # File may have been deleted or moved, skip it
                pass

    def on_modified(self, event: FileSystemEvent):
        """
        Handle file modification events.

        Args:
            event (FileSystemEvent): File system event
        """
        src_path = event.src_path
        if isinstance(src_path, (bytes, bytearray, memoryview)):
            src_path = bytes(src_path).decode()
        # For modified files, we're more conservative to avoid processing
        # files that are being actively written to
        if not event.is_directory and self._should_process(src_path):
            # Only process if file hasn't been modified in last 2 seconds
            # This prevents processing files that are still being written
            try:
                path = Path(src_path)
                if time.time() - path.stat().st_mtime > 2:
                    self._process_file(src_path)
            except OSError:
                pass

    def _process_file(self, file_path: str):
        """
        Process a detected file.

        Args:
            file_path (str): Path to the file
        """
        if self.callback:
            self.callback(file_path)

        if self.file_queue:
            self.file_queue.put(file_path)


class FolderWatcher:
    """
    Main folder watching orchestrator.

    This class manages observers for multiple directories and coordinates
    file detection with classification and processing.

    Attributes:
        folders (List[str]): Directories to watch
        callback (Callable): Function to call when files are detected
        observer (Observer): Watchdog observer instance
        file_queue (Queue): Queue of detected files
        processing_thread (threading.Thread): Background processing thread
        executor (ThreadPoolExecutor): Thread pool for async processing
        loop (asyncio.AbstractEventLoop): Event loop for async operations
    """

    def __init__(self, folders: List[str], callback: Optional[Callable] = None, config: Optional[object] = None):
        """
        Initialize folder watcher.

        Args:
            folders (List[str]): List of directory paths to watch
            callback (Callable, optional): Function to call with file path when detected
        """
        self.folders = [Path(f).expanduser().resolve() for f in folders]
        self.callback = callback
        self.config = config
        self.observer = None  # type: ignore
        self.file_queue = Queue()
        self.processing_thread = None
        self.executor = None
        self.loop = None
        self._running = False

    def start(self, background: bool = True, async_processing: bool = False):
        """
        Start watching folders.

        Args:
            background (bool): If True, run processing in background thread
            async_processing (bool): If True, use async processing with ThreadPoolExecutor
        """
        if self._running:
            print("[Watcher] Already running")
            return

        # Create event handler
        blacklist = []
        try:
            if self.config:
                blacklist = getattr(self.config, 'path_blacklist', [])
        except Exception:
            blacklist = []

        event_handler = FileEventHandler(
            callback=self.callback,
            file_queue=self.file_queue,
            blacklist=blacklist
        )

        # Create observer
        self.observer = Observer()

        # Schedule observers for all folders
        for folder in self.folders:
            if folder.exists() and folder.is_dir():
                self.observer.schedule(event_handler, str(folder), recursive=True)
                print(f"[Watcher] Monitoring: {folder}")
            else:
                print(f"[Watcher] Warning: Folder not found: {folder}")

        # Start observer
        self.observer.start()
        self._running = True
        print("[Watcher] Started successfully")

        # Start processing thread if background mode
        if background and self.callback:
            if async_processing:
                self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="FileProcessor")
                self.processing_thread = threading.Thread(target=self._process_queue_async, daemon=True)
            else:
                self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.processing_thread.start()

    def stop(self):
        """Stop watching folders."""
        if not self._running:
            return

        self._running = False

        if self.observer:
            self.observer.stop()
            self.observer.join()

        # Clean up executor
        if self.executor:
            self.executor.shutdown(wait=True)

        print("[Watcher] Stopped")

    def _process_queue(self):
        """
        Process files from queue in background.
        This runs in a separate thread.
        """
        while self._running:
            try:
                # Get file from queue with timeout
                if not self.file_queue.empty():
                    file_path = self.file_queue.get(timeout=1)

                    # Call callback if provided
                    if self.callback and Path(file_path).exists():
                        try:
                            self.callback(file_path)
                        except Exception as e:
                            print(f"[Watcher] Error processing {file_path}: {e}")

                    self.file_queue.task_done()
                else:
                    time.sleep(0.5)
            except Exception as e:
                print(f"[Watcher] Queue processing error: {e}")
                time.sleep(1)

    def _process_queue_async(self):
        """
        Process files from queue asynchronously using ThreadPoolExecutor.
        This runs in a separate thread and uses async processing for better performance.
        """
        while self._running:
            try:
                # Get file from queue with timeout
                if not self.file_queue.empty():
                    file_path = self.file_queue.get(timeout=1)

                    # Process file asynchronously if executor is available
                    if self.executor and self.callback and Path(file_path).exists():
                        try:
                            # Submit async processing task
                            future = self.executor.submit(self._async_process_file, file_path)
                            # Don't wait for completion - let it run in background
                        except Exception as e:
                            print(f"[Watcher] Error submitting async task for {file_path}: {e}")

                    self.file_queue.task_done()
                else:
                    time.sleep(0.5)
            except Exception as e:
                print(f"[Watcher] Async queue processing error: {e}")
                time.sleep(1)

    def _async_process_file(self, file_path: str):
        """
        Process a single file asynchronously.

        Args:
            file_path (str): Path to the file to process
        """
        try:
            if self.callback and Path(file_path).exists():
                self.callback(file_path)
        except Exception as e:
            print(f"[Watcher] Error in async processing of {file_path}: {e}")

    def get_pending_count(self) -> int:
        """
        Get number of files waiting to be processed.

        Returns:
            int: Queue size
        """
        return self.file_queue.qsize()

    def start_watchfiles(self, background: bool = True, async_processing: bool = False):
        """
        Start watching folders using watchfiles library (alternative to watchdog).

        Args:
            background (bool): If True, run processing in background thread
            async_processing (bool): If True, use async processing with ThreadPoolExecutor
        """
        if not WATCHFILES_SUPPORT:
            print("[Watcher] watchfiles library not available, falling back to watchdog")
            return self.start(background, async_processing)

        if self._running:
            print("[Watcher] Already running")
            return

        self._running = True
        print("[Watcher] Starting with watchfiles...")

        # Initialize executor for async processing
        if async_processing:
            self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="FileProcessor")

        # Start watchfiles in a separate thread
        self.processing_thread = threading.Thread(target=self._watch_with_watchfiles, daemon=True)
        self.processing_thread.start()

        if background:
            # Start processing thread
            if async_processing:
                processing_thread = threading.Thread(target=self._process_queue_async, daemon=True)
            else:
                processing_thread = threading.Thread(target=self._process_queue, daemon=True)
            processing_thread.start()

    def _watch_with_watchfiles(self):
        """
        Watch folders using watchfiles library.
        """
        try:
            # Convert folders to strings
            watch_paths = [str(f) for f in self.folders if f.exists() and f.is_dir()]

            if not watch_paths:
                print("[Watcher] No valid folders to watch")
                return

            print(f"[Watcher] Monitoring with watchfiles: {watch_paths}")

            # Use watchfiles.watch for continuous monitoring
            for changes in watchfiles.watch(*watch_paths, watch_filter=self._watchfiles_filter):
                for change_type, file_path in changes:
                    if change_type in (watchfiles.Change.added, watchfiles.Change.modified):
                        if self._should_process_watchfiles(file_path):
                            if self.callback:
                                self.callback(file_path)

        except Exception as e:
            print(f"[Watcher] watchfiles error: {e}")
        finally:
            self._running = False

    def _watchfiles_filter(self, change: watchfiles.Change, path: str) -> bool:
        """
        Filter function for watchfiles.

        Args:
            change: Type of change
            path: File path

        Returns:
            bool: Whether to process this change
        """
        # Only process file additions and modifications
        if change not in (watchfiles.Change.added, watchfiles.Change.modified):
            return False

        # Check if it's a file
        if not os.path.isfile(path):
            return False

        return self._should_process_watchfiles(path)

    def _should_process_watchfiles(self, file_path: str) -> bool:
        """
        Check if file should be processed (watchfiles version).

        Args:
            file_path (str): Path to check

        Returns:
            bool: Whether to process
        """
        path = Path(file_path)

        # Basic checks
        if not path.exists() or path.is_dir():
            return False

        # Check file size (skip very large files)
        try:
            if path.stat().st_size > 100 * 1024 * 1024:  # 100MB limit
                return False
        except OSError:
            return False

        # Get blacklist from config
        blacklist = []
        try:
            if self.config:
                blacklist = getattr(self.config, 'path_blacklist', [])
        except Exception:
            blacklist = []

        # Check blacklist
        try:
            resolved = str(path.resolve())
            for b in blacklist:
                try:
                    if os.path.commonpath([resolved, b]) == b:
                        return False
                except Exception:
                    if resolved.lower().startswith(b.lower()):
                        return False
        except Exception:
            pass

        return True


def create_watcher(folders: List[str], callback: Optional[Callable] = None) -> FolderWatcher:
    """
    Create and configure a folder watcher.

    Args:
        folders (List[str]): Directories to watch
        callback (Callable, optional): Function to call when files detected

    Returns:
        FolderWatcher: Configured watcher instance
    """
    return FolderWatcher(folders, callback)


if __name__ == "__main__":
    # Test watcher
    def test_callback(file_path: str):
        print(f"File detected: {file_path}")

    # Watch current directory for testing
    test_folders = ["."]

    watcher = create_watcher(test_folders, callback=test_callback)
    watcher.start()

    try:
        print("Watcher running... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
            pending = watcher.get_pending_count()
            if pending > 0:
                print(f"Pending files in queue: {pending}")
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        watcher.stop()
