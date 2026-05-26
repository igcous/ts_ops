import pandas as pd
import numpy as np


def compute_anomaly_scores(daily_volume: pd.Series, window: int = 28) -> pd.DataFrame:
    df = daily_volume.rename("volume").to_frame()
    df["rolling_mean"] = df["volume"].rolling(window, min_periods=7).mean()
    df["rolling_std"] = df["volume"].rolling(window, min_periods=7).std()
    df["z_score"] = (df["volume"] - df["rolling_mean"]) / df["rolling_std"].replace(0, np.nan)
    df["anomaly_score"] = df["z_score"].clip(lower=0)
    df["is_anomaly"] = df["z_score"] > 2.0
    df = df.reset_index().rename(columns={"created_at": "date", "index": "date"})
    return df


def get_active_alerts(cases_df: pd.DataFrame, enforcement_df: pd.DataFrame, agents_df: pd.DataFrame) -> list:
    alerts = []
    today = pd.Timestamp.now()
    week_ago = today - pd.Timedelta(days=7)
    two_weeks_ago = today - pd.Timedelta(days=14)

    # Volume anomaly check (last 60 days)
    recent = cases_df[cases_df["created_at"] >= today - pd.Timedelta(days=60)].copy()
    if len(recent) > 7:
        daily_vol = recent.set_index("created_at").resample("D").size()
        scores_df = compute_anomaly_scores(daily_vol)
        anomalies = scores_df[scores_df["is_anomaly"]]
        for _, row in anomalies.tail(3).iterrows():
            date_str = str(row["date"])[:10]
            alerts.append({
                "level": "HIGH",
                "type": "volume_spike",
                "message": f"Case volume {row['z_score']:.1f}σ above baseline on {date_str} ({int(row['volume'])} cases)",
                "date": date_str,
            })

    # Fraud spike: WoW fraud share change
    cur_fraud_share = 0.0
    prev_fraud_share = 0.0
    cur_total = len(cases_df[cases_df["created_at"] >= week_ago])
    cur_fraud = len(cases_df[(cases_df["created_at"] >= week_ago) & (cases_df["category"] == "fraud")])
    prev_total = len(cases_df[(cases_df["created_at"] >= two_weeks_ago) & (cases_df["created_at"] < week_ago)])
    prev_fraud = len(cases_df[(cases_df["created_at"] >= two_weeks_ago) & (cases_df["created_at"] < week_ago) & (cases_df["category"] == "fraud")])

    if cur_total > 0:
        cur_fraud_share = cur_fraud / cur_total
    if prev_total > 0:
        prev_fraud_share = prev_fraud / prev_total

    if prev_fraud_share > 0:
        fraud_wow = (cur_fraud_share - prev_fraud_share) / prev_fraud_share
        if fraud_wow > 0.30:
            alerts.append({
                "level": "HIGH",
                "type": "fraud_spike",
                "message": f"Fraud share increased {fraud_wow:.0%} WoW ({prev_fraud_share:.1%} → {cur_fraud_share:.1%})",
                "date": str(today.date()),
            })

    # SLA degradation: p90 resolution time WoW
    resolved = cases_df.dropna(subset=["resolved_at"]).copy()
    resolved["resolution_hours"] = (resolved["resolved_at"] - resolved["created_at"]).dt.total_seconds() / 3600
    cur_resolved = resolved[resolved["created_at"] >= week_ago]
    prev_resolved = resolved[(resolved["created_at"] >= two_weeks_ago) & (resolved["created_at"] < week_ago)]

    if len(cur_resolved) >= 10 and len(prev_resolved) >= 10:
        cur_p90 = cur_resolved["resolution_hours"].quantile(0.90)
        prev_p90 = prev_resolved["resolution_hours"].quantile(0.90)
        if prev_p90 > 0 and (cur_p90 - prev_p90) / prev_p90 > 0.20:
            alerts.append({
                "level": "MEDIUM",
                "type": "sla_degradation",
                "message": f"P90 resolution time degraded {(cur_p90 - prev_p90) / prev_p90:.0%} WoW ({prev_p90:.0f}h → {cur_p90:.0f}h)",
                "date": str(today.date()),
            })

    # Escalation rate drift
    cur_esc_rate = 0.0
    if cur_total > 0:
        cur_esc = len(cases_df[(cases_df["created_at"] >= week_ago) & (cases_df["status"] == "escalated")])
        cur_esc_rate = cur_esc / cur_total
    if cur_esc_rate > 0.15:
        alerts.append({
            "level": "LOW",
            "type": "escalation_drift",
            "message": f"Escalation rate elevated at {cur_esc_rate:.1%} this week (baseline: 10%)",
            "date": str(today.date()),
        })

    return alerts
