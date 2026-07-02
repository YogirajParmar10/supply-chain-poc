| Header           | Description                                      |
| ---------------- | ------------------------------------------------ |
| `snapshot_date`  | End-of-day date for this inventory level         |
| `warehouse_id`   | Warehouse where the inventory is stored          |
| `material_id`    | Material in stock                                |
| `quantity`       | Available quantity at end of `snapshot_date`     |

Daily snapshots are rebuilt from all `inventory_transactions` up to and including each calendar day.
