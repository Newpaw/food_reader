# Calorie Tracker Application

A simple yet powerful nutrition tracking application with AI-powered food image analysis. This application allows users to track their meals by simply uploading photos, and the system automatically analyzes the food to determine nutritional information including calories, macronutrients, and more.

## Features

- **AI-Powered Food Analysis**: Upload food photos and get automatic analysis using OpenAI's Vision API  
- **Comprehensive Nutritional Tracking**: Track calories, protein, fat, carbohydrates, fiber, sugar, and sodium  
- **User Authentication**: Email and password-based registration and login with JWT tokens  
- **Meal Tracking**: Upload meal photos with automatic or manual metadata (nutritional info, meal type, time, notes)  
- **Image Storage**: Photos are stored on disk with proper organization  
- **Calorie Summaries**: View daily calorie totals and meal counts  
- **Responsive UI**: Simple and clean interface for tracking meals  
- **Timezone Support**: All dates and times are displayed in the user's local timezone  
- **Docker Support**: Easy deployment with Docker and docker-compose  
- **Nginx Web Server**: Static content served efficiently through Nginx  

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
│  │  ├─ crud.py             # Database operations
│  │  ├─ deps.py             # Dependency injection
│  │  ├─ ai_analyzer.py      # OpenAI Vision API integration
│  │  └─ routers/            # API endpoints
│  ├─ uploads/               # Generated at runtime
│  └─ static/                # Optional static files
├─ frontend/
│  ├─ index.html             # Main application page
│  ├─ login.html             # Login page
│  ├─ history.html           # Meal history page
│  ├─ metrics.html           # Nutrition metrics page
│  ├─ common.js              # Shared JavaScript utilities
│  ├─ charts.js             # Chart visualization code
│  ├─ app.js                # Frontend JavaScript
│  └─ styles.css            # CSS styles
├─ nginx.conf               # Nginx configuration
├─ Dockerfile              # Docker build instructions
├─ docker-compose.yml      # Docker Compose (production)
├─ docker-compose.local.yml # Docker Compose (local dev)
├─ Makefile               # Shortcuts for local dev
├─ .env.example           # Example environment variables
└─ requirements.txt       # Python dependencies
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

## API Endpoints

- `POST /auth/register` - Create new user account
- `POST /auth/login` - Obtain JWT token
- `GET /users/me` - Get current user profile
- `POST /me/meals` - Create new meal entry
- `GET /me/meals` - List user's meals
- `GET /me/summary` - Get nutrition summary
- `PUT /me/meals/{meal_id}` - Update meal
- `DELETE /me/meals/{meal_id}` - Delete meal

## Development

### Using the Makefile

```bash
make up         # Start application
make down       # Stop application
make rebuild    # Rebuild containers
make logs       # View backend logs
make reset-db   # Reset database (⚠️ Deletes all data)
```

## Security Notes

For production deployment:
- Generate a strong JWT secret key
- Enable HTTPS
- Configure rate limiting
- Set appropriate file upload limits
- Consider using PostgreSQL instead of SQLite

## License

MIT License - See LICENSE file for details
  make rebuild


> **Reset the database (⚠️ deletes all data):**

  ```bash
  make reset-db
  ```

> Requires `make`. On Ubuntu/Debian:
>
> ```bash
> sudo apt update && sudo apt install make -y
> ```

---

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

---

## Getting Started

1. Register a new user account
2. Login with your credentials
3. Upload a food image
4. Review the AI-generated nutritional info
5. Save meal → view in history & metrics

---

## API Endpoints

* `POST /auth/register` – Register a new user
* `POST /auth/login` – Login and get JWT
* `GET /users/me` – Get user profile
* `POST /me/meals` – Create meal (with image + nutrition info)
* `GET /me/meals` – List meals
* `GET /me/summary` – Calorie summary
* `PUT /me/meals/{meal_id}` – Update meal
* `DELETE /me/meals/{meal_id}` – Delete meal

---

## Technologies Used

* **Backend**: FastAPI, SQLAlchemy, Pydantic, JWT, SQLite, OpenAI API
* **Frontend**: HTML, JavaScript, Chart.js
* **Infrastructure**: Nginx, Docker, Docker Compose

---

## Troubleshooting

* **Backend API not accessible** → check containers (`docker compose ps`), ports, logs.
* **Image upload fails** → check permissions on `backend/uploads`.
* **OpenAI API errors** → verify API key & quota.

Logs:

```bash
docker compose logs -f app
```

---

## Security Considerations

For production:

* Change JWT secret in `.env`
* Use HTTPS
* Add rate limiting
* Limit upload size
* Move to PostgreSQL/MySQL for scale

---

## License

MIT License – see LICENSE file for details.

---

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
```
