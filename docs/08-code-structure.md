Organize the code into the following structure:

```
app/
├── alembic.ini
├── alembic/
│   └── versions/
│       └── ...
├── core/
│   ├── settings/
│   ├── base/
│   ├── security/
│   ├── database.py
│   ├── adapter/
│   └── service/
├── {{ entity }}/
│   ├── __init__.py
│   ├── model.py          # SQLAlchemy database model
│   ├── schema.py        # Pydantic request/response schemas (DTOs)
│   ├── repository.py    # Database access layer
│   ├── service.py       # Business logic for this entity
│   └── validator.py     # Validation logic
├── endpoints/
│   ├── {{ version }}/
│   │   └── {{ entity }}.py
│   └── __init__.py
├── consumers/           # Kafka consumers
│   └── ...
└── schemas/            # Shared DTOs (Pydantic models) across entities
    └── ...
build/
├── local/
│   ├── docker-compose.yml
│   ├── README.md
│   └── .env
├── staging/
│   ├── docker-compose.yml
│   ├── README.md
│   └── .env
├── production/
│   ├── docker-compose.yml
│   ├── README.md
│   └── .env
├── Dockerfile
└── README.md
tests/
├── {{ entity }}/
│   ├── test_model.py
│   ├── test_schema.py
│   ├── test_repository.py
│   ├── test_service.py
│   └── test_validator.py
└── __init__.py
scripts/
├── setup_local_docker.sh
└── ...
```

## Key Rules

### 1. Business Logic Location
- **Business logic for each entity resides in `service.py` within the entity folder**
- Do NOT create a separate `services/` folder at the app root
- Each entity module is self-contained with its own service

### 2. Models vs Schemas
- **`model.py`**: SQLAlchemy database models (classes that interact with the database)
- **`schema.py`**: Pydantic request/response schemas (DTOs) for the entity
- **`schemas/` folder**: Shared DTOs (Pydantic models) used across multiple entities
- Do NOT use `models/` folder - use `schemas/` for shared DTOs

### 3. Dependency Management
- **Use `pyproject.toml`** for dependency management (PEP 621 standard)
- Do NOT use `requirements.txt`
- All dependencies must be declared in `pyproject.toml` under `[project.dependencies]` and `[project.optional-dependencies]`

### 4. Package Management
- **Use `uv`** instead of `pip` for package management
- **Use `uv`** instead of `pyenv` for Python version management
- Install dependencies with: `uv pip install -e .`
- Install dev dependencies with: `uv pip install -e ".[dev]"`
- **Dockerfile**: Use `uv` for all package installations (install via official installer, not pip)
- **Docker CMD**: Do NOT set CMD in Dockerfile - define it in docker-compose.yml for environment-specific control
  - Local/Dev: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
  - Production: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`

### 5. Kafka Configuration
- **Use KRaft mode** (no Zookeeper required)
- KRaft is production-ready since Kafka 3.3+ and simplifies infrastructure
- Advantages: Simpler setup, better performance, easier operations, future-proof
- See `docs/kafka-kraft-notes.md` for detailed information

## Package Descriptions

The core package is meant to implement the DRY principle.

- **core.adapter**: Infrastructure components like Postgres, Redis, Kafka, Mongo, etc.
- **core.security**: Code related to authentication, JWT encode/decode and FastAPI dependency to fetch user from JWT
- **core.service**: Shared services like cache, feature flags, mutex, distributed locking, etc.
- **core.settings**: All application configurations. The overall implementation of having base settings that are overridden by environment specific packages (dev, staging, qa, prod, etc) must be here.
- **core.base**: Common implementations necessary for model, service, repo, validator for any entity.