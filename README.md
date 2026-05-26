# Trust & Safety Ops Intelligence Dashboard

A portfolio analytics stack simulating a T&S operations dashboard (synthetic data, SQLite, Python and Streamlit).

## Documentation

Design decisions, how the app works, KPI definitions and a walkthrough of each dashboard page are covered in `ts_ops_dashboard.pptx`.

## How to run

**First run** (generates data and launches the dashboard):
```bash
./run.sh
```

**Regenerate data from scratch:**
```bash
rm -rf data/ ts_ops.db && python3 src/generate_data.py && python3 src/load_db.py
```

**Launch dashboard only** (data already exists):
```bash
streamlit run app/streamlit_app.py --server.port 8501
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```
