import numpy as np
import pandas as pd

from generator.config.settings import DatasetSizes
from generator.utils.ids import format_id

# Warehouse names are plant-specific; index order matches plant assignment below.
WAREHOUSE_DEFINITIONS: tuple[tuple[str, int], ...] = (
    ("Birmingham Raw Materials Warehouse", 0),
    ("Birmingham Finished Goods Warehouse", 0),
    ("Rotterdam Distribution Center", 1),
)


def generate_warehouses(
    sizes: DatasetSizes,
    plants: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    plant_ids = plants["plant_id"].tolist()
    if not plant_ids:
        raise ValueError("At least one plant is required to generate warehouses")

    rows = []
    for index in range(1, sizes.warehouses + 1):
        name, plant_index = WAREHOUSE_DEFINITIONS[index - 1]
        if plant_index >= len(plant_ids):
            plant_index = int(rng.integers(0, len(plant_ids)))

        rows.append(
            {
                "warehouse_id": format_id("WH", index, 3),
                "warehouse_name": name,
                "plant_id": plant_ids[plant_index],
            }
        )

    return pd.DataFrame(rows)
