import numpy as np
import pandas as pd

from generator.config.settings import NoiseSettings
from generator.mes.noise import apply_production_output_noise
from generator.utils.ids import format_id


def _positive_quantity(value: object) -> int | None:
    try:
        quantity = int(float(value))
    except (TypeError, ValueError):
        return None
    if quantity <= 0:
        return None
    return quantity


def _raw_material_ids(materials: pd.DataFrame) -> list[str]:
    raw_materials = materials.loc[materials["material_type"] == "RAW_MATERIAL", "material_id"]
    if raw_materials.empty:
        raise ValueError("No raw materials found in materials master data")
    return raw_materials.astype(str).tolist()


def _finished_good_ids(materials: pd.DataFrame) -> set[str]:
    finished_goods = materials.loc[materials["material_type"] == "FINISHED_GOOD", "material_id"]
    return set(finished_goods.astype(str).tolist())


def _input_quantity(output_quantity: int, rng: np.random.Generator) -> int:
    ratio = rng.uniform(0.35, 0.65)
    return max(1, int(round(output_quantity * ratio)))


def generate_production_output(
    production_orders: pd.DataFrame,
    materials: pd.DataFrame,
    rng: np.random.Generator,
    noise_settings: NoiseSettings | None = None,
    *,
    id_start: int = 1,
) -> pd.DataFrame:
    raw_material_ids = _raw_material_ids(materials)
    finished_good_ids = _finished_good_ids(materials)
    rows: list[dict[str, object]] = []
    sequence = id_start

    for _, order in production_orders.iterrows():
        production_order_id = order.get("production_order_id")
        output_material_id = order.get("material_id")
        output_quantity = _positive_quantity(order.get("actual_quantity"))

        if not production_order_id or not output_material_id or output_quantity is None:
            continue
        if str(output_material_id) not in finished_good_ids:
            continue

        rows.append(
            {
                "production_output_id": format_id("POUT", sequence, 6),
                "production_order_id": str(production_order_id),
                "input_material_id": str(rng.choice(raw_material_ids)),
                "input_quantity": _input_quantity(output_quantity, rng),
                "output_material_id": str(output_material_id),
                "output_quantity": output_quantity,
            }
        )
        sequence += 1

    production_output = pd.DataFrame(rows)
    if production_output.empty:
        return pd.DataFrame(
            columns=[
                "production_output_id",
                "production_order_id",
                "input_material_id",
                "input_quantity",
                "output_material_id",
                "output_quantity",
            ]
        )

    if noise_settings is None:
        return production_output

    return apply_production_output_noise(
        production_output,
        materials,
        noise_settings,
        rng,
    )
