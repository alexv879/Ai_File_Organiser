"""
Parallel Processing System for AI File Organiser

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module provides parallel processing capabilities for file operations,
integrating with the progress reporting and action management systems.

NOTICE: This software is proprietary and confidential. Unauthorized copying,
modification, distribution, or use is strictly prohibited.
See LICENSE.txt for full terms and conditions.

Version: 1.0.0
Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import List, Dict, Any, Callable, Optional, Union
from pathlib import Path
from queue import Queue
import time

from src.progress import get_progress_reporter, get_parallel_processor
from src.config_yaml import get_yaml_config
from src.auth import get_auth_manager, User, Permission


class ParallelActionProcessor:
    """
    Parallel processor for file organization actions with progress reporting.
    """

    def __init__(self, max_workers: int = 4, enable_progress: bool = True):
        """
        Initialize parallel action processor.

        Args:
            max_workers: Maximum number of parallel worker threads
            enable_progress: Whether to enable progress reporting
        """
        self.max_workers = max_workers
        self.enable_progress = enable_progress
        self._progress = get_progress_reporter(enable_progress_bars=enable_progress)
        self._parallel = get_parallel_processor(max_workers)
        self._yaml_config = get_yaml_config()
        self._auth = get_auth_manager()

        # Thread-safe result collection
        self._results_lock = threading.Lock()
        self._results: List[Dict[str, Any]] = []

    def process_files_parallel(self, file_paths: List[Union[str, Path]],
                             action_manager, user: Optional[User] = None,
                             tags: Optional[List[str]] = None, dry_run: bool = True) -> Dict[str, Any]:
        """
        Process multiple files in parallel using YAML configuration rules.

        Args:
            file_paths: List of file paths to process
            action_manager: Action manager instance
            user: Authenticated user (for permission checks)
            tags: Rule tags to filter by
            dry_run: Whether to simulate operations

        Returns:
            Processing results summary
        """
        if not file_paths:
            return {'total_files': 0, 'processed': 0, 'errors': 0, 'results': []}

        # Create progress task
        task_name = f"Processing {len(file_paths)} files"
        task = self._progress.create_task("file_processing", task_name, len(file_paths))

        # Convert to Path objects
        paths = [Path(fp) for fp in file_paths]

        def process_single_file(file_path: Path) -> Dict[str, Any]:
            """Process a single file with YAML rules."""
            try:
                # Check user permissions if provided
                if user and not user.has_permission(Permission.WRITE_FILES):
                    return {
                        'file': str(file_path),
                        'success': False,
                        'error': 'Permission denied: write_files required'
                    }

                # Execute rules for this file
                results = self._yaml_config.execute_rules(file_path, tags or [], dry_run)

                # If rules were executed, also run through action manager for compatibility
                if results and not dry_run:
                    classification = {'suggested_path': None, 'method': 'yaml_rules'}
                    action_result = action_manager.execute(
                        str(file_path), classification, user_approved=True
                    )

                    return {
                        'file': str(file_path),
                        'success': action_result['success'],
                        'rules_executed': len(results),
                        'action_result': action_result,
                        'yaml_results': results
                    }
                else:
                    return {
                        'file': str(file_path),
                        'success': all(r['success'] for r in results),
                        'rules_executed': len(results),
                        'yaml_results': results
                    }

            except Exception as e:
                return {
                    'file': str(file_path),
                    'success': False,
                    'error': str(e)
                }

        # Process files in parallel
        results = self._parallel.map_with_progress(
            process_single_file,
            paths,
            "Processing files"
        )

        # Update progress
        self._progress.update_task("file_processing", len(file_paths))
        self._progress.complete_task("file_processing")

        # Summarize results
        successful = sum(1 for r in results if r['success'])
        errors = sum(1 for r in results if not r['success'])

        return {
            'total_files': len(file_paths),
            'processed': successful,
            'errors': errors,
            'results': results,
            'summary': {
                'success_rate': successful / len(file_paths) if file_paths else 0,
                'total_rules_executed': sum(r.get('rules_executed', 0) for r in results)
            }
        }

    def scan_directory_parallel(self, directory: str, recursive: bool = True,
                              filters: Optional[List[str]] = None, max_files: int = 1000) -> List[Path]:
        """
        Scan directory in parallel to find files matching filters.

        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            filters: YAML filter names to apply
            max_files: Maximum number of files to return

        Returns:
            List of matching file paths
        """
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            return []

        # Create progress task
        task_name = f"Scanning {directory}"
        task = self._progress.create_task("directory_scan", task_name)

        # Collect all files first (this could be parallelized further if needed)
        if recursive:
            all_files = list(dir_path.rglob('*'))
        else:
            all_files = list(dir_path.glob('*'))

        file_paths = [f for f in all_files if f.is_file()]

        if not file_paths:
            self._progress.complete_task("directory_scan")
            return []

        task.total = len(file_paths)

        def check_file_matches(file_path: Path) -> Optional[Path]:
            """Check if file matches the specified filters."""
            try:
                if not filters:
                    self._progress.update_task("directory_scan", 1)
                    return file_path

                # Check against YAML filters
                for filter_name in filters:
                    if filter_name not in self._yaml_config._filters:
                        continue

                    filter_rule = self._yaml_config._filters[filter_name]
                    if filter_rule.matches(file_path):
                        self._progress.update_task("directory_scan", 1)
                        return file_path

                self._progress.update_task("directory_scan", 1)
                return None

            except Exception:
                self._progress.update_task("directory_scan", 1)
                return None

        # Filter files in parallel
        matching_files = self._parallel.map_with_progress(
            lambda fp: check_file_matches(fp) if check_file_matches(fp) else None,
            file_paths,
            "Filtering files"
        )

        # Remove None values
        matching_files = [f for f in matching_files if f is not None]

        self._progress.complete_task("directory_scan")

        # Limit results
        return matching_files[:max_files]

    def batch_operation(self, operation_func: Callable[[Any], Any], items: List[Any],
                       operation_name: str = "Batch Operation") -> List[Any]:
        """
        Execute a batch operation in parallel.

        Args:
            operation_func: Function to execute on each item
            items: List of items to process
            operation_name: Name for progress tracking

        Returns:
            List of operation results
        """
        return self._parallel.map_with_progress(operation_func, items, operation_name)

    def cleanup_temp_files_parallel(self, directories: List[str],
                                  patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Clean up temporary files in parallel across multiple directories.

        Args:
            directories: List of directories to clean
            patterns: File patterns to match for deletion

        Returns:
            Cleanup results
        """
        if patterns is None:
            patterns = ['*.tmp', '*.temp', '~*', '*.bak', '*.log']

        # Create progress task
        task_name = f"Cleaning temp files in {len(directories)} directories"
        task = self._progress.create_task("temp_cleanup", task_name)

        total_cleaned = 0
        total_space_freed = 0
        errors = []

        def cleanup_directory(directory: str) -> Dict[str, Any]:
            """Clean temp files in a single directory."""
            try:
                dir_path = Path(directory)
                if not dir_path.exists():
                    return {'directory': directory, 'cleaned': 0, 'space_freed': 0, 'errors': []}

                cleaned = 0
                space_freed = 0

                for pattern in patterns:
                    for file_path in dir_path.rglob(pattern):
                        if file_path.is_file():
                            try:
                                size = file_path.stat().st_size
                                file_path.unlink()
                                cleaned += 1
                                space_freed += size
                            except Exception as e:
                                errors.append(f"Error deleting {file_path}: {e}")

                return {
                    'directory': directory,
                    'cleaned': cleaned,
                    'space_freed': space_freed,
                    'errors': []
                }

            except Exception as e:
                return {
                    'directory': directory,
                    'cleaned': 0,
                    'space_freed': 0,
                    'errors': [str(e)]
                }

        # Process directories in parallel
        results = self._parallel.map_with_progress(
            cleanup_directory,
            directories,
            "Cleaning directories"
        )

        # Aggregate results
        for result in results:
            total_cleaned += result['cleaned']
            total_space_freed += result['space_freed']
            errors.extend(result['errors'])
            self._progress.update_task("temp_cleanup", 1)

        self._progress.complete_task("temp_cleanup")

        return {
            'directories_processed': len(directories),
            'total_files_cleaned': total_cleaned,
            'total_space_freed': total_space_freed,
            'errors': errors,
            'results': results
        }


