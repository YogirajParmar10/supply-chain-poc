from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from generator.config.settings import PurchaseOrderSettings
from generator.utils.csv_export import write_csv
from generator.utils.ids import format_id

QUANTITY_RANGES: tuple[tuple[int, int], ...] = (
    (500, 2_000),
    (2_000, 10_000),
    (10_000, 50_000),
)


def _raw_material_ids(materials: pd.DataFrame) -> list[str]:
    raw_materials = materials.loc[materials["material_type"] == "RAW_MATERIAL", "material_id"]
    if raw_materials.empty:
        raise ValueError("No raw materials found in materials master data")
    return raw_materials.tolist()


def _supplier_ids(suppliers: pd.DataFrame) -> list[str]:
    if suppliers.empty:
        raise ValueError("No suppliers found in suppliers master data")
    return suppliers["supplier_id"].tolist()


def _status_choices(settings: PurchaseOrderSettings) -> tuple[list[str], list[float]]:
    statuses = [status for status, _ in settings.status_weights]
    weights = [weight for _, weight in settings.status_weights]
    return statuses, weights


def _generate_order_dates(
    count: int,
    start_date: date,
    end_date: date,
    rng: np.random.Generator,
) -> list[date]:
    start_ord = start_date.toordinal()
    end_ord = end_date.toordinal()
    day_offsets = rng.integers(0, end_ord - start_ord + 1, size=count)
    return [date.fromordinal(start_ord + int(offset)) for offset in day_offsets]


def _generate_quantities(count: int, rng: np.random.Generator) -> list[int]:
    tier_indices = rng.integers(0, len(QUANTITY_RANGES), size=count)
    quantities: list[int] = []
    for tier_index in tier_indices:
        low, high = QUANTITY_RANGES[int(tier_index)]
        quantities.append(int(rng.integers(low, high + 1)))
    return quantities


def generate_purchase_orders(
    materials: pd.DataFrame,
    suppliers: pd.DataFrame,
    settings: PurchaseOrderSettings,
    rng: np.random.Generator,
) -> pd.DataFrame:
    material_ids = _raw_material_ids(materials)
    supplier_ids = _supplier_ids(suppliers)
    statuses, status_weights = _status_choices(settings)

    order_dates = _generate_order_dates(
        settings.count,
        settings.resolved_start_date,
        settings.resolved_end_date,
        rng,
    )
    lead_times = rng.integers(
        settings.min_lead_time_days,
        settings.max_lead_time_days + 1,
        size=settings.count,
    )
    quantities = _generate_quantities(settings.count, rng)
    selected_suppliers = rng.choice(supplier_ids, size=settings.count)
    selected_materials = rng.choice(material_ids, size=settings.count)
    selected_statuses = rng.choice(statuses, size=settings.count, p=status_weights)

    rows = []
    for index in range(settings.count):
        order_date = order_dates[index]
        expected_delivery_date = order_date + timedelta(days=int(lead_times[index]))
        rows.append(
            {
                "purchase_order_id": format_id("PO", index + 1, 6),
                "order_date": order_date.isoformat(),
                "supplier_id": selected_suppliers[index],
                "material_id": selected_materials[index],
                "quantity": quantities[index],
                "expected_delivery_date": expected_delivery_date.isoformat(),
                "status": selected_statuses[index],
            }
        )

    return pd.DataFrame(rows)


def purchase_order_batch_filename(order_date: date) -> str:
    return f"purchase_orders_{order_date.strftime('%Y%m%d')}.csv"


def write_purchase_order_batches(purchase_orders: pd.DataFrame, output_dir: Path) -> list[Path]:
    if purchase_orders.empty:
        return []

    grouped_orders = purchase_orders.groupby("order_date", sort=True)
    written_paths: list[Path] = []
    for order_date, daily_orders in grouped_orders:
        filename = purchase_order_batch_filename(date.fromisoformat(str(order_date)))
        path = output_dir / filename
        write_csv(daily_orders.reset_index(drop=True), path)
        written_paths.append(path)

    return written_paths
