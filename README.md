# Endorsement Management System (EMS)

A specialized middleware platform designed to bridge the gap between Employers (Group Insurance Policyholders) and Insurance Providers.

## Overview

The EMS automates the workflow of managing employee coverage changes (endorsements) in group insurance policies, optimizing cash flow and ensuring zero coverage gaps.

## Key Features

- **Zero Coverage Gaps**: Ensures legally binding coverage from the exact date of eligibility
- **Liquidity Optimization**: Minimizes capital required in Endorsement Account by intelligently scheduling transactions
- **Scalability**: Supports 100,000 employers generating ~1 million transactions daily
- **Resiliency**: Handles insurer downtime and API failures with robust retry mechanisms
- **Visibility**: Provides real-time transparency into transaction status and account balances

## Tech Stack

- **Language**: Python 3.14+
- **Framework**: FastAPI
- **Databases**: PostgreSQL 15, MongoDB 6.0, Redis 7.0
- **Message Broker**: Apache Kafka
- **Observability**: Prometheus, Grafana, Structured Logging

## Project Structure

```
app/
├── core/           # Core infrastructure (settings, adapters, security, base)
├── employer/       # Employer entity module
├── employee/       # Employee entity module
├── policy_coverage/ # Policy coverage module
├── endorsement_request/ # Endorsement request module
├── ledger_transaction/  # Ledger transaction module
├── audit_log/      # Audit log module (MongoDB)
├── endpoints/      # API endpoints
├── consumers/      # Kafka consumers
└── schemas/        # Shared DTOs (Pydantic models)

tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
└── e2e/           # End-to-end tests

build/
├── local/          # Local development configs
├── staging/         # Staging environment configs
└── production/     # Production environment configs
```

## Setup

### Prerequisites

- Docker (23.x+ recommended) with the Compose v2 plugin so you can run `docker compose`.
- Environment configs are baked under `build/`. Copy `build/env.example` to `build/local/.env` or symlink to one of the stage-specific overrides (`local.env`, `staging.env`, `production.env`).

### Docker local development

1. Prepare the environment file:
   ```bash
   cp build/env.example build/local/.env
   ```
   Modify `.env` if you need different credentials (the local compose assumes Postgres/Mongo/Redis are reachable on the default ports).

2. Start the stack:
   ```bash
   docker compose -f build/local/docker-compose.yml up --build
   ```
   The stack includes Postgres 17, MongoDB 8.0, Redis 8.0, Kafka 7.6 (KRaft mode), and all application workers.

3. Run migrations inside the app container:
   ```bash
   docker compose -f build/local/docker-compose.yml exec app alembic upgrade head
   ```
   This inspects the `.env` file your compose stack is using and upgrades Postgres to the latest schema before any workers start handling Kafka traffic.

4. Monitor health and logs:
   ```bash
   docker compose -f build/local/docker-compose.yml logs -f app
   ```
   The application exposes FastAPI on `http://localhost:8000`, Kafka UI (Kafdrop) on `http://localhost:9000`, and Prometheus metrics on `/metrics`.

5. Tear down:
   ```bash
   docker compose -f build/local/docker-compose.yml down -v
   ```
   Use `--remove-orphans` if you staged additional services.

### Manual local setup (optional)

1. Install `uv` (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install the required Python version (3.14 is the target):
   ```bash
   uv python install 3.14
   ```

3. Install dependencies:
   ```bash
   uv pip install -e .
   uv pip install -e ".[dev]"
   ```

4. Set up the `.env` file as described above and run database migrations:
   ```bash
   alembic upgrade head
   ```

5. Launch the API:
   ```bash
   uvicorn app.main:app --reload
   ```

## Development

### Code Quality

```bash
# Format code
black app tests

# Lint
ruff check app tests

# Type check
mypy app
```

## API Documentation

Once the server is running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Metrics: http://localhost:8000/metrics

## Documentation

See the `docs/` folder for detailed documentation:
- API Guidelines (versioning, error handling, pagination)
- Technical Specification
- Testing Guidelines
- Implementation Plan

## License

MIT