class AsyncOperationQueue:
    """
    Asynchronous operation queue for background processing.
    """

    def __init__(self, max_workers: int = 2):
        """
        Initialize async operation queue.

        Args:
            max_workers: Maximum number of background workers
        """
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._queue: Queue[Dict[str, Any]] = Queue()
        self._results: Dict[str, Future] = {}
        self._lock = threading.Lock()

        # Start result collector thread
        self._collector_thread = threading.Thread(target=self._collect_results, daemon=True)
        self._collector_thread.start()

    def submit_operation(self, operation_id: str, operation_func: Callable, *args, **kwargs) -> str:
        """
        Submit an operation for asynchronous execution.

        Args:
            operation_id: Unique identifier for the operation
            operation_func: Function to execute
            *args, **kwargs: Arguments for the operation function

        Returns:
            Operation ID
        """
        future = self._executor.submit(operation_func, *args, **kwargs)

        with self._lock:
            self._results[operation_id] = future

        return operation_id

    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of an asynchronous operation.

        Args:
            operation_id: Operation ID to check

        Returns:
            Operation status or None if not found
        """
        with self._lock:
            future = self._results.get(operation_id)
            if not future:
                return None

            if future.done():
                try:
                    result = future.result()
                    return {
                        'id': operation_id,
                        'status': 'completed',
                        'result': result
                    }
                except Exception as e:
                    return {
                        'id': operation_id,
                        'status': 'failed',
                        'error': str(e)
                    }
            else:
                return {
                    'id': operation_id,
                    'status': 'running'
                }

    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel a running operation.

        Args:
            operation_id: Operation ID to cancel

        Returns:
            True if cancelled, False otherwise
        """
        with self._lock:
            future = self._results.get(operation_id)
            if future and not future.done():
                cancelled = future.cancel()
                if cancelled:
                    del self._results[operation_id]
                return cancelled

        return False

    def _collect_results(self) -> None:
        """Background thread to collect completed operation results."""
        while True:
            # Clean up completed operations periodically
            with self._lock:
                completed_ids = [oid for oid, future in self._results.items() if future.done()]
                for oid in completed_ids:
                    del self._results[oid]

            time.sleep(60)  # Clean up every minute

    def shutdown(self) -> None:
        """Shutdown the async operation queue."""
        self._executor.shutdown(wait=True)


