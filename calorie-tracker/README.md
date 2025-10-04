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
│  │  ├─ crud.py              # Database operations
│  │  ├─ deps.py              # Dependency injection
│  │  ├─ ai_analyzer.py       # OpenAI Vision API integration
│  │  └─ routers/             # API endpoints
│  │     ├─ auth_router.py    # Authentication routes
│  │     ├─ meals_router.py   # Meal management routes
│  │     └─ users_router.py   # User profile routes
│  ├─ uploads/                # Generated at runtime
│  └─ static/                 # Optional static files
├─ frontend/
│  ├─ index.html              # Main application page
│  ├─ login.html              # Login page
│  ├─ history.html            # Meal history page
│  ├─ metrics.html            # Nutrition metrics page
│  ├─ common.js               # Shared JavaScript utilities
│  ├─ charts.js               # Chart visualization code
│  ├─ app.js                  # Frontend JavaScript
│  └─ styles.css              # CSS styles
├─ nginx.conf                 # Nginx configuration
├─ Dockerfile                 # Docker build instructions
├─ docker-compose.yml         # Docker Compose configuration
├─ .env.example               # Example environment variables
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

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env file to add your OpenAI API key and other settings
   ```

## Running the Application

### Option 1: Running Locally (Without Docker)

#### Backend Setup

1. Set up environment variables:
   ```bash
   export OPENAI_API_KEY=your_openai_api_key_here
   export JWT_SECRET_KEY=your_jwt_secret_key_here
   ```

2. Start the backend server:
   ```bash
   cd calorie-tracker
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

#### Frontend Setup

##### Option A: Using Nginx (Recommended)

1. Install Nginx:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install nginx

   # CentOS/RHEL
   sudo yum install nginx

   # macOS
   brew install nginx
   ```

2. Configure Nginx:
   ```bash
   # Copy the nginx.conf file to your Nginx configuration directory
   sudo cp nginx.conf /etc/nginx/conf.d/calorie-tracker.conf
   
   # Edit the configuration file to update paths if needed
   sudo nano /etc/nginx/conf.d/calorie-tracker.conf
   
   # Restart Nginx
   sudo systemctl restart nginx  # Linux
   sudo brew services restart nginx  # macOS
   ```

3. Access the application:
   - Open http://localhost:8080/frontend/login.html in your browser

##### Option B: Using Python's HTTP Server

1. Serve the frontend files:
   ```bash
   cd calorie-tracker
   python -m http.server 8080
   ```

2. Access the application:
   - Open http://localhost:8080/frontend/login.html in your browser

### Option 2: Running with Docker Compose

1. Make sure Docker and Docker Compose are installed on your system.

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env file to add your OpenAI API key and other settings
   ```

3. Build and start the Docker containers:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - Open http://localhost:8080/frontend/login.html in your browser

5. To stop the containers:
   ```bash
   docker-compose down
   ```

### Option 3: Running with Docker (Without Compose)

1. Build the Docker image:
   ```bash
   docker build -t calorie-tracker .
   ```

2. Run the container:
   ```bash
   docker run -d \
     -p 8080:80 \
     -p 8000:8000 \
     -e OPENAI_API_KEY=your_openai_api_key_here \
     -e JWT_SECRET_KEY=your_jwt_secret_key_here \
     -v $(pwd)/backend/uploads:/app/backend/uploads \
     --name calorie-tracker \
     calorie-tracker
   ```

3. Access the application:
   - Open http://localhost:8080/frontend/login.html in your browser

4. To stop the container:
   ```bash
   docker stop calorie-tracker
   docker rm calorie-tracker
   ```

## Getting Started

1. Register a new user account
2. Login with your credentials
3. Upload a food image on the main page
4. Review the AI-generated nutritional information
5. Adjust values if needed and save
6. View your meal history and nutritional metrics

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

- `PUT /me/meals/{meal_id}` - Update a meal
  - Headers: `Authorization: Bearer <token>`
  - Body: JSON with fields to update

- `DELETE /me/meals/{meal_id}` - Delete a meal
  - Headers: `Authorization: Bearer <token>`

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
  - Chart.js - For data visualization

- **Infrastructure**:
  - Nginx - High-performance web server
  - Docker - Containerization
  - Docker Compose - Multi-container orchestration

## Troubleshooting

### Common Issues

1. **Backend API not accessible**:
   - Check if the backend server is running on port 8000
   - Verify network settings if running in Docker
   - Check for any error messages in the backend logs

2. **Frontend not loading**:
   - Ensure Nginx or the HTTP server is running correctly
   - Check browser console for JavaScript errors
   - Verify that the frontend can access the backend API

3. **Image upload failing**:
   - Check if the uploads directory exists and has proper permissions
   - Verify that the image file size is not too large
   - Check backend logs for any API errors

4. **OpenAI API errors**:
   - Verify your API key is correct and has sufficient credits
   - Check network connectivity to OpenAI services
   - Look for rate limiting or quota issues in the logs

### Logs

- **Backend logs**: When running with `uvicorn`, logs are output to the console
- **Docker logs**: Use `docker-compose logs` or `docker logs calorie-tracker`
- **Nginx logs**: Check `/var/log/nginx/error.log` and `/var/log/nginx/access.log`

## Security Considerations

For production deployment, consider:
- Changing the JWT secret key in the .env file
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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.