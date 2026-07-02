from generator.config.settings import GeneratorConfig
from generator.master import (
    generate_customers,
    generate_materials,
    generate_plants,
    generate_suppliers,
    generate_warehouses,
)
from generator.mes.production_orders import generate_production_orders
from generator.mes.production_output import generate_production_output
from generator.transactional.purchase_orders import generate_purchase_orders
from generator.transactional.sales_orders import generate_sales_orders
from generator.utils.db import get_engine
from generator.utils.db_export import write_dataframe
from generator.utils.migrations import ensure_migrations_applied
from generator.utils.master_data import (
    load_clean_completed_production_orders,
    load_clean_delivered_purchase_orders,
    load_clean_production_output,
    load_clean_shipped_sales_orders,
    load_customers,
    load_materials,
    load_plants,
    load_suppliers,
    load_warehouses,
)
from generator.utils.order_ids import resolve_next_id_start
from generator.wms.inventory import refresh_inventory_snapshot
from generator.wms.inventory_transactions import generate_inventory_transactions
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
    id_start = resolve_next_id_start(engine, "purchase_orders", "purchase_order_id", "PO")
    purchase_orders = generate_purchase_orders(
        materials,
        suppliers,
        config.purchase_orders,
        rng,
        noise_settings=config.noise,
        id_start=id_start,
    )

    rows_written = write_dataframe(purchase_orders, "purchase_orders", engine)
    last_id = id_start + config.purchase_orders.count - 1
    print(f"  purchase_order_id range: PO{id_start:06d} – PO{last_id:06d}")
    return rows_written


def generate_sales_order_data(config: GeneratorConfig | None = None) -> int:
    config = config or GeneratorConfig()
    engine = get_engine()
    rng = create_rng(config.seed)

    materials = load_materials(engine)
    customers = load_customers(engine)
    id_start = resolve_next_id_start(engine, "sales_orders", "sales_order_id", "SO")
    sales_orders = generate_sales_orders(
        materials,
        customers,
        config.sales_orders,
        rng,
        noise_settings=config.noise,
        id_start=id_start,
    )

    rows_written = write_dataframe(sales_orders, "sales_orders", engine)
    last_id = id_start + config.sales_orders.count - 1
    print(f"  sales_order_id range: SO{id_start:06d} – SO{last_id:06d}")
    return rows_written


def generate_production_order_data(config: GeneratorConfig | None = None) -> int:
    config = config or GeneratorConfig()
    engine = get_engine()
    rng = create_rng(config.seed)

    materials = load_materials(engine)
    plants = load_plants(engine)
    id_start = resolve_next_id_start(
        engine, "production_orders", "production_order_id", "PR"
    )
    production_orders = generate_production_orders(
        materials,
        plants,
        config.production_orders,
        rng,
        noise_settings=config.noise,
        id_start=id_start,
    )

    rows_written = write_dataframe(production_orders, "production_orders", engine)
    last_id = id_start + config.production_orders.count - 1
    print(f"  production_order_id range: PR{id_start:06d} – PR{last_id:06d}")
    return rows_written


def generate_production_output_data(config: GeneratorConfig | None = None) -> int:
    config = config or GeneratorConfig()
    engine = get_engine()
    rng = create_rng(config.seed)

    materials = load_materials(engine)
    completed_production_orders = load_clean_completed_production_orders(engine)
    id_start = resolve_next_id_start(
        engine, "production_output", "production_output_id", "POUT"
    )
    production_output = generate_production_output(
        completed_production_orders,
        materials,
        rng,
        noise_settings=config.noise,
        id_start=id_start,
    )

    rows_written = write_dataframe(production_output, "production_output", engine)
    if rows_written:
        last_id = id_start + rows_written - 1
        print(f"  production_output_id range: POUT{id_start:06d} – POUT{last_id:06d}")
        print(f"  production output rows linked to completed orders: {rows_written}")
    return rows_written


def generate_wms_transaction_data(config: GeneratorConfig | None = None) -> int:
    config = config or GeneratorConfig()
    engine = get_engine()

    purchase_orders = load_clean_delivered_purchase_orders(engine)
    sales_orders = load_clean_shipped_sales_orders(engine)
    production_output = load_clean_production_output(engine)
    materials = load_materials(engine)
    warehouses = load_warehouses(engine)
    id_start = resolve_next_id_start(
        engine, "inventory_transactions", "transaction_id", "IT"
    )

    inventory_transactions = generate_inventory_transactions(
        purchase_orders,
        sales_orders,
        production_output,
        materials,
        warehouses,
        id_start=id_start,
    )

    rows_written = write_dataframe(inventory_transactions, "inventory_transactions", engine)
    if rows_written:
        last_id = id_start + rows_written - 1
        goods_receipts = len(
            inventory_transactions[inventory_transactions["transaction_type"] == "GOODS_RECEIPT"]
        )
        sales_shipments = len(
            inventory_transactions[inventory_transactions["transaction_type"] == "SALES_SHIPMENT"]
        )
        production_consumptions = len(
            inventory_transactions[
                inventory_transactions["transaction_type"] == "PRODUCTION_CONSUMPTION"
            ]
        )
        production_receipts = len(
            inventory_transactions[
                inventory_transactions["transaction_type"] == "PRODUCTION_RECEIPT"
            ]
        )
        print(f"  inventory_transaction_id range: IT{id_start:06d} – IT{last_id:06d}")
        print(f"  goods receipts linked to purchase orders: {goods_receipts}")
        print(f"  sales shipments linked to sales orders: {sales_shipments}")
        print(f"  production consumptions linked to production output: {production_consumptions}")
        print(f"  production receipts linked to production output: {production_receipts}")
    return rows_written


def generate_wms_inventory_data(config: GeneratorConfig | None = None) -> int:
    config = config or GeneratorConfig()
    engine = get_engine()

    rows_written = refresh_inventory_snapshot(engine)
    print(f"  inventory snapshot rows: {rows_written}")
    return rows_written


def generate_wms_data(config: GeneratorConfig | None = None) -> dict[str, int]:
    transaction_rows = generate_wms_transaction_data(config)
    inventory_rows = generate_wms_inventory_data(config)
    return {
        "inventory_transactions": transaction_rows,
        "inventory": inventory_rows,
    }


def main() -> None:
    config = GeneratorConfig()

    applied_migrations = ensure_migrations_applied()
    if applied_migrations:
        print("Applied pending database migrations:")
        for migration_name in applied_migrations:
            print(f"  - {migration_name}")

    master_rows = generate_master_data(config)
    purchase_order_rows = generate_purchase_order_data(config)
    sales_order_rows = generate_sales_order_data(config)
    production_order_rows = generate_production_order_data(config)
    production_output_rows = generate_production_output_data(config)
    wms_rows = generate_wms_data(config)

    print(f"Generated data for {config.company_name}")
    for table_name, row_count in master_rows.items():
        print(f"  - {table_name}: {row_count} rows")
    print(f"  - purchase_orders: {purchase_order_rows} rows")
    print(f"  - sales_orders: {sales_order_rows} rows")
    print(f"  - production_orders: {production_order_rows} rows")
    print(f"  - production_output: {production_output_rows} rows")
    print(f"  - inventory_transactions: {wms_rows['inventory_transactions']} rows")
    print(f"  - inventory: {wms_rows['inventory']} rows")


if __name__ == "__main__":
    main()
