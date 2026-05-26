-- ============================================================
-- Trust & Safety Operations — KPI Query Library
-- Database: ts_ops.db (SQLite)
-- ============================================================

-- ============================================================
-- OPERATIONAL KPIs
-- ============================================================

-- Case Volume by Day
SELECT
    DATE(created_at) AS date,
    COUNT(*)         AS case_volume
FROM cases
GROUP BY DATE(created_at)
ORDER BY date;

-- Case Volume by Week
SELECT
    strftime('%Y-W%W', created_at) AS week,
    COUNT(*)                        AS case_volume
FROM cases
GROUP BY week
ORDER BY week;

-- Backlog Size (current open + escalated)
SELECT COUNT(*) AS backlog
FROM cases
WHERE status != 'closed';

-- Resolution Time Distribution (closed cases only)
SELECT
    AVG((JULIANDAY(resolved_at) - JULIANDAY(created_at)) * 24)          AS mean_hours,
    -- SQLite has no native PERCENTILE; use the window function trick
    -- p50 approximation via subquery ordering
    (
        SELECT (JULIANDAY(resolved_at) - JULIANDAY(created_at)) * 24
        FROM cases
        WHERE resolved_at IS NOT NULL
        ORDER BY (JULIANDAY(resolved_at) - JULIANDAY(created_at))
        LIMIT 1
        OFFSET CAST(0.5 * (SELECT COUNT(*) FROM cases WHERE resolved_at IS NOT NULL) AS INT)
    ) AS median_hours,
    (
        SELECT (JULIANDAY(resolved_at) - JULIANDAY(created_at)) * 24
        FROM cases
        WHERE resolved_at IS NOT NULL
        ORDER BY (JULIANDAY(resolved_at) - JULIANDAY(created_at))
        LIMIT 1
        OFFSET CAST(0.9 * (SELECT COUNT(*) FROM cases WHERE resolved_at IS NOT NULL) AS INT)
    ) AS p90_hours
FROM cases
WHERE resolved_at IS NOT NULL;

-- Escalation Rate by Week
SELECT
    strftime('%Y-W%W', created_at)                                         AS week,
    COUNT(*)                                                                AS total_cases,
    SUM(CASE WHEN status = 'escalated' THEN 1 ELSE 0 END)                  AS escalated_cases,
    ROUND(
        SUM(CASE WHEN status = 'escalated' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    )                                                                       AS escalation_rate_pct
FROM cases
GROUP BY week
ORDER BY week;

-- ============================================================
-- QUALITY KPIs
-- ============================================================

-- Enforcement Rate (enforcement actions per resolved case, weekly)
SELECT
    strftime('%Y-W%W', c.created_at)      AS week,
    COUNT(DISTINCT c.case_id)             AS resolved_cases,
    COUNT(e.case_id)                      AS enforcement_actions,
    ROUND(COUNT(e.case_id) * 100.0 / COUNT(DISTINCT c.case_id), 2) AS enforcement_rate_pct
FROM cases c
LEFT JOIN enforcement_actions e ON c.case_id = e.case_id
WHERE c.status != 'open'
GROUP BY week
ORDER BY week;

-- Enforcement Actions by Type Over Time
SELECT
    strftime('%Y-W%W', action_date)                                  AS week,
    SUM(CASE WHEN action_type = 'warning' THEN 1 ELSE 0 END)        AS warnings,
    SUM(CASE WHEN action_type = 'removal' THEN 1 ELSE 0 END)        AS removals,
    SUM(CASE WHEN action_type = 'ban'     THEN 1 ELSE 0 END)        AS bans
FROM enforcement_actions
GROUP BY week
ORDER BY week;

-- Fraud Share by Week
SELECT
    strftime('%Y-W%W', created_at)                                     AS week,
    COUNT(*)                                                            AS total_cases,
    SUM(CASE WHEN category = 'fraud' THEN 1 ELSE 0 END)               AS fraud_cases,
    ROUND(
        SUM(CASE WHEN category = 'fraud' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    )                                                                   AS fraud_share_pct
FROM cases
GROUP BY week
ORDER BY week;

-- ============================================================
-- EFFICIENCY KPIs
-- ============================================================

-- Cases per Agent per Day
SELECT
    DATE(c.created_at)                     AS date,
    COUNT(c.case_id)                        AS total_cases,
    COUNT(DISTINCT a.agent_id)              AS active_agents,
    ROUND(
        COUNT(c.case_id) * 1.0 / NULLIF(COUNT(DISTINCT a.agent_id), 0),
        2
    )                                       AS cases_per_agent
FROM cases c
JOIN agents a ON DATE(c.created_at) = a.date
GROUP BY DATE(c.created_at)
ORDER BY date;

-- Agent Capacity Utilization (assumes max 25 cases/day per agent)
SELECT
    date,
    SUM(cases_handled)                                              AS total_cases_handled,
    COUNT(DISTINCT agent_id)                                        AS active_agents,
    SUM(hours_worked)                                               AS total_hours,
    ROUND(SUM(cases_handled) * 1.0 / (COUNT(DISTINCT agent_id) * 25), 3) AS capacity_utilization
FROM agents
WHERE cases_handled > 0
GROUP BY date
ORDER BY date;

-- ============================================================
-- RISK SIGNAL QUERIES
-- ============================================================

-- Rolling 7-Day Average Case Volume (for anomaly detection baseline)
SELECT
    date,
    case_volume,
    AVG(case_volume) OVER (
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_avg
FROM (
    SELECT DATE(created_at) AS date, COUNT(*) AS case_volume
    FROM cases
    GROUP BY DATE(created_at)
) daily
ORDER BY date;

-- Week-over-Week Fraud Share Change
SELECT
    curr.week,
    curr.fraud_share_pct,
    prev.fraud_share_pct                                                AS prev_fraud_share_pct,
    ROUND(curr.fraud_share_pct - prev.fraud_share_pct, 2)              AS fraud_share_delta_pct
FROM (
    SELECT strftime('%Y-W%W', created_at) AS week,
           ROUND(SUM(CASE WHEN category='fraud' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS fraud_share_pct
    FROM cases GROUP BY week
) curr
LEFT JOIN (
    SELECT strftime('%Y-W%W', created_at) AS week,
           ROUND(SUM(CASE WHEN category='fraud' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS fraud_share_pct
    FROM cases GROUP BY week
) prev ON strftime('%Y-%W', curr.week) = strftime('%Y-%W', date(prev.week || '-1', '+7 days'))
ORDER BY curr.week;

-- Category Breakdown by Week (pivot-friendly)
SELECT
    strftime('%Y-W%W', created_at)                                     AS week,
    category,
    COUNT(*)                                                            AS case_count
FROM cases
GROUP BY week, category
ORDER BY week, category;

-- Resolution Time by Severity
SELECT
    severity,
    COUNT(*)                                                                    AS case_count,
    ROUND(AVG((JULIANDAY(resolved_at) - JULIANDAY(created_at)) * 24), 2)      AS mean_hours
FROM cases
WHERE resolved_at IS NOT NULL
GROUP BY severity
ORDER BY severity;
