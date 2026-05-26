# T&S Ops Intelligence Dashboard

Portfolio project simulating a Trust & Safety operations analytics stack. Greenfield Python/Streamlit app with synthetic data.

## Commands

```bash
# First run (generates data + launches dashboard)
./run.sh

# Regenerate data from scratch
rm -rf data/ ts_ops.db && python3 src/generate_data.py && python3 src/load_db.py

# Launch dashboard only (data already exists)
streamlit run app/streamlit_app.py --server.port 8501

# Install dependencies
pip install -r requirements.txt --break-system-packages
```

## Architecture

```
src/generate_data.py   →  data/*.csv
src/load_db.py         →  ts_ops.db (SQLite)
src/metrics_engine.py  ←  reads ts_ops.db, all KPI logic lives here
src/forecasting.py         consumes pd.Series from metrics_engine
src/anomaly_detection.py   consumes daily volume DataFrame
src/report_generator.py    consumes all three DataFrames
app/streamlit_app.py   ←  imports all src/ modules
```

## Key Conventions

- **No Streamlit imports in `src/`** — all analytics functions are pure pandas/numpy. Only `app/streamlit_app.py` touches Streamlit.
- **Use `python3`** — `python` is not in PATH on this machine.
- **DB path**: `ts_ops.db` lives in the project root. All `src/` modules resolve it relative to `__file__` using `os.path.join(os.path.dirname(__file__), "..", "ts_ops.db")`.
- **Data is reproducible**: `generate_data.py` seeds both `Faker` and `numpy.random` at 42. Re-running produces identical output.
- **Caching**: data loading is cached at the Streamlit layer via `@st.cache_data(ttl=300)`. Do not add caching inside `src/` modules.

## Data Model

| Table | Rows | Key columns |
|---|---|---|
| `cases` | 20,000 | `case_id`, `created_at`, `resolved_at`, `category`, `severity`, `status`, `channel` |
| `enforcement_actions` | ~12,300 | `case_id`, `action_type`, `action_date` |
| `agents` | ~5,800 | `agent_id`, `date`, `cases_handled`, `hours_worked` |

Categories: `fraud / abuse / identity / spam`. Statuses: `open / closed / escalated`.

## Dashboard Pages

1. Executive Overview — KPI tiles, volume chart with anomaly overlay, alerts
2. Case Operations — volume trend (daily/weekly/monthly toggle), category breakdown, resolution by severity
3. Enforcement & Risk — enforcement trend, fraud share %, severity scatter
4. Capacity & Forecasting — agent workload, 28-day forecast with confidence band, staffing gap table
5. Insights Report — WoW KPI table + "Generate Report" button → downloadable narrative

## KPI Reference

- **Backlog**: `status != 'closed'`
- **Resolution time**: `(resolved_at - created_at)` in hours, tracked at mean/median/p90
- **Escalation rate**: `escalated / total`
- **Enforcement rate**: `enforcement_actions / resolved_cases`
- **Fraud share**: `fraud_cases / total_cases`
- **Anomaly threshold**: daily volume > rolling 28-day mean + 2σ
