#!/usr/bin/env bash
# HyphaGraph self-hosting setup
# Run once on a fresh server to generate secrets, configure your domain, and prepare .env.
#
# Usage:
#   bash scripts/setup-self-host.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${GREEN}✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}!${RESET} $*"; }
error()   { echo -e "${RED}✗${RESET} $*" >&2; }
heading() { echo -e "\n${BOLD}$*${RESET}"; }

# ── Checks ─────────────────────────────────────────────────────────────────────

heading "HyphaGraph Self-Host Setup"

if ! command -v openssl &>/dev/null; then
    error "openssl is required to generate secrets. Install it and re-run."
    exit 1
fi

if ! command -v docker &>/dev/null; then
    error "Docker is not installed. Install Docker and re-run."
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
CADDYFILE="$REPO_ROOT/deploy/caddy/Caddyfile.self-host"
TEMPLATE="$REPO_ROOT/.env.prod.template"

if [[ ! -f "$TEMPLATE" ]]; then
    error "Template not found: $TEMPLATE"
    exit 1
fi

# ── Prompt ─────────────────────────────────────────────────────────────────────

heading "Configuration"

read -rp "  Domain name (e.g. yoursite.com): " DOMAIN
if [[ -z "$DOMAIN" ]]; then
    error "Domain name is required."
    exit 1
fi

read -rp "  Admin email: " ADMIN_EMAIL
if [[ -z "$ADMIN_EMAIL" ]]; then
    error "Admin email is required."
    exit 1
fi

while true; do
    read -rsp "  Admin password (min 12 chars): " ADMIN_PASSWORD
    echo
    if [[ ${#ADMIN_PASSWORD} -lt 12 ]]; then
        warn "Password must be at least 12 characters. Try again."
    else
        break
    fi
done

read -rp "  HyphaGraph version to deploy [latest]: " VERSION
VERSION="${VERSION:-latest}"

# ── Generate secrets ───────────────────────────────────────────────────────────

heading "Generating secrets"

SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 24)

info "SECRET_KEY generated"
info "JWT_SECRET_KEY generated"
info "POSTGRES_PASSWORD generated"

# ── Write .env ─────────────────────────────────────────────────────────────────

heading "Writing .env"

if [[ -f "$ENV_FILE" ]]; then
    BACKUP="$ENV_FILE.bak.$(date +%Y%m%d%H%M%S)"
    warn "Existing .env found — backing up to $BACKUP"
    cp "$ENV_FILE" "$BACKUP"
fi

cp "$TEMPLATE" "$ENV_FILE"

# Replace placeholders
sed -i "s|change-me-prod-password|${POSTGRES_PASSWORD}|g"   "$ENV_FILE"
sed -i "s|change-me-prod-secret-key|${SECRET_KEY}|g"        "$ENV_FILE"
sed -i "s|change-me-prod-jwt-secret-key|${JWT_SECRET_KEY}|g" "$ENV_FILE"
sed -i "s|change-me-prod-admin-password|${ADMIN_PASSWORD}|g" "$ENV_FILE"
sed -i "s|admin@mydomain.com|${ADMIN_EMAIL}|g"              "$ENV_FILE"
sed -i "s|HYPHAGRAPH_VERSION=latest|HYPHAGRAPH_VERSION=${VERSION}|g" "$ENV_FILE"
# Update DATABASE_URL to use the generated password
sed -i "s|change-me-prod-password@db|${POSTGRES_PASSWORD}@db|g" "$ENV_FILE"
# Update FRONTEND_URL
sed -i "s|https://mydomain.com|https://${DOMAIN}|g"         "$ENV_FILE"

info ".env written"

# ── Write Caddyfile ────────────────────────────────────────────────────────────

heading "Configuring Caddy"

cat > "$CADDYFILE" <<CADDYEOF
# Self-hosting Caddyfile
# Caddy obtains and renews HTTPS certificates from Let's Encrypt automatically.
# Requires ports 80 and 443 open to the internet.

${DOMAIN} {
    handle /api/* {
        reverse_proxy api:8000
    }

    handle {
        reverse_proxy web:80
    }
}
CADDYEOF

info "Caddyfile updated with domain: $DOMAIN"

# ── Done ───────────────────────────────────────────────────────────────────────

heading "Setup complete"

cat <<EOF

  Domain:       https://${DOMAIN}
  Admin email:  ${ADMIN_EMAIL}
  Version:      ${VERSION}

${BOLD}Next steps:${RESET}
  1. Ensure ports 80 and 443 are open on this server.
  2. Start HyphaGraph:

       make self-host-up

  3. Verify deployment:

       make self-host-check

${YELLOW}Keep your .env file safe — it contains your database password and secrets.${RESET}
EOF
