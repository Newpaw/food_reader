# Use Python 3.10 as the base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create uploads directory
RUN mkdir -p backend/uploads && chmod 777 backend/uploads

# Expose ports for the backend API and frontend server
EXPOSE 8000 8080

# Create a script to run both services
RUN echo '#!/bin/bash\n\
cd /app && python -m http.server 8080 & \n\
cd /app && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000\n\
' > /app/start.sh && chmod +x /app/start.sh

# Set the entrypoint
ENTRYPOINT ["/app/start.sh"]