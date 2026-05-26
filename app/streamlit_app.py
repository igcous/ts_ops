import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.anomaly_detection import compute_anomaly_scores, get_active_alerts
from src.forecasting import forecast_agent_demand, forecast_case_volume
from src.metrics_engine import (
    get_agent_workload,
    get_backlog_trend,
    get_category_breakdown,
    get_enforcement_trend,
    get_resolution_time_by_severity,
    get_summary_kpis,
    get_volume_trend,
    load_agents,
    load_cases,
    load_enforcement,
)
from src.report_generator import generate_weekly_report

st.set_page_config(page_title="T&S Ops Dashboard", layout="wide", page_icon="🛡️")


@st.cache_data(ttl=300)
def load_all_data():
    return load_cases(), load_enforcement(), load_agents()


cases_df, enforcement_df, agents_df = load_all_data()

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("🛡️ T&S Ops Dashboard")
page = st.sidebar.radio(
    "Navigation",
    ["Executive Overview", "Case Operations", "Enforcement & Risk", "Capacity & Forecasting", "Insights Report"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Global Filters")

min_date = cases_df["created_at"].min().date()
max_date = cases_df["created_at"].max().date()
date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

all_cats = ["fraud", "abuse", "identity", "spam"]
selected_cats = st.sidebar.multiselect("Categories", all_cats, default=all_cats)

# Apply global filter
start_dt, end_dt = (date_range[0], date_range[1]) if len(date_range) == 2 else (min_date, max_date)
mask = (
    (cases_df["created_at"].dt.date >= start_dt)
    & (cases_df["created_at"].dt.date <= end_dt)
    & (cases_df["category"].isin(selected_cats if selected_cats else all_cats))
)
filtered = cases_df[mask].copy()


# ── Page 1: Executive Overview ───────────────────────────────────────────────
if page == "Executive Overview":
    st.title("Executive Overview")

    kpis = get_summary_kpis(filtered, enforcement_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Cases", f"{kpis['total_cases']:,}", delta=f"{kpis['wow_volume_change']:+.1f}% WoW")
    col2.metric("Backlog", f"{kpis['backlog_size']:,}", delta=f"{kpis['backlog_change']:+,}")
    col3.metric("Avg Resolution", f"{kpis['mean_resolution_hours']:.1f}h")
    col4.metric("Escalation Rate", f"{kpis['escalation_rate']:.1%}")

    st.markdown("---")

    # Volume chart with anomaly overlay
    vol_df = get_volume_trend(filtered, freq="D")
    daily_series = filtered.set_index("created_at").resample("D").size()
    scores_df = compute_anomaly_scores(daily_series)
    anomalies = scores_df[scores_df["is_anomaly"]].copy()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=vol_df["date"], y=vol_df["case_volume"],
        fill="tozeroy", name="Daily Volume",
        line=dict(color="#4C78A8"),
    ))
    fig.add_trace(go.Scatter(
        x=vol_df["date"], y=vol_df["rolling_7d_avg"],
        name="7-Day Avg", line=dict(dash="dash", color="#F58518"),
    ))
    if len(anomalies):
        fig.add_trace(go.Scatter(
            x=anomalies["date"], y=anomalies["volume"],
            mode="markers", name="Anomaly",
            marker=dict(color="red", size=10, symbol="x"),
        ))
    fig.update_layout(title="Daily Case Volume", xaxis_title="Date", yaxis_title="Cases", height=350)
    st.plotly_chart(fig, use_container_width=True)

    # Alerts
    alerts = get_active_alerts(filtered, enforcement_df, agents_df)
    if alerts:
        st.markdown("### Active Alerts")
        for alert in alerts:
            if alert["level"] == "HIGH":
                st.error(f"**[HIGH]** {alert['message']}")
            elif alert["level"] == "MEDIUM":
                st.warning(f"**[MEDIUM]** {alert['message']}")
            else:
                st.info(f"**[LOW]** {alert['message']}")
    else:
        st.success("No active alerts.")

    # KPI summary table
    st.markdown("### KPI Summary")
    kpi_rows = [
        ("Total Cases", f"{kpis['total_cases']:,}"),
        ("Backlog Size", f"{kpis['backlog_size']:,}"),
        ("Escalation Rate", f"{kpis['escalation_rate']:.1%}"),
        ("Fraud Share", f"{kpis['fraud_share']:.1%}"),
        ("Enforcement Rate", f"{kpis['enforcement_rate']:.1%}"),
        ("Mean Resolution", f"{kpis['mean_resolution_hours']:.1f}h"),
        ("Median Resolution", f"{kpis['median_resolution_hours']:.1f}h"),
        ("P90 Resolution", f"{kpis['p90_resolution_hours']:.1f}h"),
    ]
    kpi_df = pd.DataFrame(kpi_rows, columns=["Metric", "Value"])
    st.dataframe(kpi_df, use_container_width=True, hide_index=True)


# ── Page 2: Case Operations ───────────────────────────────────────────────────
elif page == "Case Operations":
    st.title("Case Operations")

    freq_label = st.radio("Granularity", ["Daily", "Weekly", "Monthly"], horizontal=True)
    freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}
    vol_df = get_volume_trend(filtered, freq=freq_map[freq_label])

    fig = px.area(
        vol_df, x="date", y="case_volume",
        title=f"{freq_label} Case Volume",
        labels={"date": "Date", "case_volume": "Cases"},
    )
    fig.add_scatter(
        x=vol_df["date"], y=vol_df["rolling_7d_avg"],
        name="7-Day Rolling Avg", line=dict(dash="dash", color="orange"),
    )
    st.plotly_chart(fig, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        cat_df = get_category_breakdown(filtered, freq="W")
        cats_present = [c for c in ["fraud", "abuse", "identity", "spam"] if c in cat_df.columns]
        fig2 = px.area(
            cat_df, x="date", y=cats_present,
            title="Category Breakdown (Weekly)",
            labels={"date": "Week", "value": "Cases", "variable": "Category"},
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_right:
        sev_df = get_resolution_time_by_severity(filtered)
        fig3 = px.bar(
            sev_df, x="mean_hours", y="severity",
            orientation="h",
            title="Avg Resolution Time by Severity",
            labels={"mean_hours": "Hours", "severity": "Severity"},
            color="severity",
            color_continuous_scale="RdYlGn_r",
            error_x=sev_df["p90_hours"] - sev_df["mean_hours"],
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("### Status Distribution")
    status_counts = filtered["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    fig4 = px.pie(status_counts, names="status", values="count", title="Case Status Breakdown")
    st.plotly_chart(fig4, use_container_width=True)


# ── Page 3: Enforcement & Risk ────────────────────────────────────────────────
elif page == "Enforcement & Risk":
    st.title("Enforcement & Risk")

    kpis = get_summary_kpis(filtered, enforcement_df)
    c1, c2, c3 = st.columns(3)
    c1.metric("Enforcement Rate", f"{kpis['enforcement_rate']:.1%}")
    c2.metric("Fraud Share", f"{kpis['fraud_share']:.1%}")
    ban_count = len(enforcement_df[enforcement_df["action_type"] == "ban"])
    total_enf = len(enforcement_df)
    c3.metric("Ban Rate", f"{ban_count / total_enf:.1%}" if total_enf else "N/A")

    st.markdown("---")

    enf_trend = get_enforcement_trend(filtered, enforcement_df, freq="W")
    action_cols = [c for c in ["warning", "removal", "ban"] if c in enf_trend.columns]
    fig_enf = px.bar(
        enf_trend, x="date", y=action_cols,
        title="Enforcement Actions by Type (Weekly)",
        labels={"date": "Week", "value": "Count", "variable": "Action Type"},
        barmode="stack",
    )
    st.plotly_chart(fig_enf, use_container_width=True)

    col_l, col_r = st.columns(2)

    with col_l:
        fraud_weekly = filtered.set_index("created_at").resample("W").apply(
            lambda x: (x["category"] == "fraud").sum() / max(len(x), 1) * 100
        ).reset_index()
        fraud_weekly.columns = ["date", "fraud_share_pct"]
        fig_fraud = px.line(
            fraud_weekly, x="date", y="fraud_share_pct",
            title="Fraud Share % (Weekly)",
            labels={"date": "Week", "fraud_share_pct": "Fraud Share (%)"},
        )
        fig_fraud.add_hline(y=25, line_dash="dash", line_color="red", annotation_text="25% threshold")
        st.plotly_chart(fig_fraud, use_container_width=True)

    with col_r:
        scatter_df = filtered.dropna(subset=["resolved_at"]).copy()
        scatter_df["resolution_hours"] = (
            (scatter_df["resolved_at"] - scatter_df["created_at"]).dt.total_seconds() / 3600
        ).clip(upper=200)
        sample = scatter_df.sample(min(2000, len(scatter_df)), random_state=42)
        fig_sc = px.scatter(
            sample, x="severity", y="resolution_hours", color="category",
            title="Severity vs Resolution Time",
            labels={"severity": "Severity", "resolution_hours": "Hours to Resolve", "category": "Category"},
            opacity=0.5,
        )
        st.plotly_chart(fig_sc, use_container_width=True)


# ── Page 4: Capacity & Forecasting ───────────────────────────────────────────
elif page == "Capacity & Forecasting":
    st.title("Capacity & Forecasting")

    workload = get_agent_workload(agents_df)

    fig_wl = go.Figure()
    fig_wl.add_trace(go.Bar(x=workload["date"], y=workload["cases_handled"], name="Cases Handled", opacity=0.7))
    fig_wl.add_trace(go.Scatter(
        x=workload["date"], y=workload["active_agents"] * 18,
        name="Agent Capacity (cases)", line=dict(color="red", dash="dash"),
        yaxis="y",
    ))
    fig_wl.update_layout(
        title="Daily Cases Handled vs Agent Capacity",
        xaxis_title="Date", yaxis_title="Cases", height=350,
    )
    st.plotly_chart(fig_wl, use_container_width=True)

    st.markdown("---")
    st.markdown("### Forecast: Next 4 Weeks")

    daily_series = filtered.set_index("created_at").resample("D").size()
    if len(daily_series) >= 14:
        forecast_df = forecast_case_volume(daily_series, periods=28)
        current_agents = int(agents_df["agent_id"].nunique())

        fig_fc = go.Figure()
        hist = forecast_df[~forecast_df["is_forecast"]]
        fut = forecast_df[forecast_df["is_forecast"]]

        fig_fc.add_trace(go.Scatter(
            x=daily_series.index, y=daily_series.values,
            name="Actual Volume", line=dict(color="#4C78A8"),
        ))
        fig_fc.add_trace(go.Scatter(
            x=fut["date"], y=fut["forecast_volume"],
            name="Forecast", line=dict(color="#F58518", dash="dash"),
        ))
        fig_fc.add_trace(go.Scatter(
            x=fut["date"], y=fut["upper_bound"],
            fill=None, line_color="rgba(0,0,0,0)", showlegend=False,
        ))
        fig_fc.add_trace(go.Scatter(
            x=fut["date"], y=fut["lower_bound"],
            fill="tonexty", fillcolor="rgba(245,133,24,0.15)",
            line_color="rgba(0,0,0,0)", name="Confidence Band",
        ))
        fig_fc.update_layout(title="Case Volume Forecast (28-Day)", xaxis_title="Date", yaxis_title="Cases", height=350)
        st.plotly_chart(fig_fc, use_container_width=True)

        demand_df = forecast_agent_demand(forecast_df, current_agents=current_agents)
        st.markdown("### Staffing Gap Analysis")
        display = demand_df[["date", "forecast_volume", "required_agents", "current_agents", "staffing_gap"]].copy()
        display["date"] = display["date"].dt.strftime("%Y-%m-%d")
        display.columns = ["Date", "Forecast Cases", "Required Agents", "Current Agents", "Gap"]

        def color_gap(val):
            if val > 0:
                return "background-color: #ffcccc"
            elif val < 0:
                return "background-color: #ccffcc"
            return ""

        st.dataframe(
            display.style.map(color_gap, subset=["Gap"]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.warning("Not enough data to generate a forecast. Expand your date range.")

    st.markdown("---")
    st.markdown("### Agent Workload Summary")
    recent_wl = workload.tail(14)
    st.line_chart(recent_wl.set_index("date")[["cases_per_agent", "avg_hours"]])


# ── Page 5: Insights Report ───────────────────────────────────────────────────
elif page == "Insights Report":
    st.title("Weekly Intelligence Report")

    kpis = get_summary_kpis(filtered, enforcement_df)

    st.markdown("### KPI Week-over-Week Changes")
    wow_data = {
        "Metric": ["Case Volume", "Backlog", "Escalation Rate", "Fraud Share", "Enforcement Rate"],
        "This Week": [
            kpis["current_week_volume"],
            kpis["backlog_size"],
            f"{kpis['escalation_rate']:.1%}",
            f"{kpis['fraud_share']:.1%}",
            f"{kpis['enforcement_rate']:.1%}",
        ],
        "WoW Change": [
            f"{kpis['wow_volume_change']:+.1f}%",
            f"{kpis['backlog_change']:+,}",
            "—",
            "—",
            "—",
        ],
    }
    st.dataframe(pd.DataFrame(wow_data), use_container_width=True, hide_index=True)

    st.markdown("---")
    if st.button("Generate Weekly Report", type="primary"):
        with st.spinner("Analyzing data and generating report..."):
            report_text = generate_weekly_report(filtered, enforcement_df, agents_df)
        st.text_area("Report", report_text, height=500)
        st.download_button(
            "Download Report (.txt)",
            data=report_text,
            file_name="weekly_ops_report.txt",
            mime="text/plain",
        )
