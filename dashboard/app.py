"""Streamlit dashboard: streamlit run dashboard/app.py"""
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

sys.path.append(str(Path(__file__).resolve().parent.parent))
from etl.config import DB_URL  # noqa: E402

st.set_page_config(page_title="Olist Sales Dashboard", layout="wide")
engine = create_engine(DB_URL)


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, engine)


st.title("Olist E-commerce Sales Dashboard")

years = q("SELECT DISTINCT order_year FROM dim_date ORDER BY 1")["order_year"].tolist()
sel = st.sidebar.multiselect("Year", years, default=years)
if not sel:
    st.stop()
yr = ",".join(str(int(y)) for y in sel)

kpi = q(f"""SELECT COUNT(DISTINCT f.order_id) AS orders, ROUND(SUM(f.price),0) AS revenue,
            ROUND(AVG(f.price),2) AS aov_item, ROUND(AVG(f.delivery_days),1) AS avg_delivery
            FROM fact_sales f JOIN dim_date d ON f.date_key=d.date_key
            WHERE d.order_year IN ({yr})""").iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Orders", f"{int(kpi.orders):,}")
c2.metric("Revenue", f"R$ {kpi.revenue:,.0f}")
c3.metric("Avg item price", f"R$ {kpi.aov_item}")
c4.metric("Avg delivery (days)", kpi.avg_delivery)

monthly = q(f"""SELECT d.order_year*100+d.order_month AS ym, SUM(f.price) AS revenue
                FROM fact_sales f JOIN dim_date d ON f.date_key=d.date_key
                WHERE d.order_year IN ({yr}) GROUP BY 1 ORDER BY 1""")
monthly["ym"] = monthly["ym"].astype(str)
st.plotly_chart(px.line(monthly, x="ym", y="revenue", title="Monthly revenue", markers=True), use_container_width=True)

left, right = st.columns(2)
cat = q(f"""SELECT p.category, SUM(f.price) AS revenue FROM fact_sales f
            JOIN dim_product p ON f.product_key=p.product_key JOIN dim_date d ON f.date_key=d.date_key
            WHERE d.order_year IN ({yr}) GROUP BY 1 ORDER BY 2 DESC LIMIT 10""")
left.plotly_chart(px.bar(cat, x="revenue", y="category", orientation="h", title="Top categories"), use_container_width=True)

st_df = q(f"""SELECT c.state, SUM(f.price) AS revenue FROM fact_sales f
              JOIN dim_customer c ON f.customer_key=c.customer_key JOIN dim_date d ON f.date_key=d.date_key
              WHERE d.order_year IN ({yr}) GROUP BY 1 ORDER BY 2 DESC""")
right.plotly_chart(px.bar(st_df, x="state", y="revenue", title="Revenue by state"), use_container_width=True)
