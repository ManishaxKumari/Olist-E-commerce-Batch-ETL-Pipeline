# Olist E-commerce Batch ETL Pipeline

End-to-end batch ETL: raw CSVs -> cleaning/transformation (Pandas) -> data quality checks -> star-schema warehouse (PostgreSQL/SQLite) -> SQL analytics -> Streamlit dashboard.

## Architecture
```
Olist CSVs --> extract --> transform --> validate (DQ) --> load --> star schema --> SQL analytics + Streamlit
 (5 files)    (pandas)   (clean, keys,   (8 checks,      (idempotent   fact_sales
                          dim/fact)       fail-fast)      drop+create)  dim_customer / dim_product / dim_date
```

## Quick start
```bash
pip install -r requirements.txt

# Option A: no download, generates dirty Olist-shaped sample data
python -m etl.generate_data 5000
# Option B: real data -> download Kaggle "Brazilian E-Commerce Public Dataset by Olist"
#           and copy the 5 CSVs (orders, order_items, customers, products, order_payments) into data/raw/

python -m etl.pipeline            # runs ETL (SQLite by default -> warehouse.db)
pytest -q tests                   # unit tests
streamlit run dashboard/app.py    # dashboard
```

### Use PostgreSQL instead
```bash
docker compose up -d
export DB_URL=postgresql+psycopg2://etl:etl@localhost:5432/warehouse
python -m etl.pipeline
```

## Star schema
`fact_sales` (grain: one row per order item) -> `dim_customer`, `dim_product`, `dim_date`.

## What the transform does
- Dedupes orders/customers/products, parses dates, drops canceled/unavailable orders
- Fills missing categories with `unknown`
- Derives `delivery_days` and `is_late`
- Builds surrogate keys, `dim_date` (year/quarter/month/day), picks main payment type per order

## Data quality checks (fail-fast)
Non-empty fact, unique keys, no null FKs, positive price, non-negative freight, all date keys exist in `dim_date`.

## Analytics (`sql/analytics.sql`)
MoM growth (LAG), top-N categories per year (RANK), revenue share (window SUM), cumulative revenue, late-delivery rate (CTE), payment mix.

## Design decisions (interview talking points)
- **Why star schema?** Fast aggregations, simple joins for BI.
- **Idempotency:** schema.sql drops/recreates tables, so reruns never double-load.
- **Why fail-fast DQ checks?** Bad data should never reach the warehouse silently.
- **Next steps:** PySpark for transform, Parquet staging, Airflow DAG (daily), incremental loads, dbt.

## Resume bullet
> Built a batch ETL pipeline in Python/Pandas to clean and load 100K+ e-commerce records into a PostgreSQL star schema with automated data quality checks and unit tests; wrote analytical SQL (window functions, CTEs) and a Streamlit dashboard for sales insights.
