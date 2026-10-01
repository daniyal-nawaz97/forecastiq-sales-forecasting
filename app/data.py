"""Read a client's sales file, clean it, and explain every fix in plain language (the data health check)."""
from __future__ import annotations

import io
import re
from datetime import timedelta

import numpy as np
import pandas as pd

ALIASES = {
    "date": ["date", "day", "order date", "invoice date", "sale date", "transaction date", "posting date", "tarikh"],
    "product": ["product", "item", "sku", "product name", "item name", "description"],
    "branch": ["branch", "store", "location", "outlet", "shop", "warehouse", "channel"],
    "category": ["category", "department", "group", "product category"],
    "quantity": ["quantity", "qty", "units", "units sold", "pieces", "volume"],
    "revenue": ["revenue", "sales", "amount", "total", "net sales", "sales amount", "value", "net amount"],
    "unit_price": ["unit price", "price", "rate", "selling price"],
    "unit_cost": ["unit cost", "cost", "cost price", "purchase price", "cogs"],
    "ad_spend": ["ad spend", "marketing", "marketing spend", "advertising"],
}


class DataError(Exception):
    pass


def _norm(c: str) -> str:
    return re.sub(r"[^a-z ]", "", str(c).lower().replace("_", " ")).strip()


def read_any(filename: str, content: bytes) -> pd.DataFrame:
    name = filename.lower()
    try:
        if name.endswith((".xlsx", ".xlsm", ".xls")):
            return pd.read_excel(io.BytesIO(content))
        text = content.decode("utf-8-sig", errors="replace")
        sep = ";" if text.count(";") > text.count(",") else ","
        return pd.read_csv(io.StringIO(text), sep=sep)
    except Exception:
        raise DataError("We couldn't read this file. Please upload a CSV or Excel (.xlsx) file.")


def map_columns(df: pd.DataFrame) -> dict:
    found = {}
    cols = {_norm(c): c for c in df.columns}
    for key, names in ALIASES.items():
        for n in names:
            if n in cols:
                found[key] = cols[n]
                break
    if "date" not in found:
        raise DataError("We couldn't find a date column. Please name it 'date' (see the sample format).")
    if "revenue" not in found and not ("quantity" in found and "unit_price" in found):
        raise DataError("We need sales amounts: a 'revenue' column, or 'quantity' and 'unit_price'.")
    return found


