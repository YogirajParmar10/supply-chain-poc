import pandas as pd

from generator.config.settings import DatasetSizes
from generator.utils.ids import format_id

PLANT_NAMES: tuple[str, ...] = (
    "FlexiPack Birmingham Plant",
    "FlexiPack Rotterdam Plant",
)

PLANT_COUNTRIES: tuple[str, ...] = (
    "United Kingdom",
    "Netherlands",
)


def generate_plants(sizes: DatasetSizes) -> pd.DataFrame:
    rows = [
        {
            "plant_id": format_id("PL", index, 3),
            "plant_name": PLANT_NAMES[index - 1],
            "country": PLANT_COUNTRIES[index - 1],
        }
        for index in range(1, sizes.plants + 1)
    ]
    return pd.DataFrame(rows)
