
# 🚀 Getting started (5 minutes)

## Prerequisites

* Docker + Docker Compose
* Node.js ≥ 20
* Python ≥ 3.12
* (optionnel) VS Code


## 1. Clone the repository

```
git clone https://github.com/your-org/hyphagraph.git
cd hyphagraph
```

## 2. Environment variables

Create a `.env` file from the sample (for Docker Compose):

```
cp .env.sample .env
```

The `backend/.env.test` file is already included in the repository with sensible test defaults.

Defaults are suitable for local development.


## 3. Start everything with Docker

```
docker compose up --build
```

This starts:

- PostgreSQL (database)
- FastAPI backend (http://localhost/api)
- Vite + React frontend (http://localhost)


## 4. Initialize the database (first run)

The database schema is managed with Alembic migrations.

**⚠️ Important:** All commands must be run inside the Docker container, not on your host machine.

In another terminal:

```bash
# Run migrations inside the API container
docker compose exec api alembic upgrade head
```

This will create all tables with the correct schema, indexes, and constraints.

**Note:** If you need to reset the database:

```bash
docker compose exec api alembic downgrade base  # Drop all tables
docker compose exec api alembic upgrade head     # Recreate from scratch
```

**Alternative:** Interactive shell inside the container:

```bash
docker compose exec api bash
# Now you're inside the container
alembic upgrade head
exit
```


## 5. Open in VS Code

For VS Code users: 

```
code .hyphagraph.code-workspace
```

VS Code will:

- select the correct Python environment
- enable Ruff (Python lint + format)
- enable ESLint / Prettier for React
- expose ready-to-use tasks (Run → Tasks)


## 6. Authentication (Create your first user)

HyphaGraph uses **custom JWT-based authentication** (not FastAPI Users).

### Option A: Register a new user

```bash
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-secure-password"
  }'
```

### Option B: Use default admin account

The system creates a default admin on startup:
- Email: `admin@example.com`
- Password: `changeme123`

**⚠️ Change this in production!**

### Login and get access token

```bash
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=changeme123"
```

Returns:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

### Use token in requests

Include in Authorization header:
```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost/api/auth/me
```

For complete authentication documentation, see **AUTHENTICATION.md**.


## 7. First API call (example)

Now you can create entities, sources, and relations:

### Create an entity

```bash
POST http://localhost/api/entities
Authorization: Bearer <your_token>
Content-Type: application/json

{
  "slug": "hydroxychloroquine",
  "ui_category_id": "<category_id>",
  "summary": {
    "en": "Antimalarial drug"
  },
  "terms": [
    {"term": "hydroxychloroquine", "language": "en"},
    {"term": "HCQ", "language": null}
  ]
}
```

### Create a source

```bash
POST http://localhost/api/sources
Authorization: Bearer <your_token>
Content-Type: application/json

{
  "kind": "study",
  "title": "Efficacy Study A",
  "authors": ["Smith J.", "Doe A."],
  "year": 2023,
  "origin": "Journal of Medicine",
  "url": "https://example.org/study",
  "trust_level": 0.8,
  "summary": {
    "en": "Randomized controlled trial"
  }
}
```

### Create a relation (hyper-edge)

```bash
POST http://localhost/api/relations
Authorization: Bearer <your_token>
Content-Type: application/json

{
  "source_id": "<source_uuid>",
  "kind": "effect",
  "direction": "supports",
  "confidence": 0.7,
  "scope": {
    "population": "adults",
    "condition": "chronic use"
  },
  "notes": {
    "en": "Moderate efficacy observed"
  },
  "roles": [
    {
      "entity_id": "<drug_entity_uuid>",
      "role_type": "agent"
    },
    {
      "entity_id": "<symptom_entity_uuid>",
      "role_type": "outcome"
    }
  ]
}
```


## 8. Minimal inference

Query all relations involving an entity:

```bash
GET http://localhost/api/inferences/entity/<entity_uuid>
Authorization: Bearer <your_token>
```

This returns a structured, traceable view of assertions — no synthesis, no consensus.


## 9. Running tests

### Backend tests (inside Docker)

```bash
# All tests
docker compose exec api pytest

# With coverage
docker compose exec api pytest --cov=app --cov-report=html --cov-report=term-missing

# Specific test file
docker compose exec api pytest tests/test_auth_endpoints.py

# Verbose
docker compose exec api pytest -vv
```

### Frontend tests (can run locally or in Docker)

```bash
# Locally (if Node.js installed)
cd frontend
npm test

# Or inside Docker
docker compose exec web npm test

# With UI (locally only)
cd frontend
npm run test:ui

# With coverage
npm run test:coverage
```

For complete testing documentation, see **TESTING.md**.


## 10. API Documentation

Once running, visit:

- **Swagger UI**: http://localhost/api/docs
- **ReDoc**: http://localhost/api/redoc

These provide interactive API documentation with request/response examples.


## Troubleshooting

### "Could not connect to database"

```bash
# Check database is running
docker compose ps db

# Check database logs
docker compose logs db

# Restart database
docker compose restart db
```

### "Migrations not applied"

```bash
docker compose exec api alembic upgrade head
```

### "Port already in use"

```bash
# Check what's using port 80
# On Linux/Mac:
sudo lsof -i :80

# On Windows:
netstat -ano | findstr :80

# Stop conflicting service or change port in docker-compose.yml
```

### Reset everything

```bash
# Stop and remove all containers and volumes
docker compose down -v

# Rebuild and restart
docker compose up --build -d

# Reapply migrations (inside Docker container)
docker compose exec api alembic upgrade head
```


## Development workflow

### Typical session

```bash
# Start services
docker compose up -d

# Watch logs
docker compose logs -f api web

# Make code changes (auto-reload enabled)

# Run tests (backend inside Docker, frontend locally or in Docker)
docker compose exec api pytest
cd frontend && npm test

# Create migration if models changed (inside Docker)
docker compose exec api alembic revision --autogenerate -m "Add new field"
docker compose exec api alembic upgrade head
```

### Before committing

```bash
# Backend checks (inside Docker)
docker compose exec api pytest --cov=app
docker compose exec api ruff check .
docker compose exec api ruff format .
docker compose exec api mypy app/

# Frontend checks (locally or in Docker)
cd frontend
npm test
npm run lint
npm run format
```


## Production considerations

**⚠️ This is a proof of concept. NOT production-ready.**

If deploying anyway, you MUST:

1. Change all default passwords (`ADMIN_PASSWORD`, `POSTGRES_PASSWORD`)
2. Generate secure secrets:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Set as `SECRET_KEY` and `JWT_SECRET_KEY` in `.env`
3. Enable HTTPS (Caddy with Let's Encrypt)
4. Configure proper CORS origins
5. Enable rate limiting and monitoring
6. Set up PostgreSQL backups
7. Configure email service (SMTP)
8. Set `ENV=production` in `.env`

See **ARCHITECTURE.md** for security constraints.


## Notes

- The backend is schemaless by design (no domain rules hardcoded)
- All "knowledge" is derived at query time
- The database is the single source of truth
- LLMs are optional and never authoritative
- Authentication uses custom JWT (not FastAPI Users)
- All syntheses are computed, not authored


## Next steps

After setup, read these documents in order:

1. **AUTHENTICATION.md** - Authentication system implementation
2. **PROJECT.md** - Scientific motivation and vision
3. **ARCHITECTURE.md** - System architecture
4. **DATABASE_SCHEMA.md** - Data model
5. **CODE_GUIDE.md** - Coding guidelines
6. **TESTING.md** - Testing strategies
7. **UX.md** - Design principles


## Getting help

- **API Docs**: http://localhost/api/docs
- **Documentation**: Check markdown files at repository root
- **Architecture Questions**: See `ARCHITECTURE.md`
- **Code Questions**: See `CODE_GUIDE.md`
- **Issues**: Report on GitHub
