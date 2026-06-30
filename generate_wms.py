"""Generate WMS inventory transactions from clean ERP orders in Postgres."""

from generator.main import generate_wms_transaction_data


def main() -> None:
    row_count = generate_wms_transaction_data()
    print(f"Generated WMS inventory transactions: {row_count} rows")


if __name__ == "__main__":
    main()
