#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f "data/cases.csv" ]; then
    echo "Generating synthetic data..."
    python3 src/generate_data.py
    python3 src/load_db.py
else
    echo "Data files found, skipping generation. Delete data/ to regenerate."
fi

echo "Starting dashboard..."
streamlit run app/streamlit_app.py --server.port 8501
