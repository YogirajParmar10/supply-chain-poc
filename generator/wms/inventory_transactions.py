import pandas as pd

from generator.utils.ids import format_id
from generator.wms.warehouses import resolve_warehouse_ids, select_finished_goods_warehouse

RECEIPT_TRANSACTION_TYPES: frozenset[str] = frozenset(
    {"GOODS_RECEIPT", "PRODUCTION_RECEIPT"}
)
ISSUE_TRANSACTION_TYPES: frozenset[str] = frozenset(
    {"SALES_SHIPMENT", "PRODUCTION_CONSUMPTION"}
)


def _positive_quantity(value: object) -> int | None:
    try:
        quantity = int(float(value))
    except (TypeError, ValueError):
        return None
    if quantity <= 0:
        return None
    return quantity


def _raw_material_ids(materials: pd.DataFrame) -> set[str]:
    return set(
        materials.loc[materials["material_type"] == "RAW_MATERIAL", "material_id"].astype(str)
    )


def _finished_good_ids(materials: pd.DataFrame) -> set[str]:
    return set(
        materials.loc[materials["material_type"] == "FINISHED_GOOD", "material_id"].astype(str)
    )


def _goods_receipt_rows(
    purchase_orders: pd.DataFrame,
    materials: pd.DataFrame,
    raw_materials_warehouse_id: str,
    *,
    id_start: int,
) -> list[dict[str, object]]:
    raw_material_ids = _raw_material_ids(materials)
    rows: list[dict[str, object]] = []
    sequence = id_start

    for _, order in purchase_orders.iterrows():
        purchase_order_id = order.get("purchase_order_id")
        material_id = order.get("material_id")
        transaction_date = order.get("expected_delivery_date")
        quantity = _positive_quantity(order.get("quantity"))

        if not purchase_order_id or not material_id or not transaction_date or quantity is None:
            continue
        if str(material_id) not in raw_material_ids:
            continue

        rows.append(
            {
                "transaction_id": format_id("IT", sequence, 6),
                "transaction_date": str(transaction_date),
                "warehouse_id": raw_materials_warehouse_id,
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
    materials: pd.DataFrame,
    finished_goods_warehouse_ids: list[str],
    *,
    id_start: int,
) -> list[dict[str, object]]:
    finished_good_ids = _finished_good_ids(materials)
    rows: list[dict[str, object]] = []
    sequence = id_start

    for _, order in sales_orders.iterrows():
        sales_order_id = order.get("sales_order_id")
        material_id = order.get("material_id")
        transaction_date = order.get("requested_delivery_date")
        quantity = _positive_quantity(order.get("quantity"))

        if not sales_order_id or not material_id or not transaction_date or quantity is None:
            continue
        if str(material_id) not in finished_good_ids:
            continue

        rows.append(
            {
                "transaction_id": format_id("IT", sequence, 6),
                "transaction_date": str(transaction_date),
                "warehouse_id": select_finished_goods_warehouse(
                    str(sales_order_id),
                    finished_goods_warehouse_ids,
                ),
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
    materials: pd.DataFrame,
    warehouses: pd.DataFrame,
    *,
    id_start: int = 1,
) -> pd.DataFrame:
    raw_materials_warehouse_id, finished_goods_warehouse_ids = resolve_warehouse_ids(warehouses)

    goods_receipt_rows = _goods_receipt_rows(
        purchase_orders,
        materials,
        raw_materials_warehouse_id,
        id_start=id_start,
    )
    sales_shipment_rows = _sales_shipment_rows(
        sales_orders,
        materials,
        finished_goods_warehouse_ids,
        id_start=id_start + len(goods_receipt_rows),
    )

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
