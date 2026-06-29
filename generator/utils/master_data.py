from pathlib import Path

import pandas as pd


def load_materials(erp_dir: Path) -> pd.DataFrame:
    return pd.read_csv(erp_dir / "materials.csv")


def load_suppliers(erp_dir: Path) -> pd.DataFrame:
    return pd.read_csv(erp_dir / "suppliers.csv")


def load_customers(erp_dir: Path) -> pd.DataFrame:
    return pd.read_csv(erp_dir / "customers.csv")
