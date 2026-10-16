#!/usr/bin/env python3
"""
Synthetic data generator for the Chef's Table SQL portfolio project.

The original Excel files are gone, so this regenerates 12 weeks of data that
reproduces the REAL patterns observed at Chef's Table (Edison, NJ):
  1. Waste concentrated in a few perishable items (Pareto).
  2. Demand spikes Fri-Sun dinner (the staffing story).
  3. Waste rate trending down ~20% over the 12 weeks (the improvement story).

Tables (match schema.sql):
  menu_items    52 REAL items from the Chef's Table online menu
                (ourchefstable.com, Edison NJ): appetizer / entree / bread /
                dessert / beverage. Item names and menu prices are real;
                unit_cost is estimated at 30% of menu price (standard
                food-cost rule) since only public menu prices are known.
  inventory_log one row per item per day (12 weeks x 40 items = 3360 rows)
  sales         one row per line item

Accounting identity: qty_received = qty_used + qty_wasted, every row.
qty_used is always exactly the sum of that day's sales qty for the item,
so the sales <-> inventory join in the over-prep query is consistent.

Run:  python3 generate_data.py   (writes data/*.csv)
Seeded for reproducibility (SEED = 42).
"""

import csv
import math
import os
import random
from datetime import date, datetime, timedelta

SEED = 42
START_DATE = date(2024, 1, 8)   # a Monday
WEEKS = 12
DAYS = WEEKS * 7                # 84 days, ends Sunday 2024-03-31

random.seed(SEED)

# ----------------------------------------------------------------------------
# Menu: (name, category, unit_cost, unit_price)
# Real items and real menu prices from the Chef's Table online menu
# (ourchefstable.com, Edison NJ). unit_cost estimated at 30% of price.
# ----------------------------------------------------------------------------
MENU = [
    # appetizers (Indian, Tandoori, Pan-Asian)
    ("Samosa", "appetizer", 3.30, 11.00),
    ("Chicken 65", "appetizer", 4.80, 16.00),
    ("Bhajiya Pakora", "appetizer", 3.60, 12.00),
    ("Dahi Sev Puri", "appetizer", 3.60, 12.00),
    ("Gol Gappe", "appetizer", 3.60, 12.00),
    ("Papri Ki Chat", "appetizer", 3.60, 12.00),
    ("Murg Tikka", "appetizer", 6.30, 21.00),
    ("Lamb Seekh Kabab", "appetizer", 7.80, 26.00),
    ("Hariyali Murg Tikka", "appetizer", 6.30, 21.00),
    ("Chilli Chicken (Dry)", "appetizer", 5.70, 19.00),
    ("Chicken Dumpling", "appetizer", 3.60, 12.00),
    ("Mini Spring Roll", "appetizer", 2.70, 9.00),
    # entrees (Indian Curry Pot, Pan-Asian, Biryani, Noodles)
    ("Butter Chicken", "entree", 6.30, 21.00),
    ("Murg Tikka Masala", "entree", 6.30, 21.00),
    ("Dal Makhani", "entree", 5.70, 19.00),
    ("Kadai Chicken", "entree", 6.30, 21.00),
    ("Matka Goat", "entree", 8.70, 29.00),
    ("Saag Gosht", "entree", 7.20, 24.00),
    ("Paneer Makhani", "entree", 6.00, 20.00),
    ("Kadai Paneer", "entree", 6.00, 20.00),
    ("Malai Kofta", "entree", 6.30, 21.00),
    ("Paneer Tikka Masala", "entree", 6.00, 20.00),
    ("Peshwari Chole", "entree", 4.80, 16.00),
    ("Baingan Bharta", "entree", 5.70, 19.00),
    ("Chicken Biryani", "entree", 6.30, 21.00),
    ("Goat Biryani", "entree", 8.70, 29.00),
    ("Vegetable Biryani", "entree", 5.70, 19.00),
    ("Chilli Garlic Noodles", "entree", 4.50, 15.00),
    ("Hakka Noodles", "entree", 4.50, 15.00),
    ("Chicken Red Thai Curry", "entree", 5.70, 19.00),
    # breads
    ("Garlic Naan", "bread", 1.80, 6.00),
    ("Butter Naan", "bread", 1.50, 5.00),
    ("Tandoori Roti", "bread", 1.50, 5.00),
    ("Lachha Paratha", "bread", 1.80, 6.00),
    ("Onion Kulcha", "bread", 1.80, 6.00),
    ("Cheese Naan", "bread", 1.80, 6.00),
    ("Chilli Garlic Naan", "bread", 1.80, 6.00),
    ("Methi Paratha", "bread", 1.80, 6.00),
    # desserts
    ("Gulab Jamun", "dessert", 2.10, 7.00),
    ("Rasmalai", "dessert", 3.30, 11.00),
    ("Kulfi Falooda", "dessert", 3.30, 11.00),
    ("Gajar Ka Halwa", "dessert", 2.40, 8.00),
    ("Baked Rasgulla", "dessert", 2.40, 8.00),
    ("Kulfi (Plain)", "dessert", 3.00, 10.00),
    # beverages
    ("Mango Lassi", "beverage", 2.70, 9.00),
    ("Sweet Lassi", "beverage", 2.40, 8.00),
    ("Masala Soda", "beverage", 1.50, 5.00),
    ("Sweet Lime Soda", "beverage", 1.50, 5.00),
    ("Coca-Cola", "beverage", 0.90, 3.00),
    ("Diet Coke", "beverage", 0.90, 3.00),
    ("Mineral Water", "beverage", 0.60, 2.00),
    ("Aam Ka Panna", "beverage", 2.40, 8.00),
]

