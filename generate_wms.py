"""Generate WMS inventory transactions and inventory snapshot from ERP orders in Postgres."""

from generator.main import generate_wms_data


def main() -> None:
    wms_rows = generate_wms_data()
    print("Generated WMS data")
    print(f"  - inventory_transactions: {wms_rows['inventory_transactions']} rows")
    print(f"  - inventory: {wms_rows['inventory']} rows")


if __name__ == "__main__":
    main()
