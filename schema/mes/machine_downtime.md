machine_downtime

| Header         | Description                              |
| -------------- | ---------------------------------------- |
| `downtime_id`  | Unique identifier for the downtime event |
| `plant_id`     | Plant where the downtime occurred        |
| `machine_name` | Name or identifier of the machine        |
| `start_time`   | Downtime start date and time             |
| `end_time`     | Downtime end date and time               |
| `reason`       | Reason for the downtime                  |


reason

| Value               |
| ------------------- |
| `MAINTENANCE`       |
| `POWER_FAILURE`     |
| `MATERIAL_SHORTAGE` |
| `MACHINE_FAILURE`   |
| `QUALITY_CHECK`     |
