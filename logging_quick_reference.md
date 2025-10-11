# Python Logging Quick Reference Guide

## Overview

This document provides a quick reference for using the logging system implemented in the Calorie Tracker application. The logging system is built on Python's built-in `logging` module and provides comprehensive logging capabilities with appropriate log levels, multiple handlers, contextual information, and best practices for exception logging.

## Key Components

1. **Logger Module**: `calorie-tracker/backend/app/logger.py`
2. **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
3. **Output Destinations**: Console and rotating log files
4. **Log Files**:
   - `logs/app.log`: All log messages
   - `logs/error.log`: Error and critical messages only
   - `logs/access.log`: API request/response logs

## Basic Usage

### Getting a Logger

```python
from app.logger import get_logger

# Use the module name as the logger name
logger = get_logger(__name__)
```

### Logging at Different Levels

```python
# Debug: Detailed information for troubleshooting
logger.debug("Database query executed: SELECT * FROM users")

# Info: Confirmation that things are working as expected
logger.info("User authenticated successfully")

# Warning: Indication that something unexpected happened
logger.warning("API rate limit approaching (80% used)")

# Error: Due to a more serious problem, couldn't perform some function
logger.error("Failed to connect to database")

# Critical: A serious error, the program may be unable to continue
logger.critical("Application configuration missing critical values")
```

### Logging Exceptions

```python
from app.logger import log_exception

try:
    # Some operation that might fail
    result = risky_operation()
except Exception as e:
    log_exception(logger, e, "Failed to perform operation")
    # Handle the exception
```

### Timing Function Execution

```python
from app.logger import log_execution_time

@log_execution_time(logger)
def expensive_operation():
    # Operation logic
    pass
```

## Log Level Guidelines

| Level | When to Use | Examples |
|-------|-------------|----------|
| DEBUG | Detailed information for diagnosing problems | Function parameters, SQL queries, API request/response details |
| INFO | Confirmation that things are working as expected | Application startup, user authentication, meal creation |
| WARNING | Indication that something unexpected happened | Deprecated feature usage, API rate limiting, AI analysis fallbacks |
| ERROR | Due to a more serious problem, couldn't perform some function | Database connection failures, API errors, file I/O errors |
| CRITICAL | A serious error, the program may be unable to continue | Unhandled exceptions, configuration errors preventing startup |

## Best Practices

### 1. Contextual Information

Include relevant context in log messages:

```python
# Good
logger.info(f"User {user.username} (ID: {user.id}) authenticated successfully")

# Not as good
logger.info("User authenticated successfully")
```

### 2. Structured Logging

Use consistent message formats:

```python
# Good
logger.info(f"Meal created: id={meal.id}, calories={meal.calories}, user_id={meal.user_id}")

# Not as good
logger.info(f"Created meal {meal.id} with {meal.calories} calories")
```

### 3. Exception Handling Patterns

```python
# Pattern 1: Log and re-raise
try:
    result = some_operation()
    return result
except Exception as e:
    log_exception(logger, e, "Operation failed")
    raise  # Re-raise the exception

# Pattern 2: Log and return fallback
try:
    result = some_operation()
    return result
except Exception as e:
    log_exception(logger, e, "Operation failed, using fallback")
    return fallback_value  # Return a default/fallback value

# Pattern 3: Log and raise HTTP exception (for API endpoints)
try:
    result = some_operation()
    return result
except Exception as e:
    log_exception(logger, e, "Operation failed")
    raise HTTPException(status_code=500, detail=str(e))
```

### 4. Performance Considerations

Use lazy evaluation for expensive operations:

```python
# Instead of this:
logger.debug(f"Complex calculation result: {expensive_calculation()}")

# Do this:
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Complex calculation result: {expensive_calculation()}")
```

### 5. Avoid Logging Sensitive Information

Never log sensitive information:

```python
# BAD - logs sensitive information
logger.debug(f"User login attempt with password: {password}")

# GOOD - logs non-sensitive information
logger.debug(f"User login attempt for username: {username}")
```

## Configuration

The logging system is configured through the application settings:

```python
# In settings.py
class Settings(BaseSettings):
    # Logging settings
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_DIR: str = "logs"
    LOG_FILE_MAX_SIZE: int = 10 * 1024 * 1024  # 10 MB
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_ACCESS_TO_CONSOLE: bool = False  # Whether to log API access to console
```

## Log File Rotation

Log files are automatically rotated when they reach the configured maximum size:

- Maximum file size: 10 MB (configurable)
- Number of backup files: 5 (configurable)

When a log file reaches the maximum size, it is renamed with a suffix (e.g., `app.log.1`) and a new log file is created. The oldest backup is deleted when the maximum number of backups is reached.

## Thread Safety

The logging system is thread-safe by default. You can safely use loggers from multiple threads without additional synchronization.

## Common Logging Scenarios

### 1. Application Startup

```python
logger.info("Starting Calorie Tracker application")
logger.info(f"Environment: {settings.ENVIRONMENT}")
logger.info(f"Database: {settings.DATABASE_URL}")
logger.info("Application ready")
```

### 2. Database Operations

```python
logger.debug(f"Executing query: {query}")
logger.info(f"Created new record: id={record.id}")
logger.error(f"Database error: {str(e)}")
```

### 3. API Requests

The `RequestLoggingMiddleware` automatically logs API requests and responses:

```
2025-10-11 22:01:57,762 - access - INFO - Request started - request_id=1697065317-a1b2c3d4 - method=POST - path=/me/meals - status=200 - duration=0.00ms
2025-10-11 22:01:57,965 - access - INFO - Request completed - request_id=1697065317-a1b2c3d4 - method=POST - path=/me/meals - status=201 - duration=203.45ms
```

### 4. Error Handling

```python
try:
    # Operation that might fail
    result = risky_operation()
except Exception as e:
    log_exception(logger, e, "Operation failed")
    # Handle the exception appropriately
```

## Viewing Logs

### Console Logs

Console logs are displayed in the terminal where the application is running.

### File Logs

Log files are stored in the `logs` directory:

- `logs/app.log`: All log messages
- `logs/error.log`: Error and critical messages only
- `logs/access.log`: API request/response logs

You can view these logs using standard tools:

```bash
# View the last 100 lines of the app log
tail -n 100 logs/app.log

# Follow the app log in real-time
tail -f logs/app.log

# Search for errors in the app log
grep "ERROR" logs/app.log

# View logs for a specific date
grep "2025-10-11" logs/app.log
```

## Troubleshooting

### 1. No Logs Appearing

- Check that the log level is set appropriately in settings
- Verify that the logs directory exists and is writable
- Check that the logger is being initialized correctly

### 2. Too Many Logs

- Increase the log level (e.g., from DEBUG to INFO)
- Review code for excessive logging
- Consider batching log messages for high-volume operations

### 3. Missing Context in Logs

- Ensure that log messages include relevant context
- Use the appropriate log formatter
- Consider adding more context to log messages