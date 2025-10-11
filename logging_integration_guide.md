# Logging Integration Guide

This guide provides detailed instructions for integrating the logging system into the existing Calorie Tracker application code.

## 1. Settings Update

First, we need to update the settings module to include logging configuration parameters.

### File: `calorie-tracker/backend/app/settings.py`

```python
# Add these to the existing Settings class
class Settings(BaseSettings):
    # Existing settings...
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FILE_MAX_SIZE: int = 10 * 1024 * 1024  # 10 MB
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_ACCESS_TO_CONSOLE: bool = False  # Whether to log API access to console
```

## 2. Main Application Integration

### File: `calorie-tracker/backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import Base, engine
from .settings import settings
from .routers import auth_router, meals_router, users_router
from .logger import get_logger, RequestLoggingMiddleware
import os

# Get logger for this module
logger = get_logger(__name__)

# Log application startup
logger.info("Starting Calorie Tracker application")

# Database initialization
logger.info("Initializing database")
Base.metadata.create_all(bind=engine)
logger.info("Database initialized")

app = FastAPI(title="Calorie Tracker")

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware
logger.info("Configuring CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

# Static serving for uploaded images
logger.info(f"Configuring static file serving from {settings.UPLOAD_DIR}")
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Routers
logger.info("Registering API routers")
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(meals_router.router)
logger.info("API routers registered")

# Log application ready
logger.info("Calorie Tracker application ready")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Calorie Tracker application")
```

## 3. AI Analyzer Integration

### File: `calorie-tracker/backend/app/ai_analyzer.py`

```python
# Add at the top of the file
from .logger import get_logger, log_exception, log_execution_time

# Get logger for this module
logger = get_logger(__name__)

# Update the encode_image_to_base64 function
def encode_image_to_base64(image_path: str) -> str:
    """
    Encode an image file to base64 string
    """
    logger.debug(f"Encoding image to base64: {image_path}")
    try:
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            logger.debug(f"Successfully encoded image: {image_path}")
            return encoded
    except Exception as e:
        log_exception(logger, e, f"Failed to encode image: {image_path}")
        raise

# Update the analyze_food_image function
@log_execution_time(level=logging.INFO)
def analyze_food_image(image_path: str, corrections: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Analyze a food image using OpenAI's Vision API
    """
    logger.info(f"Analyzing food image: {image_path}")
    if corrections:
        logger.info(f"With corrections: {corrections}")
    
    # Encode the image to base64
    try:
        base64_image = encode_image_to_base64(image_path)
        
        # Prepare the base prompt for the API
        # ... existing code ...
        
        # Call the OpenAI API with the image
        logger.debug(f"Calling OpenAI API with model: {settings.LLM_MODEL}")
        response = client.chat.completions.create(
            # ... existing code ...
        )
        
        logger.debug("Successfully received response from OpenAI API")
        
        # Extract and process the response
        # ... existing code ...
        
        logger.info(f"Successfully analyzed image: {image_path}")
        return result
        
    except Exception as e:
        log_exception(logger, e, f"Error analyzing image: {image_path}")
        # Return a default response on error
        logger.warning("Returning default values due to analysis error")
        return {
            # ... existing default values ...
        }

# Similarly update the other functions
```

## 4. Router Integration Example (Meals Router)

### File: `calorie-tracker/backend/app/routers/meals_router.py`

```python
# Add at the top of the file
from ..logger import get_logger, log_exception, log_execution_time

# Get logger for this module
logger = get_logger(__name__)

# Update the parse_iso_datetime function
def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Parse ISO 8601 datetime strings
    """
    logger.debug(f"Parsing ISO datetime: {iso_string}")
    try:
        # ... existing code ...
        return datetime.fromisoformat(iso_string)
    except Exception as e:
        log_exception(logger, e, f"Failed to parse ISO datetime: {iso_string}")
        raise

# Update the create_meal endpoint
@router.post("/meals", response_model=schemas.MealOut)
async def create_meal(
    # ... existing parameters ...
):
    logger.info(f"Creating new meal for user: {user.id}")
    
    # Save file
    user_dir = os.path.join(settings.UPLOAD_DIR, str(user.id))
    os.makedirs(user_dir, exist_ok=True)
    ext = os.path.splitext(image.filename or "")[1].lower() or ".jpg"
    fname = f"{uuid.uuid4()}{ext}"
    path = os.path.join(user_dir, fname)
    
    logger.debug(f"Saving uploaded image to: {path}")
    try:
        with open(path, "wb") as f:
            f.write(await image.read())
        logger.debug(f"Image saved successfully: {path}")
    except Exception as e:
        log_exception(logger, e, f"Failed to save image: {path}")
        raise HTTPException(status_code=500, detail="Failed to save image")

    # Use AI to analyze the image if manual data is not provided
    if (calories is None or protein is None or fat is None or carbs is None or
        fiber is None or sugar is None or sodium is None or
        meal_type is None or consumed_at is None):
        logger.info("Missing nutritional data, using AI analysis")
        try:
            logger.debug(f"Starting AI analysis for image: {path}")
            (ai_calories, ai_protein, ai_fat, ai_carbs, ai_fiber,
             ai_sugar, ai_sodium, ai_meal_type, ai_consumed_at, ai_notes) = get_meal_data_from_image(path)
            
            logger.debug("AI analysis completed successfully")
            
            # Use AI-generated data if not manually provided
            # ... existing code ...
            
        except Exception as e:
            log_exception(logger, e, "AI analysis failed, using default values")
            # Continue with default values if AI analysis fails
            # ... existing code ...

    logger.debug(f"Creating meal record with calories: {calories}, protein: {protein}, etc.")
    meal = models.Meal(
        # ... existing code ...
    )
    try:
        db.add(meal); db.commit(); db.refresh(meal)
        logger.info(f"Meal created successfully with ID: {meal.id}")
    except Exception as e:
        log_exception(logger, e, "Failed to create meal record in database")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create meal record")

    return schemas.MealOut(
        # ... existing code ...
    )

# Similarly update other endpoints
```

## 5. Database Integration

### File: `calorie-tracker/backend/app/database.py`

```python
# Add at the top of the file
from .logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Log database connection
logger.info(f"Setting up database connection: {settings.DATABASE_URL}")

# Create engine
engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
logger.debug("Database engine created")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.debug("Database session factory created")

# Create base class
Base = declarative_base()
logger.debug("Declarative base created")

# Update the get_db function
def get_db():
    db = SessionLocal()
    logger.debug("Database session created")
    try:
        yield db
        logger.debug("Database session yielded")
    finally:
        logger.debug("Closing database session")
        db.close()
```

## 6. Authentication Integration

### File: `calorie-tracker/backend/app/auth.py`

```python
# Add at the top of the file
from .logger import get_logger, log_exception

# Get logger for this module
logger = get_logger(__name__)

# Update the create_access_token function
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    logger.debug(f"Creating access token for user: {data.get('sub', 'unknown')}")
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
        logger.debug(f"Access token created successfully for user: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        log_exception(logger, e, f"Failed to create access token for user: {data.get('sub', 'unknown')}")
        raise

# Update the verify_token function
def verify_token(token: str, credentials_exception):
    logger.debug("Verifying access token")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
        token_data = TokenData(username=username)
        logger.debug(f"Token verified successfully for user: {username}")
        return token_data
    except JWTError as e:
        log_exception(logger, e, "JWT verification failed")
        raise credentials_exception
```

## 7. Dependencies Integration

### File: `calorie-tracker/backend/app/deps.py`

```python
# Add at the top of the file
from .logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Update the get_current_user function
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    logger.debug("Authenticating user from token")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = verify_token(token, credentials_exception)
        user = db.query(models.User).filter(models.User.username == token_data.username).first()
        if user is None:
            logger.warning(f"User not found: {token_data.username}")
            raise credentials_exception
        logger.debug(f"User authenticated: {user.username} (ID: {user.id})")
        return user
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise
```

## 8. CRUD Operations Integration

### File: `calorie-tracker/backend/app/crud.py`

```python
# Add at the top of the file
from .logger import get_logger, log_exception

# Get logger for this module
logger = get_logger(__name__)

# Update CRUD functions with logging
def create_user(db: Session, user: schemas.UserCreate):
    logger.info(f"Creating new user: {user.username}")
    try:
        hashed_password = get_password_hash(user.password)
        db_user = models.User(username=user.username, hashed_password=hashed_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User created successfully: {user.username} (ID: {db_user.id})")
        return db_user
    except Exception as e:
        log_exception(logger, e, f"Failed to create user: {user.username}")
        db.rollback()
        raise

# Similarly update other CRUD functions
```

## 9. Best Practices for Exception Handling

When handling exceptions, follow these patterns:

```python
# Pattern 1: Log and re-raise
try:
    # Operation that might fail
    result = some_operation()
    return result
except Exception as e:
    log_exception(logger, e, "Operation failed")
    raise  # Re-raise the exception

# Pattern 2: Log and return fallback
try:
    # Operation that might fail
    result = some_operation()
    return result
except Exception as e:
    log_exception(logger, e, "Operation failed, using fallback")
    return fallback_value  # Return a default/fallback value

# Pattern 3: Log and raise HTTP exception (for API endpoints)
try:
    # Operation that might fail
    result = some_operation()
    return result
except Exception as e:
    log_exception(logger, e, "Operation failed")
    raise HTTPException(status_code=500, detail=str(e))
```

## 10. Performance Considerations

1. **Lazy Evaluation**: Use lazy evaluation for expensive operations in log messages

```python
# Instead of this:
logger.debug(f"Complex calculation result: {expensive_calculation()}")

# Do this:
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Complex calculation result: {expensive_calculation()}")
```

2. **Appropriate Log Levels**: Use appropriate log levels to control verbosity

```python
# High-volume, detailed information
logger.debug("Detailed information for debugging")

# Normal operational information
logger.info("Normal operational information")

# Warning conditions
logger.warning("Warning condition")

# Error conditions
logger.error("Error condition")

# Critical conditions
logger.critical("Critical condition")
```

3. **Batch Logging**: For high-volume logs, consider batching log messages

```python
# Instead of logging in a loop:
for item in items:
    logger.debug(f"Processing item: {item}")

# Log a summary:
logger.debug(f"Processing {len(items)} items")
logger.debug(f"First few items: {items[:5]}")
```

## 11. Thread Safety Considerations

The Python `logging` module is thread-safe by default. However, ensure:

1. Don't modify logger configurations from multiple threads simultaneously
2. Use thread-local storage for any custom logging context
3. Avoid shared mutable state in logging functions

## 12. Testing the Logging System

To test the logging system:

1. Set the log level to DEBUG temporarily
2. Trigger various application functions
3. Check the log files for appropriate entries
4. Verify that log rotation works by generating enough logs to trigger rotation
5. Test exception logging by intentionally causing errors