"""Central config. Override with env vars.

Default DB is SQLite (zero setup). For PostgreSQL:
  export DB_URL=postgresql+psycopg2://etl:etl@localhost:5432/warehouse
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = Path(os.getenv("RAW_DIR", ROOT / "data" / "raw"))
DB_URL = os.getenv("DB_URL", f"sqlite:///{ROOT / 'warehouse.db'}")
SCHEMA_SQL = ROOT / "sql" / "schema.sql"

# Real Olist file names (Kaggle: "Brazilian E-Commerce Public Dataset by Olist")
FILES = {
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
}
