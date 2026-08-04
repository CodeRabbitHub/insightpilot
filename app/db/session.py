from sqlalchemy import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.catalog.sync import require_env


def database_url() -> URL:
    """The app-schema pool's connection URL, authenticated as POSTGRES_USER
    -- never OLIST_RO_USER. Built via URL.create() rather than raw string
    interpolation so a password containing a URL-reserved character
    (@, :, /, %, #) still parses correctly instead of silently
    mis-splitting host/db or failing auth. ARCHITECT.md's blast-radius
    isolation requires this pool and execute_sql()'s read-only asyncpg
    pool to stay separate, so this must never be reused for generated
    SQL."""
    return URL.create(
        "postgresql+asyncpg",
        username=require_env("POSTGRES_USER"),
        password=require_env("POSTGRES_PASSWORD"),
        host=require_env("POSTGRES_HOST"),
        port=int(require_env("POSTGRES_PORT")),
        database=require_env("POSTGRES_DB"),
    )


# NullPool: asyncpg connections are bound to the event loop that created
# them, and a pooled connection handed out under a *different* loop raises
# "another operation is in progress" / "Event loop is closed" -- which a
# real pool would otherwise do across this project's per-test-method event
# loops (unittest.IsolatedAsyncioTestCase) and, later, across process
# forks. NullPool opens a fresh connection per checkout instead, trading
# pooling's reuse for correctness across loops. Revisit before wiring this
# pool into a live request handler under uvicorn's single persistent
# event loop -- a real pool (e.g. AsyncAdaptedQueuePool) may be worth the
# connection-reuse win once cross-loop reuse in tests is no longer the
# constraint.
engine = create_async_engine(database_url(), poolclass=NullPool)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
