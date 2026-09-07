"""Automated migration and schema rollback tests (DEV-003, DATA-001)."""

import os
from pathlib import Path

from sqlalchemy import create_engine, inspect

from alembic import command
from alembic.config import Config
from app.main import create_app


def get_alembic_config(db_url: str) -> Config:
    """Generate Alembic configuration targeting the test database."""
    ini_path = Path(__file__).parent.parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_empty_db_migrates_to_head_and_app_boots(tmp_path: Path) -> None:
    """Acceptance Criterion 1: Empty DB migrates to head and application boots."""
    db_file = tmp_path / "test_boot_migration.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    sync_db_url = f"sqlite:///{db_file}"

    os.environ["TOKI_DATABASE_URL"] = db_url
    try:
        cfg = get_alembic_config(db_url)

        # 1. Upgrade from empty DB to head
        command.upgrade(cfg, "head")

        # 2. Inspect created schema
        sync_engine = create_engine(sync_db_url)
        inspector = inspect(sync_engine)
        table_names = set(inspector.get_table_names())

        expected_tables = {
            "guardians",
            "children",
            "devices",
            "consents",
            "curriculum_versions",
            "curriculum_skills",
            "curriculum_items",
            "sessions",
            "turns",
            "attempts",
            "child_mastery",
            "mastery_history",
            "domain_events",
            "outbox_events",
            "version_metadata",
            "protocol_cursors",
            "alembic_version",
        }
        assert expected_tables.issubset(
            table_names
        ), f"Missing tables: {expected_tables - table_names}"
        sync_engine.dispose()

        # 3. Verify application boots with migrated DB
        app = create_app()
        assert "TOKI" in app.title
    finally:
        os.environ.pop("TOKI_DATABASE_URL", None)


def test_migration_and_rollback_cycle(tmp_path: Path) -> None:
    """Acceptance Criterion 5: Migration upgrade and downgrade cycle executes cleanly."""
    db_file = tmp_path / "test_rollback_cycle.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"
    sync_db_url = f"sqlite:///{db_file}"

    os.environ["TOKI_DATABASE_URL"] = db_url
    try:
        cfg = get_alembic_config(db_url)

        # 1. Upgrade to head
        command.upgrade(cfg, "head")
        sync_engine = create_engine(sync_db_url)
        inspector = inspect(sync_engine)
        assert "sessions" in inspector.get_table_names()
        assert "attempts" in inspector.get_table_names()
        sync_engine.dispose()

        # 2. Rollback to base
        command.downgrade(cfg, "base")
        sync_engine = create_engine(sync_db_url)
        inspector = inspect(sync_engine)
        remaining_tables = set(inspector.get_table_names()) - {"alembic_version"}
        assert len(remaining_tables) == 0, f"Tables not cleaned up on downgrade: {remaining_tables}"
        sync_engine.dispose()

        # 3. Re-upgrade to head
        command.upgrade(cfg, "head")
        sync_engine = create_engine(sync_db_url)
        inspector = inspect(sync_engine)
        assert "sessions" in inspector.get_table_names()
        assert "attempts" in inspector.get_table_names()
        sync_engine.dispose()
    finally:
        os.environ.pop("TOKI_DATABASE_URL", None)
