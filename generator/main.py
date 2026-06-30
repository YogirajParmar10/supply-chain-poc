from generator.config.settings import GeneratorConfig
from generator.master import (
    generate_customers,
    generate_materials,
    generate_plants,
    generate_suppliers,
    generate_warehouses,
)
from generator.transactional.purchase_orders import generate_purchase_orders
from generator.transactional.sales_orders import generate_sales_orders
from generator.utils.db import get_engine
from generator.utils.db_export import write_dataframe
from generator.utils.master_data import load_customers, load_materials, load_suppliers
from generator.utils.rng import create_rng


def generate_master_data(config: GeneratorConfig | None = None) -> dict[str, int]:
    config = config or GeneratorConfig()
    engine = get_engine()
    rng = create_rng(config.seed)

    plants = generate_plants(config.sizes)
    datasets = {
        "materials": generate_materials(config.sizes, rng),
        "suppliers": generate_suppliers(config.sizes, rng),
        "customers": generate_customers(config.sizes, rng),
        "plants": plants,
        "warehouses": generate_warehouses(config.sizes, plants, rng),
    }

    rows_written: dict[str, int] = {}
    for table_name, dataframe in datasets.items():
        rows_written[table_name] = write_dataframe(dataframe, table_name, engine)

    return rows_written


def generate_purchase_order_data(config: GeneratorConfig | None = None) -> int:
    config = config or GeneratorConfig()
    engine = get_engine()
    rng = create_rng(config.seed)

    materials = load_materials(engine)
    suppliers = load_suppliers(engine)
    purchase_orders = generate_purchase_orders(
        materials,
        suppliers,
        config.purchase_orders,
        rng,
        noise_settings=config.noise,
    )

    return write_dataframe(purchase_orders, "purchase_orders", engine)


def generate_sales_order_data(config: GeneratorConfig | None = None) -> int:
    config = config or GeneratorConfig()
    engine = get_engine()
    rng = create_rng(config.seed)

    materials = load_materials(engine)
    customers = load_customers(engine)
    sales_orders = generate_sales_orders(
        materials,
        customers,
        config.sales_orders,
        rng,
        noise_settings=config.noise,
    )

    return write_dataframe(sales_orders, "sales_orders", engine)


def main() -> None:
    config = GeneratorConfig()
    master_rows = generate_master_data(config)
    purchase_order_rows = generate_purchase_order_data(config)
    sales_order_rows = generate_sales_order_data(config)

    print(f"Generated data for {config.company_name}")
    for table_name, row_count in master_rows.items():
        print(f"  - {table_name}: {row_count} rows")
    print(f"  - purchase_orders: {purchase_order_rows} rows")
    print(f"  - sales_orders: {sales_order_rows} rows")


if __name__ == "__main__":
    main()
