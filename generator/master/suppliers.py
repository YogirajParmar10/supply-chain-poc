import numpy as np
import pandas as pd

from generator.config.settings import DatasetSizes
from generator.utils.ids import format_id

SUPPLIER_NAMES: tuple[str, ...] = (
    "ChemResin Global GmbH",
    "Pacific Polymers Ltd",
    "Nordic Masterbatch AS",
    "SinoPlast Materials Co",
    "Gulf Petrochemical Trading",
    "Atlantic Additives Inc",
    "EuroCap Manufacturing SA",
    "LabelTech Solutions BV",
    "PackRight Cartons LLC",
    "Prime Resin Partners",
    "Baltic PET Compounds",
    "Iberian Plastics Supply",
    "Danube Chemical Trading",
    "Scandinavian Film Extrusion",
    "Rhine Valley Resins",
    "Adriatic Packaging Materials",
    "BlackSea Polymer Exports",
    "Alpine Foil & Laminate AG",
    "Benelux Closure Systems",
    "Celtic Corrugated Board",
    "Mediterranean Ink Solutions",
    "Central Europe Adhesives",
    "Nordic Recycled PET Co",
    "AsiaPac Masterbatch Hub",
    "Americas Resin Brokers",
)

SUPPLIER_COUNTRIES: tuple[str, ...] = (
    "Germany",
    "Singapore",
    "Norway",
    "China",
    "United Arab Emirates",
    "United States",
    "France",
    "Netherlands",
    "United Kingdom",
    "India",
    "Poland",
    "Spain",
    "Romania",
    "Sweden",
    "Belgium",
    "Italy",
    "Turkey",
    "Switzerland",
    "Czech Republic",
    "Ireland",
    "Portugal",
    "Hungary",
    "Denmark",
    "South Korea",
    "Brazil",
)


def generate_suppliers(sizes: DatasetSizes, rng: np.random.Generator) -> pd.DataFrame:
    if sizes.suppliers > len(SUPPLIER_NAMES):
        raise ValueError(
            f"Requested {sizes.suppliers} suppliers but only {len(SUPPLIER_NAMES)} names are defined"
        )

    country_pool = list(SUPPLIER_COUNTRIES)
    rng.shuffle(country_pool)
    selected_countries = country_pool[: sizes.suppliers]
    active_flags = rng.random(sizes.suppliers) < sizes.active_partner_rate

    rows = [
        {
            "supplier_id": format_id("SUP", index, 3),
            "supplier_name": SUPPLIER_NAMES[index - 1],
            "country": selected_countries[index - 1],
            "active": bool(active_flags[index - 1]),
        }
        for index in range(1, sizes.suppliers + 1)
    ]
    return pd.DataFrame(rows)


def main() -> None:
    from generator.config.settings import GeneratorConfig
    from generator.utils.db import get_engine
    from generator.utils.db_export import write_dataframe
    from generator.utils.rng import create_rng

    config = GeneratorConfig()
    engine = get_engine()
    rng = create_rng(config.seed)

    suppliers = generate_suppliers(config.sizes, rng)
    rows_written = write_dataframe(suppliers, "suppliers", engine)

    print(f"Wrote {rows_written} suppliers to database")
    print(suppliers.to_string(index=False))


if __name__ == "__main__":
    main()
