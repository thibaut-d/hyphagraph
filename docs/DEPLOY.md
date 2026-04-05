# Multi-Environment Deployment (local, remote dev, production)

Goal: keep **one repository** that can run:
- locally (developer machine)
- on a dev server (`dev.mydomain.com`)
- for self-hosted production (`mydomain.com`)

This document prioritizes your current need: **deploying the dev version on your OVH VPS**.

---

## 1. Files added to simplify deployments

### Compose
- `docker-compose.local.yml`: local development
- `docker-compose.remote-dev.yml`: remote development server
- `docker-compose.prod.yml`: production stack from published images
- `docker-compose.e2e.yml`: isolated E2E test stack

### Caddy (versioned templates)
- `deploy/caddy/Caddyfile.dev`
- `deploy/caddy/Caddyfile.self-host`

### Environment templates
- `.env.example` (development: local or remote dev server)
- `.env.prod.template` (self-host production)

### Makefile commands
- `make up`, `make down`, `make logs`
- `make remote-dev-up`, `make remote-dev-down`, `make remote-dev-logs`, `make remote-dev-migrate`
- `make prod-setup`, `make prod-up`, `make prod-logs`, `make prod-update`

---

## 2. Server prerequisites (OVH VPS 2)

On Ubuntu 22.04/24.04:

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker version
docker compose version
```

Open firewall ports:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

DNS:
- `A dev.mydomain.com -> dev VPS public IP`
- later, `A mydomain.com -> production server public IP`

---

## 3. Current setup: deploy DEV on the VPS

### 3.1 Clone the repository

```bash
sudo mkdir -p /srv
sudo chown $USER:$USER /srv
cd /srv
git clone <REPO_URL> hyphagraph
cd hyphagraph
```

### 3.2 Create `.env`

```bash
cp .env.example .env
```

Edit `.env` and at minimum update:
- `POSTGRES_PASSWORD`
- `DATABASE_URL` (matching DB password)
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `ADMIN_PASSWORD`
- LLM keys if needed

### 3.3 Update the dev domain

`deploy/caddy/Caddyfile.dev` contains a placeholder domain. Replace it with your actual dev domain before starting:

```bash
sed -i "s|dev.mydomain.com|dev.yourdomain.com|g" deploy/caddy/Caddyfile.dev
```

### 3.4 Start the dev server stack

```bash
make remote-dev-up
```

Migrations run automatically on container start (via `docker-entrypoint.sh`). No separate migration step is needed.

Verify:

```bash
make remote-dev-logs
docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml ps
curl -I https://dev.mydomain.com
curl -I https://dev.mydomain.com/api/docs
```

---

## 4. Remote development workflow

### Recommended option: VS Code Remote SSH

On your local machine, add this to `~/.ssh/config`:

```sshconfig
Host hyphagraph-dev
  HostName dev.mydomain.com
  User <ssh_user>
  IdentityFile ~/.ssh/id_ed25519
```

Then:
1. Open remote folder `/srv/hyphagraph`.
2. Develop directly on the VPS.
3. Use these commands:

```bash
make remote-dev-logs
docker stats
docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml exec api pytest -q
docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml exec web npx tsc --noEmit
```

---

## 5. Local deployment (unchanged)

```bash
cp .env.example .env
docker compose -f docker-compose.local.yml up -d --build
```

> Migrations run automatically on container startup — no manual `alembic upgrade head` needed.
> To run migrations manually (e.g. for debugging): `docker compose -f docker-compose.local.yml exec api alembic upgrade head`

Access:
- `http://localhost`
- `http://localhost/api/docs`

Smoke-check the proxied API path:

```bash
make dev-check
```

---

## 6. Production deployment

### 6.1 Prepare production secrets

```bash
cp .env.prod.template .env
```

Fill all sensitive values, including `HYPHAGRAPH_VERSION`.

### 6.2 Update production domain

Edit `deploy/caddy/Caddyfile.self-host` and replace `your-domain.com` with your actual domain:

```bash
sed -i "s|your-domain.com|yourdomain.com|g" deploy/caddy/Caddyfile.self-host
```

Verify the result before starting the stack:

```bash
cat deploy/caddy/Caddyfile.self-host
```

### 6.3 Start the production stack

```bash
make prod-up
```

Production applies:
- backend and frontend pull published GHCR images pinned by `HYPHAGRAPH_VERSION`
- backend runs `alembic upgrade head` then uvicorn on start
- HTTPS Caddy with persisted certificates

Helpful follow-up commands:

```bash
make prod-logs
make prod-check
make prod-update
```

---

## 7. Important if you only have one VPS

You can use the same repository for dev and prod, but:
- in the current setup, **dev and prod cannot both bind 80/443 at the same time** on one machine
- simplest approach: run **dev OR prod** depending on your current need

If you want both in parallel on one VPS, you need an extra edge reverse-proxy layer (different internal ports + domain routing).

---

## 8. Quick runbook

Update code:

```bash
cd /srv/hyphagraph
git pull
make remote-dev-up
```

Stop dev:

```bash
make remote-dev-down
```

Stop production:

```bash
make prod-down
```

Docker cleanup:

```bash
docker system prune -f
```
