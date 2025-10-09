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
