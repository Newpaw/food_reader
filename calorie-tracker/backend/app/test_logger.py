"""
Test script for the Calorie Tracker logging system.

This script tests all aspects of the logging implementation:
- Basic logging at different levels
- Exception logging
- Function timing decorator
- Request logging middleware
"""

import os
import time
import logging
import asyncio
import shutil
from pathlib import Path

# Import logger module
from app.logger import (
    get_logger,
    log_exception,
    log_execution_time,
    RequestLoggingMiddleware,
    RequestContextFilter,
    get_access_logger,
    LOGS_DIR
)

# Set log level to DEBUG for testing
import logging
from app.settings import settings
settings.LOG_LEVEL = "DEBUG"

# Create a test logger
test_logger = get_logger("test_logger")
test_logger.setLevel(logging.DEBUG)

def test_log_levels():
    """Test all log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""
    print("\n=== Testing Log Levels ===")
    
    # Explicitly test DEBUG level
    test_logger.debug("This is a DEBUG message")
    test_logger.info("This is an INFO message")
    test_logger.warning("This is a WARNING message")
    test_logger.error("This is an ERROR message")
    test_logger.critical("This is a CRITICAL message")
    
    print("Log level messages written. Check log files for output.")

def test_exception_logging():
    """Test exception logging functionality"""
    print("\n=== Testing Exception Logging ===")
    
    try:
        # Deliberately cause an exception
        result = 1 / 0
    except Exception as e:
        log_exception(test_logger, e, "Division by zero error")
    
    print("Exception logged. Check log files for traceback information.")

@log_execution_time()
def slow_function():
    """A deliberately slow function to test timing decorator"""
    print("Executing slow function...")
    time.sleep(2)  # Sleep for 2 seconds
    return "Slow function completed"

def test_timing_decorator():
    """Test the function timing decorator"""
    print("\n=== Testing Function Timing Decorator ===")
    
    # Call the decorated function
    result = slow_function()
    print(f"Result: {result}")
    print("Function timing logged. Check log files for timing information.")

async def test_request_middleware():
    """Test the request logging middleware"""
    print("\n=== Testing Request Logging Middleware ===")
    
    # Create a mock application
    async def mock_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b"Hello, world!"})
    
    # Create middleware with the mock app
    middleware = RequestLoggingMiddleware(mock_app)
    
    # Create a mock scope for a GET request to /test
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test"
    }
    
    # Mock receive and send functions
    async def mock_receive():
        return {"type": "http.request"}
    
    response_messages = []
    async def mock_send(message):
        response_messages.append(message)
    
    # Call the middleware
    await middleware(scope, mock_receive, mock_send)
    
    print(f"Middleware test completed. Response status: {response_messages[0]['status']}")
    print("Request logging completed. Check access log file for details.")

def verify_log_files():
    """Verify that logs are written to the appropriate files"""
    print("\n=== Verifying Log Files ===")
    
    log_files = ["app.log", "error.log", "access.log"]
    for file in log_files:
        path = LOGS_DIR / file
        if path.exists():
            size = path.stat().st_size
            print(f"{file}: Exists, Size: {size} bytes")
        else:
            print(f"{file}: Does not exist")

def test_log_rotation():
    """Test log rotation by creating a large log file"""
    print("\n=== Testing Log Rotation ===")
    
    # Create a large log file to trigger rotation
    for i in range(1000):
        test_logger.info(f"Log rotation test message {i} with some padding to increase file size" * 10)
    
    # Check for rotated log files
    app_log_files = list(LOGS_DIR.glob("app.log*"))
    print(f"Number of app log files: {len(app_log_files)}")
    for file in app_log_files:
        print(f"- {file.name}")

async def run_tests():
    """Run all tests"""
    print("Starting logger tests...")
    
    # Ensure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Test basic logging
    test_log_levels()
    
    # Test exception logging
    test_exception_logging()
    
    # Test timing decorator
    test_timing_decorator()
    
    # Test request middleware
    await test_request_middleware()
    
    # Verify log files
    verify_log_files()
    
    # Test log rotation
    test_log_rotation()
    
    print("\nAll tests completed. Check log files for results.")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(run_tests())