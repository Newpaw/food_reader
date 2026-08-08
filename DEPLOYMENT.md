# Food Reader deployment

Production is image-based. The VM does not build the application and does not need source-code updates after the initial deployment setup.

## Release flow

```text
push / merge to master
        |
        v
GitHub Actions
  - backend tests
  - Docker build
  - push to GHCR
        |
        v
ghcr.io/newpaw/food_reader:latest
        |
        v
Watchtower on VM every 5 minutes
  - compare image digest
  - pull only when changed
  - recreate Food Reader container
  - keep .env + SQLite + uploads on VM
```

Every release also gets an immutable `sha-<commit>` tag for rollback.

## Production network

The existing VM deployment uses the external Docker network `cloudflare`. Production compose is intentionally pinned to this network so the bundled frontend Nginx remains reachable from the existing reverse-proxy stack.

Verify it before deployment:

```bash
docker network inspect cloudflare >/dev/null && echo "cloudflare network OK"
```

If this command fails, do not create an arbitrary replacement network. Verify the reverse-proxy deployment first.

## GitHub release

Workflow: `.github/workflows/release-container.yml`

Every push to `master` publishes:

```text
ghcr.io/newpaw/food_reader:latest
ghcr.io/newpaw/food_reader:sha-<commit>
```

GitHub Actions uses the repository `GITHUB_TOKEN` for publishing.

## One-time migration on the VM

The previous compose used container name `calorie-tracker`, mounted SQLite into `/app/data`, uploads into `/app/calorie-tracker/backend/uploads`, ports `18000/18080`, and the external `cloudflare` network. The new deployment keeps the same host ports and network but moves persistent files into `/opt/food-reader/data`.

### 1. Inspect current persistent paths

Run this while the old container still exists:

```bash
OLD_DB_DIR=$(docker inspect calorie-tracker --format '{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Source}}{{end}}{{end}}')
OLD_UPLOAD_DIR=$(docker inspect calorie-tracker --format '{{range .Mounts}}{{if eq .Destination "/app/calorie-tracker/backend/uploads"}}{{.Source}}{{end}}{{end}}')

echo "DB:      $OLD_DB_DIR"
echo "Uploads: $OLD_UPLOAD_DIR"
```

Do not continue if either path is empty.

### 2. Create the new runtime directory

```bash
sudo mkdir -p /opt/food-reader/data/db /opt/food-reader/data/uploads
sudo chown -R "$USER":"$USER" /opt/food-reader
```

### 3. Copy current persistent data

Create a backup first:

```bash
mkdir -p "$HOME/food-reader-backup"
cp -a "$OLD_DB_DIR/." "$HOME/food-reader-backup/db/"
cp -a "$OLD_UPLOAD_DIR/." "$HOME/food-reader-backup/uploads/"
```

Then copy data into the new deployment location:

```bash
cp -a "$OLD_DB_DIR/." /opt/food-reader/data/db/
cp -a "$OLD_UPLOAD_DIR/." /opt/food-reader/data/uploads/
```

### 4. Copy deployment files from the current master branch

From a temporary checkout of `Newpaw/food_reader` master, copy:

```bash
cp deploy/docker-compose.prod.yml /opt/food-reader/docker-compose.prod.yml
cp deploy/watchtower-compose.yml /opt/food-reader/watchtower-compose.yml
cp deploy/.env.example /opt/food-reader/.env.example
```

The checkout is needed only for this initial infrastructure setup. Runtime application releases come only from GHCR afterwards.

### 5. Create production `.env`

```bash
cd /opt/food-reader
cp .env.example .env
chmod 600 .env
```

Carry over the existing production values for OpenAI, JWT and Withings, then add Oura credentials.

Required shape:

