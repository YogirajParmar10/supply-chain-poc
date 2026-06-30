import pandas as pd
from sqlalchemy.engine import Engine


def load_materials(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("materials", con=engine)


def load_suppliers(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("suppliers", con=engine)


def load_customers(engine: Engine) -> pd.DataFrame:
    return pd.read_sql_table("customers", con=engine)
