# Use Python 3.12 to match the locked project requirements
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Install system dependencies including Nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/nginx /var/run \
    && chown -R www-data:www-data /var/log/nginx /var/run

# Copy the uv project metadata first for better layer caching
COPY pyproject.toml uv.lock README.md ./

# Install the locked runtime dependencies
RUN uv sync --frozen --no-install-project

# Copy the application code
COPY calorie-tracker ./calorie-tracker

# Create uploads directory
RUN mkdir -p /app/calorie-tracker/backend/uploads \
    && chmod 777 /app/calorie-tracker/backend/uploads \
    && chmod +x /app/calorie-tracker/start.sh

# Copy Nginx configuration
RUN cp /app/calorie-tracker/nginx.conf /etc/nginx/nginx.conf

# Expose ports for the backend API and Nginx frontend server
EXPOSE 8000 8080

# Set the entrypoint
ENTRYPOINT ["/app/calorie-tracker/start.sh"]
