-- Star schema (works on PostgreSQL and SQLite)
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_customer (
    customer_key       INTEGER PRIMARY KEY,
    customer_id        VARCHAR(50) NOT NULL,
    customer_unique_id VARCHAR(50),
    city               VARCHAR(100),
    state              VARCHAR(5)
);

CREATE TABLE dim_product (
    product_key INTEGER PRIMARY KEY,
    product_id  VARCHAR(50) NOT NULL,
    category    VARCHAR(100),
    weight_g    NUMERIC(10,2)
);

CREATE TABLE dim_date (
    date_key    INTEGER PRIMARY KEY,   -- yyyymmdd
    full_date   DATE NOT NULL,
    order_year  INTEGER,
    quarter     INTEGER,
    order_month INTEGER,
    month_name  VARCHAR(10),
    day_of_week VARCHAR(10)
);

CREATE TABLE fact_sales (
    sale_id       INTEGER PRIMARY KEY,
    order_id      VARCHAR(50) NOT NULL,
    order_item_id INTEGER,
    customer_key  INTEGER REFERENCES dim_customer(customer_key),
    product_key   INTEGER REFERENCES dim_product(product_key),
    date_key      INTEGER REFERENCES dim_date(date_key),
    order_status  VARCHAR(20),
    price         NUMERIC(10,2),
    freight_value NUMERIC(10,2),
    payment_type  VARCHAR(20),
    delivery_days INTEGER,
    is_late       BOOLEAN
);

CREATE INDEX idx_fact_date     ON fact_sales(date_key);
CREATE INDEX idx_fact_product  ON fact_sales(product_key);
CREATE INDEX idx_fact_customer ON fact_sales(customer_key);
