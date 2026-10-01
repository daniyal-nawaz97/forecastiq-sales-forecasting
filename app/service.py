"""Datasets, caching and the numbers behind every screen."""
from __future__ import annotations

import json
import logging
import math
import threading
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import calendar, data, db, model
from .config import DATASETS_DIR

log = logging.getLogger("forecast.service")
_lock = threading.RLock()
_cache: dict = {}
_ds_cache: dict = {}


# --------------------------------------------------------------------------- datasets
def save_dataset(name: str, filename: str, raw_bytes: bytes, stock_bytes: bytes | None, is_demo=0, decisions=None, user=None) -> int:
    raw = data.read_any(filename, raw_bytes)
    daily, health, ad = data.clean(raw, decisions or {})
    did = db.execute("INSERT INTO datasets(name, filename, created_at, is_demo, health_json, decisions_json, uploaded_by) VALUES(?,?,?,?,?,?,?)",
                     (name, filename, db.now(), is_demo, json.dumps(health), json.dumps(decisions or {}), user))
    (DATASETS_DIR / f"{did}_raw{Path(filename).suffix.lower() or '.csv'}").write_bytes(raw_bytes)
    daily.to_pickle(DATASETS_DIR / f"{did}_daily.pkl")
    if ad is not None:
        ad.to_pickle(DATASETS_DIR / f"{did}_ad.pkl")
    if stock_bytes:
        data.read_stock(stock_bytes).to_csv(DATASETS_DIR / f"{did}_stock.csv", index=False)
    return did


def redo_cleaning(did: int, decisions: dict):
    d = db.one("SELECT * FROM datasets WHERE id=?", (did,))
    raw_path = next(DATASETS_DIR.glob(f"{did}_raw.*"))
    raw = data.read_any(raw_path.name, raw_path.read_bytes())
    daily, health, ad = data.clean(raw, decisions)
    daily.to_pickle(DATASETS_DIR / f"{did}_daily.pkl")
    if ad is not None:
        ad.to_pickle(DATASETS_DIR / f"{did}_ad.pkl")
    db.execute("UPDATE datasets SET health_json=?, decisions_json=? WHERE id=?", (json.dumps(health), json.dumps(decisions), did))
    invalidate()


def active_id() -> int | None:
    r = db.one("SELECT id FROM datasets WHERE active=1 ORDER BY id DESC LIMIT 1") or db.one("SELECT id FROM datasets ORDER BY id DESC LIMIT 1")
    return r["id"] if r else None


def load(did: int | None = None):
    did = did or active_id()
    if did is None:
        return None
    with _lock:
        if did not in _ds_cache:
            daily = pd.read_pickle(DATASETS_DIR / f"{did}_daily.pkl")
            ad_path = DATASETS_DIR / f"{did}_ad.pkl"
            stock_path = DATASETS_DIR / f"{did}_stock.csv"
            _ds_cache[did] = {"id": did, "daily": daily, "ad": pd.read_pickle(ad_path) if ad_path.exists() else None,
                              "stock": pd.read_csv(stock_path) if stock_path.exists() else None}
        return _ds_cache[did]


def events() -> list[dict]:
    rows = db.query("SELECT * FROM events ORDER BY start")
    return [{"name": r["name"], "start": date.fromisoformat(r["start"]), "end": date.fromisoformat(r["end"]), "kind": r["kind"], "discount": r["discount"] or 0}
            for r in rows]


def invalidate():
    with _lock:
        _cache.clear()
        _ds_cache.clear()


# --------------------------------------------------------------------------- cached forecasts
def run(product=None, category=None, branch=None, full=True):
    """Series + backtest + 12-month forecast for a selection (cached)."""
    ds = load()
    key = (ds["id"], product, category, branch, full)
    with _lock:
        if key in _cache:
            return _cache[key]
    ev = events()
    s = model.build_series(ds["daily"], ds["ad"], product=product, category=category, branch=branch)
    bt = model.backtest(s, ev, methods=("regression", "holt_winters") if full else ("regression",))
    fc = model.forecast(s, ev, 12, bt)
    res = {"series": s, "backtest": bt, "forecast": fc, "events": ev}
    with _lock:
        _cache[key] = res
    return res


