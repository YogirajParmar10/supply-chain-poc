from datetime import date, timedelta

import numpy as np
import pandas as pd

from generator.config.settings import NoiseSettings

INVALID_PURCHASE_STATUSES: tuple[str, ...] = (
    "DELIVERD",
    "CONFIRMED ",  # trailing space
    "confirmed",
    "PENDING",
    "SHIPPED",
    "",
)

INVALID_SALES_STATUSES: tuple[str, ...] = (
    "DELIVERD",
    "Shipped",
    "CONFIRMED ",
    "pending",
    "INVOICED",
    "",
)

BAD_DATE_FORMATS: tuple[str, ...] = (
    "15/06/2025",
    "2025-06-15T00:00:00",
    "15-Jun-2025",
    "invalid-date",
    "",
)


def _pick_indices(count: int, rate: float, rng: np.random.Generator) -> np.ndarray:
    if count == 0 or rate <= 0:
        return np.array([], dtype=int)
    noise_count = max(1, int(round(count * rate)))
    noise_count = min(noise_count, count)
    return rng.choice(count, size=noise_count, replace=False)


def _fake_id(prefix: str, rng: np.random.Generator) -> str:
    return f"{prefix}{int(rng.integers(900, 999)):03d}"


def _apply_nulls(df: pd.DataFrame, index: int, columns: list[str], rng: np.random.Generator) -> None:
    column = str(rng.choice(columns))
    df.at[index, column] = None


def _apply_whitespace(value: str) -> str:
    return f" {value} "


def _invalid_delivery_date(order_date_value: object, rng: np.random.Generator) -> str:
    try:
        order_date = date.fromisoformat(str(order_date_value)[:10])
        return (order_date - timedelta(days=int(rng.integers(1, 14)))).isoformat()
    except ValueError:
        return "2020-01-01"


def _append_duplicates(df: pd.DataFrame, rate: float, rng: np.random.Generator) -> pd.DataFrame:
    duplicate_count = max(0, int(round(len(df) * rate)))
    if duplicate_count == 0:
        return df

    duplicate_indices = rng.choice(len(df), size=duplicate_count, replace=True)
    duplicates = df.iloc[duplicate_indices].copy()
    return pd.concat([df, duplicates], ignore_index=True)


def apply_purchase_order_noise(
    purchase_orders: pd.DataFrame,
    materials: pd.DataFrame,
    _suppliers: pd.DataFrame,
    settings: NoiseSettings,
    rng: np.random.Generator,
) -> pd.DataFrame:
    if not settings.enabled or purchase_orders.empty:
        return purchase_orders

    df = purchase_orders.copy()
    wrong_material_ids = materials.loc[
        materials["material_type"] == "FINISHED_GOOD", "material_id"
    ].tolist()

    noisy_indices = _pick_indices(len(df), settings.row_noise_rate, rng)
    for index in noisy_indices:
        noise_type = int(rng.integers(0, 9))
        if noise_type == 0:
            df.at[index, "supplier_id"] = _fake_id("SUP", rng)
        elif noise_type == 1 and wrong_material_ids:
            df.at[index, "material_id"] = str(rng.choice(wrong_material_ids))
        elif noise_type == 2:
            df.at[index, "material_id"] = _fake_id("RM", rng)
        elif noise_type == 3:
            _apply_nulls(
                df,
                index,
                ["supplier_id", "material_id", "order_date", "quantity"],
                rng,
            )
        elif noise_type == 4:
            df.at[index, "expected_delivery_date"] = _invalid_delivery_date(
                df.at[index, "order_date"], rng
            )
        elif noise_type == 5:
            df.at[index, "status"] = str(rng.choice(INVALID_PURCHASE_STATUSES))
        elif noise_type == 6:
            df.at[index, "quantity"] = int(rng.choice([0, -1, -50, 9_999_999]))
        elif noise_type == 7:
            df.at[index, "supplier_id"] = _apply_whitespace(str(df.at[index, "supplier_id"]))
        elif noise_type == 8:
            df.at[index, "order_date"] = str(rng.choice(BAD_DATE_FORMATS))

    return _append_duplicates(df, settings.duplicate_rate, rng)


def apply_sales_order_noise(
    sales_orders: pd.DataFrame,
    materials: pd.DataFrame,
    _customers: pd.DataFrame,
    settings: NoiseSettings,
    rng: np.random.Generator,
) -> pd.DataFrame:
    if not settings.enabled or sales_orders.empty:
        return sales_orders

    df = sales_orders.copy()
    wrong_material_ids = materials.loc[
        materials["material_type"] == "RAW_MATERIAL", "material_id"
    ].tolist()

    noisy_indices = _pick_indices(len(df), settings.row_noise_rate, rng)
    for index in noisy_indices:
        noise_type = int(rng.integers(0, 9))
        if noise_type == 0:
            df.at[index, "customer_id"] = _fake_id("CUS", rng)
        elif noise_type == 1 and wrong_material_ids:
            df.at[index, "material_id"] = str(rng.choice(wrong_material_ids))
        elif noise_type == 2:
            df.at[index, "material_id"] = _fake_id("FG", rng)
        elif noise_type == 3:
            _apply_nulls(
                df,
                index,
                ["customer_id", "material_id", "order_date", "quantity"],
                rng,
            )
        elif noise_type == 4:
            df.at[index, "requested_delivery_date"] = _invalid_delivery_date(
                df.at[index, "order_date"], rng
            )
        elif noise_type == 5:
            df.at[index, "status"] = str(rng.choice(INVALID_SALES_STATUSES))
        elif noise_type == 6:
            df.at[index, "quantity"] = int(rng.choice([0, -1, -25, 9_999_999]))
        elif noise_type == 7:
            df.at[index, "customer_id"] = _apply_whitespace(str(df.at[index, "customer_id"]))
        elif noise_type == 8:
            df.at[index, "order_date"] = str(rng.choice(BAD_DATE_FORMATS))

    return _append_duplicates(df, settings.duplicate_rate, rng)
