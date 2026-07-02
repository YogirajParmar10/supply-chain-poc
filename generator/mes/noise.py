import numpy as np
import pandas as pd

from generator.config.settings import NoiseSettings
from generator.transactional.noise import (
    BAD_DATE_FORMATS,
    _append_duplicates,
    _apply_null,
    _apply_nulls,
    _apply_whitespace,
    _fake_id,
    _pick_indices,
    sanitize_material_ids,
)

INVALID_PRODUCTION_STATUSES: tuple[str, ...] = (
    "COMPLETD",
    "IN_PROGRESS ",
    "planned",
    "RUNNING",
    "COMPLETE",
    "",
)


def _invalid_end_date(start_date_value: object) -> str:
    try:
        from datetime import date, timedelta

        start_date = date.fromisoformat(str(start_date_value)[:10])
        return (start_date - timedelta(days=7)).isoformat()
    except ValueError:
        return "2020-01-01"


def apply_production_order_noise(
    production_orders: pd.DataFrame,
    materials: pd.DataFrame,
    _plants: pd.DataFrame,
    settings: NoiseSettings,
    rng: np.random.Generator,
) -> pd.DataFrame:
    if not settings.enabled or production_orders.empty:
        return production_orders

    df = production_orders.copy()
    noisy_indices = _pick_indices(len(df), settings.row_noise_rate, rng)
    for index in noisy_indices:
        noise_type = int(rng.integers(0, 8))
        if noise_type == 0:
            df.at[index, "plant_id"] = _fake_id("PL", rng)
        elif noise_type == 1:
            _apply_null(df, index, "material_id")
        elif noise_type == 2:
            _apply_nulls(
                df,
                index,
                ["plant_id", "start_date", "planned_quantity", "actual_quantity"],
                rng,
            )
        elif noise_type == 3:
            df.at[index, "end_date"] = _invalid_end_date(df.at[index, "start_date"])
        elif noise_type == 4:
            df.at[index, "status"] = str(rng.choice(INVALID_PRODUCTION_STATUSES))
        elif noise_type == 5:
            df.at[index, "planned_quantity"] = int(rng.choice([0, -1, -100, 9_999_999]))
        elif noise_type == 6:
            df.at[index, "plant_id"] = _apply_whitespace(str(df.at[index, "plant_id"]))
        elif noise_type == 7:
            df.at[index, "start_date"] = str(rng.choice(BAD_DATE_FORMATS))

    allowed_material_ids = set(
        materials.loc[materials["material_type"] == "FINISHED_GOOD", "material_id"].astype(str)
    )
    return _append_duplicates(
        sanitize_material_ids(df, allowed_material_ids),
        settings.duplicate_rate,
        rng,
    )


def _sanitize_production_output_materials(
    production_output: pd.DataFrame,
    raw_material_ids: set[str],
    finished_good_ids: set[str],
) -> pd.DataFrame:
    sanitized = production_output.copy()

    for index, row in sanitized.iterrows():
        input_material_id = row.get("input_material_id")
        if input_material_id is None or (isinstance(input_material_id, float) and pd.isna(input_material_id)):
            sanitized.at[index, "input_material_id"] = None
        else:
            material_id = str(input_material_id).strip()
            if not material_id or material_id not in raw_material_ids:
                sanitized.at[index, "input_material_id"] = None
            else:
                sanitized.at[index, "input_material_id"] = material_id

        output_material_id = row.get("output_material_id")
        if output_material_id is None or (
            isinstance(output_material_id, float) and pd.isna(output_material_id)
        ):
            sanitized.at[index, "output_material_id"] = None
        else:
            material_id = str(output_material_id).strip()
            if not material_id or material_id not in finished_good_ids:
                sanitized.at[index, "output_material_id"] = None
            else:
                sanitized.at[index, "output_material_id"] = material_id

    return sanitized


def apply_production_output_noise(
    production_output: pd.DataFrame,
    materials: pd.DataFrame,
    settings: NoiseSettings,
    rng: np.random.Generator,
) -> pd.DataFrame:
    if not settings.enabled or production_output.empty:
        return production_output

    df = production_output.copy()
    finished_good_ids = set(
        materials.loc[materials["material_type"] == "FINISHED_GOOD", "material_id"].astype(str)
    )
    raw_material_ids = set(
        materials.loc[materials["material_type"] == "RAW_MATERIAL", "material_id"].astype(str)
    )

    noisy_indices = _pick_indices(len(df), settings.row_noise_rate, rng)
    for index in noisy_indices:
        noise_type = int(rng.integers(0, 8))
        if noise_type == 0:
            df.at[index, "production_order_id"] = _fake_id("PR", rng)
        elif noise_type == 1:
            _apply_null(df, index, "input_material_id")
        elif noise_type == 2:
            _apply_null(df, index, "output_material_id")
        elif noise_type == 3:
            _apply_nulls(
                df,
                index,
                ["input_quantity", "output_quantity", "production_order_id"],
                rng,
            )
        elif noise_type == 4 and finished_good_ids:
            df.at[index, "input_material_id"] = str(rng.choice(list(finished_good_ids)))
        elif noise_type == 5 and raw_material_ids:
            df.at[index, "output_material_id"] = str(rng.choice(list(raw_material_ids)))
        elif noise_type == 6:
            df.at[index, "input_quantity"] = int(rng.choice([0, -1, -50, 9_999_999]))
        elif noise_type == 7:
            df.at[index, "production_order_id"] = _apply_whitespace(
                str(df.at[index, "production_order_id"])
            )

    return _append_duplicates(
        _sanitize_production_output_materials(df, raw_material_ids, finished_good_ids),
        settings.duplicate_rate,
        rng,
    )
