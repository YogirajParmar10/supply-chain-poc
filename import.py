"""
Legacy CSV import script.

The generator now writes directly to PostgreSQL. Use this script only if you
need to backfill from existing CSV files in output/erp/.
"""

import glob

import pandas as pd

from generator.utils.db import get_engine
from generator.utils.db_export import write_dataframe

engine = get_engine()

csv_files = sorted(glob.glob("output/erp/purchase_orders/purchase_orders_*.csv"))
df = pd.concat((pd.read_csv(file) for file in csv_files), ignore_index=True)
df = df.drop_duplicates(subset="purchase_order_id", keep="last")

row_count = write_dataframe(df, "purchase_orders", engine)
print(f"Imported {row_count} purchase orders from {len(csv_files)} files")
