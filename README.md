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

- **Language**: Python 3.11+
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

- Python 3.14+
- PostgreSQL 17
- MongoDB 8.0
- Redis 8.0
- Kafka 7.6.0 (KRaft mode - no Zookeeper required)

### Installation

1. Install `uv` (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone the repository

3. Install Python version (if needed):
   ```bash
   uv python install 3.14
   ```

4. Install dependencies:
   ```bash
   uv pip install -e .
   uv pip install -e ".[dev]"  # For development dependencies
   ```

4. Set up environment variables:
   - copy `env_configs/env.example` to `.env` or build one from the stage-specific files in `env_configs/` (`local.env`, `staging.env`, `production.env`)

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test type
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

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
