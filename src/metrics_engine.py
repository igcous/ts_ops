import os
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE_DIR, "ts_ops.db")


def _engine():
    return create_engine(f"sqlite:///{DB_PATH}")


def load_cases() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM cases", _engine(), parse_dates=["created_at", "resolved_at"])
    return df


def load_enforcement() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM enforcement_actions", _engine(), parse_dates=["action_date"])
    return df


def load_agents() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM agents", _engine(), parse_dates=["date"])
    return df


def get_summary_kpis(cases_df: pd.DataFrame, enforcement_df: pd.DataFrame) -> dict:
    today = pd.Timestamp.now()
    week_start = today - pd.Timedelta(days=7)
    prev_week_start = today - pd.Timedelta(days=14)

    total = len(cases_df)
    backlog = int((cases_df["status"] != "closed").sum())
    escalation_rate = float((cases_df["status"] == "escalated").sum() / total) if total else 0.0

    resolved = cases_df.dropna(subset=["resolved_at"]).copy()
    resolved["resolution_hours"] = (resolved["resolved_at"] - resolved["created_at"]).dt.total_seconds() / 3600
    mean_res = float(resolved["resolution_hours"].mean()) if len(resolved) else 0.0
    median_res = float(resolved["resolution_hours"].median()) if len(resolved) else 0.0
    p90_res = float(resolved["resolution_hours"].quantile(0.90)) if len(resolved) else 0.0

    resolved_count = (cases_df["status"] != "open").sum()
    enforcement_count = len(enforcement_df) if enforcement_df is not None else 0
    enforcement_rate = float(enforcement_count / resolved_count) if resolved_count else 0.0

    fraud_share = float((cases_df["category"] == "fraud").sum() / total) if total else 0.0

    cur_vol = int((cases_df["created_at"] >= week_start).sum())
    prev_vol = int(((cases_df["created_at"] >= prev_week_start) & (cases_df["created_at"] < week_start)).sum())
    wow_volume_change = float((cur_vol - prev_vol) / prev_vol * 100) if prev_vol else 0.0

    cur_backlog = int((cases_df["status"] != "closed").sum())
    cases_prev = cases_df[cases_df["created_at"] < week_start]
    prev_backlog = int((cases_prev["status"] != "closed").sum())
    backlog_change = cur_backlog - prev_backlog

    return {
        "total_cases": total,
        "backlog_size": backlog,
        "escalation_rate": escalation_rate,
        "mean_resolution_hours": mean_res,
        "median_resolution_hours": median_res,
        "p90_resolution_hours": p90_res,
        "enforcement_rate": enforcement_rate,
        "fraud_share": fraud_share,
        "wow_volume_change": wow_volume_change,
        "backlog_change": backlog_change,
        "current_week_volume": cur_vol,
        "prior_week_volume": prev_vol,
    }


def get_volume_trend(df: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    series = df.set_index("created_at").resample(freq).size().rename("case_volume")
    rolling = series.rolling(7, min_periods=1).mean().rename("rolling_7d_avg")
    result = pd.concat([series, rolling], axis=1).reset_index()
    result.rename(columns={"created_at": "date"}, inplace=True)
    return result


def get_category_breakdown(df: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    tmp = df.copy()
    tmp["period"] = tmp["created_at"].dt.to_period(freq).dt.start_time
    pivot = tmp.groupby(["period", "category"]).size().unstack(fill_value=0).reset_index()
    pivot.rename(columns={"period": "date"}, inplace=True)
    return pivot


def get_resolution_time_by_severity(df: pd.DataFrame) -> pd.DataFrame:
    resolved = df.dropna(subset=["resolved_at"]).copy()
    resolved["resolution_hours"] = (resolved["resolved_at"] - resolved["created_at"]).dt.total_seconds() / 3600
    result = resolved.groupby("severity")["resolution_hours"].agg(
        mean_hours="mean",
        median_hours="median",
        p90_hours=lambda x: x.quantile(0.90),
        count="count",
    ).reset_index()
    return result


def get_enforcement_trend(cases_df: pd.DataFrame, enforcement_df: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    enf = enforcement_df.copy()
    enf["period"] = enf["action_date"].dt.to_period(freq).dt.start_time
    grouped = enf.groupby(["period", "action_type"]).size().unstack(fill_value=0).reset_index()
    for col in ["warning", "removal", "ban"]:
        if col not in grouped.columns:
            grouped[col] = 0
    grouped.rename(columns={"period": "date"}, inplace=True)

    resolved = cases_df[cases_df["status"] != "open"].copy()
    resolved["period"] = resolved["resolved_at"].dt.to_period(freq).dt.start_time
    res_counts = resolved.groupby("period").size().reset_index(name="resolved_cases")
    res_counts.rename(columns={"period": "date"}, inplace=True)

    merged = grouped.merge(res_counts, on="date", how="left")
    merged["resolved_cases"] = merged["resolved_cases"].fillna(1)
    enf_total = merged[["warning", "removal", "ban"]].sum(axis=1)
    merged["enforcement_rate"] = enf_total / merged["resolved_cases"]
    return merged


def get_agent_workload(agents_df: pd.DataFrame) -> pd.DataFrame:
    daily = agents_df.groupby("date").agg(
        cases_handled=("cases_handled", "sum"),
        active_agents=("agent_id", "nunique"),
        total_hours=("hours_worked", "sum"),
    ).reset_index()
    daily["cases_per_agent"] = daily["cases_handled"] / daily["active_agents"].replace(0, np.nan)
    daily["avg_hours"] = daily["total_hours"] / daily["active_agents"].replace(0, np.nan)
    return daily


def get_backlog_trend(df: pd.DataFrame) -> pd.DataFrame:
    dates = pd.date_range(df["created_at"].min().floor("D"), df["created_at"].max().floor("D"), freq="D")
    backlog_counts = []
    for d in dates:
        snapshot = df[df["created_at"].dt.floor("D") <= d]
        open_count = int(
            ((snapshot["status"] != "closed") | (snapshot["resolved_at"].isna()) |
             (snapshot["resolved_at"].dt.floor("D") > d)).sum()
        )
        backlog_counts.append(open_count)
    return pd.DataFrame({"date": dates, "backlog": backlog_counts})