def clean(raw: pd.DataFrame, decisions: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Returns (daily data per product and branch, health report)."""
    decisions = decisions or {}
    m = map_columns(raw)
    df = pd.DataFrame({k: raw[v] for k, v in m.items()})
    health = {"rows_read": int(len(raw)), "columns": {k: str(v) for k, v in m.items()}, "messages": []}
    msgs = health["messages"]

    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=not str(raw[m["date"]].iloc[0]).startswith(("19", "20")))
    bad = int(df["date"].isna().sum())
    df = df.dropna(subset=["date"])
    if bad:
        msgs.append({"level": "warn", "text": f"{bad} rows had a date we couldn't read and were left out."})
    for c in ("quantity", "revenue", "unit_price", "unit_cost", "ad_spend"):
        if c in df:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(r"[^\d.\-]", "", regex=True), errors="coerce")
    if "revenue" not in df:
        df["revenue"] = df["quantity"] * df["unit_price"]
    if "quantity" not in df:
        df["quantity"] = np.nan
    df["product"] = df["product"].astype(str).str.strip() if "product" in df else "All products"
    df["branch"] = df["branch"].astype(str).str.strip() if "branch" in df else "All branches"
    df["category"] = df["category"].astype(str).str.strip() if "category" in df else "All"

    before = len(df)
    df = df.drop_duplicates()
    dups = before - len(df)
    if dups:
        msgs.append({"level": "info", "text": f"{dups} duplicate rows were found and removed (the same line appeared twice in the export)."})

    neg = df["revenue"] < 0
    if neg.any():
        msgs.append({"level": "info", "text": f"{int(neg.sum())} rows with negative amounts (returns) were left out of the forecast."})
        df = df[~neg]

    df["date"] = df["date"].dt.normalize()
    cost_col = df["unit_cost"] * df["quantity"] if "unit_cost" in df else np.nan
    df["cost"] = cost_col
    daily = (df.groupby(["date", "branch", "product"], as_index=False)
             .agg(category=("category", "first"), quantity=("quantity", "sum"), revenue=("revenue", "sum"), cost=("cost", "sum")))
    ad = df.groupby("date")["ad_spend"].sum() if "ad_spend" in df else None

    # unusual values: far above what this product normally sells at this branch
    daily["exclude"] = False
    daily["reason"] = ""
    daily = daily.sort_values(["branch", "product", "date"]).reset_index(drop=True)
    med = daily.groupby(["branch", "product"])["revenue"].transform(lambda s: s.rolling(29, center=True, min_periods=7).median())
    spike = (daily["revenue"] > 10 * med.clip(lower=1)) & (daily["revenue"] > daily.groupby(["branch", "product"])["revenue"].transform("median") * 10)
    if spike.any():
        ex = daily[spike].head(3)
        examples = "; ".join(f"{r.product} at {r.branch} on {r.date:%d %b %Y}" for r in ex.itertuples())
        msgs.append({"level": "warn", "key": "spikes", "text": f"{int(spike.sum())} unusually large values (e.g. {examples}), about 20× the normal day. "
                     "They look like typing errors, so we left them out of the forecast. Is this correct?"})
        daily.loc[spike, ["exclude", "reason"]] = [True, "unusual value"]

    # stock-outs: long runs of zero sales for a product that normally sells every day
    stockouts = []
    for (b, p), g in daily.groupby(["branch", "product"]):
        units = g["quantity"] if g["quantity"].sum() > 0 else g["revenue"]
        zero = (g["revenue"] == 0).astype(int).values
        run, start = 0, None
        for i, z in enumerate(np.append(zero, 0)):
            if z:
                run += 1; start = i if run == 1 else start
            else:
                # only a stock-out if it was selling normally in the 4 weeks before (not a quiet season)
                if run >= 5 and units.iloc[max(0, start - 28):start].median() >= 2:
                    idx = g.index[start:start + run]
                    daily.loc[idx, ["exclude", "reason"]] = [True, "possible stock-out"]
                    stockouts.append((p, b, g["date"].iloc[start], run))
                run = 0
    for p, b, d0, n in stockouts[:5]:
        msgs.append({"level": "warn", "text": f"{p} at {b} sold nothing for {n} days from {d0:%d %b %Y}, which looks like it was out of stock. "
                     "These days are left out so they don't pull the forecast down."})

    # missing days per branch (no rows at all while the branch was trading)
    gaps = []
    for b, g in daily.groupby("branch"):
        have = set(g["date"])
        rng_days = pd.date_range(g["date"].min(), g["date"].max(), freq="D")
        missing = [d for d in rng_days if d not in have]
        if missing:
            runs, cur = [], [missing[0]]
            for d in missing[1:]:
                if d - cur[-1] == timedelta(days=1):
                    cur.append(d)
                else:
                    runs.append(cur); cur = [d]
            runs.append(cur)
            for r in runs:
                gaps.append({"branch": b, "start": r[0], "end": r[-1], "days": len(r)})
    health["missing_days"] = int(sum(g["days"] for g in gaps))
    fill = decisions.get("missing", "zero")  # zero | missing
    for g in gaps[:6]:
        key = f"gap:{g['branch']}:{g['start']:%Y-%m-%d}"
        txt = (f"{g['days']} day{'s' if g['days'] > 1 else ''} {'are' if g['days'] > 1 else 'is'} missing in {g['start']:%B %Y} for {g['branch']} "
               f"({g['start']:%d}–{g['end']:%d %b}). ")
        if fill == "zero":
            msgs.append({"level": "ask", "key": "missing", "text": txt + "We filled them with zero sales. Is this correct?",
                         "options": [["zero", "Yes, there were no sales"], ["missing", "No, the data is missing"]], "choice": "zero"})
        else:
            msgs.append({"level": "ask", "key": "missing", "text": txt + "You told us the data is missing for these days, so they are left out of the forecast.",
                         "options": [["zero", "There were no sales"], ["missing", "The data is missing"]], "choice": "missing"})
    if gaps:
        products = daily[["branch", "product", "category"]].drop_duplicates()
        add = []
        for g in gaps:
            for d in pd.date_range(g["start"], g["end"], freq="D"):
                for r in products[products["branch"] == g["branch"]].itertuples():
                    add.append({"date": d, "branch": r.branch, "product": r.product, "category": r.category, "quantity": 0, "revenue": 0.0, "cost": 0.0,
                                "exclude": fill == "missing", "reason": "missing day" if fill == "missing" else ""})
        daily = pd.concat([daily, pd.DataFrame(add)], ignore_index=True)

    daily = daily.sort_values(["date", "branch", "product"]).reset_index(drop=True)
    health.update({
        "date_from": daily["date"].min().strftime("%Y-%m-%d"), "date_to": daily["date"].max().strftime("%Y-%m-%d"),
        "months": int(round((daily["date"].max() - daily["date"].min()).days / 30.4)),
        "products": int(daily["product"].nunique()), "branches": int(daily["branch"].nunique()), "categories": int(daily["category"].nunique()),
        "duplicates_removed": int(dups), "unusual_values": int(spike.sum()), "stockout_streaks": len(stockouts),
        "has_cost": bool(daily["cost"].sum() > 0), "has_quantity": bool(daily["quantity"].sum() > 0), "has_ad_spend": ad is not None,
        "total_revenue": float(daily["revenue"].sum()),
    })
    if health["months"] < 12:
        msgs.insert(0, {"level": "warn", "text": f"Only {health['months']} months of history. Forecasts work, but 12-24 months gives much better results, especially for seasonal products."})
    if not msgs:
        msgs.append({"level": "ok", "text": "Everything looks clean. No missing days, duplicates or unusual values."})
    daily_ad = ad.reindex(pd.date_range(daily["date"].min(), daily["date"].max()), fill_value=0) if ad is not None else None
    return daily, health, daily_ad


def read_stock(content: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(content))
    cols = {_norm(c): c for c in df.columns}
    need = {"branch", "product"}
    if not need <= set(cols) or not ({"on hand", "onhand", "stock", "quantity"} & set(cols)):
        raise DataError("The stock file needs columns: branch, product, on_hand")
    qty = next(cols[c] for c in ("on hand", "onhand", "stock", "quantity") if c in cols)
    return pd.DataFrame({"branch": df[cols["branch"]].astype(str), "product": df[cols["product"]].astype(str), "on_hand": pd.to_numeric(df[qty], errors="coerce").fillna(0)})
