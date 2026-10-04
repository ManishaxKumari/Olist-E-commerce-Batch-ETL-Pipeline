-- 1. Monthly revenue + month-over-month growth (window: LAG)
WITH monthly AS (
    SELECT d.order_year, d.order_month, ROUND(SUM(f.price), 2) AS revenue
    FROM fact_sales f JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY d.order_year, d.order_month
)
SELECT order_year, order_month, revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_year, order_month))
             / LAG(revenue) OVER (ORDER BY order_year, order_month), 1) AS mom_growth_pct
FROM monthly ORDER BY order_year, order_month;

-- 2. Top 3 categories per year (window: RANK + PARTITION BY)
SELECT * FROM (
    SELECT d.order_year, p.category, ROUND(SUM(f.price), 2) AS revenue,
           RANK() OVER (PARTITION BY d.order_year ORDER BY SUM(f.price) DESC) AS rnk
    FROM fact_sales f
    JOIN dim_product p ON f.product_key = p.product_key
    JOIN dim_date d    ON f.date_key = d.date_key
    GROUP BY d.order_year, p.category
) t WHERE rnk <= 3 ORDER BY order_year, rnk;

-- 3. Revenue by state with share of total
SELECT c.state, ROUND(SUM(f.price), 2) AS revenue,
       ROUND(100.0 * SUM(f.price) / SUM(SUM(f.price)) OVER (), 1) AS pct_of_total
FROM fact_sales f JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.state ORDER BY revenue DESC;

-- 4. Running (cumulative) revenue
SELECT d.full_date, ROUND(SUM(f.price), 2) AS daily_revenue,
       ROUND(SUM(SUM(f.price)) OVER (ORDER BY d.full_date), 2) AS cumulative_revenue
FROM fact_sales f JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.full_date ORDER BY d.full_date;

-- 5. Late-delivery rate by state (CTE)
WITH delivered AS (
    SELECT c.state, f.is_late
    FROM fact_sales f JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE f.delivery_days IS NOT NULL
)
SELECT state, COUNT(*) AS deliveries,
       ROUND(100.0 * SUM(CASE WHEN is_late THEN 1 ELSE 0 END) / COUNT(*), 1) AS late_pct
FROM delivered GROUP BY state ORDER BY late_pct DESC;

-- 6. Payment type mix
SELECT payment_type, COUNT(DISTINCT order_id) AS orders, ROUND(SUM(price), 2) AS revenue
FROM fact_sales GROUP BY payment_type ORDER BY revenue DESC;
