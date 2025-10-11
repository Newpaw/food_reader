# Calorie Tracker Logging System Guide

## Table of Contents
- [Overview](#overview)
- [How to Import and Use the Logger](#how-to-import-and-use-the-logger)
- [Examples of Logging at Different Levels](#examples-of-logging-at-different-levels)
- [Exception Logging](#exception-logging)
- [Function Timing Decorator](#function-timing-decorator)
- [Request Logging Middleware](#request-logging-middleware)
- [Viewing and Analyzing Logs](#viewing-and-analyzing-logs)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The Calorie Tracker application includes a comprehensive logging system designed to provide visibility into application behavior, performance, and errors. The logging system is built on Python's standard `logging` module with additional features tailored for our application.

Key features of the logging system include:

- **Multiple log levels** (DEBUG, INFO, WARNING, ERROR, CRITICAL) for different severity of messages
- **Console and file handlers** to output logs to both the terminal and persistent files
- **Contextual information** in log messages including timestamps, module names, and line numbers
- **Log rotation** to manage file sizes and maintain historical logs
- **Thread-safe implementation** for reliable logging in concurrent environments
- **Exception logging utilities** to capture detailed error information
- **Function timing decorator** to measure and log execution times
- **Request logging middleware** for FastAPI to track HTTP requests and responses

The logging system is configured through environment variables and the `settings.py` file, making it adaptable to different deployment environments.

## How to Import and Use the Logger

### Basic Logger Setup

To use the logger in your module, import the `get_logger` function and create a logger instance:

```python
from app.logger import get_logger

# Create a logger with your module name
logger = get_logger(__name__)

# Now you can use the logger
logger.info("Module initialized")
```

The `get_logger` function configures the logger with appropriate handlers and formatters based on the application settings. It's recommended to create one logger per module, typically at the module level.

### Logger Configuration

The logging system is configured through the following settings in `settings.py`:

```python
# Logging configuration
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")  # Default log level
LOG_DIR: str = os.getenv("LOG_DIR", "logs")      # Directory for log files
LOG_FILE_MAX_SIZE: int = 10 * 1024 * 1024        # 10 MB max file size
LOG_FILE_BACKUP_COUNT: int = 5                   # Keep 5 backup files
LOG_ACCESS_TO_CONSOLE: bool = False              # Don't log access to console
```

These settings can be overridden through environment variables, allowing for different configurations in development, testing, and production environments.

## Examples of Logging at Different Levels

The logging system supports five standard log levels, each appropriate for different types of messages:

### DEBUG Level

Use for detailed information, typically useful only for diagnosing problems:

```python
logger.debug("Database connection established with parameters: %s", connection_params)
logger.debug(f"Processing item {item_id} with attributes: {attributes}")
```

### INFO Level

Use for confirmation that things are working as expected:

```python
logger.info("Application started successfully")
logger.info(f"User {user.id} logged in")
logger.info(f"Processing request for user_id={user.id}, frm={frm}, to={to}")
```

### WARNING Level

Use for indicating something unexpected happened, or may happen in the near future (e.g. "disk space low"):

```python
logger.warning("API rate limit approaching threshold: %d/%d", current_rate, max_rate)
logger.warning(f"Found {len(deleted_check)} meals that might be deleted but still in DB")
```

### ERROR Level

Use for errors that don't prevent the application from running but need to be investigated:

```python
logger.error("Failed to connect to database: %s", str(e))
logger.error(f"Date parsing error: {str(e)}")
```

### CRITICAL Level

Use for critical errors that may prevent the application from continuing to run:

```python
logger.critical("Unable to access configuration file, shutting down")
logger.critical(f"Fatal error in data processing pipeline: {str(e)}")
```

## Exception Logging

The logging system includes a utility function for logging exceptions with full traceback information:

```python
from app.logger import get_logger, log_exception

logger = get_logger(__name__)

try:
    # Some code that might raise an exception
    result = process_data(data)
except Exception as e:
    # Log the exception with a custom message
    log_exception(logger, e, "Error processing data")
    
    # You can still handle the exception as needed
    raise HTTPException(status_code=500, detail="Internal server error")
```

The `log_exception` function logs the exception message at ERROR level and the full traceback at DEBUG level. This approach ensures that error messages are always visible in the logs, while detailed traceback information is available for debugging but doesn't clutter the logs at higher log levels.

Example from the application:

```python
try:
    # Use AI to analyze the image
    (ai_calories, ai_protein, ai_fat, ai_carbs, ai_fiber,
     ai_sugar, ai_sodium, ai_meal_type, ai_consumed_at, ai_notes) = get_meal_data_from_image(path)
    
    # Use AI-generated data
    # ...
except Exception as e:
    # Log the exception
    log_exception(logger, e, "AI analysis failed for meal image")
    # Continue with default values if AI analysis fails
    # ...
```

## Function Timing Decorator

The logging system includes a decorator for measuring and logging the execution time of functions:

```python
from app.logger import get_logger, log_execution_time
import logging

logger = get_logger(__name__)

# Basic usage with default settings (DEBUG level)
@log_execution_time()
def process_data(data):
    # Function implementation
    return result

# Specify a different log level
@log_execution_time(level=logging.INFO)
def generate_report(report_id):
    # Function implementation
    return report

# Specify a custom logger
custom_logger = get_logger("performance")
@log_execution_time(logger=custom_logger, level=logging.INFO)
def complex_calculation(parameters):
    # Function implementation
    return result
```

The decorator logs the following information:
1. When the function starts executing
2. When the function completes, including the execution time in milliseconds
3. If the function raises an exception, it logs the failure with the execution time

Example from the application:

```python
@router.get("/meals", response_model=List[schemas.MealOut])
@log_execution_time(level=logging.INFO)
def list_meals(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    frm: str | None = None,
    to: str | None = None,
    limit: int = 50,
    offset: int = 0
):
    # Function implementation
```

This will produce log entries like:
```
2025-10-11 22:12:35,806 - INFO - Executing list_meals
2025-10-11 22:12:35,920 - INFO - Completed list_meals in 114.23ms
```

## Request Logging Middleware

The logging system includes middleware for logging HTTP requests and responses in FastAPI applications:

```python
# In main.py
from fastapi import FastAPI
from app.logger import RequestLoggingMiddleware

app = FastAPI()

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)
```

The middleware logs the following information for each request:
- Request start time
- HTTP method (GET, POST, etc.)
- Request path
- Response status code
- Request duration in milliseconds
- A unique request ID for correlating related log entries

The middleware uses a dedicated access logger that writes to a separate log file (`access.log`). This separation allows for easier analysis of API usage patterns without cluttering the main application logs.

Example log entry:
```
2025-10-11 22:12:35,806 - INFO - Request completed - request_id=1697061155-a1b2c3d4 - method=GET - path=/me/meals - status=200 - duration=114.23ms
```

## Viewing and Analyzing Logs

### Log File Structure

The logging system creates three main log files:

1. **app.log** - Contains all log messages (DEBUG and above)
2. **error.log** - Contains only error messages (ERROR and CRITICAL)
3. **access.log** - Contains API request/response logs

These files are located in the directory specified by the `LOG_DIR` setting (default: `logs/`).

### Log Rotation

To prevent log files from growing indefinitely, the logging system implements log rotation with the following settings:

- Maximum file size: 10 MB (configurable via `LOG_FILE_MAX_SIZE`)
- Backup count: 5 files (configurable via `LOG_FILE_BACKUP_COUNT`)

When a log file reaches the maximum size, it is renamed with a suffix (e.g., `app.log.1`) and a new log file is created. The oldest backup is deleted when the number of backup files exceeds the backup count.

### Analyzing Logs

Here are some common techniques for analyzing the log files:

#### Basic Log Viewing

```bash
# View the most recent log entries
tail -f logs/app.log

# View error logs
cat logs/error.log

# Search for specific terms
grep "user_id=123" logs/app.log
```

#### Advanced Analysis

For more advanced analysis, you can use tools like `awk`, `sed`, or dedicated log analysis tools:

```bash
# Count occurrences of each log level
cat logs/app.log | grep -oE ' - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - ' | sort | uniq -c

# Calculate average request duration
cat logs/access.log | grep -oE 'duration=[0-9]+\.[0-9]+ms' | cut -d= -f2 | cut -d. -f1 | awk '{ sum += $1; count++ } END { print sum/count }'

# Find slow requests (>500ms)
grep -E 'duration=[5-9][0-9][0-9]\.[0-9]+ms|duration=[0-9]{4,}\.[0-9]+ms' logs/access.log
```

## Best Practices

### When to Use Each Log Level

- **DEBUG**: Use for detailed information that is useful during development and debugging
  - Database queries and parameters
  - Function entry/exit with detailed parameters
  - Intermediate calculation results
  - Detailed flow control information

- **INFO**: Use for tracking the general flow of the application
  - Application startup/shutdown
  - Configuration settings at startup
  - User authentication events
  - Major state changes
  - Periodic status updates for long-running processes

- **WARNING**: Use for potentially problematic situations that don't cause errors
  - Deprecated feature usage
  - Resource usage approaching limits
  - Missing optional configuration
  - Automatic recovery from unexpected conditions
  - Potential security issues

- **ERROR**: Use for error conditions that affect specific operations but not the whole application
  - Failed API requests
  - Database connection failures
  - File I/O errors
  - Authentication failures
  - Data validation errors

- **CRITICAL**: Use for severe error conditions that might cause the application to terminate
  - Unrecoverable database corruption
  - Critical security breaches
  - Complete exhaustion of a required resource
  - Application deadlock situations

### Effective Logging Practices

1. **Be consistent with log levels** - Use the same log level for similar types of events across the application

2. **Include contextual information** - Log messages should include relevant context:
   ```python
   # Good
   logger.info(f"User {user.id} updated profile with fields: {', '.join(updated_fields)}")
   
   # Not as useful
   logger.info("Profile updated")
   ```

3. **Use structured logging for machine parsing** - When possible, include key-value pairs in a consistent format:
   ```python
   logger.info(f"Request processed - user_id={user.id} - action={action} - duration={duration}ms")
   ```

4. **Log at the appropriate level** - Don't log routine operations at ERROR level, and don't log errors at INFO level

5. **Use exception logging for all caught exceptions** - Always log exceptions with the `log_exception` utility

6. **Use timing decorators for performance-sensitive functions** - Monitor execution times to identify bottlenecks

7. **Don't log sensitive information** - Avoid logging passwords, tokens, or personal information

8. **Use lazy evaluation for expensive operations** - Use callables or f-strings only when the log will actually be emitted:
   ```python
   # Good - only evaluated if DEBUG is enabled
   logger.debug("Complex result: %s", calculate_complex_result())
   
   # Also good with f-strings
   logger.debug(f"Complex result: {calculate_complex_result()}")
   
   # Bad - always evaluated even if DEBUG is disabled
   logger.debug("Complex result: " + str(calculate_complex_result()))
   ```

## Troubleshooting

### Common Issues and Solutions

#### Logs Not Appearing in Files

**Issue**: Log messages are not being written to log files.

**Solutions**:
- Check if the `LOG_DIR` directory exists and is writable
- Verify that the log level in settings is not higher than the level you're logging at
- Check for permission issues on the log directory

```python
import os
from app.logger import LOGS_DIR

# Ensure logs directory exists and is writable
os.makedirs(LOGS_DIR, exist_ok=True)
assert os.access(LOGS_DIR, os.W_OK), f"Log directory {LOGS_DIR} is not writable"
```

#### Too Many or Too Few Log Messages

**Issue**: Log files contain too much or too little information.

**Solutions**:
- Adjust the `LOG_LEVEL` setting in `settings.py` or via environment variables
- For development: `LOG_LEVEL=DEBUG`
- For production: `LOG_LEVEL=INFO` or `LOG_LEVEL=WARNING`

```bash
# Set log level via environment variable
export LOG_LEVEL=DEBUG
python -m app.main
```

#### Log Files Growing Too Large

**Issue**: Log files are consuming too much disk space.

**Solutions**:
- Decrease the `LOG_FILE_MAX_SIZE` setting
- Decrease the `LOG_FILE_BACKUP_COUNT` setting
- Implement external log rotation using system tools like `logrotate`
- Consider sending logs to a centralized logging system

#### Missing Context in Log Messages

**Issue**: Log messages don't contain enough information to diagnose problems.

**Solutions**:
- Add more contextual information to log messages
- Use the verbose formatter for console logs:
  ```python
  from app.logger import VERBOSE_FORMATTER
  console_handler.setFormatter(VERBOSE_FORMATTER)
  ```
- Consider creating a custom formatter with additional fields

#### Performance Impact of Logging

**Issue**: Excessive logging is impacting application performance.

**Solutions**:
- Use appropriate log levels and only log what's necessary
- Use lazy evaluation for expensive logging operations
- Consider asynchronous logging for high-throughput applications
- Profile the application to identify logging bottlenecks

### Getting Help

If you encounter issues with the logging system that aren't covered in this guide, please:

1. Check the existing log files for error messages related to the logging system
2. Review the logger implementation in `app/logger.py`
3. Consult the Python logging documentation: https://docs.python.org/3/library/logging.html
4. Contact the development team for assistance