"""
Enhanced Structured Logging Module

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module provides production-grade structured logging with:
- JSON formatting for easy parsing and analysis
- Configurable log levels per module
- File rotation to prevent disk space issues
- Performance timing decorators
- Integration with error handling

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable
import time
from functools import wraps


# ============================================================================
# JSON Formatter for Structured Logging
# ============================================================================

class JSONFormatter(logging.Formatter):
    """
    Format logs as JSON for structured logging.
    
    Based on Microsoft Azure logging best practices:
    - Structured format for easy parsing
    - Includes timestamp, level, message, context
    - Optional exception information
    - Custom fields support
    
    Research Source: Microsoft Docs - Azure logging patterns
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
        
        Returns:
            JSON string with log data
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add custom fields from 'extra' parameter in log calls
        # Example: logger.info("msg", extra={'file_path': path, 'operation': 'move'})
        custom_fields = [
            'file_path', 'operation', 'category', 'confidence', 'method',
            'risk_level', 'action', 'destination', 'duration', 'attempt',
            'model', 'error_type', 'user', 'task_id'
        ]
        
        for field in custom_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        
        return json.dumps(log_data)


# ============================================================================
# Enhanced Logger Setup
# ============================================================================

def setup_structured_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    app_name: str = "ai_file_organiser",
    enable_json: bool = True,
    enable_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        app_name: Application name (used for log filenames)
        enable_json: Use JSON format for file logs
        enable_console: Enable console output
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        Configured root logger
    
    Example:
        >>> logger = setup_structured_logging(log_level="DEBUG", enable_json=True)
        >>> logger.info("Application started", extra={'version': '1.0.0'})
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # ========================================
    # Console Handler (Human-Readable)
    # ========================================
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Simple format for console
        console_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # ========================================
    # File Handler (JSON for Parsing)
    # ========================================
    log_file = log_path / f"{app_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # Capture everything to file
    
    if enable_json:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
    
    root_logger.addHandler(file_handler)
    
    # ========================================
    # Error File Handler (Errors Only)
    # ========================================
    error_file = log_path / f"{app_name}_errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    
    if enable_json:
        error_handler.setFormatter(JSONFormatter())
    else:
        error_handler.setFormatter(file_formatter)
    
    root_logger.addHandler(error_handler)
    
    # Log startup
    root_logger.info(
        f"Logging initialized: level={log_level}, json={enable_json}, dir={log_dir}",
        extra={'event_type': 'logging_initialized'}
    )
    
    return root_logger


# ============================================================================
# Performance Timing Decorator
# ============================================================================

