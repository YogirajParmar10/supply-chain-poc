"""Generate WMS inventory transactions and daily inventory snapshots from ERP orders in Postgres."""

from generator.main import generate_wms_data


def main() -> None:
    wms_rows = generate_wms_data()
    print("Generated WMS data")
    print(f"  - inventory_transactions: {wms_rows.get('inventory_transactions', 0)} rows")
    print(f"  - transaction days: {wms_rows.get('transaction_days', 0)}")
    print(f"  - transaction csv days: {wms_rows.get('transaction_csv_days', 0)}")
    print(f"  - inventory: {wms_rows.get('inventory', 0)} rows")
    print(f"  - inventory days: {wms_rows.get('inventory_days', 0)}")


if __name__ == "__main__":
    main()
