from datetime import timedelta

import numpy as np
import pandas as pd

from generator.config.settings import NoiseSettings, ProductionOrderSettings
from generator.mes.noise import apply_production_order_noise
from generator.transactional.common import (
    generate_order_dates,
    generate_quantities,
    status_choices,
)
from generator.utils.ids import format_id


def _finished_good_ids(materials: pd.DataFrame) -> list[str]:
    finished_goods = materials.loc[materials["material_type"] == "FINISHED_GOOD", "material_id"]
    if finished_goods.empty:
        raise ValueError("No finished goods found in materials master data")
    return finished_goods.tolist()


def _plant_ids(plants: pd.DataFrame) -> list[str]:
    if plants.empty:
        raise ValueError("No plants found in plants master data")
    return plants["plant_id"].tolist()


def _actual_quantity(planned_quantity: int, status: str, rng: np.random.Generator) -> int:
    if status == "COMPLETED":
        variance = rng.uniform(0.85, 1.0)
        return max(1, int(round(planned_quantity * variance)))
    if status == "IN_PROGRESS":
        variance = rng.uniform(0.30, 0.80)
        return max(1, int(round(planned_quantity * variance)))
    return 0


def generate_production_orders(
    materials: pd.DataFrame,
    plants: pd.DataFrame,
    settings: ProductionOrderSettings,
    rng: np.random.Generator,
    noise_settings: NoiseSettings | None = None,
    *,
    id_start: int = 1,
) -> pd.DataFrame:
    material_ids = _finished_good_ids(materials)
    plant_ids = _plant_ids(plants)
    statuses, status_weights = status_choices(settings.status_weights)

    start_dates = generate_order_dates(
        settings.count,
        settings.resolved_start_date,
        settings.resolved_end_date,
        rng,
    )
    durations = rng.integers(
        settings.min_duration_days,
        settings.max_duration_days + 1,
        size=settings.count,
    )
    planned_quantities = generate_quantities(settings.count, rng)
    selected_plants = rng.choice(plant_ids, size=settings.count)
    selected_materials = rng.choice(material_ids, size=settings.count)
    selected_statuses = rng.choice(statuses, size=settings.count, p=status_weights)

    rows = []
    for index in range(settings.count):
        start_date = start_dates[index]
        end_date = start_date + timedelta(days=int(durations[index]))
        planned_quantity = planned_quantities[index]
        status = selected_statuses[index]
        rows.append(
            {
                "production_order_id": format_id("PR", id_start + index, 6),
                "plant_id": selected_plants[index],
                "material_id": selected_materials[index],
                "planned_quantity": planned_quantity,
                "actual_quantity": _actual_quantity(planned_quantity, status, rng),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "status": status,
            }
        )

    production_orders = pd.DataFrame(rows)
    if noise_settings is None:
        return production_orders

    return apply_production_order_noise(
        production_orders,
        materials,
        plants,
        noise_settings,
        rng,
    )
