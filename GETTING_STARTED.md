
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

Create a .env file from the sample:

```
cp .env.example .env
```

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

In another terminal:

```
cd backend
alembic upgrade head
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


## 6. First API call (example)

Create an entity:

```
POST http://localhost/api/entities
{
  "kind": "drug",
  "label": "hydroxychloroquine"
}
```

Create a source:

```
POST http://localhost/api/sources
{
  "kind": "study",
  "title": "Study A",
  "year": 2020,
  "trust_level": 0.8
}
```

Create a relation (hyper-edge):

```
POST http://localhost:8000/relations
{
  "source_id": "<source_id>",
  "kind": "effect",
  "direction": "positive",
  "confidence": 0.7,
  "roles": [
    { "entity_id": "<entity_id>", "role_type": "intervention" },
    { "entity_id": "<entity_id>", "role_type": "outcome" }
  ]
}
```


## 7. Minimal inference

Query all relations involving an entity:

```
GET http://localhost:8000/inferences/entity/<entity_id>
```

This returns a structured, traceable view of assertions — no synthesis, no consensus.


## Notes

The backend is schemaless by design (no domain rules hardcoded).

All “knowledge” is derived at query time.

The database is the single source of truth.

LLMs are optional and never authoritative.


