# Backend Setup Guide

## Prerequisites

- Python 3.12+
- pip

## Development Setup (SQLite)

1. **Install dependencies:**
   ```bash
   pip install -e .
   ```

2. **Create development database:**
   ```bash
   # Create database from models
   python << EOF
from app.config import settings
from app.models.base import Base
from app.models import *
from sqlalchemy import create_engine

sync_url = settings.DATABASE_URL.replace('+aiosqlite', '')
engine = create_engine(sync_url)
Base.metadata.create_all(engine)
print("Database created successfully!")
EOF

   # Stamp with latest migration
   alembic stamp head
   ```

3. **Configure environment:**
   - Copy `.env.test` to `.env` (already done if you have `.env`)
   - Update `DATABASE_URL` if needed (defaults to SQLite)
   - Set `OPENAI_API_KEY` if using LLM features

4. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Default admin: `admin@example.com` / `changeme123`

## Production Setup (PostgreSQL)

1. **Install dependencies:**
   ```bash
   pip install -e .
   ```

2. **Configure environment:**
   Create `.env` file:
   ```bash
   ENV=production
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/hyphagraph
   SECRET_KEY=your-secret-key-here
   ADMIN_EMAIL=admin@yourdomain.com
   ADMIN_PASSWORD=secure-password
   OPENAI_API_KEY=your-openai-key
   ```

3. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Run the server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## Database Notes

- **Development**: Uses SQLite (default: `hyphagraph.db`)
- **Production**: Uses PostgreSQL
- Models use cross-compatible types:
  - `JSON` instead of `JSONB` (auto-maps to JSONB in PostgreSQL)
  - `JSON` for arrays instead of PostgreSQL `ARRAY` type

## Testing

Run tests with:
```bash
pytest
```

Tests use SQLite by default (configured in `.env.test`).
