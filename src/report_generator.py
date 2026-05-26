import pandas as pd


def generate_weekly_report(cases_df: pd.DataFrame, enforcement_df: pd.DataFrame, agents_df: pd.DataFrame) -> str:
    today = pd.Timestamp.now()
    week_start = today - pd.Timedelta(days=7)
    prev_week_start = today - pd.Timedelta(days=14)

    week_start_str = week_start.strftime("%B %d, %Y")
    week_end_str = today.strftime("%B %d, %Y")

    cur = cases_df[cases_df["created_at"] >= week_start]
    prev = cases_df[(cases_df["created_at"] >= prev_week_start) & (cases_df["created_at"] < week_start)]

    cur_vol = len(cur)
    prev_vol = len(prev)
    wow_pct = (cur_vol - prev_vol) / prev_vol * 100 if prev_vol else 0.0

    cur_backlog = int((cases_df["status"] != "closed").sum())
    prev_backlog_cases = cases_df[cases_df["created_at"] < week_start]
    prev_backlog = int((prev_backlog_cases["status"] != "closed").sum())
    backlog_delta = cur_backlog - prev_backlog

    cur_esc_rate = float((cur["status"] == "escalated").sum() / cur_vol) if cur_vol else 0.0

    top_cat = cur["category"].value_counts().idxmax() if cur_vol else "N/A"
    top_cat_n = int(cur["category"].value_counts().iloc[0]) if cur_vol else 0
    top_cat_pct = top_cat_n / cur_vol * 100 if cur_vol else 0.0

    cur_fraud_n = int((cur["category"] == "fraud").sum())
    cur_fraud_share = cur_fraud_n / cur_vol if cur_vol else 0.0
    prev_fraud_n = int((prev["category"] == "fraud").sum())
    prev_fraud_share = prev_fraud_n / prev_vol if prev_vol else 0.0
    fraud_wow = (cur_fraud_share - prev_fraud_share) / prev_fraud_share * 100 if prev_fraud_share else 0.0

    resolved = cases_df.dropna(subset=["resolved_at"]).copy()
    resolved["resolution_hours"] = (resolved["resolved_at"] - resolved["created_at"]).dt.total_seconds() / 3600
    cur_resolved = resolved[resolved["created_at"] >= week_start]
    prev_resolved_df = resolved[(resolved["created_at"] >= prev_week_start) & (resolved["created_at"] < week_start)]

    mean_res = float(cur_resolved["resolution_hours"].mean()) if len(cur_resolved) else 0.0
    median_res = float(cur_resolved["resolution_hours"].median()) if len(cur_resolved) else 0.0
    p90_res = float(cur_resolved["resolution_hours"].quantile(0.90)) if len(cur_resolved) else 0.0
    prev_p90 = float(prev_resolved_df["resolution_hours"].quantile(0.90)) if len(prev_resolved_df) else p90_res

    p90_change_pct = (p90_res - prev_p90) / prev_p90 * 100 if prev_p90 else 0.0

    cur_enf = enforcement_df[enforcement_df["action_date"] >= week_start] if enforcement_df is not None else pd.DataFrame()
    enf_count = len(cur_enf)
    cur_resolved_count = len(cur_resolved)
    enf_rate = enf_count / cur_resolved_count if cur_resolved_count else 0.0

    # Agent capacity
    cur_agents = agents_df[agents_df["date"] >= week_start] if "date" in agents_df.columns else pd.DataFrame()
    active_agents = int(cur_agents["agent_id"].nunique()) if len(cur_agents) else 0
    req_agents = int(cur_vol / (18 * 5)) + 1 if cur_vol else 0
    staffing_gap = req_agents - active_agents

    # ---- Build narrative ----

    # Executive Summary
    if wow_pct > 0:
        vol_direction = f"increased {wow_pct:.1f}%"
        vol_note = " Volume is elevated. Recommend reviewing capacity allocation." if wow_pct > 10 else ""
    elif wow_pct < 0:
        vol_direction = f"decreased {abs(wow_pct):.1f}%"
        vol_note = ""
    else:
        vol_direction = "remained flat"
        vol_note = ""

    backlog_note = f"up {backlog_delta:,}" if backlog_delta > 0 else f"down {abs(backlog_delta):,}" if backlog_delta < 0 else "unchanged"

    summary = (
        f"Case volume {vol_direction} week-over-week ({cur_vol:,} vs {prev_vol:,} cases).{vol_note}\n"
        f"Current backlog stands at {cur_backlog:,} cases ({backlog_note} from last week)."
    )

    # Key Drivers
    fraud_direction = "up" if fraud_wow > 0 else "down"
    fraud_line = f"Fraud share: {cur_fraud_share:.1%} ({fraud_direction} from {prev_fraud_share:.1%} last week)"

    fraud_alert = ""
    if abs(fraud_wow) > 30:
        fraud_alert = f"\n  ALERT: Fraud volume {('spiked' if fraud_wow > 0 else 'dropped')} {abs(fraud_wow):.0f}% WoW. {'Potential coordinated attack pattern — review detection rules.' if fraud_wow > 0 else 'Monitor for data integrity issues.'}"

    esc_note = "above" if cur_esc_rate > 0.10 else "below"
    drivers = (
        f"- Top category: {top_cat.title()} ({top_cat_n:,} cases, {top_cat_pct:.1f}% of weekly volume)\n"
        f"- {fraud_line}{fraud_alert}\n"
        f"- Escalation rate: {cur_esc_rate:.1%} ({esc_note} the 10% baseline)"
    )

    # Operational Metrics
    sla_warning = ""
    if p90_change_pct > 20:
        sla_warning = f"\n  WARNING: P90 resolution time degraded {p90_change_pct:.0f}% WoW. Backlog pressure detected."

    ops = (
        f"- Mean resolution time: {mean_res:.1f}h  |  Median: {median_res:.1f}h  |  P90: {p90_res:.1f}h{sla_warning}\n"
        f"- Enforcement actions taken: {enf_count:,} ({enf_rate:.1%} of resolved cases)"
    )

    # Recommendations
    recs = []
    if staffing_gap > 0:
        recs.append(f"Add {staffing_gap} agent(s) to meet projected demand of ~{cur_vol:,} cases next week.")
    if cur_fraud_share > 0.30:
        recs.append("Fraud category exceeds 30% of volume. Review automated detection rules and fraud routing logic.")
    if cur_esc_rate > 0.15:
        recs.append("Escalation rate is above 15% threshold. Audit case routing logic and agent triage guidelines.")
    if p90_res > 48:
        recs.append("P90 resolution time exceeds 48h SLA target. Prioritize clearing aged backlog cases.")
    recs.append(f"Continue monitoring {top_cat.title()} trends daily through end of week.")
    if not recs:
        recs.append("No critical actions required. Maintain current operational cadence.")

    rec_block = "\n".join(f"- {r}" for r in recs)

    report = f"""TRUST & SAFETY WEEKLY OPS REPORT
Week of {week_start_str} to {week_end_str}
Generated: {today.strftime("%Y-%m-%d %H:%M")}
{'=' * 55}

EXECUTIVE SUMMARY
{summary}

KEY DRIVERS
{drivers}

OPERATIONAL METRICS
{ops}

RECOMMENDATIONS
{rec_block}
"""
    return report
