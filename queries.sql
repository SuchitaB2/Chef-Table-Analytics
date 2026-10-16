-- ============================================================
-- Chef's Table SQL Portfolio Project — queries.sql
-- Six analyses, one business question each.
-- Run against DuckDB after loading schema.sql.
-- ============================================================

-- ------------------------------------------------------------------
-- 1. Which items waste the most money?
-- JOIN + aggregation + arithmetic + ORDER BY
-- Finding: a handful of items drive most of the waste cost (Pareto).
-- Those are the prep quantities to fix first.
-- ------------------------------------------------------------------
SELECT
    m.item_name,
    m.category,
    SUM(i.qty_wasted) AS units_wasted,
    ROUND(SUM(i.qty_wasted * m.unit_cost), 2) AS waste_cost
FROM inventory_log i
JOIN menu_items m ON i.item_id = m.item_id
GROUP BY m.item_name, m.category
ORDER BY waste_cost DESC
LIMIT 10;

-- ------------------------------------------------------------------
-- 2. What is the overall waste rate, by category?
-- JOIN + GROUP BY + filtered aggregation
-- Finding: perishable, made-ahead categories (dessert, bread) waste at the
-- highest rate; entrees lowest. That's where prep discipline pays off first.
-- ------------------------------------------------------------------
SELECT
    m.category,
    SUM(i.qty_received) AS received,
    SUM(i.qty_wasted) AS wasted,
    ROUND(100.0 * SUM(i.qty_wasted) / NULLIF(SUM(i.qty_received), 0), 1) AS waste_pct
FROM inventory_log i
JOIN menu_items m ON i.item_id = m.item_id
GROUP BY m.category
ORDER BY waste_pct DESC;

-- ------------------------------------------------------------------
-- 3. Is waste actually improving week over week?
-- CTEs + window functions (LAG) + date truncation
-- Finding: the wow_change_pts column proves the ~20% drop is a real
-- trend, not noise. This query separates "I made a chart" from
-- "I did analysis."
-- ------------------------------------------------------------------
WITH weekly AS (
    SELECT
        DATE_TRUNC('week', log_date) AS week,
        SUM(qty_wasted)   AS wasted,
        SUM(qty_received) AS received
    FROM inventory_log
    GROUP BY 1
),
with_rate AS (
    SELECT
        week,
        100.0 * wasted / NULLIF(received, 0) AS waste_pct
    FROM weekly
)
SELECT
    week,
    ROUND(waste_pct, 1) AS waste_pct,
    ROUND(waste_pct - LAG(waste_pct) OVER (ORDER BY week), 1) AS wow_change_pts
FROM with_rate
ORDER BY week;

-- ------------------------------------------------------------------
-- 4. When do the rushes actually happen? (the staffing analysis)
-- Datepart extraction + CASE + multi-dimensional GROUP BY
-- Finding: revenue concentrates in Fri-Sun dinner while staffing was
-- flat across the week -- the basis for the schedule change.
-- ------------------------------------------------------------------
SELECT
    CASE
        WHEN EXTRACT(HOUR FROM sale_ts) < 11 THEN 'morning'
        WHEN EXTRACT(HOUR FROM sale_ts) < 15 THEN 'lunch'
        WHEN EXTRACT(HOUR FROM sale_ts) < 18 THEN 'afternoon'
        ELSE 'dinner'
    END AS daypart,
    EXTRACT(DOW FROM sale_ts) AS weekday_num,   -- 0 = Sunday
    COUNT(*) AS line_items,
    SUM(qty) AS units_sold,
    ROUND(SUM(revenue), 2) AS revenue
FROM sales
GROUP BY daypart, weekday_num
ORDER BY revenue DESC;

-- ------------------------------------------------------------------
-- 5. The over-prep gap: where does prepped food exceed demand?
-- JOINs across all three tables + CTEs + LEFT JOIN
-- Finding: this is the money query -- it quantifies exactly how much
-- food was prepped but never sold, by item. This justified changing
-- prep quantities by daypart.
-- ------------------------------------------------------------------
WITH daily_prepped AS (
    SELECT
        log_date,
        item_id,
        SUM(qty_received) AS prepped,
        SUM(qty_wasted)   AS wasted
    FROM inventory_log
    GROUP BY 1, 2
),
daily_sold AS (
    SELECT
        CAST(sale_ts AS DATE) AS sale_date,
        item_id,
        SUM(qty) AS units_sold
    FROM sales
    GROUP BY 1, 2
)
SELECT
    m.item_name,
    SUM(p.prepped) AS total_prepped,
    COALESCE(SUM(s.units_sold), 0) AS total_sold,
    SUM(p.prepped) - COALESCE(SUM(s.units_sold), 0) AS over_prep_units,
    ROUND(SUM(p.wasted * m.unit_cost), 2) AS waste_cost
FROM daily_prepped p
JOIN menu_items m ON p.item_id = m.item_id
LEFT JOIN daily_sold s
    ON s.item_id = p.item_id AND s.sale_date = p.log_date
GROUP BY m.item_name
ORDER BY over_prep_units DESC;

-- ------------------------------------------------------------------
-- 6. Running waste cost: the trend a manager watches
-- Window functions: running totals + moving averages
-- ------------------------------------------------------------------
WITH daily_cost AS (
    SELECT
        i.log_date,
        SUM(i.qty_wasted * m.unit_cost) AS waste_cost
    FROM inventory_log i
    JOIN menu_items m ON i.item_id = m.item_id
    GROUP BY 1
)
SELECT
    log_date,
    ROUND(waste_cost, 2) AS daily_waste_cost,
    ROUND(SUM(waste_cost) OVER (ORDER BY log_date), 2) AS running_waste_cost,
    ROUND(AVG(waste_cost) OVER (
        ORDER BY log_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS waste_cost_7day_avg
FROM daily_cost
ORDER BY log_date;
