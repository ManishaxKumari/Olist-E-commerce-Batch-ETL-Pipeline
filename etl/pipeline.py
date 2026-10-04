"""Olist batch ETL: extract CSVs -> clean/transform -> validate -> load star schema.

Run:  python -m etl.pipeline
Idempotent: schema.sql drops + recreates tables, so re-running gives the same result.
"""
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from .config import RAW_DIR, DB_URL, SCHEMA_SQL, FILES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("etl")

KEEP_STATUS = {"delivered", "shipped", "invoiced", "processing", "approved"}


# ---------- EXTRACT ----------
def extract() -> dict:
    raw = {}
    for name, fname in FILES.items():
        path = RAW_DIR / fname
        if not path.exists():
            raise FileNotFoundError(f"{path} missing. Put Olist CSVs there or run: python -m etl.generate_data")
        raw[name] = pd.read_csv(path)
        log.info("extracted %-10s %7d rows", name, len(raw[name]))
    return raw


# ---------- TRANSFORM ----------
def clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    o = orders.drop_duplicates("order_id").copy()
    for c in ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]:
        o[c] = pd.to_datetime(o[c], errors="coerce")
    o = o.dropna(subset=["order_purchase_timestamp"])
    o = o[o["order_status"].isin(KEEP_STATUS)].copy()   # drop canceled / unavailable
    o["delivery_days"] = (o["order_delivered_customer_date"] - o["order_purchase_timestamp"]).dt.days
    o["is_late"] = (o["order_delivered_customer_date"] > o["order_estimated_delivery_date"]).fillna(False)
    o["purchase_date"] = o["order_purchase_timestamp"].dt.normalize()
    return o


def build_dim_customer(customers: pd.DataFrame) -> pd.DataFrame:
    d = customers.drop_duplicates("customer_id").reset_index(drop=True)
    d.insert(0, "customer_key", d.index + 1)
    d = d.rename(columns={"customer_city": "city", "customer_state": "state"})
    d["city"] = d["city"].str.title()
    return d[["customer_key", "customer_id", "customer_unique_id", "city", "state"]]


def build_dim_product(products: pd.DataFrame) -> pd.DataFrame:
    d = products.drop_duplicates("product_id").reset_index(drop=True)
    d.insert(0, "product_key", d.index + 1)
    d["category"] = d["product_category_name"].fillna("unknown")
    d = d.rename(columns={"product_weight_g": "weight_g"})
    return d[["product_key", "product_id", "category", "weight_g"]]


def build_dim_date(dates: pd.Series) -> pd.DataFrame:
    u = pd.Series(pd.to_datetime(dates.dropna().unique())).sort_values()
    return pd.DataFrame({
        "date_key": u.dt.strftime("%Y%m%d").astype(int),
        "full_date": u.dt.date,
        "order_year": u.dt.year,
        "quarter": u.dt.quarter,
        "order_month": u.dt.month,
        "month_name": u.dt.strftime("%B"),
        "day_of_week": u.dt.strftime("%A"),
    }).reset_index(drop=True)


def build_fact(orders, items, payments, dim_c, dim_p) -> pd.DataFrame:
    main_pay = (payments.sort_values("payment_value")
                .drop_duplicates("order_id", keep="last")[["order_id", "payment_type"]])
    f = (items.merge(orders, on="order_id", how="inner")
              .merge(main_pay, on="order_id", how="left")
              .merge(dim_c[["customer_key", "customer_id"]], on="customer_id", how="left")
              .merge(dim_p[["product_key", "product_id"]], on="product_id", how="left"))
    f["date_key"] = f["purchase_date"].dt.strftime("%Y%m%d").astype(int)
    f["payment_type"] = f["payment_type"].fillna("unknown")
    f = f.reset_index(drop=True)
    f.insert(0, "sale_id", f.index + 1)
    cols = ["sale_id", "order_id", "order_item_id", "customer_key", "product_key", "date_key",
            "order_status", "price", "freight_value", "payment_type", "delivery_days", "is_late"]
    f = f[cols].copy()
    f["delivery_days"] = f["delivery_days"].astype("Int64")
    f["is_late"] = f["is_late"].astype(bool)
    return f


def transform(raw: dict) -> dict:
    orders = clean_orders(raw["orders"])
    dim_c = build_dim_customer(raw["customers"])
    dim_p = build_dim_product(raw["products"])
    fact = build_fact(orders, raw["items"], raw["payments"], dim_c, dim_p)
    dim_d = build_dim_date(orders["purchase_date"])
    log.info("transformed: fact=%d customers=%d products=%d dates=%d",
             len(fact), len(dim_c), len(dim_p), len(dim_d))
    return {"dim_customer": dim_c, "dim_product": dim_p, "dim_date": dim_d, "fact_sales": fact}


# ---------- VALIDATE (data quality) ----------
def validate(t: dict) -> None:
    f = t["fact_sales"]
    checks = {
        "fact not empty": len(f) > 0,
        "sale_id unique": f["sale_id"].is_unique,
        "no null foreign keys": not f[["customer_key", "product_key", "date_key"]].isna().any().any(),
        "price positive": (f["price"] > 0).all(),
        "freight non-negative": (f["freight_value"] >= 0).all(),
        "dim_customer key unique": t["dim_customer"]["customer_key"].is_unique,
        "dim_product key unique": t["dim_product"]["product_key"].is_unique,
        "all date_keys in dim_date": f["date_key"].isin(t["dim_date"]["date_key"]).all(),
    }
    failed = [k for k, ok in checks.items() if not ok]
    for k, ok in checks.items():
        log.info("DQ check %-28s %s", k, "PASS" if ok else "FAIL")
    if failed:
        raise ValueError(f"Data quality checks failed: {failed}")


# ---------- LOAD ----------
def load(t: dict, engine) -> None:
    with engine.begin() as conn:
        for stmt in SCHEMA_SQL.read_text().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
        for name in ["dim_customer", "dim_product", "dim_date", "fact_sales"]:   # dims first (FK order)
            t[name].to_sql(name, conn, if_exists="append", index=False, chunksize=5000)
            log.info("loaded %-13s %7d rows", name, len(t[name]))


def run() -> None:
    raw = extract()
    t = transform(raw)
    validate(t)
    load(t, create_engine(DB_URL))
    log.info("ETL finished OK -> %s", DB_URL)


if __name__ == "__main__":
    run()
