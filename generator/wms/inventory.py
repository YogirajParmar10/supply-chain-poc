import pandas as pd
from sqlalchemy.engine import Engine

from generator.wms.inventory_transactions import (
    ISSUE_TRANSACTION_TYPES,
    RECEIPT_TRANSACTION_TYPES,
)


def _positive_quantity(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def generate_inventory(inventory_transactions: pd.DataFrame) -> pd.DataFrame:
    if inventory_transactions.empty:
        return pd.DataFrame(columns=["warehouse_id", "material_id", "quantity"])

    balances: dict[tuple[str, str], int] = {}

    for _, transaction in inventory_transactions.iterrows():
        warehouse_id = transaction.get("warehouse_id")
        material_id = transaction.get("material_id")
        transaction_type = transaction.get("transaction_type")
        quantity = _positive_quantity(transaction.get("quantity"))

        if not warehouse_id or not material_id or quantity <= 0 or not transaction_type:
            continue

        key = (str(warehouse_id), str(material_id))
        if transaction_type in RECEIPT_TRANSACTION_TYPES:
            balances[key] = balances.get(key, 0) + quantity
        elif transaction_type in ISSUE_TRANSACTION_TYPES:
            balances[key] = balances.get(key, 0) - quantity

    rows = [
        {
            "warehouse_id": warehouse_id,
            "material_id": material_id,
            "quantity": quantity,
        }
        for (warehouse_id, material_id), quantity in sorted(balances.items())
        if quantity > 0
    ]

    return pd.DataFrame(rows)


def refresh_inventory_snapshot(engine: Engine) -> int:
    from generator.utils.db_export import write_dataframe
    from generator.utils.master_data import load_inventory_transactions

    inventory_transactions = load_inventory_transactions(engine)
    inventory = generate_inventory(inventory_transactions)
    return write_dataframe(inventory, "inventory", engine)