# Global instances
_parallel_processor: Optional[ParallelActionProcessor] = None
_async_queue: Optional[AsyncOperationQueue] = None


def get_parallel_action_processor(max_workers: int = 4) -> ParallelActionProcessor:
    """Get or create global parallel action processor instance."""
    global _parallel_processor
    if _parallel_processor is None:
        _parallel_processor = ParallelActionProcessor(max_workers)
    return _parallel_processor


def get_async_operation_queue(max_workers: int = 2) -> AsyncOperationQueue:
    """Get or create global async operation queue instance."""
    global _async_queue
    if _async_queue is None:
        _async_queue = AsyncOperationQueue(max_workers)
    return _async_queue


if __name__ == "__main__":
    # Test parallel processing
    processor = get_parallel_action_processor()

    # Test directory scanning
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test files
        for i in range(10):
            test_file = Path(temp_dir) / f"test_{i}.txt"
            test_file.write_text(f"Test content {i}")

        # Scan directory
        files = processor.scan_directory_parallel(temp_dir, recursive=False)
        print(f"Found {len(files)} files in {temp_dir}")

        # Test batch operation
        def count_lines(file_path: Path) -> int:
            try:
                return len(file_path.read_text().splitlines())
            except:
                return 0

        results = processor.batch_operation(count_lines, files, "Counting lines")
        print(f"Line counts: {results}")