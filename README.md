# Calorie Tracker Application

A simple yet powerful nutrition tracking application with AI-powered food image analysis. This application allows users to track their meals by simply uploading photos, and the system automatically analyzes the food to determine nutritional information including calories, macronutrients, and more.

## Features

- **AI-Powered Food Analysis**: Upload food photos and get automatic analysis using OpenAI's Vision API  
- **Text-Based Meal Tracking**: Add meals by text description without requiring photos
- **Comprehensive Nutritional Tracking**: Track calories, protein, fat, carbohydrates, fiber, sugar, and sodium  
- **User Authentication**: Email and password-based registration and login with JWT tokens  
- **Meal Tracking**: Upload meal photos with automatic or manual metadata (nutritional info, meal type, time, notes)  
- **Image Storage**: Photos are stored on disk with proper organization  
- **Calorie Summaries**: View daily calorie totals and meal counts  
- **Responsive UI**: Simple and clean interface for tracking meals  
- **Timezone Support**: All dates and times are displayed in the user's local timezone  
- **Docker Support**: Easy deployment with Docker and docker-compose  
- **Nginx Web Server**: Static content served efficiently through Nginx  
- **Comprehensive Logging System**: Detailed application logging with multiple log levels, file rotation, and request tracking

## Project Structure

```
calorie-tracker/
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # FastAPI application setup
│  │  ├─ settings.py          # Configuration settings
│  │  ├─ database.py          # Database connection
│  │  ├─ models.py            # SQLAlchemy models
│  │  ├─ schemas.py           # Pydantic schemas
│  │  ├─ auth.py              # Authentication utilities
│  │  ├─ crud.py              # Database operations
│  │  ├─ deps.py              # Dependency injection
│  │  ├─ ai_analyzer.py       # OpenAI Vision API integration
│  │  ├─ logger.py            # Logging system implementation
│  │  └─ routers/             # API endpoints
│  ├─ logs/                   # Application logs directory
│  │  ├─ app.log              # Main application logs
│  │  ├─ error.log            # Error-level logs only
│  │  └─ access.log           # API request/response logs
│  └─ uploads/                # Generated at runtime
├─ frontend/
│  ├─ index.html              # Main application page
│  ├─ login.html              # Login page
│  ├─ history.html            # Meal history page
│  ├─ metrics.html            # Nutrition metrics page
│  ├─ common.js               # Shared JavaScript utilities
│  ├─ charts.js               # Chart visualization code
│  ├─ app.js                  # Frontend JavaScript
│  ├─ imageOptimizer.js       # Image optimization utilities
│  └─ styles.css              # CSS styles
├─ nginx.conf                 # Nginx configuration
├─ Dockerfile                 # Docker build instructions
├─ docker-compose.yml         # Docker Compose (production)
├─ docker-compose.local.yml   # Docker Compose (local dev)
├─ Makefile                   # Shortcuts for local dev
├─ Makefile.local             # Additional local dev shortcuts
├─ .env.example               # Example environment variables
└─ requirements.txt           # Python dependencies
```

## Installation

### Prerequisites
- Python 3.8+
- Docker and Docker Compose (optional)
- Make (optional, for using Makefile)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/calorie-tracker.git
cd calorie-tracker
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key and other settings
```

## Running the Application

### Option 1: Docker Compose (Recommended)

Production mode:
```bash
docker compose up -d
```

Development mode:
```bash
make up    # Starts the application
make down  # Stops the application
make logs  # Views backend logs
```

Access the application at: http://localhost:18080

### Option 2: Manual Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Start the backend:
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

3. Serve the frontend:
- Using Python: `python -m http.server 8080`
- Or configure with Nginx

### Option 3: Running with Docker (Without Compose)

```bash
docker build -t calorie-tracker .
docker run -d \
  -p 18080:8080 \
  -p 18000:8000 \
  -e OPENAI_API_KEY=your_openai_api_key_here \
  -e JWT_SECRET_KEY=your_jwt_secret_key_here \
  -v $(pwd)/backend/uploads:/app/backend/uploads \
  --name calorie-tracker \
  calorie-tracker
