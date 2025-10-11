"""
Logging module for the Calorie Tracker application.

This module provides a centralized logging configuration with:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Console and file handlers
- Contextual information in log messages
- Log rotation for file handlers
- Thread-safe implementation
- Exception logging utilities
"""

import logging
import os
import sys
import time
import traceback
import asyncio
from datetime import datetime
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from .settings import settings

# Type variables for function decorators
F = TypeVar('F', bound=Callable[..., Any])

# Create logs directory if it doesn't exist
LOGS_DIR = Path(getattr(settings, "LOG_DIR", "logs"))
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
APP_LOG_FILE = LOGS_DIR / "app.log"
ERROR_LOG_FILE = LOGS_DIR / "error.log"
ACCESS_LOG_FILE = LOGS_DIR / "access.log"

# Log rotation settings
MAX_BYTES = getattr(settings, "LOG_FILE_MAX_SIZE", 10 * 1024 * 1024)  # 10 MB
BACKUP_COUNT = getattr(settings, "LOG_FILE_BACKUP_COUNT", 5)

# Log formatters
VERBOSE_FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
SIMPLE_FORMATTER = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ACCESS_FORMATTER = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - request_id=%(request_id)s - '
    'method=%(method)s - path=%(path)s - status=%(status)d - duration=%(duration).2fms'
)

# Default log level
DEFAULT_LOG_LEVEL = getattr(logging, getattr(settings, "LOG_LEVEL", "INFO"))

def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger with the specified name.
    
    Args:
        name: The name of the logger, typically __name__ of the module
        
    Returns:
        A configured logger instance with appropriate handlers
    """
    logger = logging.getLogger(name)
    
    # Only configure handlers if they haven't been added yet
    if not logger.handlers:
        # Set the log level
        logger.setLevel(DEFAULT_LOG_LEVEL)
        
        # Console handler (for all levels)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(SIMPLE_FORMATTER)
        logger.addHandler(console_handler)
        
        # File handler for all logs
        file_handler = RotatingFileHandler(
            APP_LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT
        )
        file_handler.setFormatter(VERBOSE_FORMATTER)
        logger.addHandler(file_handler)
        
        # File handler for errors only
        error_file_handler = RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(VERBOSE_FORMATTER)
        logger.addHandler(error_file_handler)
    
    return logger

def log_exception(logger: logging.Logger, e: Exception, message: str = "An exception occurred"):
    """
    Log an exception with traceback information.
    
    Args:
        logger: The logger instance
        e: The exception to log
        message: Optional message to include with the exception
    """
    logger.error(f"{message}: {str(e)}")
    logger.debug(f"Exception traceback: {''.join(traceback.format_tb(e.__traceback__))}")

class RequestContextFilter(logging.Filter):
    """
    Logging filter that adds request context information to log records.
    """
    def __init__(self, request_id: str = "", method: str = "", path: str = "", 
                 status: int = 0, duration: float = 0.0):
        super().__init__()
        self.request_id = request_id
        self.method = method
        self.path = path
        self.status = status
        self.duration = duration
    
    def filter(self, record):
        record.request_id = self.request_id
        record.method = self.method
        record.path = self.path
        record.status = self.status
        record.duration = self.duration
        return True

def get_access_logger() -> logging.Logger:
    """
    Get a logger specifically for API access logs.
    
    Returns:
        A configured logger for access logs
    """
    logger = logging.getLogger("access")
    
    # Only configure handlers if they haven't been added yet
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # File handler for access logs
        access_file_handler = RotatingFileHandler(
            ACCESS_LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT
        )
        access_file_handler.setFormatter(ACCESS_FORMATTER)
        logger.addHandler(access_file_handler)
        
        # Console handler for access logs (optional, can be disabled)
        if getattr(settings, "LOG_ACCESS_TO_CONSOLE", False):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(ACCESS_FORMATTER)
            logger.addHandler(console_handler)
    
    return logger

def log_execution_time(logger: Optional[logging.Logger] = None, level: int = logging.DEBUG):
    """
    Decorator to log the execution time of a function.
    Supports both synchronous and asynchronous functions.
    
    Args:
        logger: The logger to use. If None, a logger will be created with the function's module name.
        level: The log level to use (default: DEBUG)
    
    Returns:
        Decorator function that works with both sync and async functions
    """
    def decorator(func: F) -> F:
        # Check if the function is a coroutine function (async)
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Get logger if not provided
                nonlocal logger
                if logger is None:
                    logger = get_logger(func.__module__)
                
                # Log function call
                func_name = func.__qualname__
                logger.log(level, f"Executing async {func_name}")
                
                # Time execution
                start_time = time.time()
                try:
                    # Await the coroutine
                    result = await func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000  # Convert to ms
                    logger.log(level, f"Completed async {func_name} in {execution_time:.2f}ms")
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000  # Convert to ms
                    logger.log(level, f"Failed async {func_name} after {execution_time:.2f}ms: {str(e)}")
                    # Re-raise the exception
                    raise
            
            return cast(F, async_wrapper)
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Get logger if not provided
                nonlocal logger
                if logger is None:
                    logger = get_logger(func.__module__)
                
                # Log function call
                func_name = func.__qualname__
                logger.log(level, f"Executing {func_name}")
                
                # Time execution
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000  # Convert to ms
                    logger.log(level, f"Completed {func_name} in {execution_time:.2f}ms")
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000  # Convert to ms
                    logger.log(level, f"Failed {func_name} after {execution_time:.2f}ms: {str(e)}")
                    # Re-raise the exception
                    raise
            
            return cast(F, sync_wrapper)
    
    return decorator

class RequestLoggingMiddleware:
    """
    Middleware for logging FastAPI requests and responses.
    """
    def __init__(self, app):
        self.app = app
        self.logger = get_access_logger()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        # Generate request ID
        request_id = f"{int(time.time())}-{os.urandom(4).hex()}"
        
        # Extract request information
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "UNKNOWN")
        
        # Create context filter
        context_filter = RequestContextFilter(
            request_id=request_id,
            method=method,
            path=path
        )
        
        # Add filter to logger
        self.logger.addFilter(context_filter)
        
        # Log request start
        self.logger.info(f"Request started")
        
        # Time the request
        start_time = time.time()
        
        # Custom send function to capture response status
        status_code = [200]  # Default status code
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
            await send(message)
        
        # Process the request
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Log exception
            status_code[0] = 500
            self.logger.error(f"Request failed: {str(e)}")
            raise
        finally:
            # Calculate duration
            duration = (time.time() - start_time) * 1000  # Convert to ms
            
            # Update context filter with final information
            context_filter.status = status_code[0]
            context_filter.duration = duration
            
            # Log request completion
            self.logger.info(f"Request completed")
            
            # Remove filter
            self.logger.removeFilter(context_filter)

# Initialize root logger
root_logger = logging.getLogger()
root_logger.setLevel(DEFAULT_LOG_LEVEL)

# Add a console handler to the root logger if it doesn't have one
if not root_logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(SIMPLE_FORMATTER)
    root_logger.addHandler(console_handler)

# Create a module-level logger
logger = get_logger(__name__)
logger.info("Logging system initialized")