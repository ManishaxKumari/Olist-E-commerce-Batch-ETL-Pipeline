import pandas as pd
from etl.pipeline import clean_orders, build_dim_product, build_dim_date


def test_clean_orders_dedupes_filters_and_computes_delivery():
    o = pd.DataFrame({
        "order_id": ["a", "a", "b", "c"],
        "customer_id": ["x"] * 4,
        "order_status": ["delivered", "delivered", "canceled", "delivered"],
        "order_purchase_timestamp": ["2018-01-01 10:00:00"] * 3 + ["bad-date"],
        "order_delivered_customer_date": ["2018-01-06 10:00:00", "2018-01-06 10:00:00", None, None],
        "order_estimated_delivery_date": ["2018-01-04 10:00:00"] * 4,
    })
    r = clean_orders(o)
    assert list(r["order_id"]) == ["a"]
    assert r.iloc[0]["delivery_days"] == 5
    assert bool(r.iloc[0]["is_late"]) is True


def test_dim_product_fills_unknown_category():
    p = pd.DataFrame({"product_id": ["p1", "p1", "p2"],
                      "product_category_name": ["toys", "toys", None],
                      "product_weight_g": [1.0, 1.0, 2.0]})
    d = build_dim_product(p)
    assert len(d) == 2 and d.loc[d.product_id == "p2", "category"].iloc[0] == "unknown"


def test_dim_date_key_format():
    d = build_dim_date(pd.Series(pd.to_datetime(["2018-03-05", "2018-03-05"])))
    assert len(d) == 1 and d.iloc[0]["date_key"] == 20180305
