production_orders

| Header                | Description                                |
| --------------------- | ------------------------------------------ |
| `production_order_id` | Unique identifier for the production order |
| `plant_id`            | Plant executing the production             |
| `material_id`         | Finished good being manufactured           |
| `planned_quantity`    | Planned production quantity                |
| `actual_quantity`     | Actual quantity produced                   |
| `start_date`          | Production start date and time             |
| `end_date`            | Production end date and time               |
| `status`              | Current production order status            |


status

| Value         | Description                       |
| ------------- | --------------------------------- |
| `PLANNED`     | Production is scheduled           |
| `IN_PROGRESS` | Production is currently running   |
| `COMPLETED`   | Production completed successfully |
| `CANCELLED`   | Production order cancelled        |