# Items that were chronically over-prepped (perishable, short shelf life).
# These carry the waste story: high waste rate vs ~7-14% for the rest.
WASTE_PRONE = {
    "Garlic Naan", "Butter Naan", "Tandoori Roti", "Lachha Paratha",
    "Bhajiya Pakora", "Samosa", "Dahi Sev Puri", "Gol Gappe",
    "Papri Ki Chat", "Mini Spring Roll",
    "Gulab Jamun", "Rasmalai", "Kulfi Falooda",
    "Mango Lassi",
}

# Obvious bestsellers pinned to the top of the popularity curve so the
# simulated demand mix looks like a real Indian restaurant's.
POPULAR = [
    "Butter Chicken", "Chicken Biryani", "Garlic Naan", "Murg Tikka Masala",
    "Samosa", "Mango Lassi", "Chicken 65", "Dal Makhani",
    "Murg Tikka", "Paneer Makhani",
]

# Popularity: a few items drive most volume (shuffled, then exponential decay).
_item_order = list(range(len(MENU)))
random.shuffle(_item_order)
_name_to_idx = {m[0]: i for i, m in enumerate(MENU)}
_boosted = [_name_to_idx[n] for n in POPULAR]
_rest = [i for i in _item_order if i not in set(_boosted)]
_item_order = _boosted + _rest
popularity = {}
for rank, idx in enumerate(_item_order):
    popularity[MENU[idx][0]] = math.exp(-0.16 * rank)
_pop_total = sum(popularity.values())
TARGET_DAILY_UNITS = 600.0
base_daily = {name: TARGET_DAILY_UNITS * w / _pop_total for name, w in popularity.items()}

# Day-of-week demand multiplier: the Fri-Sun dinner spike.
DOW_MULT = {0: 0.80, 1: 0.75, 2: 0.85, 3: 0.95, 4: 1.35, 5: 1.60, 6: 1.45}

# Hour weights for sale timestamps (restaurant 11:00-22:00). Dinner = 18+.
HOUR_WEIGHTS = {
    11: 2, 12: 5, 13: 6, 14: 4, 15: 2, 16: 1,
    17: 2, 18: 5, 19: 9, 20: 10, 21: 8, 22: 3,
}
_hours = list(HOUR_WEIGHTS.keys())
_hour_cum = []
_running = 0
for h in _hours:
    _running += HOUR_WEIGHTS[h]
    _hour_cum.append(_running)


