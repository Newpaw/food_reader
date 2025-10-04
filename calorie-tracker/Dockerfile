# Use Python 3.10 as the base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system dependencies including Nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/nginx /var/run \
    && chown -R www-data:www-data /var/log/nginx /var/run

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create uploads directory
RUN mkdir -p backend/uploads && chmod 777 backend/uploads

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose ports for the backend API and Nginx frontend server
EXPOSE 8000 8080

# Create a script to run both services
RUN echo '#!/bin/bash\n\
# Debug info\n\
echo "Starting services..."\n\
echo "Checking Nginx configuration..."\n\
nginx -t\n\
\n\
# Create necessary directories if they don't exist\n\
mkdir -p /var/log/nginx /var/run\n\
chown -R www-data:www-data /var/log/nginx /var/run\n\
\n\
# Debug frontend files\n\
echo "Checking frontend files:"\n\
ls -la /app/frontend\n\
\n\
# Start the FastAPI backend in the background\n\
echo "Starting FastAPI backend..."\n\
cd /app && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 & \n\
\n\
# Wait a moment for the backend to start\n\
sleep 2\n\
\n\
# Start Nginx in the foreground\n\
echo "Starting Nginx..."\n\
cat /etc/nginx/nginx.conf\n\
nginx -g "daemon off;"\n\
' > /app/start.sh && chmod +x /app/start.sh

# Set the entrypoint
ENTRYPOINT ["/app/start.sh"]