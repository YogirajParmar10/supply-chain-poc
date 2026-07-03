# Databricks notebook source
# MAGIC %md
# MAGIC # Operations Transformation Pipeline
# MAGIC
# MAGIC Lakeflow Declarative Pipeline that transforms **ingest** data into **refined** (silver)
# MAGIC and **serve** (gold) tables for FlexiPack Industries Ltd.
# MAGIC
# MAGIC | Layer | Schema | Pipeline object type |
# MAGIC |-------|--------|----------------------|
# MAGIC | Silver | `refined` | Streaming tables (ERP) + materialized views (WMS) |
# MAGIC | Gold | `serve` | Materialized views |
# MAGIC
# MAGIC **Sources**
# MAGIC - Lakeflow Connect streaming tables: ERP master + transactional tables in `ingest`
# MAGIC - Fivetran batch Delta tables: `ingest.inventory`, `ingest.inventory_transactions`
# MAGIC
# MAGIC Data-quality rules are applied in the silver transformation helpers below.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

CATALOG = "jm_databricks_learning_ws"
INGEST_SCHEMA = "ingest"
REFINED_SCHEMA = "refined"
SERVE_SCHEMA = "serve"

INGEST = f"{CATALOG}.{INGEST_SCHEMA}"
REFINED = f"{CATALOG}.{REFINED_SCHEMA}"
SERVE = f"{CATALOG}.{SERVE_SCHEMA}"

# COMMAND ----------

from pyspark import pipelines as dp
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    coalesce,
    col,
    count,
    countDistinct,
    length,
    lit,
    max as spark_max,
    regexp_extract,
    row_number,
    sum as spark_sum,
    to_date,
    trim,
    upper,
    when,
)
from pyspark.sql.types import LongType
from pyspark.sql.window import Window

VALID_PURCHASE_ORDER_STATUSES = ("CREATED", "CONFIRMED", "DELIVERED", "CANCELLED")
VALID_SALES_ORDER_STATUSES = ("CREATED", "CONFIRMED", "SHIPPED", "DELIVERED", "CANCELLED")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Shared transformation helpers
# MAGIC
# MAGIC Reusable data-quality and cleansing functions for the silver layer.

# COMMAND ----------


def _dedupe_order_columns(df: DataFrame) -> list:
    """
    Build window ordering from ingest metadata columns that exist on the source table.

    bronze_row_id may only be present on transactional order tables (purchase_orders,
    sales_orders). Other sources use updated_at, Fivetran sync metadata, or dropDuplicates.
    """
    order_cols = []
    for column_name in ("bronze_row_id", "updated_at", "_fivetran_synced", "created_at"):
        if column_name in df.columns:
            order_cols.append(col(column_name).desc_nulls_last())
    return order_cols


def _dedupe_latest(df: DataFrame, business_key: str) -> DataFrame:
    """Keep the latest row per business key when duplicates exist."""
    order_cols = _dedupe_order_columns(df)
    if not order_cols:
        return df.dropDuplicates([business_key])
    window = Window.partitionBy(business_key).orderBy(*order_cols)
    return (
        df.withColumn("_row_num", row_number().over(window))
        .filter(col("_row_num") == 1)
        .drop("_row_num")
    )


def _dedupe_exact_rows(df: DataFrame, key_columns: list[str]) -> DataFrame:
    """Remove duplicate rows for batch WMS tables, keeping the latest ingest record."""
    order_cols = _dedupe_order_columns(df)
    if not order_cols:
        return df.dropDuplicates(key_columns)
    window = Window.partitionBy(*key_columns).orderBy(*order_cols)
    return (
        df.withColumn("_row_num", row_number().over(window))
        .filter(col("_row_num") == 1)
        .drop("_row_num")
    )


def _trim_string_columns(df: DataFrame, columns: list[str]) -> DataFrame:
    """Trim leading and trailing whitespace on string columns."""
    trimmed = df
    for column_name in columns:
        if column_name in trimmed.columns:
            trimmed = trimmed.withColumn(column_name, trim(col(column_name)))
    return trimmed


