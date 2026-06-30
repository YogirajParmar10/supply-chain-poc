import pandas as pd

from generator.utils.ids import format_id

RAW_MATERIALS_WAREHOUSE_ID = "WH001"
FINISHED_GOODS_WAREHOUSE_IDS: tuple[str, ...] = ("WH002", "WH003")


def _positive_quantity(value: object) -> int | None:
    try:
        quantity = int(float(value))
    except (TypeError, ValueError):
        return None
    if quantity <= 0:
        return None
    return quantity


def _goods_receipt_rows(purchase_orders: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    sequence = 1

    for _, order in purchase_orders.iterrows():
        quantity = _positive_quantity(order.get("quantity"))
        material_id = order.get("material_id")
        purchase_order_id = order.get("purchase_order_id")
        transaction_date = order.get("expected_delivery_date")

        if not material_id or not purchase_order_id or not transaction_date or quantity is None:
            continue

        rows.append(
            {
                "transaction_id": format_id("IT", sequence, 6),
                "transaction_date": str(transaction_date),
                "warehouse_id": RAW_MATERIALS_WAREHOUSE_ID,
                "material_id": str(material_id),
                "transaction_type": "GOODS_RECEIPT",
                "quantity": quantity,
                "reference_id": str(purchase_order_id),
            }
        )
        sequence += 1

    return rows


def _sales_shipment_rows(
    sales_orders: pd.DataFrame,
    *,
    start_sequence: int = 1,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    sequence = start_sequence

    for _, order in sales_orders.iterrows():
        quantity = _positive_quantity(order.get("quantity"))
        material_id = order.get("material_id")
        sales_order_id = order.get("sales_order_id")
        transaction_date = order.get("requested_delivery_date")

        if not material_id or not sales_order_id or not transaction_date or quantity is None:
            continue

        # Finished goods ship from WH002; schema allows multiple FG warehouses.
        warehouse_id = FINISHED_GOODS_WAREHOUSE_IDS[0]

        rows.append(
            {
                "transaction_id": format_id("IT", sequence, 6),
                "transaction_date": str(transaction_date),
                "warehouse_id": warehouse_id,
                "material_id": str(material_id),
                "transaction_type": "SALES_SHIPMENT",
                "quantity": quantity,
                "reference_id": str(sales_order_id),
            }
        )
        sequence += 1

    return rows


def generate_inventory_transactions(
    purchase_orders: pd.DataFrame,
    sales_orders: pd.DataFrame,
) -> pd.DataFrame:
    goods_receipt_rows = _goods_receipt_rows(purchase_orders)
    next_sequence = len(goods_receipt_rows) + 1
    sales_shipment_rows = _sales_shipment_rows(sales_orders, start_sequence=next_sequence)
    rows = goods_receipt_rows + sales_shipment_rows
    if not rows:
        return pd.DataFrame(
            columns=[
                "transaction_id",
                "transaction_date",
                "warehouse_id",
                "material_id",
                "transaction_type",
                "quantity",
                "reference_id",
            ]
        )

    return pd.DataFrame(rows)
