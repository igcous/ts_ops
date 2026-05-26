import os
import pandas as pd
from sqlalchemy import create_engine

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "ts_ops.db")


def load_db():
    engine = create_engine(f"sqlite:///{DB_PATH}")

    tables = [
        ("cases", os.path.join(DATA_DIR, "cases.csv"), ["created_at", "resolved_at"]),
        ("enforcement_actions", os.path.join(DATA_DIR, "enforcement.csv"), ["action_date"]),
        ("agents", os.path.join(DATA_DIR, "agents.csv"), ["date"]),
    ]

    for table_name, csv_path, date_cols in tables:
        df = pd.read_csv(csv_path, parse_dates=date_cols)
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"Loaded {len(df):,} rows into '{table_name}'")

    print(f"Database written to {DB_PATH}")


if __name__ == "__main__":
    load_db()
