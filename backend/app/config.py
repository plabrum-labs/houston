"""Houston's single concrete config.

One `Config` class holds every field the platform reads — DB URLs, auth secrets,
S3 buckets, SES/comms identity, Stripe keys, LLM/embeddings knobs, and template
dirs — each backed by an env var with a sensible default. There is no config ABC
and no `configure()`/`get_config()` indirection: Houston owns its platform and is the only
consumer, so platform code imports the concrete `config` singleton directly.

`get_config()` returns `TestConfig` when `ENV == "testing"` (pytest sets this before
importing `app`), otherwise `Config`; `config` is the resolved module singleton.

Uppercase property names (e.g. `ASYNC_DATABASE_URL`) are intentional field names, not
functions — `N802` is ignored for this file via `pyproject.toml`.
"""

import os

from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv("../.env.local")
load_dotenv(".env")
load_dotenv("../.env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _build_db_url(driver: str = "") -> str:
    # Prod deploy targets (ec2_stack/app_stack) inject these parts, not a full URL.
    endpoint = os.getenv("DB_ENDPOINT", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "houston")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    return f"postgresql{driver}://{user}:{password}@{endpoint}:{port}/{name}"


class Config:
    """Every config value the Houston platform reads, resolved from the environment."""

    # --- Core / environment ---------------------------------------------------
    ENV: str = os.getenv("ENV", "production")
    # Run queued tasks inline (dev default). Set QUEUE_SYNC=false + run a worker for async.
    QUEUE_SYNC: bool = _env_bool("QUEUE_SYNC", True)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # --- Auth -----------------------------------------------------------------
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret")

    # --- LLM / embeddings -----------------------------------------------------
    USE_REAL_LLM: bool = _env_bool("USE_REAL_LLM", False)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_REALTIME_MODEL: str = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2025-08-28")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    # Domain persona prepended to every system prompt (see llm/prompts.py). Generic by
    # default; a deployment overrides it with its own product name and vocabulary.
    LLM_PERSONA: str = os.getenv(
        "LLM_PERSONA",
        "You are a helpful assistant integrated into this application.",
    )

    # --- Comms (SES / email) --------------------------------------------------
    SES_FROM_EMAIL: str = os.getenv("SES_FROM_EMAIL", "")
    SES_FROM_NAME: str = os.getenv("SES_FROM_NAME", "")
    SES_REPLY_TO_EMAIL: str = os.getenv("SES_REPLY_TO_EMAIL", "")
    INBOX_DOMAIN: str = os.getenv("INBOX_DOMAIN", "")
    PRODUCT_NAME: str = os.getenv("PRODUCT_NAME", "the app")
    EMAIL_TEMPLATES_DIR: str = os.getenv("EMAIL_TEMPLATES_DIR", "email_templates/out/emails-react")

    # --- Documents ------------------------------------------------------------
    S3_DOCUMENTS_BUCKET: str = os.getenv("S3_DOCUMENTS_BUCKET", "")
    MAX_DOCUMENT_SIZE: int = _env_int("MAX_DOCUMENT_SIZE", 100 * 1024 * 1024)  # 100 MB

    # --- Media ----------------------------------------------------------------
    S3_MEDIA_BUCKET: str = os.getenv("S3_MEDIA_BUCKET", "")
    MAX_UPLOAD_SIZE: int = _env_int("MAX_UPLOAD_SIZE", 50 * 1024 * 1024)  # 50 MB

    # --- Billing (Stripe) -----------------------------------------------------
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_CONNECT_WEBHOOK_SECRET: str = os.getenv("STRIPE_CONNECT_WEBHOOK_SECRET", "")

    @property
    def IS_DEV(self) -> bool:
        return self.ENV == "development"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        # Runtime connection — RLS-enforced. In prod this connects as a NON-superuser
        # LOGIN role so row-level security actually isolates orgs (superusers bypass it).
        if url := os.getenv("DATABASE_URL"):
            return url
        return _build_db_url(driver="+psycopg")

    @property
    def ADMIN_DB_URL(self) -> str:
        # Sync URL for Alembic. Migrations run as a privileged role, outside RLS.
        if url := os.getenv("ADMIN_DATABASE_URL"):
            return url
        return _build_db_url(driver="+psycopg")


class TestConfig(Config):
    """Config for the pytest harness — points at a throwaway test database.

    `tests/fixtures/database.py` reset-migrates `ADMIN_DB_URL` (sync) and connects the
    suite as a non-superuser role so RLS actually isolates orgs. Override the URLs via
    `TEST_DATABASE_URL` / `TEST_ADMIN_DATABASE_URL` in CI.
    """

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        # Matches backend/docker-compose.dev.yml's `test-db` service (port 5435, db `houston`).
        return os.getenv(
            "TEST_DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5435/houston",
        )

    @property
    def ADMIN_DB_URL(self) -> str:
        return os.getenv("TEST_ADMIN_DATABASE_URL", self.ASYNC_DATABASE_URL)


def get_config() -> Config:
    """Resolve the active config: `TestConfig` under pytest, else `Config`."""
    if os.getenv("ENV") == "testing":
        return TestConfig()
    return Config()


config = get_config()