def warm():
    """Pre-compute the common selections in the background so screens open instantly."""
    try:
        ds = load()
        if not ds:
            return
        run()
        stock_risks()
        d = ds["daily"]
        for b in sorted(d["branch"].unique()):
            run(branch=b)
        for c in sorted(d["category"].unique()):
            run(category=c)
        for p in sorted(d["product"].unique()):
            run(product=p)
        log.info("forecasts ready")
    except Exception:
        log.exception("warm-up failed")


def periods(s: model.Series, fc: dict, start: pd.Timestamp, fend: pd.Timestamp, rule: str, range_pct: float):
    """History and forecast by period. The period that contains today mixes actual + forecast days,
    and periods cut off at either end are dropped so the chart never shows false dips."""
    end = s.y.index.max()
    act = s.y[(s.y.index >= start) & (s.y.index <= end)]
    f = fc["daily"][(fc["daily"].index > end) & (fc["daily"].index <= fend)]
    lo, hi = fc["daily_low"].reindex(f.index), fc["daily_high"].reindex(f.index)
    allv = pd.concat([act, f])
    lab = allv.resample(rule).sum()
    counts = allv.resample(rule).count()
    fpart = f.resample(rule).sum().reindex(lab.index, fill_value=0)
    lop, hip = lo.resample(rule).sum().reindex(lab.index, fill_value=0), hi.resample(rule).sum().reindex(lab.index, fill_value=0)
    fdays = f.resample(rule).count().reindex(lab.index, fill_value=0)
    full = {"D": 1, "W-SUN": 7}.get(rule)
    hist, fore = [], []
    for i, (t, v) in enumerate(lab.items()):
        n = counts[t]
        expected_n = full or (t + pd.offsets.MonthEnd(0)).day
        if n < expected_n * 0.999 and (i == 0 or i == len(lab) - 1):
            continue  # partial period at the edges
        if fdays[t] == 0:
            hist.append((t, float(v)))
        else:
            actual_part = float(v - fpart[t])
            if rule == "D":
                l, h = actual_part + float(lop[t]), actual_part + float(hip[t])
            else:
                # weekly/monthly range from the measured monthly error (summing daily extremes would overstate it)
                width = min(0.9, model.Z80 * range_pct * (1.5 if rule == "W-SUN" else 1.0))
                l = actual_part + float(fpart[t]) * (1 - width)
                h = actual_part + float(fpart[t]) * (1 + width)
            fore.append((t, float(v), l, h))
    return hist, fore


# --------------------------------------------------------------------------- overview
def _last_month(s: model.Series):
    full = model.complete_months(s)
    m = full[-1]
    return m, float(model.monthly_actual(s)[m])


def overview() -> dict:
    r = run()
    s, bt, fc = r["series"], r["backtest"], r["forecast"]
    lm, lm_val = _last_month(s)
    nxt = fc["monthly"][0]
    # weekly chart: last 18 months actual + next 3 months forecast
    end = s.y.index.max()
    hist, fore = periods(s, fc, end - pd.DateOffset(months=18), end + pd.DateOffset(months=3), "W-SUN", bt["range_pct"])
    first_week = hist[0][0] if hist else end
    last_week = fore[-1][0] if fore else end
    flags = [{"date": str(e["start"]), "name": e["name"]} for e in r["events"]
             if first_week - pd.Timedelta(days=6) <= pd.Timestamp(e["start"]) <= last_week and e["kind"] in ("ramadan", "eid", "promotion", "adha_shopping")]
    return {
        "cards": {"last_month": lm.strftime("%B %Y"), "last_month_value": lm_val, "next_month": pd.Timestamp(nxt["month"] + "-01").strftime("%B %Y"),
                  "next_value": nxt["expected"], "growth": (nxt["expected"] / lm_val - 1) * 100, "low": nxt["low"], "high": nxt["high"],
                  "accuracy": round(100 * (1 - bt["error"]), 1) if bt["error"] is not None else None, "backtest_months": len(bt["rows"])},
        "chart": {"history": [{"week": d.strftime("%Y-%m-%d"), "value": v} for d, v in hist],
                  "forecast": [{"week": d.strftime("%Y-%m-%d"), "value": v, "low": l, "high": h} for d, v, l, h in fore],
                  "events": flags},
        "drivers": model.drivers(s, r["events"], fc),
        "attention": attention(),
        "data_to": s.y.index.max().strftime("%Y-%m-%d"),
    }


