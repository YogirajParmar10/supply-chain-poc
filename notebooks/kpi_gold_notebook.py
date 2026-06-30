# Databricks notebook source
# MAGIC %md
# MAGIC # FlexiPack KPI Gold Tables
# MAGIC
# MAGIC Builds nine gold KPI tables from silver tables.
# MAGIC
# MAGIC **Prerequisites:** silver tables must already exist in `jm_databricks_learning_ws.default`.

# COMMAND ----------

CATALOG = "jm_databricks_learning_ws.default"

# COMMAND ----------

# Load silver tables
purchase_order_df = spark.table(f"{CATALOG}.silver_purchase_orders")
sales_order_df = spark.table(f"{CATALOG}.silver_sales_orders")
supplier_df = spark.table(f"{CATALOG}.silver_suppliers")
customer_df = spark.table(f"{CATALOG}.silver_customers")
material_df = spark.table(f"{CATALOG}.silver_materials")

# COMMAND ----------

from pyspark.sql.functions import (
    avg,
    coalesce,
    col,
    count,
    countDistinct,
    date_trunc,
    desc,
    lit,
    row_number,
    round,
    sum,
    to_date,
    when,
)
from pyspark.sql.window import Window

ACTIVE_PURCHASE_STATUSES = ["CREATED", "CONFIRMED", "DELIVERED"]
ACTIVE_SALES_STATUSES = ["CREATED", "CONFIRMED", "SHIPPED", "DELIVERED"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Supplier Performance

# COMMAND ----------

supplier_performance_gold = (
    purchase_order_df
        .join(supplier_df, on="supplier_id", how="inner")
        .groupBy("supplier_id", "supplier_name", "country")
        .agg(
            count("purchase_order_id").alias("total_orders"),
            sum("quantity").alias("total_quantity"),
            sum(when(col("status") == "DELIVERED", 1).otherwise(0)).alias("delivered_orders"),
            sum(when(col("status") == "CONFIRMED", 1).otherwise(0)).alias("confirmed_orders"),
            sum(when(col("status") == "CREATED", 1).otherwise(0)).alias("created_orders"),
            sum(when(col("status") == "CANCELLED", 1).otherwise(0)).alias("cancelled_orders"),
            sum(when(col("status") == "DELIVERED", col("quantity")).otherwise(0)).alias("delivered_quantity"),
        )
        .withColumn("delivery_rate", round(col("delivered_orders") / col("total_orders"), 4))
        .withColumn("cancellation_rate", round(col("cancelled_orders") / col("total_orders"), 4))
        .withColumn("fulfillment_rate", round(col("delivered_quantity") / col("total_quantity"), 4))
        .orderBy(desc("total_quantity"))
)

display(supplier_performance_gold)

# COMMAND ----------

(
    supplier_performance_gold.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(f"{CATALOG}.gold_supplier_performance")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Material Demand

# COMMAND ----------

procurement_demand_df = (
    purchase_order_df
        .filter(col("status").isin(ACTIVE_PURCHASE_STATUSES))
        .groupBy("material_id")
        .agg(
            count("purchase_order_id").alias("procurement_orders"),
            sum("quantity").alias("procurement_quantity"),
        )
)

sales_demand_df = (
    sales_order_df
        .filter(col("status").isin(ACTIVE_SALES_STATUSES))
        .groupBy("material_id")
        .agg(
            count("sales_order_id").alias("sales_orders"),
            sum("quantity").alias("sales_quantity"),
        )
)

material_demand_gold = (
    material_df
        .join(procurement_demand_df, on="material_id", how="left")
        .join(sales_demand_df, on="material_id", how="left")
        .select(
            "material_id",
            "material_name",
            "material_type",
            coalesce(col("procurement_orders"), lit(0)).alias("procurement_orders"),
            coalesce(col("procurement_quantity"), lit(0)).alias("procurement_quantity"),
            coalesce(col("sales_orders"), lit(0)).alias("sales_orders"),
            coalesce(col("sales_quantity"), lit(0)).alias("sales_quantity"),
        )
        .withColumn(
            "total_demand_quantity",
            col("procurement_quantity") + col("sales_quantity"),
        )
        .withColumn(
            "total_orders",
            col("procurement_orders") + col("sales_orders"),
        )
        .orderBy(desc("total_demand_quantity"))
)

display(material_demand_gold)

# COMMAND ----------

(
    material_demand_gold.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(f"{CATALOG}.gold_material_demand")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Customer Sales Summary

# COMMAND ----------

customer_sales_summary_gold = (
    sales_order_df
        .join(customer_df, on="customer_id", how="inner")
        .groupBy("customer_id", "customer_name", "country")
        .agg(
            count("sales_order_id").alias("total_orders"),
            sum("quantity").alias("total_quantity"),
            sum(when(col("status") == "DELIVERED", 1).otherwise(0)).alias("delivered_orders"),
            sum(when(col("status") == "SHIPPED", 1).otherwise(0)).alias("shipped_orders"),
            sum(when(col("status") == "CONFIRMED", 1).otherwise(0)).alias("confirmed_orders"),
            sum(when(col("status") == "CREATED", 1).otherwise(0)).alias("created_orders"),
            sum(when(col("status") == "CANCELLED", 1).otherwise(0)).alias("cancelled_orders"),
            sum(when(col("status") == "DELIVERED", col("quantity")).otherwise(0)).alias("delivered_quantity"),
            round(avg("quantity"), 2).alias("avg_order_quantity"),
        )
        .withColumn("delivery_rate", round(col("delivered_orders") / col("total_orders"), 4))
        .orderBy(desc("total_quantity"))
)

display(customer_sales_summary_gold)

# COMMAND ----------

(
    customer_sales_summary_gold.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(f"{CATALOG}.gold_customer_sales_summary")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Procurement vs Sales

# COMMAND ----------

procurement_monthly_df = (
    purchase_order_df
        .filter(col("status").isin(ACTIVE_PURCHASE_STATUSES))
        .withColumn("order_month", date_trunc("month", to_date(col("order_date"))))
        .groupBy("order_month")
        .agg(
            count("purchase_order_id").alias("procurement_orders"),
            sum("quantity").alias("procurement_quantity"),
        )
)

sales_monthly_df = (
    sales_order_df
        .filter(col("status").isin(ACTIVE_SALES_STATUSES))
        .withColumn("order_month", date_trunc("month", to_date(col("order_date"))))
        .groupBy("order_month")
        .agg(
            count("sales_order_id").alias("sales_orders"),
            sum("quantity").alias("sales_quantity"),
        )
)

procurement_vs_sales_gold = (
    procurement_monthly_df.alias("p")
        .join(sales_monthly_df.alias("s"), on="order_month", how="full")
        .select(
            coalesce(col("p.order_month"), col("s.order_month")).alias("order_month"),
            coalesce(col("p.procurement_orders"), lit(0)).alias("procurement_orders"),
            coalesce(col("p.procurement_quantity"), lit(0)).alias("procurement_quantity"),
            coalesce(col("s.sales_orders"), lit(0)).alias("sales_orders"),
            coalesce(col("s.sales_quantity"), lit(0)).alias("sales_quantity"),
        )
        .withColumn(
            "quantity_gap",
            col("procurement_quantity") - col("sales_quantity"),
        )
        .orderBy("order_month")
)

display(procurement_vs_sales_gold)

# COMMAND ----------

(
    procurement_vs_sales_gold.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(f"{CATALOG}.gold_procurement_vs_sales")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Monthly Procurement Trend

# COMMAND ----------

monthly_procurement_trend_gold = (
    purchase_order_df
        .withColumn("order_month", date_trunc("month", to_date(col("order_date"))))
        .groupBy("order_month")
        .agg(
            count("purchase_order_id").alias("order_count"),
            sum("quantity").alias("total_quantity"),
            sum(when(col("status") == "DELIVERED", col("quantity")).otherwise(0)).alias("delivered_quantity"),
            sum(when(col("status") == "CANCELLED", 1).otherwise(0)).alias("cancelled_orders"),
        )
        .withColumn(
            "delivered_share",
            round(col("delivered_quantity") / col("total_quantity"), 4),
        )
        .orderBy("order_month")
)

display(monthly_procurement_trend_gold)

# COMMAND ----------

(
    monthly_procurement_trend_gold.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(f"{CATALOG}.gold_monthly_procurement_trend")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Monthly Sales Trend

# COMMAND ----------

monthly_sales_trend_gold = (
    sales_order_df
        .withColumn("order_month", date_trunc("month", to_date(col("order_date"))))
        .groupBy("order_month")
        .agg(
            count("sales_order_id").alias("order_count"),
            sum("quantity").alias("total_quantity"),
            sum(when(col("status") == "DELIVERED", col("quantity")).otherwise(0)).alias("delivered_quantity"),
            sum(when(col("status") == "CANCELLED", 1).otherwise(0)).alias("cancelled_orders"),
        )
        .withColumn(
            "delivered_share",
            round(col("delivered_quantity") / col("total_quantity"), 4),
        )
        .orderBy("order_month")
)

display(monthly_sales_trend_gold)

# COMMAND ----------

(
    monthly_sales_trend_gold.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(f"{CATALOG}.gold_monthly_sales_trend")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Country-wise Procurement

# COMMAND ----------

country_wise_procurement_gold = (
    purchase_order_df
        .filter(col("status").isin(ACTIVE_PURCHASE_STATUSES))
        .join(supplier_df, on="supplier_id", how="inner")
        .groupBy(col("country"))
        .agg(
            count("purchase_order_id").alias("order_count"),
            sum("quantity").alias("total_quantity"),
            countDistinct("supplier_id").alias("supplier_count"),
        )
        .orderBy(desc("total_quantity"))
)

display(country_wise_procurement_gold)

# COMMAND ----------

(
    country_wise_procurement_gold.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(f"{CATALOG}.gold_country_wise_procurement")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Country-wise Sales

# COMMAND ----------

country_wise_sales_gold = (
    sales_order_df
        .filter(col("status").isin(ACTIVE_SALES_STATUSES))
        .join(customer_df, on="customer_id", how="inner")
        .groupBy(col("country"))
        .agg(
            count("sales_order_id").alias("order_count"),
            sum("quantity").alias("total_quantity"),
            countDistinct("customer_id").alias("customer_count"),
        )
        .orderBy(desc("total_quantity"))
)

display(country_wise_sales_gold)

# COMMAND ----------

(
    country_wise_sales_gold.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(f"{CATALOG}.gold_country_wise_sales")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Top Moving Materials

# COMMAND ----------

TOP_N = 20

top_moving_materials_gold = (
    material_demand_gold
        .filter(col("total_demand_quantity") > 0)
        .withColumn(
            "movement_rank",
            row_number().over(Window.orderBy(desc("total_demand_quantity"))),
        )
        .filter(col("movement_rank") <= TOP_N)
        .select(
            "movement_rank",
            "material_id",
            "material_name",
            "material_type",
            "procurement_orders",
            "procurement_quantity",
            "sales_orders",
            "sales_quantity",
            "total_orders",
            "total_demand_quantity",
        )
        .orderBy("movement_rank")
)

display(top_moving_materials_gold)

# COMMAND ----------

(
    top_moving_materials_gold.write
        .format("delta")
        .mode("overwrite")
        .saveAsTable(f"{CATALOG}.gold_top_moving_materials")
)
