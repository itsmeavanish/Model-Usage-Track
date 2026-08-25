"""Lightweight additive schema migrations for the dev workflow.

main.py creates tables via ``Base.metadata.create_all``, which only handles fresh
databases. These helpers add new columns to *existing* SQLite tables so that an
operator who upgrades the code and restarts does not have to wipe their data or
run Alembic by hand. Every check is additive and idempotent.
"""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def ensure_column(
    engine: AsyncEngine, table: str, column: str, type_ddl: str
) -> None:
    """Add ``column`` to ``table`` if it is not already present (SQLite only)."""
    async with engine.begin() as conn:
        rows = (
            await conn.execute(text(f"PRAGMA table_info({table})"))
        ).fetchall()
        if not rows:
            # Table does not exist yet; create_all will build it fresh.
            return
        existing = {r[1] for r in rows}
        if column in existing:
            return
        logger.info("Migrating: ADD COLUMN %s.%s %s", table, column, type_ddl)
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {type_ddl}"))


async def run_dev_migrations(engine: AsyncEngine) -> None:
    """Run all additive migrations for the current schema version."""
    await ensure_column(engine, "enriched_request", "provider", "VARCHAR")
    await ensure_column(engine, "quota_limit", "current_value", "FLOAT")
    await ensure_column(engine, "quota_limit", "limit_value", "FLOAT")
    await ensure_column(engine, "quota_limit", "remaining", "FLOAT")
