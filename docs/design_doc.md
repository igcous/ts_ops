# 📊 Trust & Safety Operations Intelligence Dashboard
## Design Document (GoFundMe S&O Analyst Portfolio Project)

---

# 1. 🧭 Overview

This project simulates a **Trust & Safety Operations analytics system** similar to what a Strategy & Operations Analyst at GoFundMe would use.

It tracks operational performance of a fictional moderation / Trust & Safety team, focusing on:

- Case management performance
- Risk and enforcement trends
- Operational capacity vs demand
- KPI reporting and forecasting
- Weekly business review automation

The system demonstrates:
> KPI design, SQL analytics, BI dashboards, forecasting, and business insight generation.

---

# 2. 🎯 Goals

## Primary goals
- Build recurring KPI dashboards for Trust & Safety operations
- Analyze trends in case volume and resolution efficiency
- Identify operational bottlenecks and anomalies
- Support capacity planning and forecasting
- Generate automated weekly business summaries

## Secondary goals
- Showcase SQL + Python + BI thinking
- Demonstrate KPI definition discipline
- Simulate real-world ops reporting workflows

---

# 3. 👤 Target Users (Simulated)

- Trust & Safety Operations team
- Strategy & Operations Analyst
- Ops Manager / Head of Integrity

---

# 4. 🧱 System Architecture

```
[Data Generator (Python)]
        ↓
   [Raw Dataset (CSV / SQLite)]
        ↓
   [Data Processing Layer (Python + SQL)]
        ↓
   [Metrics / KPI Engine]
        ↓
   [Streamlit Dashboard UI]
        ↓
   [Weekly Report Generator (Text + Charts)]
```

---

# 5. 📦 Data Model

## 5.1 Core Tables

### 1. `cases`
Represents Trust & Safety cases.

| Field | Type | Description |
|------|------|-------------|
| case_id | string | Unique identifier |
| created_at | datetime | Case creation time |
| resolved_at | datetime | Resolution time |
| category | string | fraud / abuse / identity / spam |
| severity | int (1–5) | Risk severity |
| status | string | open / closed / escalated |
| channel | string | user_report / automated / admin |

---

### 2. `enforcement_actions`

| Field | Type | Description |
|------|------|-------------|
| case_id | string | linked case |
| action_type | string | warning / removal / ban |
| action_date | datetime | timestamp |

---

### 3. `agents`

| Field | Type | Description |
|------|------|-------------|
| agent_id | string | analyst ID |
| date | date | working day |
| cases_handled | int | workload |
| hours_worked | float | capacity tracking |

---

## 5.2 Synthetic Data Rules

- 10,000–50,000 cases
- Time range: last 6–12 months
- Fraud cases should spike randomly (simulate “events”)
- Resolution time varies by severity
- 5–15% cases escalated

---

# 6. 📊 KPI Definitions (Critical Section)

---

## 6.1 Operational KPIs

### Case Volume
Total number of cases created per time period.

---

### Backlog Size
```
open_cases = cases where status != closed
```

---

### Resolution Time (SLA Metric)
```
resolved_at - created_at (in hours)
```
Tracked as:
- mean
- median
- 90th percentile

---

### Escalation Rate
```
escalated_cases / total_cases
```

---

## 6.2 Quality KPIs

### Enforcement Rate
```
enforcement_actions / resolved_cases
```

### Fraud Share
```
fraud_cases / total_cases
```

---

## 6.3 Efficiency KPIs

### Cases per Agent
```
total_cases / active_agents
```

### Capacity Utilization
```
cases_handled / max_capacity
```

---

## 6.4 Risk Signal KPIs

### Anomaly Score (simple heuristic)
- spike in fraud cases (>2 std deviations)
- sudden backlog growth
- resolution time increase >20%

---

# 7. 📈 Analytics Layer

## 7.1 Trend Analysis
- Daily/weekly/monthly case volume trends
- Category distribution changes over time

---

## 7.2 Bottleneck Detection
- Rising resolution time
- Increasing backlog
- Agent overload

---

## 7.3 Anomaly Detection (rule-based)
Trigger alerts when:
- Case volume > rolling mean + 2σ
- Fraud category spikes >30% WoW
- SLA breaches exceed threshold

---

# 8. 🔮 Forecasting Module

## Objective
Estimate future workload and staffing needs.

---

## 8.1 Forecast Targets
- Case volume (next 2–4 weeks)
- Required agent capacity

---

## 8.2 Method
- 7-day moving average OR exponential smoothing

---

## 8.3 Output Example
- Expected cases next week: 1,250
- Required agents: 18
- Current agents: 14 → deficit: 4 agents

---

# 9. 📊 Dashboard Design (Streamlit)

## Page 1: Executive Overview
- Total cases (weekly/monthly)
- Avg resolution time
- Backlog size
- Key anomalies (alerts panel)

---

## Page 2: Case Operations
- Time series of case volume
- Category breakdown
- Severity distribution

---

## Page 3: Enforcement & Risk
- enforcement actions over time
- fraud trends
- escalation rate

---

## Page 4: Capacity & Forecasting
- agent workload vs demand
- forecast charts
- staffing gap analysis

---

## Page 5: Insights / Weekly Report
Auto-generated text:
- key changes this week
- risks
- operational recommendations

---

# 10. 🧾 Weekly Business Review Generator

## Output format:

### Summary
- “Case volume increased X% WoW…”

### Key Drivers
- Fraud spike in category Y
- Increased user reports

### Operational Impact
- backlog increased
- SLA degradation

### Recommendations
- increase staffing
- adjust routing rules

---

# 11. 🛠 Tech Stack

## Core stack
- Python (data + logic)
- Pandas (processing)
- SQLite (optional persistence)
- Streamlit (dashboard UI)

## Optional enhancements
- Plotly (charts)
- Faker (data generation)
- SQLAlchemy (if using DB)

---

# 12. 📁 Project Structure

```
t&s-ops-dashboard/
│
├── data/
│   ├── cases.csv
│   ├── enforcement.csv
│   ├── agents.csv
│
├── src/
│   ├── generate_data.py
│   ├── metrics_engine.py
│   ├── forecasting.py
│   ├── anomaly_detection.py
│   ├── report_generator.py
│
├── app/
│   ├── streamlit_app.py
│
├── sql/
│   ├── queries.sql
│
├── docs/
│   ├── KPI_DEFINITIONS.md
│
└── README.md
```

---

# 13. 🧠 What This Project Signals to Employers

This project demonstrates:

### ✔ Strong KPI intuition
You define metrics like an ops team would.

### ✔ Real BI capability
Dashboards + reporting + recurring metrics.

### ✔ Analytical thinking
Trend + anomaly detection.

### ✔ Forecasting awareness
Capacity planning mindset.

### ✔ Communication skills
Weekly business review narrative.

---

# 14. 🧪 MVP Scope

## MVP (must-have)
- cases dataset
- KPI calculations
- Streamlit dashboard (2–3 pages)
- basic charts
- weekly report generator

## Nice-to-have
- forecasting
- anomaly detection
- enforcement table
- agent capacity modeling

---

# 15. 🚀 Definition of Done

Project is “hireable” when:

- Dashboard runs locally with one command
- KPIs are clearly defined
- At least 6 core metrics implemented
- One weekly report is auto-generated
- README explains business logic (not just code)