def _normalize_status(status_column: str):
    """Map common status variants to canonical ERP values and uppercase the remainder."""
    normalized = trim(col(status_column))
    return (
        when(normalized == "DELIVERD", lit("DELIVERED"))
        .when(normalized.rlike("(?i)^confirmed$"), lit("CONFIRMED"))
        .when(normalized.rlike("(?i)^shipped$"), lit("SHIPPED"))
        .when((normalized == "") | normalized.isNull(), lit(None))
        .otherwise(upper(normalized))
    )


def _parse_bronze_date(column_name: str):
    """Parse source date strings; invalid values become NULL without failing the pipeline."""
    raw = trim(col(column_name))
    iso_prefix = regexp_extract(raw, r"^(\d{4}-\d{2}-\d{2})", 1)
    return coalesce(
        when(raw.rlike(r"^\d{4}-\d{2}-\d{2}$"), to_date(raw, "yyyy-MM-dd")),
        when(raw.rlike(r"^\d{4}-\d{2}-\d{2}T"), to_date(raw, "yyyy-MM-dd'T'HH:mm:ss")),
        when(raw.rlike(r"^\d{2}/\d{2}/\d{4}$"), to_date(raw, "dd/MM/yyyy")),
        when(raw.rlike(r"^\d{2}-[A-Za-z]{3}-\d{4}$"), to_date(raw, "dd-MMM-yyyy")),
        when(length(iso_prefix) > 0, to_date(iso_prefix, "yyyy-MM-dd")),
    )


def _parse_positive_quantity(column_name: str):
    """Cast source quantity values and retain only strictly positive integers."""
    parsed = when(
        trim(col(column_name)).rlike(r"^-?\d+(\.\d+)?$"),
        trim(col(column_name)).cast("double").cast(LongType()),
    )
    return when(parsed > 0, parsed)


def _filter_non_null_key(df: DataFrame, key_column: str) -> DataFrame:
    """Drop rows with missing or blank primary/business identifiers."""
    return df.filter(col(key_column).isNotNull() & (length(col(key_column)) > 0))


def _clean_master_stream(
    source_df: DataFrame,
    business_key: str,
    string_columns: list[str],
) -> DataFrame:
    """Apply silver cleansing rules to ERP master tables."""
    cleaned = _trim_string_columns(source_df, string_columns)
    cleaned = _filter_non_null_key(cleaned, business_key)
    return _dedupe_latest(cleaned, business_key)


def _clean_order_stream(
    source_df: DataFrame,
    business_key: str,
    string_columns: list[str],
    delivery_date_column: str,
    valid_statuses: tuple[str, ...],
) -> DataFrame:
    """Apply silver cleansing rules to ERP purchase and sales orders."""
    cleaned = _trim_string_columns(source_df, string_columns)
    cleaned = _filter_non_null_key(cleaned, business_key)
    cleaned = _dedupe_latest(cleaned, business_key)

    cleaned = (
        cleaned.withColumn("status", _normalize_status("status"))
        .withColumn("order_date", _parse_bronze_date("order_date"))
        .withColumn(delivery_date_column, _parse_bronze_date(delivery_date_column))
        .withColumn("quantity", _parse_positive_quantity("quantity"))
    )

    cleaned = cleaned.filter(col("quantity").isNotNull())

    cleaned = cleaned.withColumn(
        "status",
        when(col("status").isin(*valid_statuses), col("status")).otherwise(upper(col("status"))),
    )

    return cleaned


def _clean_inventory_batch(source_df: DataFrame) -> DataFrame:
    """Silver rules for Fivetran WMS inventory snapshots."""
    string_columns = ["warehouse_id", "material_id", "quantity", "snapshot_date"]
    cleaned = _trim_string_columns(source_df, string_columns)
    cleaned = cleaned.filter(
        col("warehouse_id").isNotNull()
        & (length(col("warehouse_id")) > 0)
        & col("material_id").isNotNull()
        & (length(col("material_id")) > 0)
        & col("snapshot_date").isNotNull()
        & (length(col("snapshot_date")) > 0)
    )
    cleaned = cleaned.withColumn(
        "quantity",
        _parse_positive_quantity("quantity"),
    )
    cleaned = cleaned.filter(col("quantity").isNotNull())
    cleaned = cleaned.withColumn("snapshot_date", to_date(col("snapshot_date")))
    cleaned = _dedupe_exact_rows(cleaned, ["snapshot_date", "warehouse_id", "material_id"])
    return cleaned


