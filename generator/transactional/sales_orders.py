from datetime import date, timedelta

import numpy as np
import pandas as pd

from generator.config.settings import SalesOrderSettings, NoiseSettings
from generator.transactional.common import (
    generate_order_dates,
    generate_quantities,
    status_choices,
)
from generator.transactional.noise import apply_sales_order_noise
from generator.utils.ids import format_id


def _finished_good_ids(materials: pd.DataFrame) -> list[str]:
    finished_goods = materials.loc[materials["material_type"] == "FINISHED_GOOD", "material_id"]
    if finished_goods.empty:
        raise ValueError("No finished goods found in materials master data")
    return finished_goods.tolist()


def _customer_ids(customers: pd.DataFrame) -> list[str]:
    if customers.empty:
        raise ValueError("No customers found in customers master data")
    return customers["customer_id"].tolist()


def generate_sales_orders(
    materials: pd.DataFrame,
    customers: pd.DataFrame,
    settings: SalesOrderSettings,
    rng: np.random.Generator,
    noise_settings: NoiseSettings | None = None,
    *,
    id_start: int = 1,
) -> pd.DataFrame:
    material_ids = _finished_good_ids(materials)
    customer_ids = _customer_ids(customers)
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
    selected_customers = rng.choice(customer_ids, size=settings.count)
    selected_materials = rng.choice(material_ids, size=settings.count)
    selected_statuses = rng.choice(statuses, size=settings.count, p=status_weights)

    rows = []
    for index in range(settings.count):
        order_date = order_dates[index]
        requested_delivery_date = order_date + timedelta(days=int(lead_times[index]))
        rows.append(
            {
                "sales_order_id": format_id("SO", id_start + index, 6),
                "order_date": order_date.isoformat(),
                "customer_id": selected_customers[index],
                "material_id": selected_materials[index],
                "quantity": quantities[index],
                "requested_delivery_date": requested_delivery_date.isoformat(),
                "status": selected_statuses[index],
            }
        )

    sales_orders = pd.DataFrame(rows)
    if noise_settings is None:
        return sales_orders

    return apply_sales_order_noise(
        sales_orders,
        materials,
        customers,
        noise_settings,
        rng,
    )