```dotenv
BACKEND_PORT=18000
FRONTEND_PORT=18080
DATABASE_URL=sqlite:////app/data/app.db

JWT_SECRET=...
ACCESS_TOKEN_EXPIRE_MINUTES=10080
OPENAI_API_KEY=...

WITHINGS_CLIENT_ID=...
WITHINGS_CLIENT_SECRET=...
WITHINGS_REDIRECT_URI=https://YOUR_PUBLIC_HOST/withings/callback
APP_FRONTEND_URL=https://YOUR_PUBLIC_HOST/profile.html

OURA_CLIENT_ID=...
OURA_CLIENT_SECRET=...
OURA_REDIRECT_URI=https://YOUR_PUBLIC_HOST/oura/callback
OURA_FRONTEND_URL=https://YOUR_PUBLIC_HOST/health.html

LOG_LEVEL=INFO
LOG_TO_CONSOLE=True
LOG_TO_FILE=False
REQUEST_LOGGING_ENABLED=True
```

Do not change `DATABASE_URL`; it matches the persistent `/opt/food-reader/data/db` bind mount.

### 6. GHCR authentication

If the container package is public, Docker can pull it anonymously. If it is private, authenticate once with a classic GitHub PAT that has `read:packages`:

```bash
read -s GHCR_TOKEN
echo "$GHCR_TOKEN" | docker login ghcr.io -u Newpaw --password-stdin
unset GHCR_TOKEN
```

Watchtower reuses Docker's registry credentials through its mounted Docker config.

### 7. Stop the old application only after the data copy is complete

```bash
docker stop calorie-tracker
```

Keep the old container initially so rollback is easy. Do not remove its original persistent directories yet.

### 8. Pull and start the new image

```bash
cd /opt/food-reader
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Verify container state:

```bash
docker ps --filter name=food-reader
```

Verify the application is attached to the required network:

```bash
docker inspect food-reader --format '{{range $name, $network := .NetworkSettings.Networks}}{{println $name}}{{end}}'
```

The output must contain:

```text
cloudflare
```

Verify backend health on the VM:

```bash
curl -fsS http://127.0.0.1:18000/health && echo
```

Verify frontend Nginx on the VM:

```bash
curl -I http://127.0.0.1:18080/
```

Check startup logs:

```bash
docker logs --tail 100 food-reader
```

### 9. Verify persisted data

```bash
ls -lah /opt/food-reader/data/db
ls -lah /opt/food-reader/data/uploads | head
```

Log into the application and verify existing meal history and profile/weight data before removing the old container.

### 10. Start automatic image updates

```bash
cd /opt/food-reader
docker compose -f watchtower-compose.yml up -d
```

Only containers carrying this label are eligible:

```text
com.centurylinklabs.watchtower.enable=true
```

The Food Reader container has the label. Watchtower is configured with `WATCHTOWER_LABEL_ENABLE=true`, so it does not update unrelated containers on the VM.

It checks GHCR every 300 seconds and cleans obsolete image layers after successful updates.

Check updater logs:

```bash
docker logs --tail 100 food-reader-watchtower
```

For live observation:

```bash
docker logs -f food-reader-watchtower
```

## Normal deployment after initial setup

No VM command is needed for application-code releases:

```text
merge to master
-> GitHub Actions tests
-> image build
-> GHCR latest updated
-> Watchtower detects new digest
-> Food Reader recreated automatically
```

Persistent state remains on the VM:

```text
/opt/food-reader/.env
/opt/food-reader/data/db/app.db
/opt/food-reader/data/uploads/
```

## Reverse proxy

The application container is on the external `cloudflare` network and exposes:

```text
8000  backend inside Docker / host 18000
8080  frontend Nginx inside Docker / host 18080
```

The existing reverse proxy should continue targeting the frontend as before. The bundled frontend Nginx proxies `/auth`, `/users`, `/meals`, `/profile`, `/withings`, `/oura`, `/uploads` and `/health` to the backend container process.

For Oura, the public callback URL configured in the Oura developer application must match `OURA_REDIRECT_URI` exactly.

## Rollback

Each release also has a commit-specific image tag such as:

```text
ghcr.io/newpaw/food_reader:sha-a1b2c3d
```

To roll back, replace `:latest` in `/opt/food-reader/docker-compose.prod.yml` with the required SHA tag and run:

```bash
cd /opt/food-reader
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

To return to automatic releases, change the image back to `:latest`.

Do not delete the old `calorie-tracker` container or original data until the new deployment has been verified end to end.