# --------------------------------------------------------------------------- attention: risks and opportunities
def _share_change(by: str, name: str) -> float | None:
    d = load()["daily"]
    d = d[~d["exclude"]]
    months = d.assign(m=d["date"].dt.to_period("M"))
    last_full = months["m"].max() - (0 if months["date"].max().is_month_end else 1)
    recent = [last_full - i for i in range(3)]
    prev = [last_full - i for i in range(3, 6)]
    tot_r = months[months["m"].isin(recent)]["revenue"].sum()
    tot_p = months[months["m"].isin(prev)]["revenue"].sum()
    sel = months[months[by] == name]
    r, p = sel[sel["m"].isin(recent)]["revenue"].sum(), sel[sel["m"].isin(prev)]["revenue"].sum()
    if p <= 0 or tot_p <= 0:
        return None
    return ((r / tot_r) / (p / tot_p) - 1) * 100  # change relative to the whole business, so seasons cancel out


def stock_risks() -> list[dict]:
    ds = load()
    st = ds["stock"]
    if st is None:
        return []
    key = ("stock", ds["id"])
    with _lock:
        if key in _cache:
            return _cache[key]
    out = _stock_risks(ds)
    with _lock:
        _cache[key] = out
    return out


def _stock_risks(ds) -> list[dict]:
    st = ds["stock"]
    d = ds["daily"]
    ev = events()
    out = []
    for row in st.itertuples():
        sel = d[(d["branch"] == row.branch) & (d["product"] == row.product)]
        if sel.empty:
            continue
        s = model.build_series(d, ds["ad"], product=row.product, branch=row.branch)
        reg = model.fit_regression(s, ev)
        end = s.y.index.max()
        dates = pd.date_range(end + pd.Timedelta(days=1), periods=30)
        rev30 = float(model.predict_regression(reg, dates, ev).sum())
        last = sel[sel["date"] > end - pd.Timedelta(days=30)]
        price = last["revenue"].sum() / max(1, last["quantity"].sum())
        units30 = rev30 / price if price else 0
        cover = row.on_hand / units30 * 30 if units30 else 99
        label = "Stock-out risk" if cover < 20 else "Overstock risk" if cover > 75 else "Healthy"
        out.append({"branch": row.branch, "product": row.product, "on_hand": int(row.on_hand), "units_30d": round(units30), "days_cover": round(cover), "label": label})
    return out


def attention() -> list[dict]:
    items = []
    for r in sorted(stock_risks(), key=lambda x: x["days_cover"]):
        if r["label"] == "Stock-out risk":
            items.append({"type": "risk", "text": f"{r['product']} may run short at {r['branch']}: {r['on_hand']} in stock, about {r['units_30d']} expected to sell in 30 days ({r['days_cover']} days of cover)."})
    d = load()["daily"]
    thr = float(db.get_settings().get("alert_threshold", 15))
    for b in sorted(d["branch"].unique()):
        ch = _share_change("branch", b)
        if ch is not None and ch <= -4:
            items.append({"type": "risk", "text": f"{b} is trending down {abs(ch):.0f}% over the last 3 months compared with the rest of the business."})
        elif ch is not None and ch >= 8:
            items.append({"type": "good", "text": f"{b} is growing {ch:.0f}% faster than the rest of the business over the last 3 months."})
    for p in sorted(d["product"].unique()):
        ch = _share_change("product", p)
        if ch is not None and ch <= -12:
            items.append({"type": "risk", "text": f"{p} is losing ground: {abs(ch):.0f}% behind the rest of the range over 3 months (after seasonality)."})
    for r in sorted(stock_risks(), key=lambda x: -x["days_cover"]):
        if r["label"] == "Overstock risk":
            items.append({"type": "warn", "text": f"{r['product']} overstock risk at {r['branch']}: {r['on_hand']} in stock covers about {r['days_cover']} days."})
    bt = run()["backtest"]
    if bt["rows"]:
        last = bt["rows"][-1]
        f = last.get(bt["best"])
        if f and last["actual"] < f * (1 - thr / 100):
            items.insert(0, {"type": "risk", "text": f"Sales in {pd.Timestamp(last['month'] + '-01'):%B} were {100 * (1 - last['actual'] / f):.0f}% below forecast (alert threshold {thr:.0f}%)."})
    return items[:7]


