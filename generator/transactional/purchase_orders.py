from datetime import date, timedelta

import numpy as np
import pandas as pd

from generator.config.settings import PurchaseOrderSettings, NoiseSettings
from generator.transactional.common import (
    generate_order_dates,
    generate_quantities,
    status_choices,
)
from generator.transactional.noise import apply_purchase_order_noise
from generator.utils.ids import format_id


def _raw_material_ids(materials: pd.DataFrame) -> list[str]:
    raw_materials = materials.loc[materials["material_type"] == "RAW_MATERIAL", "material_id"]
    if raw_materials.empty:
        raise ValueError("No raw materials found in materials master data")
    return raw_materials.tolist()


def _supplier_ids(suppliers: pd.DataFrame) -> list[str]:
    if suppliers.empty:
        raise ValueError("No suppliers found in suppliers master data")
    return suppliers["supplier_id"].tolist()


def generate_purchase_orders(
    materials: pd.DataFrame,
    suppliers: pd.DataFrame,
    settings: PurchaseOrderSettings,
    rng: np.random.Generator,
    noise_settings: NoiseSettings | None = None,
    *,
    id_start: int = 1,
) -> pd.DataFrame:
    material_ids = _raw_material_ids(materials)
    supplier_ids = _supplier_ids(suppliers)
    statuses, status_weights = status_choices(settings.status_weights)

    order_dates = generate_order_dates(
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
    quantities = generate_quantities(settings.count, rng)
    selected_suppliers = rng.choice(supplier_ids, size=settings.count)
    selected_materials = rng.choice(material_ids, size=settings.count)
    selected_statuses = rng.choice(statuses, size=settings.count, p=status_weights)

    rows = []
    for index in range(settings.count):
        order_date = order_dates[index]
        expected_delivery_date = order_date + timedelta(days=int(lead_times[index]))
        rows.append(
            {
                "purchase_order_id": format_id("PO", id_start + index, 6),
                "order_date": order_date.isoformat(),
                "supplier_id": selected_suppliers[index],
                "material_id": selected_materials[index],
                "quantity": quantities[index],
                "expected_delivery_date": expected_delivery_date.isoformat(),
                "status": selected_statuses[index],
            }
        )

    purchase_orders = pd.DataFrame(rows)
    if noise_settings is None:
        return purchase_orders

    return apply_purchase_order_noise(
        purchase_orders,
        materials,
        suppliers,
        noise_settings,
        rng,
    )