def _clean_inventory_transactions_batch(source_df: DataFrame) -> DataFrame:
    """Silver rules for Fivetran WMS inventory transactions."""
    string_columns = [
        "transaction_id",
        "transaction_date",
        "warehouse_id",
        "material_id",
        "transaction_type",
        "quantity",
        "reference_id",
    ]
    cleaned = _trim_string_columns(source_df, string_columns)
    cleaned = cleaned.filter(
        col("transaction_id").isNotNull()
        & (length(col("transaction_id")) > 0)
        & col("warehouse_id").isNotNull()
        & (length(col("warehouse_id")) > 0)
        & col("material_id").isNotNull()
        & (length(col("material_id")) > 0)
        & col("transaction_type").isNotNull()
        & (length(col("transaction_type")) > 0)
    )
    cleaned = cleaned.withColumn("transaction_type", upper(col("transaction_type")))
    cleaned = cleaned.withColumn("quantity", _parse_positive_quantity("quantity"))
    cleaned = cleaned.filter(col("quantity").isNotNull())
    cleaned = _dedupe_exact_rows(cleaned, ["transaction_id"])
    return cleaned


# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver layer — `refined` schema
# MAGIC
# MAGIC ERP tables are published as **streaming tables** (Lakeflow Connect sources).
# MAGIC WMS tables are published as **materialized views** (Fivetran batch sources).

# COMMAND ----------

# MAGIC %md
# MAGIC ### ERP master data (streaming)

# COMMAND ----------


@dp.materialized_view(
    name=f"{REFINED}.customers",
    comment="Cleaned customer master from ingest.customers",
    table_properties={"quality": "silver", "domain": "erp"},
)
@dp.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL AND length(trim(customer_id)) > 0")
def refined_customers():
    return _clean_master_stream(
        spark.read.table(f"{INGEST}.customers"),
        business_key="customer_id",
        string_columns=["customer_id", "customer_name", "country"],
    )


@dp.materialized_view(
    name=f"{REFINED}.materials",
    comment="Cleaned material master from ingest.materials",
    table_properties={"quality": "silver", "domain": "erp"},
)
@dp.expect_or_drop("valid_material_id", "material_id IS NOT NULL AND length(trim(material_id)) > 0")
def refined_materials():
    cleaned = _clean_master_stream(
        spark.read.table(f"{INGEST}.materials"),
        business_key="material_id",
        string_columns=["material_id", "material_name", "material_type"],
    )
    # Normalize material_type to uppercase canonical values.
    return cleaned.withColumn("material_type", upper(col("material_type")))


@dp.materialized_view(
    name=f"{REFINED}.plants",
    comment="Cleaned plant master from ingest.plants",
    table_properties={"quality": "silver", "domain": "erp"},
)
@dp.expect_or_drop("valid_plant_id", "plant_id IS NOT NULL AND length(trim(plant_id)) > 0")
def refined_plants():
    return _clean_master_stream(
        spark.read.table(f"{INGEST}.plants"),
        business_key="plant_id",
        string_columns=["plant_id", "plant_name", "country"],
    )


@dp.materialized_view(
    name=f"{REFINED}.suppliers",
    comment="Cleaned supplier master from ingest.suppliers",
    table_properties={"quality": "silver", "domain": "erp"},
)
@dp.expect_or_drop("valid_supplier_id", "supplier_id IS NOT NULL AND length(trim(supplier_id)) > 0")
def refined_suppliers():
    return _clean_master_stream(
        spark.read.table(f"{INGEST}.suppliers"),
        business_key="supplier_id",
        string_columns=["supplier_id", "supplier_name", "country"],
    )


