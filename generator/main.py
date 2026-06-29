from pathlib import Path

from generator.config.settings import GeneratorConfig
from generator.master import (
    generate_customers,
    generate_materials,
    generate_plants,
    generate_suppliers,
    generate_warehouses,
)
from generator.transactional.purchase_orders import (
    generate_purchase_orders,
    write_purchase_order_batches,
)
from generator.utils.csv_export import write_csv
from generator.utils.master_data import load_materials, load_suppliers
from generator.utils.rng import create_rng


def generate_master_data(config: GeneratorConfig | None = None) -> dict[str, Path]:
    config = config or GeneratorConfig()
    output_dir = config.erp_output_dir
    rng = create_rng(config.seed)

    plants = generate_plants(config.sizes)
    datasets = {
        "materials.csv": generate_materials(config.sizes, rng),
        "suppliers.csv": generate_suppliers(config.sizes, rng),
        "customers.csv": generate_customers(config.sizes, rng),
        "plants.csv": plants,
        "warehouses.csv": generate_warehouses(config.sizes, plants, rng),
    }

    written_paths: dict[str, Path] = {}
    for filename, dataframe in datasets.items():
        path = output_dir / filename
        write_csv(dataframe, path)
        written_paths[filename] = path

    return written_paths


def generate_purchase_order_data(config: GeneratorConfig | None = None) -> list[Path]:
    config = config or GeneratorConfig()
    rng = create_rng(config.seed)

    materials = load_materials(config.erp_output_dir)
    suppliers = load_suppliers(config.erp_output_dir)
    purchase_orders = generate_purchase_orders(
        materials,
        suppliers,
        config.purchase_orders,
        rng,
    )

    return write_purchase_order_batches(purchase_orders, config.erp_output_dir)


def main() -> None:
    config = GeneratorConfig()
    written_paths = generate_master_data(config)
    purchase_order_paths = generate_purchase_order_data(config)

    print(f"Generated data for {config.company_name}")
    for filename, path in written_paths.items():
        print(f"  - {path}")
    for path in purchase_order_paths:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
