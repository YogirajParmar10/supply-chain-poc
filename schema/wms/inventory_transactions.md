inventory_transactions

| Header             | Description                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| `transaction_id`   | Unique identifier for the inventory transaction                                                   |
| `transaction_date` | Date and time of the transaction                                                                  |
| `warehouse_id`     | Warehouse where the transaction occurred                                                          |
| `material_id`      | Material involved in the transaction                                                              |
| `transaction_type` | Type of inventory movement                                                                        |
| `quantity`         | Quantity moved (always positive)                                                                  |
| `reference_id`     | Reference to the business document (e.g., Purchase Order ID, Sales Order ID, Production Order ID) |


transaction_type

| Value                    | Description                              |
| ------------------------ | ---------------------------------------- |
| `GOODS_RECEIPT`          | Inventory received from a supplier       |
| `PRODUCTION_RECEIPT`     | Finished goods received from production  |
| `SALES_SHIPMENT`         | Inventory shipped to a customer          |
| `PRODUCTION_CONSUMPTION` | Raw materials consumed by production     |
| `STOCK_TRANSFER`         | Inventory transferred between warehouses |
| `STOCK_ADJUSTMENT`       | Manual inventory correction              |
