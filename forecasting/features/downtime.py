"""Ensure machine_downtime exists in public and generate multi-year history."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from forecasting.config import ForecastConfig, DEFAULT_CONFIG
from generator.config.settings import GeneratorConfig, MachineDowntimeSettings, NoiseSettings
from generator.main import generate_machine_downtime_data
from generator.utils.migrations import ensure_migrations_applied


def ensure_machine_downtime_table(engine: Engine) -> None:
    """Apply project migrations so public.machine_downtime exists."""
    ensure_migrations_applied()
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'machine_downtime'
                """
            )
        ).scalar()
    if not exists:
        raise RuntimeError(
            "public.machine_downtime is missing after migrations. "
            "Check migrations/006_mes_machine_downtime.sql"
        )


def _existing_downtime_count(engine: Engine) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(text("SELECT COUNT(*) FROM public.machine_downtime")).scalar() or 0
        )


def generate_forecast_downtime(
    engine: Engine,
    config: ForecastConfig = DEFAULT_CONFIG,
    *,
    force: bool = False,
) -> int:
    """
    Generate machine downtime spanning the sales history window.

    Skips generation when rows already exist unless force=True.
    """
    ensure_machine_downtime_table(engine)
    existing = _existing_downtime_count(engine)
    if existing > 0 and not force:
        print(f"machine_downtime already has {existing} rows; skipping generation")
        return 0

    if force and existing > 0:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE public.machine_downtime RESTART IDENTITY"))
        print(f"Truncated existing machine_downtime ({existing} rows)")

    downtime_settings = MachineDowntimeSettings(
        count=config.downtime_count,
        start_date=config.downtime_start_date,
        end_date=config.downtime_end_date,
    )
    gen_config = GeneratorConfig(
        seed=config.downtime_seed,
        machine_downtime=downtime_settings,
        noise=NoiseSettings(enabled=False),
    )
    rows = generate_machine_downtime_data(gen_config)
    print(
        f"Generated {rows} machine_downtime rows "
        f"({config.downtime_start_date} → {config.downtime_end_date})"
    )
    return rows
