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
    "Continental Beverage Partners",
    "Nordic Fresh Retail",
    "Mediterranean Foods Trading",
    "BudgetMart Wholesale",
    "PremiumPet Nutrition",
    "Coastal Seafood Markets",
    "Heritage Bakery Supplies",
    "Global Snack Distributors",
    "EcoClean Household Brands",
    "Summit Outdoor Retail",
    "CityFresh Convenience",
    "Wellness Pharmacy Chain",
    "Harvest Valley Co-op",
    "Royal Catering Services",
    "BlueRiver Cold Chain",
    "GoldenGrain Cereals",
    "Sparkling Springs Ltd",
    "Artisan Coffee Roasters",
    "KidsChoice Lunchbox Co",
    "Pacific Rim Foods",
    "Heartland Grocery Group",
    "Vineyard Select Wines",
    "SmartShelf Supermarkets",
    "GreenLeaf Plant-Based Foods",
    "Express Meal Solutions",
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
    "Slovakia",
    "Croatia",
    "Bulgaria",
    "Lithuania",
    "Latvia",
    "Estonia",
    "Slovenia",
    "Luxembourg",
    "Malta",
    "Cyprus",
    "Iceland",
    "Serbia",
    "Bosnia and Herzegovina",
    "North Macedonia",
    "Albania",
    "Montenegro",
    "Moldova",
    "Ukraine",
    "Belarus",
    "Georgia",
    "Armenia",
    "Azerbaijan",
    "Kazakhstan",
    "Uzbekistan",
    "Turkey",
)


def generate_customers(sizes: DatasetSizes, rng: np.random.Generator) -> pd.DataFrame:
    if sizes.customers > len(CUSTOMER_NAMES):
        raise ValueError(
            f"Requested {sizes.customers} customers but only {len(CUSTOMER_NAMES)} names are defined"
        )

    country_pool = list(CUSTOMER_COUNTRIES)
    rng.shuffle(country_pool)
    selected_countries = country_pool[: sizes.customers]
    active_flags = rng.random(sizes.customers) < sizes.active_partner_rate

    rows = [
        {
            "customer_id": format_id("CUS", index, 3),
            "customer_name": CUSTOMER_NAMES[index - 1],
            "country": selected_countries[index - 1],
            "active": bool(active_flags[index - 1]),
        }
        for index in range(1, sizes.customers + 1)
    ]
    return pd.DataFrame(rows)
