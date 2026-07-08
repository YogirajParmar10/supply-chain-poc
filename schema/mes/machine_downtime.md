machine_downtime

Canonical silver/gold schema (mapped from ServiceNow ingest columns):

| Header         | Ingest column (ServiceNow) | Description                              |
| -------------- | -------------------------- | ---------------------------------------- |
| `downtime_id`  | `u_downtime_id`            | Unique identifier for the downtime event |
| `plant_id`     | `u_plant_id`               | Plant where the downtime occurred        |
| `machine_name` | `u_machine_name`           | Name or identifier of the machine        |
| `start_time`   | `u_start_time`             | Downtime start date and time             |
| `end_time`     | `u_end_time`               | Downtime end date and time               |
| `reason`       | `u_reason`                 | Reason for the downtime                  |

Ingest-only metadata columns (not carried to `refined`): `sys_id`, `sys_created_on`, `sys_updated_on`, `sys_created_by`, `sys_updated_by`, `sys_mod_count`, `_databricks_deleted`.


reason

| Value               |
| ------------------- |
| `MAINTENANCE`       |
| `POWER_FAILURE`     |
| `MATERIAL_SHORTAGE` |
| `MACHINE_FAILURE`   |
| `QUALITY_CHECK`     |
