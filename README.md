# Personal Quant Trading Engine

A local, paper-only quantitative research and simulation project.

## Current capabilities

- Typed strategy contracts.
- Moving-average and Bollinger validation strategies.
- Completed-bar CSV ingestion.
- Long-only, single-symbol simulated accounts.
- Mandatory simulator risk checks.
- Latched UTC daily-loss circuit breaker.
- Next-bar opening-event execution.
- Fixed-bps commissions and adverse slippage.
- Equity metrics and JSON/CSV reports.
- Optional transactional PostgreSQL/TimescaleDB persistence.
- Read-only FastAPI monitoring.
- Celery historical jobs.
- Streamlit report dashboard.

## Not enabled

- Real-money trading.
- Automated broker paper orders.
- Multi-strategy shared-account execution.
- Derivatives, leverage, or short positions.
- Exchange-session calendars.
- Persistent broker-account circuit-breaker state.
- Production deployment.

The Alpaca integration is read-only and uses the paper endpoint.

## Python

Use the project Python 3.12 environment:

    source venv312/bin/activate

## Synthetic data

    python -m app.data.demo

This writes fictional TEST hourly bars to data/demo.csv.

## Foreground simulation

    python scripts/run_backtest.py --dataset demo --strategy ma_cross

Bollinger example:

    python scripts/run_backtest.py --dataset demo --strategy bollinger

Reports are written into reports/.

These are local historical simulations, not broker paper orders.

## Database setup

Configure POSTGRES_USER, POSTGRES_DB, POSTGRES_PASSWORD,
DATABASE_URL, LOCAL_UID, and LOCAL_GID in the ignored .env file.

Start dependencies:

    sudo docker compose --env-file .env -f docker/docker-compose.yml up -d db redis

Run migrations explicitly:

    sudo docker compose --env-file .env -f docker/docker-compose.yml --profile tools run --rm migrate

Start application services:

    sudo docker compose --env-file .env -f docker/docker-compose.yml up -d --build api worker beat dashboard

API:

    http://127.0.0.1:8000/docs

Dashboard:

    http://127.0.0.1:8501

## Persist a simulation

With PostgreSQL running and migrations applied:

    python scripts/run_backtest.py --dataset demo --strategy ma_cross --persist

The account ID is simulation-<job UUID>.

## Background simulation

With Redis and the worker running:

    python scripts/run_backtest.py --dataset demo --strategy ma_cross --background --persist

The worker reads the shared data directory and writes into reports/.

## CSV contract

Required columns:

    timestamp,open,high,low,close,volume

Timestamps must be timezone-aware completed-bar closing times.

The initial replay requires continuously spaced fixed-width bars.

Do not use raw stock daily timestamps with this simulator without adding
an exchange-calendar-aware execution model.

## Quality checks

    ruff format app tests scripts dashboard
    ruff check app tests scripts dashboard
    mypy app
    pytest --cov=app --cov-report=term-missing

Install Git hooks:

    pre-commit install

## Safety

- IS_PAPER must remain true.
- ENABLE_LIVE_TRADING must remain false.
- The simulator checks every incremental order.
- A tripped circuit breaker does not automatically reset at midnight.
- The circuit breaker is not an automatic liquidation mechanism.
- Broker credentials must never enter prompts, logs, or commits.
- API ports remain loopback-only.
- Do not expose the unauthenticated monitoring API publicly.
- Do not use docker compose down -v unless deliberately deleting data.

## Remaining milestones

- Verify all code and migrations.
- Add database integration tests and failure injection.
- Reach the coverage target.
- Lock dependencies and container images.
- Add durable broker-account risk state and reconciliation.
- Implement an explicitly approved broker-paper execution path.
- Observe broker paper trading before any live consideration.
- Add mathematically verified Tier-2 and Tier-3 strategies.