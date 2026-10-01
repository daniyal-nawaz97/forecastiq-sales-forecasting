"""Fictitious demo company "Sahara Mart": 30 months of daily sales, generated with realistic patterns.

Writes sample_data/sahara_mart_sales.csv (the same format clients upload), sample_data/sahara_mart_stock.csv
and sample_data/sales_template.csv. Deliberately includes data problems so the health check has something to show.
Run:  python -m app.demo_data
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .calendar import EID_ADHA, EID_FITR, RAMADAN

OUT = Path(__file__).resolve().parent.parent / "sample_data"
START, END = date(2024, 4, 1), date(2026, 9, 30)

# name, category, price, cost ratio, base daily units (per branch), season profile
PRODUCTS = [
    ("Mango Juice 1L", "Beverages", 450, 0.72, 9, "summer"), ("Mineral Water 1.5L", "Beverages", 120, 0.65, 26, "summer"),
    ("Green Tea 25 Bags", "Beverages", 380, 0.60, 6, "winter"), ("Potato Chips Family Pack", "Snacks", 350, 0.66, 12, "flat"),
    ("Chocolate Cookies 12-Pack", "Snacks", 650, 0.62, 6, "gifting"), ("Premium Dates 500g", "Snacks", 1200, 0.70, 2, "ramadan"),
    ("Herbal Shampoo 400ml", "Personal Care", 950, 0.58, 4, "flat"), ("Body Lotion 300ml", "Personal Care", 850, 0.55, 4, "winter"),
    ("Sunscreen SPF50", "Personal Care", 1450, 0.52, 2, "summer"), ("Detergent Powder 2kg", "Household", 1100, 0.74, 6, "flat"),
    ("Dishwash Liquid 750ml", "Household", 520, 0.68, 7, "flat"), ("Basmati Rice 5kg", "Household", 2400, 0.80, 3, "eid"),
]
BRANCHES = [("Lahore (DHA)", date(2024, 4, 1), 1.15), ("Karachi (Clifton)", date(2024, 4, 1), 1.0), ("Islamabad (F-7)", date(2025, 1, 15), 0.75)]
DOW = [0.90, 0.92, 0.94, 0.97, 1.08, 1.22, 1.25]  # Mon..Sun
PROMOS = [("Summer Mega Sale", date(2025, 6, 20), date(2025, 6, 30), 0.15), ("Ramadan Bachat Week", date(2026, 3, 5), date(2026, 3, 12), 0.10)]


def season(profile: str, d: date) -> float:
    m = d.month + d.day / 31
    if profile == "summer":
        return 1 + 0.45 * np.cos((m - 6.5) / 12 * 2 * np.pi)
    if profile == "winter":
        return 1 + 0.40 * np.cos((m - 12.5) / 12 * 2 * np.pi)
    return 1 + 0.06 * np.cos((m - 12) / 12 * 2 * np.pi)


def event_mult(profile: str, cat: str, d: date) -> float:
    m = 1.0
    y = d.year
    if y in RAMADAN:
        s, e = RAMADAN[y]
        if s <= d <= e:
            m *= {"ramadan": 4.5, "eid": 1.3}.get(profile, 1.0) * (1.6 if cat == "Beverages" and profile == "summer" else 1.0) * (1.15 if (e - d).days < 10 else 1.0)
    if y in EID_FITR:
        eid = EID_FITR[y]
        if eid - timedelta(days=7) <= d < eid:
            m *= 2.3 if profile == "gifting" else 1.25
        elif eid <= d <= eid + timedelta(days=2):
            m *= 0.55
    if y in EID_ADHA:
        eid = EID_ADHA[y]
        if eid - timedelta(days=6) <= d < eid:
            m *= 1.9 if profile == "eid" else 1.12
        elif eid <= d <= eid + timedelta(days=2):
            m *= 0.6
    if d.month == 11 and d.day == 11:
        m *= 1.6
    if d.month == 12 and d.day >= 26:
        m *= 1.2
    for _, s, e, disc in PROMOS:
        if s <= d <= e and (disc != 0.10 or cat == "Household"):
            m *= 1 + 2.2 * disc
    return m


def discount_on(cat: str, d: date) -> float:
    if d.month == 11 and d.day == 11:
        return 0.20
    if d.month == 12 and d.day >= 26:
        return 0.10
    for _, s, e, disc in PROMOS:
        if s <= d <= e and (disc != 0.10 or cat == "Household"):
            return disc
    return 0.0


def generate(seed=11):
    rng = np.random.default_rng(seed)
    days = pd.date_range(START, END, freq="D")
    # weekly ad spend (Rs), campaigns before Eid and summer sale
    ad = {}
    for d in days:
        base = 150_000 + 2_000 * ((d.date() - START).days / 30)
        boost = 1.0
        for y, eid in EID_FITR.items():
            if eid - timedelta(days=21) <= d.date() < eid:
                boost = 1.8
        if date(2025, 6, 13) <= d.date() <= date(2025, 6, 30):
            boost = 2.0
        if date(2026, 7, 1) <= d.date() <= date(2026, 7, 31):
            boost = 1.6  # a summer campaign
        ad[d.date()] = base * boost * rng.uniform(0.9, 1.1) / 7
    rows = []
    for (name, cat, price, cost, base, prof) in PRODUCTS:
        for (branch, opened, bmult) in BRANCHES:
            level = rng.uniform(0.9, 1.1)
            for d in days:
                dd = d.date()
                if dd < opened:
                    continue
                t = (dd - START).days / 30.4
                trend = 1.015 ** t
                if branch.startswith("Karachi") and dd >= date(2026, 6, 1):
                    trend *= 1 - 0.035 * ((dd - date(2026, 6, 1)).days / 30.4)  # Karachi slipping since June 2026
                ramp = min(1.0, 0.55 + 0.45 * (dd - opened).days / 120) if branch.startswith("Islamabad") else 1.0
                p = price * (1.08 if cat == "Household" and dd >= date(2026, 1, 1) else 1.0)
                price_effect = 0.95 if cat == "Household" and dd >= date(2026, 1, 1) else 1.0
                ad_effect = (ad[dd] / (150_000 / 7)) ** 0.08
                mu = base * bmult * level * trend * ramp * DOW[dd.weekday()] * season(prof, dd) * event_mult(prof, cat, dd) * price_effect * ad_effect
                q = rng.poisson(max(0.05, mu * rng.lognormal(0, 0.10)))
                disc = discount_on(cat, dd)
                unit_price = round(p * (1 - disc))
                rows.append((dd.isoformat(), branch, name, cat, q, unit_price, q * unit_price, round(p * cost), round(ad[dd] / len(PRODUCTS) / 3, 2)))
    df = pd.DataFrame(rows, columns=["date", "branch", "product", "category", "quantity", "unit_price", "revenue", "unit_cost", "ad_spend"])
    # --- deliberate data problems, like real exports ---
    # 1) POS outage: Karachi has no rows for 12 days in March 2026
    out = (df["branch"] == "Karachi (Clifton)") & (df["date"] >= "2026-03-08") & (df["date"] <= "2026-03-19")
    df = df[~out]
    # 2) stock-out: Sunscreen at Lahore sold nothing for 9 days in July 2026
    so = (df["branch"] == "Lahore (DHA)") & (df["product"] == "Sunscreen SPF50") & (df["date"] >= "2026-07-05") & (df["date"] <= "2026-07-13")
    df.loc[so, ["quantity", "revenue"]] = 0
    # 3) typos: three rows with an extra zero
    idx = df.sample(3, random_state=4).index
    df.loc[idx, "quantity"] *= 20
    df.loc[idx, "revenue"] = df.loc[idx, "quantity"] * df.loc[idx, "unit_price"]
    # 4) duplicated export rows
    dups = df.sample(37, random_state=5)
    df = pd.concat([df, dups]).sort_values(["date", "branch", "product"]).reset_index(drop=True)
    return df


def stock_levels(df: pd.DataFrame) -> pd.DataFrame:
    """Current stock on hand per product and branch (for stock-out / overstock risk)."""
    last = df[df["date"] >= "2026-09-01"].groupby(["branch", "product"])["quantity"].sum().reset_index()
    rng = np.random.default_rng(3)
    cover = rng.uniform(1.5, 2.2, len(last))  # usually 1.5-2 months of September sales
    special = {("Karachi (Clifton)", "Body Lotion 300ml"): 0.35, ("Lahore (DHA)", "Green Tea 25 Bags"): 0.45,
               ("Lahore (DHA)", "Sunscreen SPF50"): 3.4, ("Islamabad (F-7)", "Mineral Water 1.5L"): 2.6}
    last["on_hand"] = [round(q * special.get((b, p), c)) for (b, p, q), c in zip(last[["branch", "product", "quantity"]].values, cover)]
    return last[["branch", "product", "on_hand"]]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(OUT / "sahara_mart_sales.csv", index=False)
    stock_levels(df).to_csv(OUT / "sahara_mart_stock.csv", index=False)
    df.head(0).to_csv(OUT / "sales_template.csv", index=False)
    with open(OUT / "sales_template.csv", "a") as f:
        f.write("2026-09-01,Main Branch,Example Product,Example Category,12,450,5400,300,\n")
    m = df.assign(month=df["date"].str[:7]).groupby("month")["revenue"].sum()
    print(f"{len(df):,} rows, {df['date'].min()} to {df['date'].max()}; monthly revenue Rs {m.min()/1e6:.1f}M to {m.max()/1e6:.1f}M (last {m.iloc[-1]/1e6:.2f}M)")


if __name__ == "__main__":
    main()