def pick_hour():
    r = random.random() * _running
    for h, c in zip(_hours, _hour_cum):
        if r < c:
            return h
    return _hours[-1]


def waste_rate(item_name, week_idx):
    """Daily waste rate for an item. Waste-prone (perishable) items run
    24-32%, everything else 7-14%. The week-by-week improvement factor
    1.0 -> 0.8 builds in the ~20% waste-rate cut over the 12 weeks."""
    base = random.uniform(0.24, 0.32) if item_name in WASTE_PRONE else random.uniform(0.07, 0.14)
    improvement = 1.0 - 0.25 * (week_idx / (WEEKS - 1))
    # Note: the 0.25 per-item improvement nets ~20% in the aggregate weekly
    # waste% (query 3) after ceil/weighting effects; verified empirically.
    return base * improvement * random.gauss(1.0, 0.10)


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(out_dir, exist_ok=True)

    menu_rows = []
    item_by_id = {}
    for i, (name, cat, cost, price) in enumerate(MENU, start=1):
        menu_rows.append([i, name, cat, f"{cost:.2f}", f"{price:.2f}"])
        item_by_id[i] = {"name": name, "cost": cost, "price": price}

    inv_rows = []    # log_id, item_id, log_date, qty_received, qty_used, qty_wasted
    sales_rows = []  # sale_id, item_id, sale_ts, qty, revenue
    log_id, sale_id = 1, 1

    for day in range(DAYS):
        day_date = START_DATE + timedelta(days=day)
        week_idx = day // 7
        dow = day_date.weekday()

        for item_id, meta in item_by_id.items():
            name = meta["name"]
            demand = base_daily[name] * DOW_MULT[dow] * random.gauss(1.0, 0.22)
            units = max(0, int(round(demand)))

            # Inventory: received = used + wasted, always.
            # Waste is modeled as a rate on received so the week-over-week
            # waste% decline in query 3 lands at ~20% by construction.
            wr = min(0.45, waste_rate(name, week_idx))
            if units > 0:
                received = math.ceil(units / (1 - wr))
            else:
                # Slow day: perishables still get a small prep, others none.
                received = 2 if name in WASTE_PRONE else 0
            wasted = received - units
            inv_rows.append([log_id, item_id, day_date.isoformat(), received, units, wasted])
            log_id += 1

            # Sales: split the day's units across line-item transactions.
            remaining = units
            while remaining > 0:
                qty = min(remaining, random.randint(1, 4))
                remaining -= qty
                h = pick_hour()
                ts = datetime(day_date.year, day_date.month, day_date.day,
                              h, random.randint(0, 59), random.randint(0, 59))
                revenue = round(qty * meta["price"], 2)
                sales_rows.append([sale_id, item_id, ts.strftime("%Y-%m-%d %H:%M:%S"),
                                   qty, f"{revenue:.2f}"])
                sale_id += 1

    def write_csv(fname, header, rows):
        with open(os.path.join(out_dir, fname), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    write_csv("menu_items.csv",
              ["item_id", "item_name", "category", "unit_cost", "unit_price"], menu_rows)
    write_csv("inventory_log.csv",
              ["log_id", "item_id", "log_date", "qty_received", "qty_used", "qty_wasted"], inv_rows)
    write_csv("sales.csv",
              ["sale_id", "item_id", "sale_ts", "qty", "revenue"], sales_rows)

    print(f"menu_items:    {len(menu_rows)} rows")
    print(f"inventory_log: {len(inv_rows)} rows")
    print(f"sales:         {len(sales_rows)} rows")
    print(f"date range:    {START_DATE} to {START_DATE + timedelta(days=DAYS - 1)}")


if __name__ == "__main__":
    main()