# --------------------------------------------------------------------------- products / categories / branches
def breakdown(by: str) -> list[dict]:
    d = load()["daily"]
    names = sorted(d[by].unique())
    risks = {}
    if by in ("product", "branch"):
        for r in stock_risks():
            k = r[by]
            risks.setdefault(k, []).append(r)
    rows = []
    for n in names:
        res = run(**{by: n})
        s, fc, bt = res["series"], res["forecast"], res["backtest"]
        lm, lm_val = _last_month(s)
        act = model.monthly_actual(s)
        spark = [float(v) for v in act[act.index <= lm].iloc[-12:]] + [m["expected"] for m in fc["monthly"][:3]]
        nxt = fc["monthly"][0]["expected"]
        growth = (nxt / lm_val - 1) * 100 if lm_val else None
        rs = risks.get(n, [])
        label = "Stock-out risk" if any(r["label"] == "Stock-out risk" for r in rs) else "Overstock risk" if any(r["label"] == "Overstock risk" for r in rs) else ("Healthy" if rs else None)
        trend = _share_change(by, n)
        if by == "branch":
            label = "Trending down" if trend is not None and trend <= -4 else "Growing" if trend is not None and trend >= 4 else "Steady"
        rows.append({"name": n, "last_month": lm_val, "next_month": nxt, "growth": growth, "spark": spark, "spark_split": len(spark) - 3, "risk": label,
                     "risk_detail": [f"{r['branch'] if by == 'product' else r['product']}: {r['days_cover']} days of cover" for r in rs if r["label"] != "Healthy"][:3],
                     "error": bt["error"], "method": bt["best"], "trend": trend})
    rows.sort(key=lambda r: -r["next_month"])
    return rows


