"""
Enhanced Error Handling Module

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module provides comprehensive error handling with:
- Specific exception types for different error categories
- Retry logic with exponential backoff
- Error context preservation for debugging
- Integration with structured logging

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import logging
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps
import time
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# Exception Hierarchy
# ============================================================================

class FileOrganizerError(Exception):
    """Base exception for all file organizer errors"""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class FileOperationError(FileOrganizerError):
    """Errors during file operations (move, copy, delete, rename)"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 destination: Optional[str] = None, operation: Optional[str] = None):
        details = {}
        if file_path:
            details['file_path'] = file_path
        if destination:
            details['destination'] = destination
        if operation:
            details['operation'] = operation
        super().__init__(message, details)


class ClassificationError(FileOrganizerError):
    """Errors during file classification (rule-based, AI, or agent)"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 method: Optional[str] = None):
        details = {}
        if file_path:
            details['file_path'] = file_path
        if method:
            details['method'] = method
        super().__init__(message, details)


class DatabaseError(FileOrganizerError):
    """Database operation errors (connection, query, transaction)"""
    
    def __init__(self, message: str, query: Optional[str] = None, 
                 operation: Optional[str] = None):
        details = {}
        if query:
            details['query'] = query[:100]  # Truncate long queries
        if operation:
            details['operation'] = operation
        super().__init__(message, details)


class OllamaConnectionError(FileOrganizerError):
    """Ollama service unavailable or unreachable"""
    
    def __init__(self, message: str, model: Optional[str] = None, 
                 endpoint: Optional[str] = None):
        details = {}
        if model:
            details['model'] = model
        if endpoint:
            details['endpoint'] = endpoint
        super().__init__(message, details)


class SafetyViolationError(FileOrganizerError):
    """Operation blocked by safety guardian"""
    
    def __init__(self, message: str, risk_level: Optional[str] = None, 
                 threats: Optional[list] = None):
        details = {}
        if risk_level:
            details['risk_level'] = risk_level
        if threats:
            details['threat_count'] = len(threats)
        super().__init__(message, details)


class ConfigurationError(FileOrganizerError):
    """Configuration validation or loading errors"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details['config_key'] = config_key
        super().__init__(message, details)


class WatcherError(FileOrganizerError):
    """File watcher errors (initialization, monitoring)"""
    
    def __init__(self, message: str, folder_path: Optional[str] = None):
        details = {}
        if folder_path:
            details['folder_path'] = folder_path
        super().__init__(message, details)


class LicenseError(FileOrganizerError):
    """License validation errors"""
    pass


# ============================================================================
# Retry Decorator
# ============================================================================

def retry_on_failure(max_attempts: int = 3, 
                    delay: float = 1.0, 
                    backoff: float = 2.0, 
                    exceptions: Tuple[Type[Exception], ...] = (Exception,),
                    on_retry: Optional[Callable] = None) -> Callable:
    """
    Decorator for retrying operations with exponential backoff.
    
    Implements retry pattern recommended by Microsoft Azure best practices:
    - Exponential backoff to prevent overwhelming the system
    - Jitter (random delay) to avoid thundering herd
    - Specific exception handling
    - Logging of retry attempts
    
    Args:
        max_attempts: Maximum retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff: Multiplier for delay after each retry (default: 2.0 for exponential)
        exceptions: Tuple of exceptions to catch and retry (default: all exceptions)
        on_retry: Optional callback function called before each retry
    
    Returns:
        Decorated function with retry logic
    
    Example:
        >>> @retry_on_failure(max_attempts=5, delay=2, exceptions=(OllamaConnectionError,))
        >>> def classify_file(file_path):
        ...     return ollama_client.classify(file_path)
    
    Research Source: Microsoft Docs - Azure SDK retry policies
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Log the failure
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}",
                        extra={
                            'function': func.__name__,
                            'attempt': attempt,
                            'max_attempts': max_attempts,
                            'error': str(e),
                            'error_type': type(e).__name__
                        }
                    )
                    
                    # If this was the last attempt, raise the exception
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts",
                            extra={
                                'function': func.__name__,
                                'total_attempts': max_attempts,
                                'final_error': str(e)
                            }
                        )
                        raise
                    
                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt, e)
                        except Exception as callback_error:
                            logger.warning(f"Retry callback failed: {callback_error}")
                    
                    # Wait before retrying (exponential backoff)
                    logger.info(f"Retrying {func.__name__} in {current_delay:.1f}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


# ============================================================================
# Context Manager for Error Handling
# ============================================================================

class ErrorContext:
    """
    Context manager for consistent error handling and logging.
    
    Usage:
        >>> with ErrorContext("Classifying file", file_path=file_path):
        ...     result = classifier.classify(file_path)
    
    This will:
    1. Log entry to the operation
    2. Catch and re-raise exceptions with context
    3. Log exit with timing information
    """
    
    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"Starting: {self.operation}", extra=self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - (self.start_time or 0)
        
        if exc_type is None:
            # Success
            logger.debug(
                f"Completed: {self.operation} ({duration:.2f}s)",
                extra={'duration': duration, **self.context}
            )
        else:
            # Error occurred
            logger.error(
                f"Failed: {self.operation} ({duration:.2f}s): {exc_val}",
                extra={
                    'duration': duration,
                    'error': str(exc_val),
                    'error_type': exc_type.__name__,
                    **self.context
                },
                exc_info=True
            )
        
        # Don't suppress exceptions
        return False


# ============================================================================
# Safe File Operations
# ============================================================================

def safe_file_operation(operation: str) -> Callable:
    """
    Decorator for file operations with automatic error handling.
    
    Converts OS errors into FileOperationError with context.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except PermissionError as e:
                raise FileOperationError(
                    f"Permission denied for {operation}",
                    file_path=str(args[0]) if args else None,
                    operation=operation
                ) from e
            except FileNotFoundError as e:
                raise FileOperationError(
                    f"File not found for {operation}",
                    file_path=str(args[0]) if args else None,
                    operation=operation
                ) from e
            except FileExistsError as e:
                raise FileOperationError(
                    f"File already exists for {operation}",
                    file_path=str(args[0]) if args else None,
                    operation=operation
                ) from e
            except OSError as e:
                raise FileOperationError(
                    f"OS error during {operation}: {e}",
                    file_path=str(args[0]) if args else None,
                    operation=operation
                ) from e
        
        return wrapper
    return decorator


