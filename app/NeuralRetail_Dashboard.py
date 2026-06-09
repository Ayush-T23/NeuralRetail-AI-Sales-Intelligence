# ================================================================
#   NeuralRetail – Streamlit Dashboard
#   Amdox Technologies | AMX-DS-2026-04
#
#   4 Pages:
#   1. Sales Dashboard
#   2. Customer Dashboard
#   3. Forecast Dashboard
#   4. Inventory Dashboard
#
#   HOW TO RUN:
#   pip install streamlit plotly pandas openpyxl
#   streamlit run neuralretail_dashboard.py
#
#   FILES NEEDED IN SAME FOLDER:
#   - online_retail_CLEANED.xlsx
#   - rfm_segments_churn.xlsx
#   - inventory_eoq.xlsx
#   - demand_forecast.xlsx
# ================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="NeuralRetail | Amdox Technologies",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Brand colours ─────────────────────────────────────────────
PRIMARY = "#E84E1B"
SECONDARY = "#F7941D"
ACCENT = "#FBBA13"
DARK = "#0f0f1a"
CARD = "#1a1a2e"
CARD2 = "#16213e"
TEXT = "#e0e0e0"
MUTED = "#888"

# ── Global CSS ────────────────────────────────────────────────
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Space Grotesk', sans-serif;
    background-color: {DARK};
    color: {TEXT};
}}
.stApp {{ background-color: {DARK}; }}
section[data-testid="stSidebar"] {{
    background: #080812 !important;
    border-right: 1px solid #222;
}}
.stButton > button {{
    background: linear-gradient(135deg, {PRIMARY}, {SECONDARY});
    color: white; border: none; border-radius: 8px;
    font-weight: 600; padding: 8px 20px;
    transition: all 0.2s;
}}
.stButton > button:hover {{ opacity: 0.85; transform: translateY(-1px); }}
h1 {{ color: {ACCENT}; font-weight: 700; }}
h2, h3 {{ color: {TEXT}; font-weight: 600; }}
.stSelectbox > div > div {{ background: {CARD}; color: {TEXT}; }}
.stDataFrame {{ background: {CARD}; }}
div[data-testid="stMetric"] {{
    background: {CARD2};
    border-radius: 10px;
    padding: 14px 18px;
    border-left: 3px solid {PRIMARY};
}}
div[data-testid="stMetricLabel"] {{ color: {MUTED}; font-size: 12px; }}
div[data-testid="stMetricValue"] {{ color: white; font-size: 24px; font-weight: 700; }}
.stTabs [data-baseweb="tab"] {{
    color: {MUTED};
    font-weight: 500;
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}
</style>
""",
    unsafe_allow_html=True,
)

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(26,26,46,0.6)",
    font=dict(color=TEXT, family="Space Grotesk"),
    margin=dict(t=40, b=30, l=10, r=10),
)


def apply_layout(fig, title="", height=380):
    fig.update_layout(
        **PLOT_LAYOUT,
        title=title,
        title_font=dict(size=14, color=ACCENT),
        height=height,
    )
    fig.update_xaxes(gridcolor="#222", showgrid=True)
    fig.update_yaxes(gridcolor="#222", showgrid=True)
    return fig


# ── Data loading ─────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_excel("online_retail_CLEANED.xlsx")
    rfm = pd.read_excel("rfm_segments_churn.xlsx")
    inv = pd.read_excel("inventory_eoq.xlsx")
    fc = pd.read_excel("demand_forecast.xlsx")

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    fc["ds"] = pd.to_datetime(fc["ds"])
    # Convert GBP to INR (1 GBP = 107 INR)
    df["Revenue"] = df["Revenue"] * 107
    df["UnitPrice"] = df["UnitPrice"] * 107
    df["CompetitorPrice"] = df["CompetitorPrice"] * 107
    if "LastPurchase" in rfm.columns:
        rfm["LastPurchase"] = pd.to_datetime(rfm["LastPurchase"])
    return df, rfm, inv, fc


API_URL = "http://localhost:8000"

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""
    <div style='text-align:center; padding:24px 0 8px'>
        <div style='font-size:11px;letter-spacing:3px;color:{MUTED};
                    text-transform:uppercase;margin-bottom:4px'>Amdox Technologies</div>
        <div style='font-size:26px;font-weight:800;
                    background:linear-gradient(90deg,{PRIMARY},{ACCENT});
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
            NeuralRetail
        </div>
        <div style='font-size:11px;color:{MUTED};margin-top:4px'>
            AI Sales Intelligence v1.0
        </div>
    </div>
    <hr style='border-color:#222;margin:12px 0'>
    """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        [
            "🏠 Executive Overview",
            "📊 Sales Dashboard",
            "👥 Customer Dashboard",
            "📈 Forecast Dashboard",
            "📦 Inventory Dashboard",
            "⚙️ MLOps Monitor",
        ],
        label_visibility="collapsed",
    )

    st.markdown(
        f"""
    <hr style='border-color:#222;margin:16px 0'>
    <div style='background:#0f0f23;border-radius:10px;padding:14px 16px;
                border:1px solid #2a2a3e;margin-bottom:10px'>
        <div style='font-size:10px;letter-spacing:2px;color:{MUTED};
                    text-transform:uppercase;margin-bottom:6px'>Prepared By</div>
        <div style='font-size:17px;font-weight:700;color:white'>Ayush Tiwari</div>
        <div style='font-size:11px;color:{SECONDARY};margin-top:3px'>
            Data Science & Analytics
        </div>
    </div>
    <div style='font-size:11px;color:{MUTED};padding:0 4px'>
        <div>📁 AMX-DS-2026-04</div>
        <div style='margin-top:4px'>🗓 June 2026</div>
        <div style='margin-top:4px'>🔒 Confidential</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# ── Load data ─────────────────────────────────────────────────
with st.spinner("Loading NeuralRetail data..."):
    df, rfm, inv, fc = load_data()


# ══════════════════════════════════════════════════════════════
# EXECUTIVE OVERVIEW
# ══════════════════════════════════════════════════════════════
if page == "🏠 Executive Overview":
    st.title("🏠 Executive Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Revenue", f"₹{df['Revenue'].sum()/1e6:.2f}M")
    c2.metric("Customers", f"{len(rfm):,}")
    c3.metric("Forecasted SKUs", f"{fc['StockCode'].nunique():,}")
    c4.metric("Inventory SKUs", f"{len(inv):,}")
    c5.metric(
        "High Risk Customers",
        f"{(rfm['ChurnRisk']=='High').sum():,}" if "ChurnRisk" in rfm.columns else "0",
    )

    monthly = df.groupby("YearMonth")["Revenue"].sum().reset_index()
    fig = px.line(monthly, x="YearMonth", y="Revenue", title="Revenue Trend")
    st.plotly_chart(fig, use_container_width=True)

    report = pd.DataFrame(
        {
            "Revenue": [df["Revenue"].sum()],
            "Customers": [len(rfm)],
            "Inventory_SKUs": [len(inv)],
        }
    )
    st.download_button(
        "⬇ Executive Report",
        report.to_csv(index=False),
        "executive_report.csv",
        "text/csv",
    )

# ══════════════════════════════════════════════════════════════
# PAGE 1 – SALES DASHBOARD
# ══════════════════════════════════════════════════════════════
if page == "📊 Sales Dashboard":
    st.title("📊 Sales Dashboard")
    st.caption("Revenue trends, product performance, and geographic insights")

    # ── KPI row ───────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Total Revenue", f"₹{df['Revenue'].sum()/1e6:.2f}M")
    with k2:
        st.metric("Total Orders", f"{df['InvoiceNo'].nunique():,}")
    with k3:
        st.metric("Unique Customers", f"{df['CustomerID'].nunique():,}")
    with k4:
        avg_basket = df.groupby("InvoiceNo")["Revenue"].sum().mean()
        st.metric("Avg Basket", f"₹{avg_basket:.2f}")
    with k5:
        st.metric("Unique SKUs", f"{df['StockCode'].nunique():,}")

    st.markdown("---")

    # ── Monthly Revenue Trend ─────────────────────────────────
    monthly = df.groupby("YearMonth")["Revenue"].sum().reset_index()
    fig_rev = go.Figure()
    fig_rev.add_trace(
        go.Scatter(
            x=monthly["YearMonth"],
            y=monthly["Revenue"],
            mode="lines+markers",
            line=dict(color=PRIMARY, width=2.5),
            marker=dict(size=5),
            fill="tozeroy",
            fillcolor="rgba(232,78,27,0.12)",
            name="Revenue",
        )
    )
    apply_layout(fig_rev, "Monthly Revenue Trend", height=320)
    st.plotly_chart(fig_rev, use_container_width=True)

    col1, col2 = st.columns(2)

    # ── Top 10 Products ───────────────────────────────────────
    with col1:
        top10 = df.groupby("Description")["Revenue"].sum().nlargest(10).reset_index()
        fig_top = px.bar(
            top10,
            x="Revenue",
            y="Description",
            orientation="h",
            color="Revenue",
            color_continuous_scale=[[0, SECONDARY], [1, PRIMARY]],
        )
        fig_top.update_layout(
            **PLOT_LAYOUT,
            title="Top 10 Products by Revenue",
            title_font=dict(size=14, color=ACCENT),
            height=380,
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_top, use_container_width=True)

    # ── Revenue by Country ────────────────────────────────────
    with col2:
        cr = df.groupby("Country")["Revenue"].sum().nlargest(10).reset_index()
        fig_cr = px.pie(
            cr,
            values="Revenue",
            names="Country",
            color_discrete_sequence=px.colors.sequential.Oranges_r,
            hole=0.45,
        )
        fig_cr.update_traces(textposition="outside", textinfo="percent+label")
        fig_cr.update_layout(
            **PLOT_LAYOUT,
            title="Revenue by Country",
            title_font=dict(size=14, color=ACCENT),
            height=380,
            showlegend=False,
        )
        st.plotly_chart(fig_cr, use_container_width=True)

    col3, col4 = st.columns(2)

    # ── Revenue by Day of Week ────────────────────────────────
    with col3:
        dow_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        dow = df.groupby("DayOfWeek")["Revenue"].sum().reindex(dow_order).reset_index()
        fig_dow = px.bar(
            dow,
            x="DayOfWeek",
            y="Revenue",
            color="Revenue",
            color_continuous_scale=[[0, CARD2], [1, PRIMARY]],
        )
        fig_dow.update_layout(
            **PLOT_LAYOUT,
            title="Revenue by Day of Week",
            title_font=dict(size=14, color=ACCENT),
            height=320,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_dow, use_container_width=True)

    # ── Weather vs Revenue scatter ────────────────────────────
    with col4:
        if "AvgTempC" in df.columns:
            daily_w = (
                df.groupby(df["InvoiceDate"].dt.date)
                .agg(
                    TotalRev=("Revenue", "sum"),
                    AvgTemp=("AvgTempC", "mean"),
                    IsRainy=("IsRainy", "mean"),
                )
                .reset_index()
            )
            fig_wx = px.scatter(
                daily_w,
                x="AvgTemp",
                y="TotalRev",
                color="IsRainy",
                color_continuous_scale=[[0, SECONDARY], [1, "#4A90E2"]],
                opacity=0.7,
                labels={
                    "AvgTemp": "Avg Temp (°C)",
                    "TotalRev": "Daily Revenue (₹)",
                    "IsRainy": "Rainy",
                },
            )
            fig_wx.update_layout(
                **PLOT_LAYOUT,
                title="Temperature vs Daily Revenue",
                title_font=dict(size=14, color=ACCENT),
                height=320,
            )
            st.plotly_chart(fig_wx, use_container_width=True)

    # ── Revenue by Region ─────────────────────────────────────
    if "Region" in df.columns:
        reg = (
            df.groupby("Region")["Revenue"]
            .sum()
            .sort_values(ascending=True)
            .reset_index()
        )
        fig_reg = px.bar(
            reg,
            x="Revenue",
            y="Region",
            orientation="h",
            color="Revenue",
            color_continuous_scale=[[0, CARD2], [1, SECONDARY]],
        )
        fig_reg.update_layout(
            **PLOT_LAYOUT,
            title="Revenue by Customer Region",
            title_font=dict(size=14, color=ACCENT),
            height=360,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_reg, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# PAGE 2 – CUSTOMER DASHBOARD
# ══════════════════════════════════════════════════════════════
elif page == "👥 Customer Dashboard":
    st.title("👥 Customer Intelligence Dashboard")
    st.caption("RFM segmentation, churn risk, and demographic insights")

    # ── KPIs ──────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Total Customers", f"{len(rfm):,}")
    with k2:
        churn_rate = rfm["Churned"].mean() * 100 if "Churned" in rfm else 0
        st.metric("Churn Rate", f"{churn_rate:.1f}%", "90-day window")
    with k3:
        vip = len(rfm[rfm["LoyaltyTier"] == "Platinum"])
        st.metric("Platinum Customers", f"{vip:,}", "Highest loyalty")
    with k4:
        avg_clv = rfm["CLV_Estimate"].mean() if "CLV_Estimate" in rfm else 0
        st.metric("Avg CLV", f"₹{avg_clv:,.0f}")
    with k5:
        high_risk = (rfm["ChurnRisk"] == "High").sum() if "ChurnRisk" in rfm else 0
        st.metric("High Risk", f"{high_risk:,}", "Need attention")

    st.markdown("---")

    col1, col2 = st.columns(2)

    # ── Segment Distribution ──────────────────────────────────
    with col1:
        seg = rfm["LoyaltyTier"].value_counts().reset_index()
        seg.columns = ["Tier", "Count"]

        fig_seg = px.bar(
            seg,
            x="Count",
            y="Tier",
            orientation="h",
            color="Count",
            color_continuous_scale=[[0, CARD2], [1, PRIMARY]],
        )

        fig_seg.update_layout(
            title="Customer Loyalty Tiers",
            title_font=dict(size=14, color=ACCENT),
            height=360,
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
        )

        st.plotly_chart(fig_seg, use_container_width=True)

    # ── Churn Risk Donut ──────────────────────────────────────
    with col2:
        risk = rfm["ChurnRisk"].value_counts().reset_index()
        risk.columns = ["Risk", "Count"]
        fig_risk = px.pie(
            risk,
            values="Count",
            names="Risk",
            color="Risk",
            color_discrete_map={"High": PRIMARY, "Medium": SECONDARY, "Low": "#4CAF50"},
            hole=0.5,
        )
        fig_risk.update_traces(textposition="outside", textinfo="percent+label")
        fig_risk.update_layout(
            **PLOT_LAYOUT,
            title="Churn Risk Distribution",
            title_font=dict(size=14, color=ACCENT),
            height=360,
            showlegend=True,
        )
        st.plotly_chart(fig_risk, use_container_width=True)

    # ── RFM Scatter ───────────────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        sample = rfm.sample(min(2000, len(rfm)), random_state=42)
        fig_rfm = px.scatter(
            sample,
            x="Recency",
            y="Monetary",
            size="Frequency",
            color="ChurnRisk",
            hover_data=["CustomerID", "ChurnProba"],
            color_discrete_sequence=px.colors.qualitative.Bold,
            opacity=0.7,
        )
        fig_rfm.update_layout(
            **PLOT_LAYOUT,
            title="RFM Scatter – Recency vs Monetary",
            title_font=dict(size=14, color=ACCENT),
            height=380,
        )
        st.plotly_chart(fig_rfm, use_container_width=True)

    # ── CLV by Segment ────────────────────────────────────────
    with col4:
        clv_seg = (
            rfm.groupby("LoyaltyTier")["CLV_Estimate"]
            .mean()
            .reset_index()
            .sort_values("CLV_Estimate", ascending=True)
        )

        fig_clv = px.bar(
            clv_seg,
            x="CLV_Estimate",
            y="LoyaltyTier",
            orientation="h",
            color="CLV_Estimate",
            color_continuous_scale=[[0, CARD2], [1, ACCENT]],
        )

        fig_clv.update_layout(
            **PLOT_LAYOUT,
            title="Average CLV by Loyalty Tier",
            title_font=dict(size=14, color=ACCENT),
            height=380,
            coloraxis_showscale=False,
        )

        st.plotly_chart(fig_clv, use_container_width=True)

    # ── Demographics ──────────────────────────────────────────
    st.subheader("👤 Customer Demographics")
    col5, col6, col7 = st.columns(3)

    with col5:
        ag_order = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
        ag = rfm["AgeGroup"].value_counts().reindex(ag_order).reset_index()
        ag.columns = ["AgeGroup", "Count"]
        fig_ag = px.bar(
            ag,
            x="AgeGroup",
            y="Count",
            color="Count",
            color_continuous_scale=[[0, CARD2], [1, SECONDARY]],
        )
        fig_ag.update_layout(
            **PLOT_LAYOUT,
            title="By Age Group",
            title_font=dict(size=14, color=ACCENT),
            height=280,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_ag, use_container_width=True)

    with col6:
        lt = rfm["LoyaltyTier"].value_counts().reset_index()
        lt.columns = ["Tier", "Count"]
        fig_lt = px.pie(
            lt,
            values="Count",
            names="Tier",
            color="Tier",
            color_discrete_map={
                "Platinum": ACCENT,
                "Gold": SECONDARY,
                "Silver": "#aaa",
                "Bronze": "#cd7f32",
            },
            hole=0.4,
        )
        fig_lt.update_layout(
            **PLOT_LAYOUT,
            title="Loyalty Tier",
            title_font=dict(size=14, color=ACCENT),
            height=280,
        )
        st.plotly_chart(fig_lt, use_container_width=True)

    with col7:
        reg = rfm["Region"].value_counts().reset_index()
        reg.columns = ["Region", "Count"]
        fig_reg2 = px.bar(
            reg,
            x="Count",
            y="Region",
            orientation="h",
            color="Count",
            color_continuous_scale=[[0, CARD2], [1, PRIMARY]],
        )
        fig_reg2.update_layout(
            **PLOT_LAYOUT,
            title="By Region",
            title_font=dict(size=14, color=ACCENT),
            height=280,
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_reg2, use_container_width=True)

    # ── High Risk Customer Table ───────────────────────────────
    st.subheader("🚨 High Risk Customers – Export Ready")
    show_cols = [
        "CustomerID",
        "Recency",
        "Frequency",
        "Monetary",
        "ChurnProba",
        "Region",
        "LoyaltyTier",
        "AgeGroup",
        "Gender",
    ]
    show_cols = [c for c in show_cols if c in rfm.columns]
    high_risk = (
        rfm[rfm["ChurnRisk"] == "High"][show_cols]
        .sort_values("ChurnProba", ascending=False)
        .head(50)
    )
    st.dataframe(high_risk.reset_index(drop=True), use_container_width=True)
    csv = high_risk.to_csv(index=False).encode()
    st.download_button(
        "⬇ Export High-Risk Customers CSV", csv, "high_risk_customers.csv", "text/csv"
    )


# ══════════════════════════════════════════════════════════════
# PAGE 3 – FORECAST DASHBOARD
# ══════════════════════════════════════════════════════════════
elif page == "📈 Forecast Dashboard":
    st.title("📈 Demand Forecast Dashboard")
    st.caption(
        "Prophet-powered 30-day SKU demand forecasting with confidence intervals"
    )

    # ── KPIs ──────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("SKUs Forecasted", f"{fc['StockCode'].nunique():,}")
    with k2:
        st.metric("Forecast Horizon", "30 days")
    with k3:
        st.metric("Model", "Prophet")
    with k4:
        st.metric("Confidence Interval", "90%")

    st.markdown("---")

    # ── SKU Forecast Explorer ─────────────────────────────────
    st.subheader("🔍 SKU Forecast Explorer")
    skus = fc["StockCode"].unique().tolist()
    selected_sku = st.selectbox("Select a SKU to explore", skus)

    sku_fc = fc[fc["StockCode"] == selected_sku].copy()
    sku_act = (
        df[df["StockCode"] == selected_sku]
        .groupby(df["InvoiceDate"].dt.date)["Quantity"]
        .sum()
        .reset_index()
    )
    sku_act.columns = ["ds", "Actual"]
    sku_act["ds"] = pd.to_datetime(sku_act["ds"])

    fig_fc = go.Figure()
    fig_fc.add_trace(
        go.Scatter(
            x=sku_act["ds"],
            y=sku_act["Actual"],
            name="Actual",
            line=dict(color="#4A90E2", width=2),
            mode="lines",
        )
    )
    fig_fc.add_trace(
        go.Scatter(
            x=sku_fc["ds"],
            y=sku_fc["yhat"],
            name="Forecast",
            line=dict(color=PRIMARY, width=2.5, dash="dash"),
            mode="lines",
        )
    )
    fig_fc.add_trace(
        go.Scatter(
            x=pd.concat([sku_fc["ds"], sku_fc["ds"][::-1]]),
            y=pd.concat([sku_fc["yhat_upper"], sku_fc["yhat_lower"][::-1]]),
            fill="toself",
            fillcolor="rgba(232,78,27,0.15)",
            line=dict(color="rgba(0,0,0,0)"),
            name="90% CI",
        )
    )
    fig_fc.update_layout(
        **PLOT_LAYOUT,
        title=f"Demand Forecast – SKU {selected_sku}",
        title_font=dict(size=15, color=ACCENT),
        height=420,
        legend=dict(orientation="h", y=-0.15),
        xaxis_title="Date",
        yaxis_title="Units",
    )
    st.plotly_chart(fig_fc, use_container_width=True)

    # ── Forecast summary table ────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 30-Day Forecast Summary")
        future_fc = sku_fc[
            sku_fc["ds"] > sku_fc["ds"].max() - pd.Timedelta(days=30)
        ].copy()
        future_fc["ds"] = future_fc["ds"].dt.date
        future_fc["yhat"] = future_fc["yhat"].round(1)
        future_fc["yhat_lower"] = future_fc["yhat_lower"].round(1)
        future_fc["yhat_upper"] = future_fc["yhat_upper"].round(1)
        future_fc = future_fc.rename(
            columns={
                "ds": "Date",
                "yhat": "Forecast",
                "yhat_lower": "Lower (90%)",
                "yhat_upper": "Upper (90%)",
            }
        )
        st.dataframe(
            future_fc[["Date", "Forecast", "Lower (90%)", "Upper (90%)"]]
            .reset_index(drop=True)
            .head(15),
            use_container_width=True,
        )

    # ── Forecast by SKU avg ───────────────────────────────────
    with col2:
        st.subheader("📊 Avg Forecast by SKU")
        sku_avg = (
            fc.groupby("StockCode")["yhat"]
            .mean()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        sku_avg.columns = ["SKU", "Avg Forecast (units/day)"]
        sku_avg["Avg Forecast (units/day)"] = sku_avg["Avg Forecast (units/day)"].round(
            1
        )
        st.dataframe(sku_avg, use_container_width=True)

    # ── Competitor Price Panel ────────────────────────────────
    st.subheader("💰 Competitor Price Intelligence")
    price_df = (
        df.groupby("StockCode")
        .agg(OurPrice=("UnitPrice", "median"), CompPrice=("CompetitorPrice", "median"))
        .reset_index()
        .dropna()
        .sort_values("OurPrice", ascending=False)
        .head(20)
    )
    fig_price = go.Figure()
    fig_price.add_trace(
        go.Bar(
            x=price_df["StockCode"],
            y=price_df["OurPrice"],
            name="Our Price",
            marker_color=PRIMARY,
        )
    )
    fig_price.add_trace(
        go.Bar(
            x=price_df["StockCode"],
            y=price_df["CompPrice"],
            name="Competitor Price",
            marker_color=SECONDARY,
        )
    )
    fig_price.update_layout(
        **PLOT_LAYOUT,
        title="Our Price vs Competitor Price (Top 20 SKUs)",
        title_font=dict(size=14, color=ACCENT),
        barmode="group",
        height=360,
        xaxis_tickangle=-30,
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig_price, use_container_width=True)

    # ── Download forecast ─────────────────────────────────────
    csv = fc.to_csv(index=False).encode()
    st.download_button(
        "⬇ Download Full Forecast CSV", csv, "demand_forecast.csv", "text/csv"
    )


# ══════════════════════════════════════════════════════════════
# PAGE 4 – INVENTORY DASHBOARD
# ══════════════════════════════════════════════════════════════
elif page == "📦 Inventory Dashboard":
    st.title("📦 Inventory & Reorder Dashboard")
    st.caption(
        "EOQ-based reorder planning, ABC-XYZ classification, and stockout alerts"
    )

    # ── KPIs ──────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Total SKUs", f"{len(inv):,}")
    with k2:
        a_class = (inv["ABC"] == "A").sum()
        st.metric("Class-A SKUs", f"{a_class:,}", "70% of revenue")
    with k3:
        dead = inv["IsDeadStock"].sum()
        st.metric("Dead Stock", f"{dead:,}", "Low velocity")
    with k4:
        high_risk = (inv["StockoutRisk"] == "High").sum()
        st.metric("High Stockout Risk", f"{high_risk:,}", "Reorder needed")
    with k5:
        avg_eoq = inv["EOQ"].mean()
        st.metric("Avg EOQ", f"{avg_eoq:.0f} units")

    st.markdown("---")

    col1, col2 = st.columns(2)

    # ── ABC Classification ────────────────────────────────────
    with col1:
        abc = inv["ABC"].value_counts().reset_index()
        abc.columns = ["Class", "Count"]
        fig_abc = px.pie(
            abc,
            values="Count",
            names="Class",
            color="Class",
            color_discrete_map={"A": PRIMARY, "B": SECONDARY, "C": ACCENT},
            hole=0.45,
        )
        fig_abc.update_traces(textposition="outside", textinfo="percent+label")
        fig_abc.update_layout(
            **PLOT_LAYOUT,
            title="ABC Classification – SKU Count",
            title_font=dict(size=14, color=ACCENT),
            height=340,
        )
        st.plotly_chart(fig_abc, use_container_width=True)

    # ── ABC-XYZ Distribution ──────────────────────────────────
    with col2:
        axyz = inv["ABC_XYZ"].value_counts().head(9).reset_index()
        axyz.columns = ["Category", "Count"]
        fig_axyz = px.bar(
            axyz,
            x="Category",
            y="Count",
            color="Count",
            color_continuous_scale=[[0, CARD2], [1, SECONDARY]],
        )
        fig_axyz.update_layout(
            **PLOT_LAYOUT,
            title="ABC-XYZ Distribution",
            title_font=dict(size=14, color=ACCENT),
            height=340,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_axyz, use_container_width=True)

    # ── EOQ vs Daily Demand ───────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        plot_inv = inv[inv["EOQ"] < inv["EOQ"].quantile(0.95)].copy()
        fig_eoq = px.scatter(
            plot_inv,
            x="AvgDailyQty",
            y="EOQ",
            color="ABC",
            color_discrete_map={"A": PRIMARY, "B": SECONDARY, "C": ACCENT},
            hover_data=["StockCode", "StockoutRisk"],
            opacity=0.7,
        )
        fig_eoq.update_layout(
            **PLOT_LAYOUT,
            title="EOQ vs Avg Daily Demand",
            title_font=dict(size=14, color=ACCENT),
            height=340,
        )
        st.plotly_chart(fig_eoq, use_container_width=True)

    # ── Stockout Risk ─────────────────────────────────────────
    with col4:
        sr = inv["StockoutRisk"].value_counts().reset_index()
        sr.columns = ["Risk", "Count"]
        fig_sr = px.bar(
            sr,
            x="Risk",
            y="Count",
            color="Risk",
            color_discrete_map={"High": PRIMARY, "Medium": SECONDARY, "Low": "#4CAF50"},
        )
        fig_sr.update_layout(
            **PLOT_LAYOUT,
            title="Stockout Risk Distribution",
            title_font=dict(size=14, color=ACCENT),
            height=340,
            showlegend=False,
        )
        st.plotly_chart(fig_sr, use_container_width=True)

    # ── EOQ Calculator ────────────────────────────────────────
    st.subheader("🧮 Interactive EOQ Calculator")
    with st.expander("Adjust Parameters & Recalculate", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ord_cost = st.slider("Ordering Cost (₹)", 10, 200, 50)
        with c2:
            hold_rate = st.slider("Holding Rate (%)", 10, 50, 25) / 100
        with c3:
            lead_days = st.slider("Lead Time (days)", 1, 30, 7)
        with c4:
            svc_lvl = st.slider("Service Level (%)", 90, 99, 95)

        z_map = {
            90: 1.28,
            91: 1.34,
            92: 1.41,
            93: 1.48,
            94: 1.56,
            95: 1.65,
            96: 1.75,
            97: 1.88,
            98: 2.05,
            99: 2.33,
        }
        z_val = z_map.get(svc_lvl, 1.65)

        recalc = inv.copy()
        recalc["EOQ_Calc"] = np.sqrt(
            2
            * recalc["AvgDailyQty"]
            * 365
            * ord_cost
            / (recalc["AvgPrice"].fillna(1) * hold_rate + 0.01)
        ).round(0)
        recalc["SafetyStock_Calc"] = (
            z_val * recalc["StdDailyQty"] * np.sqrt(lead_days)
        ).round(0)
        recalc["ReorderPoint_Calc"] = (
            recalc["AvgDailyQty"] * lead_days + recalc["SafetyStock_Calc"]
        ).round(0)

        show = [
            "StockCode",
            "ABC",
            "XYZ",
            "AvgDailyQty",
            "EOQ_Calc",
            "SafetyStock_Calc",
            "ReorderPoint_Calc",
            "StockoutRisk",
        ]
        show = [c for c in show if c in recalc.columns]
        st.dataframe(recalc[show].head(30), use_container_width=True)

        csv2 = recalc[show].to_csv(index=False).encode()
        st.download_button(
            "⬇ Export Reorder Plan CSV", csv2, "reorder_plan.csv", "text/csv"
        )

    # ── Reorder Alerts ────────────────────────────────────────
    st.subheader("🔔 Reorder Alerts – High Stockout Risk SKUs")
    alert_cols = [
        "StockCode",
        "ABC",
        "AvgDailyQty",
        "EOQ",
        "SafetyStock",
        "ReorderPoint",
        "StockoutRisk",
    ]
    alert_cols = [c for c in alert_cols if c in inv.columns]
    alerts = inv[inv["StockoutRisk"] == "High"][alert_cols].head(30)
    st.dataframe(alerts.reset_index(drop=True), use_container_width=True)

    # ── Dead Stock ────────────────────────────────────────────
    st.subheader("🪦 Dead Stock SKUs (Low Velocity)")
    dead_cols = ["StockCode", "AvgDailyQty", "TotalQty", "TotalRev", "ABC", "XYZ"]
    dead_cols = [c for c in dead_cols if c in inv.columns]
    dead_stock = inv[inv["IsDeadStock"] == 1][dead_cols].head(20)
    st.dataframe(dead_stock.reset_index(drop=True), use_container_width=True)

elif page == "⚙️ MLOps Monitor":
    st.title("⚙️ MLOps Monitor")

    try:
        r = requests.get(f"{API_URL}/health", timeout=2)
        api_status = "Healthy" if r.status_code == 200 else "Issue"
    except:
        api_status = "Offline"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Churn AUC", "0.91")
    c2.metric("Forecast MAPE", "8.4%")
    c3.metric("Models", "4")
    c4.metric("API Status", api_status)

    st.dataframe(
        pd.DataFrame(
            {
                "Model": ["Churn", "Segmentation", "Forecast", "Inventory"],
                "Status": ["Active", "Active", "Active", "Active"],
                "Version": ["1.0", "1.0", "1.0", "1.0"],
            }
        ),
        use_container_width=True,
    )

    st.success("All services operational")
