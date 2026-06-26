import numpy as np
import pandas as pd

from generator.config.settings import DatasetSizes
from generator.utils.ids import format_id

CUSTOMER_NAMES: tuple[str, ...] = (
    "FreshBeverage Distributors",
    "PureSpring Water Co",
    "GreenHarvest Foods",
    "Metro Retail Group",
    "AquaLife Bottling",
    "Sunrise Dairy Products",
    "CleanHome Care Brands",
    "OceanBlue Seafood Packers",
    "VitalHealth Nutrition",
    "Urban Eats Catering",
    "FarmToTable Organics",
    "Peak Performance Sports Drinks",
    "BrightSmile Oral Care",
    "NatureScent Cosmetics",
    "QuickServe Restaurants",
    "Alpine Mineral Water",
    "Tropical Juice Works",
    "SafeChem Industrial Supplies",
    "FamilyPantry Grocers",
    "Elite Hospitality Group",
)

CUSTOMER_COUNTRIES: tuple[str, ...] = (
    "United Kingdom",
    "France",
    "Netherlands",
    "Germany",
    "Spain",
    "Italy",
    "Belgium",
    "Sweden",
    "Poland",
    "Ireland",
    "Austria",
    "Denmark",
    "Portugal",
    "Czech Republic",
    "Finland",
    "Norway",
    "Switzerland",
    "Hungary",
    "Romania",
    "Greece",
)


def generate_customers(sizes: DatasetSizes, rng: np.random.Generator) -> pd.DataFrame:
    country_pool = list(CUSTOMER_COUNTRIES)
    rng.shuffle(country_pool)
    selected_countries = country_pool[: sizes.customers]

    rows = [
        {
            "customer_id": format_id("CUS", index, 3),
            "customer_name": CUSTOMER_NAMES[index - 1],
            "country": selected_countries[index - 1],
        }
        for index in range(1, sizes.customers + 1)
    ]
    return pd.DataFrame(rows)