```

## Getting Started

1. Register a new user account
2. Login with your credentials
3. Upload a food image or add a meal by text description
4. Review the AI-generated nutritional info
5. Save meal → view in history & metrics

## API Endpoints

### Authentication
- `POST /auth/register` – Register a new user
- `POST /auth/login` – Login and get JWT

### User Management
- `GET /users/me` – Get user profile

### Meal Management
- `POST /me/meals` – Create meal with image upload
- `POST /me/meals/text` – Create meal from text description
- `GET /me/meals` – List meals with optional date filtering
- `GET /me/summary` – Get nutrition summary by date range
- `PUT /me/meals/{meal_id}` – Update meal details
- `DELETE /me/meals/{meal_id}` – Delete meal
- `POST /me/meals/{meal_id}/reanalyze` – Reanalyze a meal with corrections

## Logging System

The application includes a comprehensive logging system with the following features:

- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, and CRITICAL for different severity of messages
- **Console and File Handlers**: Logs are output to both the terminal and persistent files
- **Contextual Information**: Log messages include timestamps, module names, and line numbers
- **Log Rotation**: Automatic rotation of log files to manage file sizes
- **Thread-Safe Implementation**: Reliable logging in concurrent environments
- **Exception Logging**: Detailed error information with tracebacks
- **Function Timing**: Performance monitoring with execution time logging
- **Request Logging**: HTTP request/response tracking with FastAPI middleware

### Log Files

The logging system creates three main log files:

1. **app.log** - Contains all log messages (DEBUG and above)
2. **error.log** - Contains only error messages (ERROR and CRITICAL)
3. **access.log** - Contains API request/response logs

These files are located in the `backend/logs/` directory.

### Configuration

Logging is configured through environment variables and the `settings.py` file:

```python
# Logging configuration
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")  # Default log level
LOG_DIR: str = os.getenv("LOG_DIR", "logs")      # Directory for log files
LOG_FILE_MAX_SIZE: int = 10 * 1024 * 1024        # 10 MB max file size
LOG_FILE_BACKUP_COUNT: int = 5                   # Keep 5 backup files
LOG_ACCESS_TO_CONSOLE: bool = False              # Don't log access to console
```

## Development

### Using the Makefile

```bash
make up         # Start application
make down       # Stop application
make rebuild    # Rebuild containers
make logs       # View backend logs
make reset-db   # Reset database (⚠️ Deletes all data)
```

Requires `make`. On Ubuntu/Debian:
```bash
sudo apt update && sudo apt install make -y
```

## Technologies Used

* **Backend**: FastAPI, SQLAlchemy, Pydantic, JWT, SQLite, OpenAI API
* **Frontend**: HTML, JavaScript, Chart.js
* **Infrastructure**: Nginx, Docker, Docker Compose

## Troubleshooting

* **Backend API not accessible** → check containers (`docker compose ps`), ports, logs.
* **Image upload fails** → check permissions on `backend/uploads`.
* **OpenAI API errors** → verify API key & quota.
* **Logs not appearing** → check if the `logs` directory exists and is writable.

View logs:
```bash
docker compose logs -f app
```

## Security Considerations

For production:

* Change JWT secret in `.env`
* Use HTTPS
* Add rate limiting
* Limit upload size
* Move to PostgreSQL/MySQL for scale

## License

MIT License – see LICENSE file for details.

## Makefile

For convenience, here is the full `Makefile`:

```makefile
# Makefile for Calorie Tracker (local environment)

COMPOSE = docker compose -f docker-compose.local.yml

# Start the application (with build)
up:
	mkdir -p ../db_folder
	$(COMPOSE) up -d --build

# Stop the application
down:
	$(COMPOSE) down

# Rebuild without cache
rebuild:
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

# View logs from the backend container
logs:
	$(COMPOSE) logs -f app

# ⚠️ WARNING: This will delete your database and all data!
reset-db:
	rm -f ../db_folder/app.db
	mkdir -p ../db_folder
	$(COMPOSE) up -d --build
