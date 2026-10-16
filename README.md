# Chef's Table — Waste & Demand Analytics (SQL)

## Overview

At Chef's Table food waste was eating into margins but it was not being recorded or measured. I built an inventory tracking system and found that we were over prepping for slow periods and cooking for a Friday dinner rush on a Tuesday lunch. Once we started cooking for the day we actually had waste dropped by a fifth.

There are three tables which cover 12 weeks. `menu_items` (52 real menu items), `inventory_log` (daily counts per item), and `sales` (line items). Each analysis answers a question that a manager would actually ask. The top three items which wasted the most money were butter chicken, samosa, and chicken biryani; by category desserts were wasted at the highest rate.

Adjusting preparation quantities by daypart drove the improvement and that same analysis helped to reshuffle weekend staffing towards Fri–Sun dinner, where the revenue concentrates. Note: The original Excel files are gone. This database is synthetic; it was generated to reproduce the real patterns. But the item names and the menu prices are from the real menu, and the cut of 20% in waste reduction is an accurate historical outcome.

## Per-Query Findings

### 1) Which items waste the most money?
*JOIN, aggregation, ORDER BY*

Butter chicken ($5,720), samosa ($4,993), and chicken biryani ($4,649)

### 2) What is the waste rate by category?
*GROUP BY, filtered aggregation*

Dessert (35.1%), followed by bread (27.4%), and beverages (25.5%)

### 3) Is waste actually improving week over week?
*CTEs, window functions (LAG), date truncation*

Weekly waste rate fell from 19.5% to 15.4%

### 4) When do the rushes actually happen?
*Datepart extraction, CASE, multi-dimensional GROUP BY*

Saturday dinner ($118k), followed by Sunday dinner ($104k), and Friday dinner ($101k)

### 5) Where does prepared food exceed demand?
*Multi-table JOINs, CTEs, LEFT JOIN*

Garlic naan (7,789 units made vs 5,867 sold), followed by samosa (1,513), and mango lassi (1,230)

### 6) What does the waste trend look like over time?
*Window functions (running totals, moving averages)*

The running waste goes to $47,200 over the 12 weeks. The waste rate (Q3) proves the improvement, since the win comes from prepping less, not selling more.