# --------------------------------------------------------------------------- scenarios
def scenario(params: dict) -> dict:
    """What-if on the next N months. Effects are learned from history where possible; assumptions are stated."""
    months = int(params.get("months", 3))
    r = run(**{k: params.get(k) or None for k in ("product", "category", "branch")})
    s, bt, ev = r["series"], r["backtest"], r["events"]
    reg = r["forecast"]["model"]
    c = dict(zip(reg.names, reg.coef))
    base = r["forecast"]["monthly"][:months]
    disc = float(params.get("discount", 0)) / 100
    mkt = float(params.get("marketing", 0)) / 100
    price = float(params.get("price", 0)) / 100
    promo_coef = max(c.get("promo", 0), 0.0)  # how sales reacted to past discounts (log effect per 100% discount)
    unit_mult_disc = math.exp(promo_coef * disc) / max(1e-9, 1 - disc) if disc else 1.0  # units lift (revenue coef already nets the discount)
    ad_coef = max(c.get("ad", 0), 0.0)
    unit_mult_mkt = (1 + mkt) ** ad_coef if mkt > -1 else 1.0
    unit_mult_price = math.exp(-promo_coef * price) / (1 + price) if price else 1.0
    rev_mult = unit_mult_disc * (1 - disc) * unit_mult_mkt * unit_mult_price * (1 + price)
    # margin from historic cost ratio
    hist = s.y[s.y.index > s.y.index.max() - pd.Timedelta(days=90)].sum()
    cost_ratio = float(s.cost[s.cost.index > s.cost.index.max() - pd.Timedelta(days=90)].sum() / hist) if hist and s.cost.sum() > 0 else 0.65
    ad_month = float(s.ad.iloc[-56:].mean() * 30.4) if s.ad is not None else 0
    # new branch: average monthly sales of the most recently opened branch in its first months
    new_branch = []
    if params.get("new_branch"):
        d = load()["daily"]
        firsts = d.groupby("branch")["date"].min().sort_values()
        newest = firsts.index[-1]
        nb = d[d["branch"] == newest].assign(m=lambda x: x["date"].dt.to_period("M")).groupby("m")["revenue"].sum().iloc[1:4]
        open_at = int(params.get("branch_month", 1))
        for i in range(months):
            k = i - (open_at - 1)
            new_branch.append(float(nb.iloc[min(k, len(nb) - 1)]) * (1.0 if k >= 0 else 0) if len(nb) and k >= 0 else 0.0)
        nb_name = newest
    rows, tot = [], {"base_rev": 0, "scen_rev": 0, "base_margin": 0, "scen_margin": 0}
    for i, m in enumerate(base):
        b = m["expected"]
        units_cost = b * cost_ratio  # cost of the units sold at normal prices
        scen = b * rev_mult + (new_branch[i] if new_branch else 0)
        scen_cost = units_cost * unit_mult_disc * unit_mult_mkt * unit_mult_price + (new_branch[i] * cost_ratio if new_branch else 0)
        b_margin = b - units_cost
        s_margin = scen - scen_cost - ad_month * mkt
        rows.append({"month": m["month"], "baseline": b, "scenario": scen, "low": m["low"], "high": m["high"]})
        tot["base_rev"] += b; tot["scen_rev"] += scen; tot["base_margin"] += b_margin; tot["scen_margin"] += s_margin
    parts = []
    if disc:
        parts.append(f"a {disc * 100:.0f}% discount")
    if mkt:
        parts.append(f"{'+' if mkt > 0 else ''}{mkt * 100:.0f}% marketing spend")
    if price:
        parts.append(f"a {price * 100:.0f}% price increase")
    if new_branch:
        parts.append(f"a new branch (based on how {nb_name} started)")
    dr, dm = tot["scen_rev"] - tot["base_rev"], tot["scen_margin"] - tot["base_margin"]
    summary = (f"With {', '.join(parts)}, revenue over {months} month{'s' if months > 1 else ''} could {'rise' if dr >= 0 else 'fall'} by about Rs. {abs(dr) / 1e3:,.0f}k "
               f"and margin {'rise' if dm >= 0 else 'fall'} by about Rs. {abs(dm) / 1e3:,.0f}k.") if parts else "Move a slider to see how a decision could change the next months."
    return {"rows": rows, "totals": tot, "summary": summary, "cost_ratio": cost_ratio,
            "assumptions": [f"Discount and price effects come from how sales reacted to past promotions ({len([e for e in ev if e['kind'] == 'promotion'])} in the calendar).",
                            "A price increase is assumed to work like a discount in reverse.",
                            f"Marketing: based on past ad spend (about Rs. {ad_month / 1e3:,.0f}k a month); the extra spend is subtracted from margin." if s.ad is not None else "No ad-spend history in this data, so marketing has no effect.",
                            f"Margin uses your recent cost ratio ({cost_ratio * 100:.0f}% of sales)."]}


# --------------------------------------------------------------------------- accuracy
def accuracy() -> dict:
    r = run()
    bt = r["backtest"]
    d = load()["daily"]
    per = []
    for p in sorted(d["product"].unique()):
        b = run(product=p)["backtest"]
        e = b["error"]
        per.append({"product": p, "error": e, "simple_error": b["simple_error"], "method": b["best"],
                    "label": None if e is None else "Easy to forecast" if e < 0.08 else "Moderate" if e < 0.15 else "Hard to forecast"})
    per.sort(key=lambda x: x["error"] if x["error"] is not None else 9)
    names = {"regression": "Explainable model (trend, season, Ramadan/Eid, promotions, ads)", "holt_winters": "Holt-Winters smoothing",
             "last_month": "Simple guess: same as last month", "last_year": "Simple guess: same month last year"}
    return {"rows": bt["rows"], "best": bt["best"], "error": bt["error"], "simple_method": names.get(bt["simple_method"]), "simple_error": bt["simple_error"],
            "improvement": bt["improvement"], "within_range": bt["within_range"], "range_pct": bt["range_pct"],
            "methods": [{"key": k, "name": names[k], "error": v, "chosen": k == bt["best"]} for k, v in sorted(bt["scores"].items(), key=lambda x: (x[1] is None, x[1]))],
            "products": per}