@dp.materialized_view(
    name=f"{REFINED}.warehouses",
    comment="Cleaned warehouse master from ingest.warehouses",
    table_properties={"quality": "silver", "domain": "erp"},
)
@dp.expect_or_drop("valid_warehouse_id", "warehouse_id IS NOT NULL AND length(trim(warehouse_id)) > 0")
def refined_warehouses():
    return _clean_master_stream(
        spark.read.table(f"{INGEST}.warehouses"),
        business_key="warehouse_id",
        string_columns=["warehouse_id", "warehouse_name", "plant_id"],
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ### ERP transactional data (materialized views)

# COMMAND ----------


@dp.materialized_view(
    name=f"{REFINED}.purchase_orders",
    comment="Deduped and validated purchase orders from ingest.purchase_orders",
    table_properties={"quality": "silver", "domain": "erp"},
)
@dp.expect_or_drop(
    "valid_purchase_order_id",
    "purchase_order_id IS NOT NULL AND length(trim(purchase_order_id)) > 0",
)
@dp.expect_or_drop("positive_quantity", "quantity IS NOT NULL AND quantity > 0")
def refined_purchase_orders():
    return _clean_order_stream(
        spark.read.table(f"{INGEST}.purchase_orders"),
        business_key="purchase_order_id",
        string_columns=[
            "purchase_order_id",
            "supplier_id",
            "material_id",
            "status",
            "order_date",
            "expected_delivery_date",
            "quantity",
        ],
        delivery_date_column="expected_delivery_date",
        valid_statuses=VALID_PURCHASE_ORDER_STATUSES,
    )


@dp.materialized_view(
    name=f"{REFINED}.sales_orders",
    comment="Deduped and validated sales orders from ingest.sales_orders",
    table_properties={"quality": "silver", "domain": "erp"},
)
@dp.expect_or_drop(
    "valid_sales_order_id",
    "sales_order_id IS NOT NULL AND length(trim(sales_order_id)) > 0",
)
@dp.expect_or_drop("positive_quantity", "quantity IS NOT NULL AND quantity > 0")
def refined_sales_orders():
    return _clean_order_stream(
        spark.read.table(f"{INGEST}.sales_orders"),
        business_key="sales_order_id",
        string_columns=[
            "sales_order_id",
            "customer_id",
            "material_id",
            "status",
            "order_date",
            "requested_delivery_date",
            "quantity",
        ],
        delivery_date_column="requested_delivery_date",
        valid_statuses=VALID_SALES_ORDER_STATUSES,
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ### WMS data (batch Delta via Fivetran)

# COMMAND ----------


@dp.materialized_view(
    name=f"{REFINED}.inventory",
    comment="Cleaned daily inventory snapshots from ingest.inventory",
    table_properties={"quality": "silver", "domain": "wms"},
)
@dp.expect_or_drop("positive_quantity", "quantity IS NOT NULL AND quantity > 0")
def refined_inventory():
    return _clean_inventory_batch(spark.read.table(f"{INGEST}.inventory"))


@dp.materialized_view(
    name=f"{REFINED}.inventory_transactions",
    comment="Cleaned inventory transactions from ingest.inventory_transactions",
    table_properties={"quality": "silver", "domain": "wms"},
)
@dp.expect_or_drop("positive_quantity", "quantity IS NOT NULL AND quantity > 0")
def refined_inventory_transactions():
    return _clean_inventory_transactions_batch(
        spark.read.table(f"{INGEST}.inventory_transactions")
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold layer — `serve` schema
# MAGIC
# MAGIC Analytical materialized views built from cleaned `refined` tables.

# COMMAND ----------

# MAGIC %md
# MAGIC ### `serve.supplier_summary`

# COMMAND ----------


@dp.materialized_view(
    name=f"{SERVE}.supplier_summary",
    comment="Purchase order volume and quantity by supplier",
    table_properties={"quality": "gold", "domain": "procurement"},
)
def serve_supplier_summary():
    purchase_orders = spark.read.table(f"{REFINED}.purchase_orders")
    suppliers = spark.read.table(f"{REFINED}.suppliers")

    return (
        purchase_orders.join(suppliers, on="supplier_id", how="left")
        .groupBy(
            col("supplier_id"),
            col("supplier_name"),
            col("country"),
        )
        .agg(
            count(lit(1)).alias("total_purchase_orders"),
            spark_sum("quantity").alias("total_quantity"),
        )
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ### `serve.customer_summary`

# COMMAND ----------


@dp.materialized_view(
    name=f"{SERVE}.customer_summary",
    comment="Sales order volume and quantity by customer",
    table_properties={"quality": "gold", "domain": "sales"},
)
def serve_customer_summary():
    sales_orders = spark.read.table(f"{REFINED}.sales_orders")
    customers = spark.read.table(f"{REFINED}.customers")

    return (
        sales_orders.join(customers, on="customer_id", how="left")
        .groupBy(
            col("customer_id"),
            col("customer_name"),
            col("country"),
        )
        .agg(
            count(lit(1)).alias("total_sales_orders"),
            spark_sum("quantity").alias("total_quantity"),
        )
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ### `serve.inventory_summary`

# COMMAND ----------


@dp.materialized_view(
    name=f"{SERVE}.inventory_summary",
    comment="Current stock and material coverage by warehouse",
    table_properties={"quality": "gold", "domain": "inventory"},
)
def serve_inventory_summary():
    inventory = spark.read.table(f"{REFINED}.inventory")

    latest_snapshot = inventory.agg(spark_max("snapshot_date").alias("latest_snapshot_date"))
    current_inventory = inventory.join(
        latest_snapshot,
        inventory.snapshot_date == latest_snapshot.latest_snapshot_date,
        how="inner",
    ).drop("latest_snapshot_date")

    warehouses = spark.read.table(f"{REFINED}.warehouses")

    return (
        current_inventory.join(warehouses, on="warehouse_id", how="left")
        .groupBy(
            col("warehouse_id"),
            col("warehouse_name"),
            col("plant_id"),
        )
        .agg(
            spark_sum("quantity").alias("current_stock"),
            countDistinct("material_id").alias("total_materials"),
        )
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ### `serve.material_summary`

# COMMAND ----------


@dp.materialized_view(
    name=f"{SERVE}.material_summary",
    comment="Purchased, sold, and on-hand quantities by material",
    table_properties={"quality": "gold", "domain": "inventory"},
)
def serve_material_summary():
    purchase_orders = spark.read.table(f"{REFINED}.purchase_orders")
    sales_orders = spark.read.table(f"{REFINED}.sales_orders")
    inventory = spark.read.table(f"{REFINED}.inventory")
    materials = spark.read.table(f"{REFINED}.materials")

    purchased = purchase_orders.groupBy("material_id").agg(
        spark_sum("quantity").alias("purchased_quantity"),
    )

    sold = sales_orders.groupBy("material_id").agg(
        spark_sum("quantity").alias("sold_quantity"),
    )

    latest_snapshot = inventory.agg(spark_max("snapshot_date").alias("latest_snapshot_date"))
    current_inventory = (
        inventory.join(
            latest_snapshot,
            inventory.snapshot_date == latest_snapshot.latest_snapshot_date,
            how="inner",
        )
        .groupBy("material_id")
        .agg(spark_sum("quantity").alias("current_inventory"))
    )

    return (
        materials.select("material_id", "material_name", "material_type")
        .join(purchased, on="material_id", how="left")
        .join(sold, on="material_id", how="left")
        .join(current_inventory, on="material_id", how="left")
        .select(
            "material_id",
            "material_name",
            "material_type",
            coalesce(col("purchased_quantity"), lit(0)).alias("purchased_quantity"),
            coalesce(col("sold_quantity"), lit(0)).alias("sold_quantity"),
            coalesce(col("current_inventory"), lit(0)).alias("current_inventory"),
        )
    )
