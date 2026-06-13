# Food Reader

Food Reader is a mobile-first nutrition tracking app with a FastAPI backend and a static frontend that can be installed as a Progressive Web App. Users can log meals from a photo or plain text, review the estimate immediately, then manage history, metrics, and profile-based targets from the same interface.

## Features

- **Mobile-First UX**: Every primary screen is designed for phone-sized layouts first, then expands for larger screens.
- **Photo And Text Capture**: Add meals from an image or a free-form description.
- **Review-First Logging**: New meals open into an editable nutrition panel so users can correct values immediately.
- **History And Metrics**: Browse grouped meal history, daily calorie summaries, and macro trends.
- **Profile-Based Targets**: Save body metrics and optional custom goals to compare intake against realistic targets.
- **Withings Scale Sync**: Connect a Withings scale, manually sync body metrics, and update profile weight-based targets from the latest measurement.
- **Progressive Web App**: Install the app from the browser, cache the shell offline, and keep it on the home screen.
- **Automated Tests**: Backend API coverage with `pytest` and frontend module coverage with `vitest`.
- **Docker And Nginx Support**: Static frontend delivery plus backend API proxying in one container setup.

## Project Structure

```
food_reader/
├─ pyproject.toml             # uv-managed Python project metadata
├─ uv.lock                    # Locked Python dependency graph
├─ calorie-tracker/
│  ├─ backend/
│  │  ├─ app/
│  │  │  ├─ main.py              # FastAPI application setup
│  │  │  ├─ settings.py          # Configuration settings
│  │  │  ├─ database.py          # Database connection
│  │  │  ├─ models.py            # SQLAlchemy models
│  │  │  ├─ schemas.py           # Pydantic schemas
│  │  │  ├─ auth.py              # Authentication utilities
│  │  │  ├─ crud.py              # Database operations
│  │  │  ├─ deps.py              # Dependency injection
│  │  │  ├─ ai_analyzer.py       # OpenAI Vision API integration
│  │  │  ├─ logger.py            # Logging system implementation
│  │  │  └─ routers/             # API endpoints
│  │  ├─ logs/                   # Application logs directory
│  │  └─ uploads/                # Generated at runtime
│  ├─ frontend/
│  │  ├─ index.html              # Add meal screen
│  │  ├─ login.html              # Sign in and registration screen
│  │  ├─ history.html            # Meal history screen
│  │  ├─ metrics.html            # Metrics dashboard
│  │  ├─ profile.html            # Profile and target settings
│  │  ├─ common.js               # Shared frontend utilities
│  │  ├─ charts.js               # Dashboard data rendering helpers
│  │  ├─ service-worker.js       # PWA service worker
│  │  ├─ manifest.webmanifest    # PWA manifest
│  │  ├─ tests/                  # Frontend unit tests
│  │  └─ styles.css              # Shared mobile-first styling
│  ├─ nginx.conf                 # Nginx configuration
│  ├─ Dockerfile                 # Docker build instructions
│  ├─ docker-compose.yml         # Docker Compose (production)
│  ├─ docker-compose.local.yml   # Docker Compose (local dev)
│  ├─ Makefile                   # Shortcuts for local dev
│  ├─ Makefile.local             # Additional local dev shortcuts
│  ├─ start.sh                   # Container entrypoint
│  └─ .env.example               # Example environment variables
```

## Installation

### Prerequisites
- `uv`
- Python 3.12
- Node.js 20+
- Docker and Docker Compose (optional)
- Make (optional, for using Makefile)

1. Clone the repository:
```bash
git clone <repository-url> food_reader
cd food_reader
```

2. Set up environment variables:
```bash
cp calorie-tracker/.env.example calorie-tracker/.env
# Edit calorie-tracker/.env with your OpenAI API key and other settings
```

For Withings scale sync, set `WITHINGS_CLIENT_ID`, `WITHINGS_CLIENT_SECRET`, `WITHINGS_REDIRECT_URI`, and `APP_FRONTEND_URL` in `calorie-tracker/.env`. The redirect URI must match the callback configured in the Withings developer application.

## Running the Application

### Option 1: Docker Compose (Recommended)

Production mode:
```bash
cd calorie-tracker
docker compose up -d
```

Development mode:
```bash
cd calorie-tracker
make up    # Starts the application
make down  # Stops the application
make logs  # Views backend logs
```

Access the application at: http://localhost:18080

### Option 2: Manual Setup

1. Install backend dependencies:
```bash
uv sync
```

2. Start the backend:
```bash
cd calorie-tracker
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

3. Serve the frontend from the `frontend/` directory:
```bash
cd calorie-tracker/frontend
python3 -m http.server 8080
```

4. Open `http://localhost:8080`.
The frontend now auto-detects this split local setup and sends API traffic to `http://localhost:8000`.
If your backend runs on another host or port, set it in the browser console with:
```js
localStorage.setItem('food-reader-api-base', 'http://YOUR-HOST:8000')
```
Then reload the page.

Auth sessions use a JWT stored in `localStorage` and now stay valid for 7 days by default, so closing the browser does not force a fresh login during that window.

### Option 3: Running with Docker (Without Compose)

```bash
docker build -f calorie-tracker/Dockerfile -t calorie-tracker .
docker run -d \
  -p 18080:8080 \
  -p 18000:8000 \
  -e OPENAI_API_KEY=your_openai_api_key_here \
  -e JWT_SECRET=your_jwt_secret_here \
  -v $(pwd)/calorie-tracker/backend/uploads:/app/calorie-tracker/backend/uploads \
  --name calorie-tracker \
  calorie-tracker
```

## PWA Install

When the browser supports installation, the app exposes an `Install` button in the header. The service worker caches the shell pages and core assets so the installed app can reopen even when the network is temporarily unavailable.

## Testing

Backend tests:
```bash
uv run pytest -q
```

Frontend tests:
```bash
cd calorie-tracker/frontend
npm install
npm test
```

Frontend end-to-end tests against a running local app:
```bash
cd calorie-tracker/frontend
E2E_EMAIL="your-email@example.com" \
E2E_PASSWORD="your-password" \
npm run test:e2e
```

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
- `GET /withings/status` – Get Withings connection status
- `POST /withings/auth-url` – Start Withings OAuth authorization
- `GET /withings/callback` – Withings OAuth callback
- `POST /withings/sync` – Manually sync Withings scale measurements
- `GET /withings/measurements` – List synced body measurements
- `DELETE /withings/disconnect` – Remove local Withings connection and synced measurements

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
* **Frontend**: HTML, CSS, vanilla JavaScript modules, Vitest
* **Infrastructure**: Nginx, Docker, Docker Compose, Progressive Web App manifest + service worker

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
* Reduce or tighten `ACCESS_TOKEN_EXPIRE_MINUTES` if you need shorter sessions
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
