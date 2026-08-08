# Food Reader deployment

The production deployment is image-based. The VM does not build the application and does not need to pull source-code changes after the initial setup.

## Release flow

```text
merge/push to master
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
Watchtower on VM (poll every 5 minutes)
  - compare image digest
  - pull only when changed
  - recreate Food Reader container
  - keep .env + SQLite + uploads on VM
```

Every release also gets an immutable `sha-<commit>` tag for rollback/audit purposes.

## GitHub side

Workflow: `.github/workflows/release-container.yml`

It runs on every push to `master` and can also be started manually with `workflow_dispatch`.

The workflow uses the repository `GITHUB_TOKEN`, so no Docker Hub credentials are required in GitHub Actions.

Published image:

```text
ghcr.io/newpaw/food_reader:latest
```

## One-time VM setup

Create a deployment directory, for example:

```bash
sudo mkdir -p /opt/food-reader/data/uploads /opt/food-reader/data/db
cd /opt/food-reader
```

Copy these files from the repository once:

```text
deploy/docker-compose.prod.yml
deploy/watchtower-compose.yml
deploy/.env.example
```

Rename the environment template and fill in the real secrets and public callback URLs:

```bash
cp .env.example .env
chmod 600 .env
```

Make sure the external reverse-proxy Docker network exists. The default is `cloudflare`; change `PROXY_NETWORK` in `.env` if this VM uses another network such as `npm_default`.

```bash
docker network ls
```

### GHCR login

If the GHCR package is private, log the VM into GHCR once using a GitHub Personal Access Token with `read:packages`:

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u Newpaw --password-stdin
```

The Watchtower compose mounts the Docker credential file, so subsequent pulls use the same login. If the package is public, authentication is not required.

## Start the application

From `/opt/food-reader`:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Check health:

```bash
docker ps
docker logs --tail 100 food-reader
```

The application container has a Docker healthcheck against the backend `/health` endpoint.

## Start automatic updates

```bash
docker compose -f watchtower-compose.yml up -d
```

Only containers carrying this label are updated:

```text
com.centurylinklabs.watchtower.enable=true
```

Food Reader has that label in `docker-compose.prod.yml`. Other containers on the VM are not touched by this Watchtower instance.

Watchtower checks for a new image every 300 seconds and removes obsolete image layers after a successful update.

Check updater logs:

```bash
docker logs -f food-reader-watchtower
```

## Persistent data

The following data stays on the VM and survives image updates:

```text
/opt/food-reader/.env
/opt/food-reader/data/db/app.db
/opt/food-reader/data/uploads/
```

The SQLite database is mounted into `/app/data` inside the container. Never bake production `.env`, database files, Oura/Withings tokens, or uploaded food images into the image.

## Rollback

Each release has a commit-specific tag such as:

```text
ghcr.io/newpaw/food_reader:sha-a1b2c3d
```

For a rollback, temporarily replace `:latest` in `docker-compose.prod.yml` with the required SHA tag and run:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

If you pin a SHA tag, Watchtower will no longer follow `latest` until the compose file is changed back.

## Oura callbacks

The real public URLs must match the OAuth applications exactly. For example:

```dotenv
OURA_REDIRECT_URI=https://food.example.com/oura/callback
OURA_FRONTEND_URL=https://food.example.com/health.html
WITHINGS_REDIRECT_URI=https://food.example.com/withings/callback
APP_FRONTEND_URL=https://food.example.com/profile.html
```

The reverse proxy must route the public host to the frontend port and preserve the `/oura` and `/withings` API paths handled by the bundled Nginx configuration.
