# Food Reader deployment

Production is image-based. The VM does not build the application and does not need the full Git repository after the initial setup.

## Release flow

```text
push / merge to master
        |
        v
GitHub Actions
  - backend tests
  - frontend syntax checks
  - Docker build
  - push to GHCR
        |
        v
ghcr.io/newpaw/food_reader:latest
        |
        v
systemd timer on VM every 5 minutes
  - docker compose pull
  - docker compose up -d
  - health verification
```

Every release also gets an immutable `sha-<commit>` tag for rollback.

## GitHub Container Registry

The project publishes to GitHub Container Registry (GHCR), not Docker Hub:

```text
ghcr.io/newpaw/food_reader:latest
ghcr.io/newpaw/food_reader:sha-<commit>
```

The GitHub Actions workflow uses the repository `GITHUB_TOKEN` with `packages: write`, so no Docker Hub credentials and no extra GitHub secret are required for publishing.

If the GHCR package is private, the VM must authenticate once with a classic GitHub PAT that has `read:packages`. Public GHCR packages can be pulled anonymously.

## Production network

The application is pinned to the existing external Docker network:

```text
cloudflare
```

Do not create a replacement network if it is missing; verify the existing Cloudflare/reverse-proxy deployment first.

## Runtime files on the VM

After setup, the VM only needs:

```text
/opt/food-reader/
├── .env
├── docker-compose.prod.yml
├── update-food-reader.sh
└── data/
    ├── db/
    │   └── app.db
    └── uploads/
```

The full Git checkout is not required for normal operation.

## One-time VM setup

Create the runtime directories:

```bash
sudo mkdir -p /opt/food-reader/data/db /opt/food-reader/data/uploads
```

Copy the existing SQLite database and uploads into those directories before starting the new container.

Copy these deployment files from the repository master branch once:

```text
deploy/docker-compose.prod.yml
deploy/update-food-reader.sh
deploy/.env.example
```

Install the updater systemd units:

```text
deploy/food-reader-update.service
deploy/food-reader-update.timer
```

## Environment

Create `/opt/food-reader/.env` from `deploy/.env.example` and protect it:

```bash
chmod 600 /opt/food-reader/.env
```

Keep:

```dotenv
BACKEND_PORT=18000
FRONTEND_PORT=18080
DATABASE_URL=sqlite:////app/data/app.db
```

Set real values for JWT/OpenAI and optional Withings/Oura OAuth configuration. Never commit secrets to Git.

## GHCR authentication

First test an anonymous pull:

```bash
docker pull ghcr.io/newpaw/food_reader:latest
```

If it succeeds, no registry login is needed.

If it returns `denied` or `unauthorized`, authenticate the Docker daemon user once with a classic GitHub PAT containing `read:packages`:

```bash
read -s GHCR_TOKEN
sudo docker login ghcr.io -u Newpaw --password-stdin <<< "$GHCR_TOKEN"
unset GHCR_TOKEN
```

Because the updater systemd service runs as root, authenticate with `sudo docker login` when the package is private.

## First start

Verify the required external network:

```bash
docker network inspect cloudflare >/dev/null && echo "cloudflare network OK"
```

Start the application:

```bash
cd /opt/food-reader
sudo docker compose -f docker-compose.prod.yml pull
sudo docker compose -f docker-compose.prod.yml up -d
```

Verify:

```bash
docker ps --filter name=food-reader
docker inspect food-reader --format '{{range $name, $network := .NetworkSettings.Networks}}{{println $name}}{{end}}'
curl -fsS http://127.0.0.1:18000/health && echo
curl -I http://127.0.0.1:18080/
docker logs --tail 100 food-reader
```

The network output must include `cloudflare` and the container should become healthy.

## Automatic updates with systemd

Install the updater:

```bash
sudo cp /opt/food-reader/food-reader-update.service /etc/systemd/system/
sudo cp /opt/food-reader/food-reader-update.timer /etc/systemd/system/
sudo chmod +x /opt/food-reader/update-food-reader.sh
sudo systemctl daemon-reload
sudo systemctl enable --now food-reader-update.timer
```

Verify:

```bash
systemctl status food-reader-update.timer --no-pager
systemctl list-timers food-reader-update.timer --no-pager
```

Run one update check immediately:

```bash
sudo systemctl start food-reader-update.service
sudo systemctl status food-reader-update.service --no-pager
journalctl -u food-reader-update.service -n 100 --no-pager
```

The timer checks GHCR every 5 minutes. `docker compose pull` downloads a changed image, and `docker compose up -d` recreates the Food Reader service only when the image/configuration changed. Persistent bind-mounted SQLite and uploads remain untouched.

## Normal application release

For application-code changes, no SSH or Git operation is required on the VM:

```text
push to master
-> GitHub Actions tests
-> GHCR image published
-> VM systemd timer detects/pulls it
-> Food Reader container recreated
```

Only infrastructure changes to `.env`, the compose file, network, ports, or systemd updater need a manual VM change.

## Rollback

Each build also publishes a commit tag such as:

```text
ghcr.io/newpaw/food_reader:sha-a1b2c3d
```

To roll back, temporarily change the image tag in `/opt/food-reader/docker-compose.prod.yml`, then run:

```bash
cd /opt/food-reader
sudo docker compose -f docker-compose.prod.yml pull
sudo docker compose -f docker-compose.prod.yml up -d
```

Change it back to `:latest` to resume automatic updates.
