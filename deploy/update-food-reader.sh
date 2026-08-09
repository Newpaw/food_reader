#!/usr/bin/env bash
set -euo pipefail

cd /opt/food-reader

# Pull the current release image. If the digest is unchanged, compose up keeps
# the existing container. If the image changed, compose recreates only this app.
docker compose -f docker-compose.prod.yml pull --quiet app
docker compose -f docker-compose.prod.yml up -d --no-deps app

# Fail the update job if the container is not healthy/running after startup.
for _ in $(seq 1 20); do
  status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' food-reader 2>/dev/null || true)"
  case "$status" in
    healthy|running)
      exit 0
      ;;
    unhealthy|exited|dead)
      docker logs --tail 100 food-reader >&2 || true
      exit 1
      ;;
  esac
  sleep 3
done

docker logs --tail 100 food-reader >&2 || true
exit 1
