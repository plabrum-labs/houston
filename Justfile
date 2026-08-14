# Houston Justfile — https://just.systems

default:
    @just --list

# ─── Install ──────────────────────────────────────────────────────────────────

# Install backend dependencies
install:
    cd backend && uv sync --dev

# ─── Database ─────────────────────────────────────────────────────────────────

# Start postgres (dev + test) and redis via Docker
db-start:
    cd backend && docker compose -f docker-compose.dev.yml up -d

# Stop all Docker services
db-stop:
    cd backend && docker compose -f docker-compose.dev.yml down

# Run alembic migrations (upgrade to head)
db-upgrade:
    cd backend && uv run alembic upgrade head

# Create a new migration from model changes
db-migrate +message:
    cd backend && uv run alembic revision --autogenerate -m "{{message}}"
    cd backend && uv run ruff check --fix alembic/versions/ && uv run ruff format alembic/versions/

# Downgrade by one revision
db-downgrade:
    cd backend && uv run alembic downgrade -1

# Drop and recreate the dev database volume (destructive!)
db-clean:
    cd backend && docker compose -f docker-compose.dev.yml down -v
    just db-start
    just db-upgrade

# Connect to the dev database via psql
db-psql:
    psql postgresql://postgres:postgres@localhost:5432/houston

# ─── Development ──────────────────────────────────────────────────────────────

# Backend + SAQ worker in separate process
dev-backend-all:
    #!/usr/bin/env bash
    trap 'kill 0' EXIT
    (cd backend && uv run litestar --app app.index:app run -r -d -p 8000) &
    (cd backend && uv run litestar --app app.index:app workers run) &
    wait

# Start Litestar backend with hot reload
dev-backend:
    cd backend && uv run litestar --app app.index:app run -r -d -p 8000

# Start SAQ worker
dev-worker:
    cd backend && uv run litestar --app app.index:app workers run

# ─── Tests ────────────────────────────────────────────────────────────────────

# Run backend tests
test:
    cd backend && uv run pytest -v

# ─── Code Quality ─────────────────────────────────────────────────────────────

# Run semgrep custom rules against backend
semgrep:
    semgrep --config=semgrep/ --error backend/

# Run semgrep tests against rule test files
semgrep-test:
    semgrep --test semgrep/

# Lint + format all code (backend)
lint: lint-backend

# Lint + format backend
lint-backend:
    cd backend && uv run ruff check --fix . && uv run ruff format .

# Type-check all code (backend)
check: check-backend

# Type-check backend
check-backend:
    cd backend && uv run basedpyright

# ─── Docker ───────────────────────────────────────────────────────────────────

# Build backend Docker image
docker-build:
    cd backend && docker build -t houston-api:local .

# ─── Prod ─────────────────────────────────────────────────────────────────────

# Open an SSM shell on the prod EC2 host (pass `-- cmd` to run non-interactively)
prod-ssh *ARGS:
    ./scripts/prod-ssh.sh {{ARGS}}

# ─── Incept verification contract ─────────────────────────────────────────────

# Install backend dependencies (incept contract)
be-install:
    cd backend && uv sync --dev

# Lint + format backend (incept contract)
be-lint:
    cd backend && uv run ruff check --fix . && uv run ruff format .

# Type-check backend (incept contract)
be-check:
    cd backend && uv run basedpyright

# Run backend tests (incept contract)
be-test:
    cd backend && uv run pytest -v
