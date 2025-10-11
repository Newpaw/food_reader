# Logging Implementation Plan for Calorie Tracker Application

## Overview

Based on the analysis of the project structure, we'll implement a comprehensive logging system using Python's built-in `logging` module. The logging system will provide appropriate log levels, multiple handlers, contextual information, and follow best practices for exception logging.

## Project Structure Analysis

The calorie tracker application is a FastAPI-based web application with the following key components:

1. **Main Application Entry Point**: `calorie-tracker/backend/app/main.py`
2. **Settings Management**: `calorie-tracker/backend/app/settings.py`
3. **API Routers**: Located in `calorie-tracker/backend/app/routers/`
4. **AI Analysis**: `calorie-tracker/backend/app/ai_analyzer.py`
5. **Database Models and CRUD Operations**: `models.py`, `crud.py`, and `database.py`

## Logging System Design

### 1. Logging Configuration Module

We'll create a new module `calorie-tracker/backend/app/logger.py` that will:

- Configure the root logger
- Define log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Set up handlers for different output destinations (file, console)
- Configure formatters with contextual information
- Implement log rotation for file handlers
- Ensure thread safety

### 2. Log Levels Usage Guidelines

- **DEBUG**: Detailed information, typically useful only for diagnosing problems
  - Database queries
  - API request/response details
  - Function entry/exit points with parameters
  
- **INFO**: Confirmation that things are working as expected
  - Application startup/shutdown
  - User authentication events
  - Meal creation/updates
  - AI analysis results
  
- **WARNING**: Indication that something unexpected happened, or may happen in the near future
  - Deprecated feature usage
  - API rate limiting approaching
  - AI analysis fallbacks
  
- **ERROR**: Due to a more serious problem, the software couldn't perform some function
  - Database connection failures
  - API errors
  - File I/O errors
  - AI analysis errors
  
- **CRITICAL**: A serious error indicating that the program itself may be unable to continue running
  - Unhandled exceptions
  - Configuration errors preventing startup

### 3. Implementation Details

#### Logger Configuration

```python
# logger.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .settings import settings

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Define log formatters
VERBOSE_FORMATTER = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
SIMPLE_FORMATTER = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: The name of the logger, typically __name__ of the module
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure handlers if they haven't been added yet
    if not logger.handlers:
        # Set the log level from settings or default to INFO
        log_level = getattr(settings, "LOG_LEVEL", "INFO")
        logger.setLevel(getattr(logging, log_level))
        
        # Console handler (for all levels)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(SIMPLE_FORMATTER)
        logger.addHandler(console_handler)
        
        # File handler for all logs
        all_logs_file = logs_dir / "app.log"
        file_handler = RotatingFileHandler(
            all_logs_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(VERBOSE_FORMATTER)
        logger.addHandler(file_handler)
        
        # File handler for errors only
        error_logs_file = logs_dir / "error.log"
        error_file_handler = RotatingFileHandler(
            error_logs_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(VERBOSE_FORMATTER)
        logger.addHandler(error_file_handler)
    
    return logger
```

#### Settings Update

We'll add logging configuration to the settings module:

```python
# settings.py additions
class Settings(BaseSettings):
    # Existing settings...
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FILE_MAX_SIZE: int = 10 * 1024 * 1024  # 10 MB
    LOG_FILE_BACKUP_COUNT: int = 5
```

#### Exception Logging Utility

```python
# logger.py (additional function)
import traceback

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
```

### 4. Integration Points

We'll integrate logging into the following key components:

1. **Application Startup/Shutdown**:
   - Log application startup in `main.py`
   - Log configuration details

2. **Request/Response Middleware**:
   - Add a middleware to log all API requests and responses
   - Include request method, path, status code, and duration

3. **Database Operations**:
   - Log database connection events
   - Log query execution (at DEBUG level)

4. **AI Analysis**:
   - Log analysis requests and responses
   - Log errors and fallbacks

5. **Authentication**:
   - Log login attempts (successful and failed)
   - Log token generation and validation

### 5. Thread Safety Considerations

The Python `logging` module is thread-safe by default. However, we'll ensure our implementation maintains this property by:

1. Using thread-local storage for any custom logging context
2. Avoiding shared mutable state in logging functions
3. Using proper synchronization for any custom handlers

### 6. Best Practices Implementation

1. **Contextual Logging**:
   - Include timestamps, module names, line numbers in log messages
   - Add request IDs to track requests across components

2. **Structured Logging**:
   - Use consistent message formats
   - Include relevant data as structured fields

3. **Error Handling**:
   - Catch and log exceptions properly
   - Include full traceback information for debugging

4. **Performance Considerations**:
   - Use lazy evaluation for expensive operations in log messages
   - Implement appropriate log levels to control verbosity

## Implementation Steps

1. Create the `logger.py` module with core functionality
2. Update `settings.py` with logging configuration
3. Integrate logging into the main application entry point
4. Add request/response logging middleware
5. Integrate logging into key components (AI analyzer, routers, etc.)
6. Add exception logging throughout the application
7. Create documentation for the logging system

## Usage Examples

### Basic Usage

```python
from app.logger import get_logger

logger = get_logger(__name__)

def some_function(param):
    logger.debug(f"some_function called with param: {param}")
    try:
        # Function logic
        result = process_data(param)
        logger.info(f"Data processed successfully: {result}")
        return result
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}", exc_info=True)
        raise
```

### Request Context Logging

```python
from fastapi import Request, Depends
from app.logger import get_logger

logger = get_logger(__name__)

async def log_request(request: Request):
    logger.info(f"Request received: {request.method} {request.url.path}")
    # Process request
```

### Exception Logging

```python
from app.logger import get_logger, log_exception

logger = get_logger(__name__)

try:
    # Some operation that might fail
    result = risky_operation()
except Exception as e:
    log_exception(logger, e, "Failed to perform risky operation")
    # Handle the exception