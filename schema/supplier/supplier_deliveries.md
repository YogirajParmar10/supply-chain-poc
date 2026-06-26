supplier_deliveries

| Header              | Description                                 |
| ------------------- | ------------------------------------------- |
| `delivery_id`       | Unique identifier for the supplier delivery |
| `purchase_order_id` | Purchase order being fulfilled              |
| `supplier_id`       | Supplier making the delivery                |
| `delivery_date`     | Actual delivery date                        |
| `status`            | Delivery status                             |

status

| Value                 | Description                                       |
| --------------------- | ------------------------------------------------- |
| `ON_TIME`             | Delivered on or before the expected delivery date |
| `DELAYED`             | Delivered after the expected delivery date        |
| `PARTIALLY_DELIVERED` | Only part of the order was delivered              |
