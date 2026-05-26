import os
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
np.random.seed(42)

N_CASES = 20_000
N_AGENTS = 25
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _random_datetimes(start: pd.Timestamp, end: pd.Timestamp, n: int) -> np.ndarray:
    delta_seconds = int((end - start).total_seconds())
    offsets = np.random.randint(0, delta_seconds, size=n)
    return np.array([start + timedelta(seconds=int(s)) for s in offsets])


def generate_cases(n: int = N_CASES) -> pd.DataFrame:
    today = pd.Timestamp.now().floor("s")
    start = today - timedelta(days=365)

    categories = ["fraud", "abuse", "identity", "spam"]
    cat_weights = [0.25, 0.30, 0.20, 0.25]
    severities = [1, 2, 3, 4, 5]
    sev_weights = [0.10, 0.25, 0.35, 0.20, 0.10]
    statuses = ["open", "closed", "escalated"]
    status_weights = [0.15, 0.75, 0.10]
    channels = ["user_report", "automated", "admin"]
    chan_weights = [0.55, 0.30, 0.15]

    case_ids = [f"CASE-{uuid.uuid4().hex[:8].upper()}" for _ in range(n)]
    created_at = _random_datetimes(start, today, n)
    category = np.random.choice(categories, size=n, p=cat_weights)
    severity = np.random.choice(severities, size=n, p=sev_weights)
    status = np.random.choice(statuses, size=n, p=status_weights)
    channel = np.random.choice(channels, size=n, p=chan_weights)

    base_hours = {1: 72, 2: 48, 3: 24, 4: 12, 5: 4}
    resolved_at = []
    for i in range(n):
        if status[i] == "open":
            resolved_at.append(pd.NaT)
        else:
            bh = base_hours[severity[i]]
            duration_hours = np.random.exponential(scale=bh)
            duration_hours = min(duration_hours, 720.0)
            resolved_at.append(created_at[i] + timedelta(hours=duration_hours))

    df = pd.DataFrame({
        "case_id": case_ids,
        "created_at": created_at,
        "resolved_at": resolved_at,
        "category": category,
        "severity": severity,
        "status": status,
        "channel": channel,
    })

    # Inject 3–5 fraud spikes
    n_spikes = np.random.randint(3, 6)
    spike_dates = []
    candidate = start + timedelta(days=30)
    for _ in range(n_spikes):
        if candidate >= today - timedelta(days=30):
            break
        jitter = np.random.randint(0, int((today - timedelta(days=30) - candidate).days))
        spike_date = candidate + timedelta(days=jitter)
        spike_dates.append(spike_date)
        candidate = spike_date + timedelta(days=30)

    fraud_idx = df[df["category"] == "fraud"].index.tolist()
    for spike_date in spike_dates:
        sample_size = min(500, len(fraud_idx))
        chosen = np.random.choice(fraud_idx, size=sample_size, replace=False)
        for idx in chosen:
            jitter_days = np.random.uniform(-3, 3)
            new_dt = spike_date + timedelta(days=jitter_days)
            new_dt = max(start, min(today, new_dt))
            df.at[idx, "created_at"] = new_dt
            if df.at[idx, "status"] != "open":
                bh = base_hours[df.at[idx, "severity"]]
                dur = min(np.random.exponential(scale=bh), 720.0)
                df.at[idx, "resolved_at"] = new_dt + timedelta(hours=dur)

    return df


def generate_enforcement(cases_df: pd.DataFrame) -> pd.DataFrame:
    eligible = cases_df[cases_df["status"].isin(["closed", "escalated"])].copy()
    sampled = eligible.sample(frac=0.70, random_state=42)

    action_types = ["warning", "removal", "ban"]
    action_weights = [0.50, 0.30, 0.20]

    rows = []
    for _, row in sampled.iterrows():
        action = np.random.choice(action_types, p=action_weights)
        hours_after = np.random.uniform(0, 24)
        action_date = row["resolved_at"] + timedelta(hours=hours_after)
        rows.append({"case_id": row["case_id"], "action_type": action, "action_date": action_date})
        # 15% of bans also get a prior warning
        if action == "ban" and np.random.random() < 0.15:
            prior_hours = np.random.uniform(1, hours_after) if hours_after > 1 else 0.5
            prior_date = row["resolved_at"] + timedelta(hours=prior_hours)
            rows.append({"case_id": row["case_id"], "action_type": "warning", "action_date": prior_date})

    return pd.DataFrame(rows)


def generate_agents(start: pd.Timestamp, end: pd.Timestamp, n_agents: int = N_AGENTS) -> pd.DataFrame:
    agent_ids = [f"AGT-{str(i).zfill(3)}" for i in range(1, n_agents + 1)]
    all_days = pd.bdate_range(start=start, end=end)

    rows = []
    for agent_id in agent_ids:
        for day in all_days:
            if np.random.random() > 0.90:
                continue
            # 5% chance PTO
            if np.random.random() < 0.05:
                rows.append({"agent_id": agent_id, "date": day.date(), "cases_handled": 0, "hours_worked": 0.0})
            else:
                cases = np.random.poisson(lam=18)
                hours = round(np.random.uniform(6.5, 8.5), 2)
                rows.append({"agent_id": agent_id, "date": day.date(), "cases_handled": cases, "hours_worked": hours})

    return pd.DataFrame(rows)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    today = pd.Timestamp.now().floor("s")
    start = today - timedelta(days=365)

    print("Generating cases...")
    cases_df = generate_cases(N_CASES)
    cases_df.to_csv(os.path.join(DATA_DIR, "cases.csv"), index=False)

    print("Generating enforcement actions...")
    enforcement_df = generate_enforcement(cases_df)
    enforcement_df.to_csv(os.path.join(DATA_DIR, "enforcement.csv"), index=False)

    print("Generating agent records...")
    agents_df = generate_agents(start, today)
    agents_df.to_csv(os.path.join(DATA_DIR, "agents.csv"), index=False)

    print(f"Generated {len(cases_df):,} cases, {len(enforcement_df):,} enforcement actions, {len(agents_df):,} agent records")


if __name__ == "__main__":
    main()