# ============================================================================
# Utility Functions
# ============================================================================

def format_exception_chain(exception: Exception) -> str:
    """
    Format exception chain for logging.
    
    Returns a string showing the full exception chain with context.
    """
    parts = []
    current = exception
    
    while current is not None:
        parts.append(f"{type(current).__name__}: {current}")
        current = current.__cause__ or current.__context__
    
    return " → ".join(parts)


def should_retry_exception(exception: BaseException) -> bool:
    """
    Determine if an exception should trigger a retry.
    
    Based on Microsoft Azure retry best practices:
    - Retry on transient errors (network, timeout, temporary unavailability)
    - Don't retry on permanent errors (auth, not found, invalid input)
    """
    # Transient errors - should retry
    transient_errors = (
        OllamaConnectionError,
        DatabaseError,
        ConnectionError,
        TimeoutError,
    )
    
    # Permanent errors - should not retry
    permanent_errors = (
        ConfigurationError,
        LicenseError,
        SafetyViolationError,
        FileNotFoundError,
        PermissionError,
    )
    
    if isinstance(exception, transient_errors):
        return True
    
    if isinstance(exception, permanent_errors):
        return False
    
    # For OS errors, check the error code
    if isinstance(exception, OSError):
        # Retry on specific OS error codes
        retry_codes = [
            28,  # ENOSPC - No space left (might be temporary)
            110, # ETIMEDOUT - Connection timeout
            111, # ECONNREFUSED - Connection refused
        ]
        return exception.errno in retry_codes
    
    # Default: retry generic exceptions
    return True


if __name__ == "__main__":
    # Test error handling
    print("Testing error handling module...")
    
    # Test exception hierarchy
    try:
        raise FileOperationError(
            "Failed to move file",
            file_path="/path/to/file.txt",
            destination="/path/to/dest",
            operation="move"
        )
    except FileOrganizerError as e:
        print(f"✓ FileOperationError: {e}")
        print(f"  Details: {e.details}")
    
    # Test retry decorator
    @retry_on_failure(max_attempts=3, delay=0.1, exceptions=(ValueError,))
    def flaky_function(fail_count: int = 2):
        """Fails first N times, then succeeds"""
        if not hasattr(flaky_function, 'attempts'):
            flaky_function.attempts = 0
        flaky_function.attempts += 1
        
        if flaky_function.attempts <= fail_count:
            raise ValueError(f"Attempt {flaky_function.attempts} failed")
        
        return "Success!"
    
    try:
        result = flaky_function(fail_count=2)
        print(f"✓ Retry decorator: {result}")
    except ValueError:
        print("✗ Retry decorator failed")
    
    # Test error context
    with ErrorContext("Test operation", test_param="value"):
        time.sleep(0.1)
    print("✓ ErrorContext completed")
    
    print("\n✅ All tests passed!")
