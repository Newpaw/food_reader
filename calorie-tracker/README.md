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
│  │  └─ routers/             # API endpoints
│  │     ├─ auth_router.py    # Authentication routes
│  │     ├─ meals_router.py   # Meal management routes
│  │     └─ users_router.py   # User profile routes
│  ├─ uploads/                # Generated at runtime
│  └─ static/                 # Optional static files
├─ frontend/
│  ├─ index.html              # Main application page
│  ├─ login.html              # Login page
│  └─ app.js                  # Frontend JavaScript
└─ requirements.txt           # Python dependencies
```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd calorie-tracker
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Option 1: Running Locally

1. Start the backend server:
   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Serve the frontend files (in a separate terminal):
   ```bash
   cd calorie-tracker
   python -m http.server 8080
   ```

3. Access the application:
   - Open http://localhost:8080/calorie-tracker/frontend/login.html in your browser
   - Register a new user
   - Login with your credentials
   - Start tracking your meals!

### Option 2: Running with Docker

1. Set your OpenAI API key in an environment variable:
   ```bash
   export OPENAI_API_KEY=your_openai_api_key_here
   ```

2. Build and start the Docker containers:
   ```bash
   docker-compose up -d
   ```

3. Access the application:
   - Open http://localhost:8080/frontend/login.html in your browser
   - Register a new user
   - Login with your credentials
   - Start tracking your meals!

4. To stop the containers:
   ```bash
   docker-compose down
   ```

## API Endpoints

### Authentication

- `POST /auth/register` - Register a new user
  - Body: `{ "email": "user@example.com", "name": "User Name", "password": "password" }`

- `POST /auth/login` - Login and get access token
  - Body: `{ "email": "user@example.com", "password": "password", "name": "n/a" }`

### User

- `GET /users/me` - Get current user profile
  - Headers: `Authorization: Bearer <token>`

### Meals

- `POST /me/meals` - Create a new meal entry
  - Headers: `Authorization: Bearer <token>`
  - Body: `multipart/form-data` with fields:
    - `image`: File upload
    - `calories`: Integer
    - `protein`: Integer (grams)
    - `fat`: Integer (grams)
    - `carbs`: Integer (grams)
    - `fiber`: Integer (grams)
    - `sugar`: Integer (grams)
    - `sodium`: Integer (milligrams)
    - `meal_type`: String (breakfast|lunch|dinner|snack)
    - `consumed_at`: ISO datetime
    - `notes`: Optional string

- `GET /me/meals` - List user's meals
  - Headers: `Authorization: Bearer <token>`
  - Query parameters:
    - `frm`: Optional start date
    - `to`: Optional end date
    - `limit`: Optional limit (default: 50)
    - `offset`: Optional offset (default: 0)

- `GET /me/summary` - Get calorie summary
  - Headers: `Authorization: Bearer <token>`
  - Query parameters:
    - `frm`: Start date
    - `to`: End date

## Technologies Used

- **Backend**:
  - FastAPI - Modern, fast web framework
  - SQLAlchemy - SQL toolkit and ORM
  - Pydantic - Data validation and settings management
  - JWT - Token-based authentication
  - SQLite - Database (easily upgradable to PostgreSQL)
  - OpenAI API - For AI-powered food image analysis

- **Frontend**:
  - Pure HTML/JavaScript - No build tools required
  - Fetch API - For API communication

## Future Improvements

- Add refresh token functionality for better security
- Implement image compression and thumbnail generation
- Add user profile management
- Create more detailed statistics and visualizations
- Implement meal categories and tags
- Add export functionality for data
- Enhance UI with CSS frameworks
- Improve AI analysis accuracy with fine-tuning
- Add nutritional information beyond just calories
- Implement multi-user support with different roles
- Add support for different measurement units

## Security Considerations

For production deployment, consider:
- Changing the JWT secret key in the docker-compose.yml file
- Securing the OpenAI API key using environment variables
- Adding file upload size limits
- Implementing MIME type validation
- Setting up proper CORS configuration
- Moving to a more robust database like PostgreSQL
- Adding rate limiting
- Using HTTPS for all communications
- Implementing proper backup strategies for the database and uploaded images

## AI Food Analysis

The application uses OpenAI's Vision API to analyze food images and extract the following information:
- Food type and description
- Comprehensive nutritional information:
  - Calories (kcal)
  - Protein (g)
  - Fat (g)
  - Carbohydrates (g)
  - Fiber (g)
  - Sugar (g)
  - Sodium (mg)
- Suggested meal type (breakfast, lunch, dinner, or snack)
- Additional nutritional insights

Users can still manually override any AI-detected values if needed. The AI analysis happens on the server-side when the image is uploaded, so no additional API calls are needed from the frontend.

## Timezone Handling

The application handles timezones in the following way:
- All dates and times are stored in UTC format in the database
- The frontend automatically converts UTC times to the user's local timezone for display
- When filtering by date ranges, the application properly converts local dates to UTC for API requests
- Date/time pickers in forms show times in the user's local timezone
- All charts and visualizations display dates in the user's local timezone

This ensures a consistent user experience regardless of the user's location or the server's timezone.

## Docker Configuration

The application includes Docker support for easy deployment:
- `Dockerfile`: Defines the container image with both frontend and backend components
- `docker-compose.yml`: Orchestrates the container and sets up the necessary environment variables

The Docker setup includes:
- Volume mapping for persistent storage of uploaded images
- Environment variable configuration for sensitive data
- Proper port mapping for both the backend API and frontend server
- Automatic restart policy for improved reliability

To customize the Docker configuration, edit the `docker-compose.yml` file to change environment variables, ports, or add additional services like a separate database container.