def log_timing(logger: Optional[logging.Logger] = None, 
               log_level: int = logging.INFO) -> Callable:
    """
    Decorator to log execution time of functions.
    
    Args:
        logger: Logger to use (if None, uses root logger)
        log_level: Log level for timing messages
    
    Returns:
        Decorated function
    
    Example:
        >>> @log_timing()
        >>> def classify_file(file_path):
        ...     return classifier.classify(file_path)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            log = logger or logging.getLogger()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                log.log(
                    log_level,
                    f"{func.__name__} completed in {duration:.3f}s",
                    extra={
                        'function': func.__name__,
                        'duration': duration,
                        'event_type': 'function_timing'
                    }
                )
                
                return result
            
            except Exception as e:
                duration = time.time() - start_time
                log.error(
                    f"{func.__name__} failed after {duration:.3f}s: {e}",
                    extra={
                        'function': func.__name__,
                        'duration': duration,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'event_type': 'function_error'
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


# ============================================================================
# Enhanced Logger Class (Backwards Compatible)
# ============================================================================

class AgentLogger:
    """
    Enhanced wrapper class for agent-specific logging with structured output.
    
    Maintains backwards compatibility with existing code while adding
    new structured logging capabilities.
    """
    
    def __init__(self, name: str = 'ai_file_organiser'):
        """
        Initialize the logger.
        
        Args:
            name: Logger name (default: 'ai_file_organiser')
        """
        self.logger = logging.getLogger(name)
        
        # Configure if not already done
        if not self.logger.handlers:
            setup_structured_logging(app_name=name)
    
    def info(self, message: str, **context):
        """Log info message with context"""
        self.logger.info(message, extra=context)
    
    def debug(self, message: str, **context):
        """Log debug message with context"""
        self.logger.debug(message, extra=context)
    
    def warning(self, message: str, **context):
        """Log warning message with context"""
        self.logger.warning(message, extra=context)
    
    def error(self, message: str, **context):
        """Log error message with context"""
        self.logger.error(message, extra=context)
    
    def critical(self, message: str, **context):
        """Log critical message with context"""
        self.logger.critical(message, extra=context)
    
    # ========================================
    # Event-Specific Logging Methods
    # ========================================
    
    def log_operation(self, operation: str, file_path: str, **details):
        """Log file operation"""
        self.logger.info(
            f"File operation: {operation}",
            extra={
                'operation': operation,
                'file_path': file_path,
                'event_type': 'file_operation',
                **details
            }
        )
    
    def log_classification(self, file_path: str, category: str, 
                          confidence: str, method: str, **details):
        """Log file classification"""
        self.logger.info(
            f"File classified: {category} ({confidence})",
            extra={
                'file_path': file_path,
                'category': category,
                'confidence': confidence,
                'method': method,
                'event_type': 'classification',
                **details
            }
        )
    
    def model_call(self, model: str, operation: str, duration: Optional[float] = None):
        """Log AI model call"""
        msg = f"Model call: {model} - {operation}"
        if duration:
            msg += f" ({duration:.2f}s)"
        
        self.logger.info(
            msg,
            extra={
                'model': model,
                'operation': operation,
                'duration': duration,
                'event_type': 'model_call'
            }
        )
    
    def model_failure(self, model: str, error: str, retry_count: int = 0):
        """Log AI model failure"""
        self.logger.error(
            f"Model call failed: {model}",
            extra={
                'model': model,
                'error': error,
                'retry_count': retry_count,
                'event_type': 'model_failure'
            }
        )
    
    def validation_failure(self, error: str, raw_response_preview: Optional[str] = None):
        """Log validation failure"""
        self.logger.warning(
            f"Validation failed: {error}",
            extra={
                'error': error,
                'raw_response_preview': raw_response_preview[:200] if raw_response_preview else None,
                'event_type': 'validation_failure'
            }
        )
    
    def safety_block(self, file_path: str, reason: str, check_type: str, risk_level: Optional[str] = None):
        """Log safety check blocking an action"""
        self.logger.warning(
            f"Safety check blocked: {reason}",
            extra={
                'file_path': file_path,
                'reason': reason,
                'check_type': check_type,
                'risk_level': risk_level,
                'event_type': 'safety_block'
            }
        )
    
    def agent_decision(self, file_path: str, action: str, reason: str, **details):
        """Log agent decision"""
        self.logger.info(
            f"Agent decision: {action}",
            extra={
                'file_path': file_path,
                'action': action,
                'reason': reason,
                'event_type': 'agent_decision',
                **details
            }
        )


# ============================================================================
# Global Logger Instance
# ============================================================================

# Global instance for backwards compatibility
_global_logger = None

def get_logger(name: str = 'ai_file_organiser') -> AgentLogger:
    """
    Get or create global logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        AgentLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = AgentLogger(name)
    return _global_logger


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    # Test structured logging
    print("Testing enhanced structured logging...")
    
    # Setup logging
    logger = setup_structured_logging(
        log_level="DEBUG",
        log_dir="logs",
        enable_json=True,
        enable_console=True
    )
    
    # Test basic logging
    logger.info("Application started", extra={'version': '1.0.0'})
    logger.debug("Debug message with context", extra={'file_path': '/test/file.txt'})
    logger.warning("Warning message", extra={'operation': 'move', 'risk_level': 'caution'})
    
    # Test timing decorator
    @log_timing(logger)
    def slow_function():
        time.sleep(0.1)
        return "Done"
    
    result = slow_function()
    print(f"✓ Timing decorator: {result}")
    
    # Test AgentLogger
    agent_logger = AgentLogger()
    agent_logger.log_classification(
        file_path="/test/document.pdf",
        category="Documents",
        confidence="high",
        method="ai"
    )
    
    agent_logger.safety_block(
        file_path="/test/system.exe",
        reason="Protected system file",
        check_type="system_protection",
        risk_level="critical"
    )
    
    # Test error logging
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.error("Caught exception", exc_info=True, extra={'operation': 'test'})
    
    print("\n✅ All logging tests completed!")
    print("Check logs/ directory for output files")
