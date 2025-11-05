"""
Progress Reporting System for AI File Organiser

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module provides progress bars, status updates, and parallel processing
capabilities for long-running file operations.

NOTICE: This software is proprietary and confidential. Unauthorized copying,
modification, distribution, or use is strictly prohibited.
See LICENSE.txt for full terms and conditions.

Version: 1.0.0
Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import threading
import time
from typing import Callable, Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
import logging

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


@dataclass
class ProgressTask:
    """Represents a single task with progress tracking."""
    id: str
    name: str
    total: int = 0
    completed: int = 0
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)

    @property
    def progress_percentage(self) -> float:
        """Get completion percentage."""
        if self.total == 0:
            return 100.0 if self.status == "completed" else 0.0
        return (self.completed / self.total) * 100.0

    @property
    def duration(self) -> Optional[float]:
        """Get task duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None

    def update(self, increment: int = 1, status: Optional[str] = None) -> None:
        """Update task progress."""
        self.completed += increment
        if status:
            self.status = status

        if self.completed >= self.total and self.total > 0:
            self.status = "completed"
            self.end_time = datetime.now()


class ProgressReporter:
    """
    Progress reporting system with progress bars and status updates.
    """

    def __init__(self, enable_progress_bars: bool = True, max_workers: int = 4):
        """
        Initialize progress reporter.

        Args:
            enable_progress_bars: Whether to show progress bars
            max_workers: Maximum number of parallel workers
        """
        self.enable_progress_bars = enable_progress_bars and TQDM_AVAILABLE
        self.max_workers = max_workers
        self.tasks: Dict[str, ProgressTask] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._logger = logging.getLogger(__name__)

    def create_task(self, task_id: str, name: str, total: int = 0) -> ProgressTask:
        """Create a new progress task."""
        task = ProgressTask(id=task_id, name=name, total=total, start_time=datetime.now())
        with self._lock:
            self.tasks[task_id] = task
        return task

    def update_task(self, task_id: str, increment: int = 1, status: Optional[str] = None) -> None:
        """Update an existing task's progress."""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(increment, status)

    def complete_task(self, task_id: str) -> None:
        """Mark a task as completed."""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = "completed"
                task.end_time = datetime.now()
                task.completed = task.total

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark a task as failed with an error."""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = "failed"
                task.end_time = datetime.now()
                task.errors.append(error)

    def get_task_status(self, task_id: str) -> Optional[ProgressTask]:
        """Get the status of a specific task."""
        with self._lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, ProgressTask]:
        """Get all current tasks."""
        with self._lock:
            return self.tasks.copy()

    def clear_completed_tasks(self) -> None:
        """Remove completed tasks from tracking."""
        with self._lock:
            self.tasks = {k: v for k, v in self.tasks.items() if v.status not in ["completed", "failed"]}

    def process_items_parallel(self, items: List[Any], process_func: Callable[[Any], Any],
                             task_name: str = "Processing", chunk_size: int = 10) -> List[Any]:
        """
        Process items in parallel with progress reporting.

        Args:
            items: List of items to process
            process_func: Function to process each item
            task_name: Name for the progress task
            chunk_size: Number of items to process before updating progress

        Returns:
            List of results
        """
        if not items:
            return []

        task_id = f"{task_name.lower().replace(' ', '_')}_{int(time.time())}"
        task = self.create_task(task_id, task_name, len(items))

        results = []
        futures = []

        # Submit all tasks
        for item in items:
            future = self._executor.submit(process_func, item)
            futures.append((future, item))

        # Process results with progress updates
        completed = 0
        for future, item in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                self._logger.error(f"Error processing item {item}: {e}")
                task.errors.append(f"Error processing {item}: {e}")

            completed += 1
            if completed % chunk_size == 0 or completed == len(items):
                self.update_task(task_id, chunk_size)

        self.complete_task(task_id)
        return results

    def process_with_progress_bar(self, items: List[Any], process_func: Callable[[Any], Any],
                                task_name: str = "Processing") -> List[Any]:
        """
        Process items with a progress bar.

        Args:
            items: List of items to process
            process_func: Function to process each item
            task_name: Name for the progress task

        Returns:
            List of results
        """
        if not self.enable_progress_bars:
            return [process_func(item) for item in items]

        results = []
        with tqdm(total=len(items), desc=task_name, unit="item") as pbar:
            for item in items:
                try:
                    result = process_func(item)
                    results.append(result)
                except Exception as e:
                    self._logger.error(f"Error processing item: {e}")
                    results.append(None)
                pbar.update(1)

        return results

    def create_progress_callback(self, task_id: str) -> Callable[[int, str], None]:
        """Create a callback function for updating task progress."""
        def callback(increment: int = 1, status: Optional[str] = None):
            self.update_task(task_id, increment, status)
        return callback

    def get_summary_report(self) -> Dict[str, Any]:
        """Get a summary report of all tasks."""
        with self._lock:
            tasks = list(self.tasks.values())

        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "completed"])
        failed_tasks = len([t for t in tasks if t.status == "failed"])
        active_tasks = len([t for t in tasks if t.status == "running"])

        total_errors = sum(len(t.errors) for t in tasks)

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "active_tasks": active_tasks,
            "total_errors": total_errors,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "status": t.status,
                    "progress": t.progress_percentage,
                    "duration": t.duration,
                    "errors": len(t.errors)
                }
                for t in tasks
            ]
        }


class ParallelProcessor:
    """
    Utility class for parallel processing with progress reporting.
    """

    def __init__(self, progress_reporter: ProgressReporter, max_workers: int = 4):
        """
        Initialize parallel processor.

        Args:
            progress_reporter: Progress reporter instance
            max_workers: Maximum number of worker threads
        """
        self.progress = progress_reporter
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def map_with_progress(self, func: Callable, items: List[Any],
                         task_name: str = "Processing") -> List[Any]:
        """
        Map function over items with progress reporting.

        Args:
            func: Function to apply to each item
            items: List of items to process
            task_name: Name for progress tracking

        Returns:
            List of results
        """
        return self.progress.process_items_parallel(items, func, task_name)

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self.executor.shutdown(wait=True)


# Global instances
_progress_reporter: Optional[ProgressReporter] = None
_parallel_processor: Optional[ParallelProcessor] = None


def get_progress_reporter(enable_progress_bars: bool = True, max_workers: int = 4) -> ProgressReporter:
    """Get or create global progress reporter instance."""
    global _progress_reporter
    if _progress_reporter is None:
        _progress_reporter = ProgressReporter(enable_progress_bars, max_workers)
    return _progress_reporter


def get_parallel_processor(max_workers: int = 4) -> ParallelProcessor:
    """Get or create global parallel processor instance."""
    global _parallel_processor, _progress_reporter
    if _progress_reporter is None:
        _progress_reporter = get_progress_reporter(max_workers=max_workers)
    if _parallel_processor is None:
        _parallel_processor = ParallelProcessor(_progress_reporter, max_workers)
    return _parallel_processor


if __name__ == "__main__":
    # Test progress reporting
    reporter = get_progress_reporter()

    # Create a test task
    task = reporter.create_task("test_task", "Test Processing", 100)

    # Simulate progress
    import time
    for i in range(100):
        time.sleep(0.01)
        reporter.update_task("test_task", 1)

    reporter.complete_task("test_task")

    # Print summary
    summary = reporter.get_summary_report()
    print("Progress Summary:")
    print(f"Total tasks: {summary['total_tasks']}")
    print(f"Completed: {summary['completed_tasks']}")
    print(f"Failed: {summary['failed_tasks']}")

    for task_info in summary['tasks']:
        print(f"  {task_info['name']}: {task_info['progress']:.1f}% ({task_info['status']})")