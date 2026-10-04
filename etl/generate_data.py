"""Generates a small *dirty* Olist-shaped dataset so the pipeline runs without
a Kaggle download. Same file names + columns as the real dataset, so you can
simply drop the real CSVs into data/raw/ instead.

Usage: python -m etl.generate_data [n_orders]
"""
import sys
import numpy as np
import pandas as pd
from .config import RAW_DIR, FILES

STATES = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "PE"]
CITIES = ["sao paulo", "rio de janeiro", "belo horizonte", "porto alegre",
          "curitiba", "salvador", "florianopolis", "recife"]
CATS = ["health_beauty", "computers", "furniture", "toys", "sports_leisure",
        "bed_bath_table", "watches_gifts", "auto"]
PAY = ["credit_card", "boleto", "voucher", "debit_card"]


def generate(n_orders: int = 5000, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    n_cust, n_prod = n_orders, 300
    si = rng.integers(0, len(STATES), n_cust)
    customers = pd.DataFrame({
        "customer_id": [f"c{i:06d}" for i in range(n_cust)],
        "customer_unique_id": [f"u{i:06d}" for i in rng.integers(0, n_cust * 9 // 10, n_cust)],
        "customer_city": [CITIES[i] for i in si],
        "customer_state": [STATES[i] for i in si],
    })

    products = pd.DataFrame({
        "product_id": [f"p{i:05d}" for i in range(n_prod)],
        "product_category_name": rng.choice(CATS, n_prod),
        "product_weight_g": rng.integers(100, 20000, n_prod).astype(float),
    })
    products.loc[rng.choice(n_prod, 15, replace=False), "product_category_name"] = np.nan  # dirty

    purchase = pd.Timestamp("2017-01-01") + pd.to_timedelta(rng.integers(0, 600 * 24 * 60, n_orders), unit="m")
    status = rng.choice(["delivered", "shipped", "canceled", "unavailable"], n_orders, p=[.9, .05, .04, .01])
    est = purchase + pd.to_timedelta(rng.integers(10, 30, n_orders), unit="D")
    deliv = purchase + pd.to_timedelta(rng.integers(3, 35, n_orders), unit="D")
    orders = pd.DataFrame({
        "order_id": [f"o{i:07d}" for i in range(n_orders)],
        "customer_id": customers["customer_id"].values[:n_orders],
        "order_status": status,
        "order_purchase_timestamp": purchase.strftime("%Y-%m-%d %H:%M:%S"),
        "order_delivered_customer_date": deliv.strftime("%Y-%m-%d %H:%M:%S"),
        "order_estimated_delivery_date": est.strftime("%Y-%m-%d %H:%M:%S"),
    })
    orders.loc[orders.order_status != "delivered", "order_delivered_customer_date"] = np.nan

    n_items = rng.integers(1, 4, n_orders)
    items = orders[["order_id"]].loc[orders.index.repeat(n_items)].reset_index(drop=True)
    items["order_item_id"] = items.groupby("order_id").cumcount() + 1
    items["product_id"] = rng.choice(products["product_id"], len(items))
    items["seller_id"] = [f"s{i:04d}" for i in rng.integers(0, 80, len(items))]
    items["price"] = rng.gamma(2.0, 45, len(items)).round(2) + 5
    items["freight_value"] = rng.gamma(2.0, 8, len(items)).round(2)

    totals = items.groupby("order_id")[["price", "freight_value"]].sum().sum(axis=1).reset_index(name="payment_value")
    payments = totals.assign(payment_sequential=1, payment_type=rng.choice(PAY, len(totals), p=[.74, .19, .04, .03]))
    payments = payments[["order_id", "payment_sequential", "payment_type", "payment_value"]]

    # inject duplicates (dirty data)
    orders = pd.concat([orders, orders.sample(40, random_state=1)])
    customers = pd.concat([customers, customers.sample(25, random_state=2)])

    for key, df in [("orders", orders), ("items", items), ("customers", customers),
                    ("products", products), ("payments", payments)]:
        df.to_csv(RAW_DIR / FILES[key], index=False)
    print(f"Sample data written to {RAW_DIR} ({n_orders} orders)")


if __name__ == "__main__":
    generate(int(sys.argv[1]) if len(sys.argv) > 1 else 5000)
