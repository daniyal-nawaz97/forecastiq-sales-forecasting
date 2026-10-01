"""Forecasting engine.

Methods compared on the client's own past months (rolling backtest):
  * Explainable regression: trend (+ recent change), weekday, yearly season, Ramadan / Eid / holidays,
    promotions (discount depth), ad spend, number of branches open. Fitted on log sales with a little ridge.
  * Holt-Winters exponential smoothing (weekly pattern, damped trend).
  * Simple guesses: "same as last month" and "same month last year" (the baseline to beat).
The best of the two real methods is used for each series. Ranges come from the backtest errors.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

Z80 = 1.2816
MIN_RANGE = 0.04


# --------------------------------------------------------------------------- series
@dataclass
class Series:
    y: pd.Series            # daily revenue
    units: pd.Series
    cost: pd.Series
    exclude: pd.Series      # True = leave out of fitting (missing days, stock-outs, typos)
    branches_open: pd.Series
    ad: pd.Series | None


def build_series(daily: pd.DataFrame, ad: pd.Series | None, product=None, category=None, branch=None) -> Series:
    d = daily
    if product:
        d = d[d["product"] == product]
    if category:
        d = d[d["category"] == category]
    if branch:
        d = d[d["branch"] == branch]
    if d.empty:
        raise ValueError("No sales for this selection")
    idx = pd.date_range(d["date"].min(), daily["date"].max(), freq="D")
    g = d.groupby("date")
    y = g["revenue"].sum().reindex(idx, fill_value=0.0)
    units = g["quantity"].sum().reindex(idx, fill_value=0.0)
    cost = g["cost"].sum().reindex(idx, fill_value=0.0)
    # a day is left out if most of its revenue rows are flagged
    excl = g.apply(lambda x: x["exclude"].mean() > 0.5 if len(x) else False, include_groups=False).reindex(idx, fill_value=False).astype(bool)
    firsts = d.groupby("branch")["date"].min()
    lasts = d.groupby("branch")["date"].max()
    bo = pd.Series([sum((f <= t) and (t <= l) for f, l in zip(firsts, lasts)) for t in idx], index=idx, dtype=float)
    a = ad.reindex(idx).ffill().fillna(ad.mean()) if ad is not None and ad.sum() > 0 else None
    return Series(y, units, cost, excl, bo, a)


# --------------------------------------------------------------------------- features
def event_matrix(dates: pd.DatetimeIndex, events: list[dict]):
    kinds = ["ramadan", "ramadan_last10", "eid_shopping", "eid", "adha_shopping", "holiday", "promo"]
    m = {k: np.zeros(len(dates)) for k in kinds}
    for ev in events:
        s, e = pd.Timestamp(ev["start"]), pd.Timestamp(ev["end"])
        mask = (dates >= s) & (dates <= e)
        if not mask.any():
            continue
        k = ev["kind"]
        if k == "promotion" or ev.get("discount"):
            m["promo"][mask] = np.maximum(m["promo"][mask], float(ev.get("discount") or 0.1))
        if k == "ramadan":
            m["ramadan"][mask] = 1
            m["ramadan_last10"][(dates >= e - pd.Timedelta(days=9)) & (dates <= e)] = 1
        elif k in ("eid_shopping", "eid", "adha_shopping", "holiday"):
            m[k][mask] = 1
    return m


def features(dates: pd.DatetimeIndex, events, t0: pd.Timestamp, hinge_at: pd.Timestamp, branches_open, ad_ratio):
    t = (dates - t0).days.values / 365.0
    cols, names = [np.ones(len(dates)), t, np.maximum(0, (dates - hinge_at).days.values / 365.0)], ["intercept", "trend", "recent_trend"]
    dow = dates.dayofweek.values
    for k in range(1, 7):
        cols.append((dow == k).astype(float)); names.append(f"dow{k}")
    doy = dates.dayofyear.values / 365.25 * 2 * np.pi
    for k in (1, 2, 3):
        cols += [np.sin(k * doy), np.cos(k * doy)]; names += [f"sin{k}", f"cos{k}"]
    for k, v in event_matrix(dates, events).items():
        cols.append(v); names.append(k)
    cols.append(np.log(np.maximum(branches_open, 1))); names.append("branches")
    cols.append(np.log(np.clip(ad_ratio, 0.2, 5)) if ad_ratio is not None else np.zeros(len(dates))); names.append("ad")
    return np.column_stack(cols), names


@dataclass
class RegModel:
    coef: np.ndarray
    names: list
    t0: pd.Timestamp
    hinge: pd.Timestamp
    sigma: float
    smear: float
    ad_mean: float | None
    ad_recent: float | None
    branches_last: float
    end: pd.Timestamp


def fit_regression(s: Series, events, end: pd.Timestamp | None = None) -> RegModel:
    end = end or s.y.index.max()
    mask = (s.y.index <= end) & (~s.exclude.values)
    dates = s.y.index[mask]
    yv = s.y[s.y.index <= end].where(~s.exclude[s.exclude.index <= end])
    if (yv == 0).mean() > 0.15:
        # sparse series (many zero days): fit on a 7-day average so zeros don't drag the log scale down
        yv = yv.rolling(7, center=True, min_periods=3).mean()
    y = np.log1p(yv.reindex(dates).fillna(0).values)
    t0 = s.y.index.min()
    hinge = end - pd.Timedelta(days=150)
    ad_mean = float(s.ad[s.ad.index <= end].mean()) if s.ad is not None else None
    ad_ratio = (s.ad.values[mask] / ad_mean) if s.ad is not None else None
    X, names = features(dates, events, t0, hinge, s.branches_open.values[mask], ad_ratio)
    # ridge: light on everything, stronger on the recent-trend hinge so it doesn't over-extrapolate
    lam = np.full(X.shape[1], 0.5)
    lam[0] = 0
    lam[names.index("recent_trend")] = 2.0
    A = X.T @ X + np.diag(lam)
    coef = np.linalg.solve(A, X.T @ y)
    resid = y - X @ coef
    recent = s.ad[(s.ad.index <= end)].iloc[-56:].mean() if s.ad is not None else None
    return RegModel(coef, names, t0, hinge, float(resid.std()), float(np.mean(np.exp(resid))), ad_mean, recent,
                    float(s.branches_open[s.branches_open.index <= end].iloc[-1]), end)


def predict_regression(m: RegModel, dates: pd.DatetimeIndex, events, branches_open=None, ad_mult: float = 1.0, extra: dict | None = None):
    bo = np.full(len(dates), branches_open if branches_open is not None else m.branches_last)
    ad_ratio = np.full(len(dates), (m.ad_recent * ad_mult) / m.ad_mean) if m.ad_mean else None
    X, names = features(dates, events, m.t0, m.hinge, bo, ad_ratio)
    if extra:
        for k, v in extra.items():
            X[:, names.index(k)] = v
    return np.maximum(0, np.expm1(X @ m.coef) * m.smear)


def fit_predict_hw(s: Series, end: pd.Timestamp, dates: pd.DatetimeIndex):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    y = s.y[s.y.index <= end].copy()
    y[s.exclude[s.exclude.index <= end].values] = np.nan
    y = y.interpolate(limit_direction="both").clip(lower=0) + 1
    y = y.iloc[-540:]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(y, trend="add", damped_trend=True, seasonal="mul", seasonal_periods=7, initialization_method="estimated").fit()
    steps = (dates.max() - end).days
    fc = fit.forecast(steps)
    fc.index = pd.date_range(end + pd.Timedelta(days=1), periods=steps, freq="D")
    return np.maximum(0, fc.reindex(dates).values - 1)


# --------------------------------------------------------------------------- monthly helpers
def month_starts(after: pd.Timestamp, n: int):
    first = (after + pd.offsets.MonthBegin(1)).normalize()
    return [first + pd.DateOffset(months=i) for i in range(n)]


def monthly_actual(s: Series) -> pd.Series:
    return s.y.resample("MS").sum()


def complete_months(s: Series) -> list[pd.Timestamp]:
    ms = monthly_actual(s)
    end = s.y.index.max()
    out = [m for m in ms.index if (m + pd.offsets.MonthEnd(0)) <= end and m >= s.y.index.min()]
    return out


def backtest(s: Series, events, months: int = 6, methods=("regression", "holt_winters")) -> dict:
    """Forecast each of the last `months` complete months using only data before it."""
    full = complete_months(s)
    act = monthly_actual(s)
    rows = []
    for m in full[-months:]:
        end = m - pd.Timedelta(days=1)
        if (end - s.y.index.min()).days < 300:
            continue
        dates = pd.date_range(m, m + pd.offsets.MonthEnd(0), freq="D")
        r = {"month": m.strftime("%Y-%m"), "actual": float(act[m])}
        # months with missing / excluded days: compare like with like
        if "regression" in methods:
            r["regression"] = float(predict_regression(fit_regression(s, events, end), dates, events).sum())
        if "holt_winters" in methods:
            try:
                r["holt_winters"] = float(fit_predict_hw(s, end, dates).sum())
            except Exception:
                r["holt_winters"] = None
        prev = m - pd.DateOffset(months=1)
        ly = m - pd.DateOffset(months=12)
        r["last_month"] = float(act[prev]) if prev in act.index else None
        r["last_year"] = float(act[ly]) if ly in act.index and ly >= s.y.index.min() else None
        excl_frac = float(s.exclude[(s.exclude.index >= m) & (s.exclude.index <= dates.max())].mean())
        r["excluded_share"] = excl_frac
        rows.append(r)

    def mape(key):
        vals = [abs(r[key] - r["actual"]) / r["actual"] for r in rows if r.get(key) is not None and r["actual"] > 0 and r["excluded_share"] < 0.2]
        return float(np.mean(vals)) if vals else None

    def bias_rmse(key):
        vals = [(r[key] - r["actual"]) / r["actual"] for r in rows if r.get(key) is not None and r["actual"] > 0 and r["excluded_share"] < 0.2]
        return float(np.sqrt(np.mean(np.square(vals)))) if vals else None

    scores = {k: mape(k) for k in ("regression", "holt_winters", "last_month", "last_year") if any(r.get(k) is not None for r in rows)}
    real = {k: v for k, v in scores.items() if k in ("regression", "holt_winters") and v is not None}
    best = min(real, key=real.get) if real else "regression"
    simple = {k: v for k, v in scores.items() if k in ("last_month", "last_year") and v is not None}
    simple_best = min(simple, key=simple.get) if simple else None
    rmse = bias_rmse(best) or 0.1
    within = [abs(r[best] - r["actual"]) <= Z80 * max(rmse, MIN_RANGE) * r[best] for r in rows if r.get(best)]
    return {"rows": rows, "scores": scores, "best": best, "error": scores.get(best), "simple_method": simple_best,
            "simple_error": simple.get(simple_best) if simple_best else None, "range_pct": max(rmse, MIN_RANGE),
            "within_range": round(100 * sum(within) / len(within)) if within else None,
            "improvement": (1 - scores[best] / simple[simple_best]) if simple_best and scores.get(best) and simple[simple_best] else None}


def forecast(s: Series, events, months: int, bt: dict | None = None, method: str | None = None, **scenario) -> dict:
    """Daily forecast for the next `months` calendar months after the data ends, with an 80% range."""
    end = s.y.index.max()
    starts = month_starts(end, months)
    dates = pd.date_range(starts[0], starts[-1] + pd.offsets.MonthEnd(0), freq="D")
    bt = bt or backtest(s, events)
    method = method or bt["best"]
    reg = fit_regression(s, events)
    if method == "holt_winters" and not scenario:
        try:
            exp = fit_predict_hw(s, end, dates)
            # Holt-Winters has no yearly / Ramadan memory: blend in the regression's view beyond 6 weeks
            reg_fc = predict_regression(reg, dates, events)
            w = np.clip((dates - dates[0]).days.values / 42.0, 0, 1)
            exp = (1 - w) * exp + w * reg_fc
        except Exception:
            exp, method = predict_regression(reg, dates, events), "regression"
    else:
        exp = predict_regression(reg, dates, events, **scenario)
    daily = pd.Series(exp, index=dates)
    monthly = daily.resample("MS").sum()
    rp = bt["range_pct"]
    out = []
    for i, (m, v) in enumerate(monthly.items()):
        width = Z80 * rp * math.sqrt(1 + 0.35 * i)
        out.append({"month": m.strftime("%Y-%m"), "expected": float(v), "low": float(v * (1 - width)), "high": float(v * (1 + width))})
    dsig = min(reg.sigma, 0.6)  # cap: very sparse series would otherwise get meaningless daily ranges
    return {"daily": daily, "daily_low": daily * np.exp(-Z80 * dsig), "daily_high": daily * np.exp(Z80 * dsig), "monthly": out, "method": method, "model": reg}


# --------------------------------------------------------------------------- plain-language drivers
def drivers(s: Series, events, fc: dict) -> list[str]:
    m: RegModel = fc["model"]
    c = dict(zip(m.names, m.coef))
    out = []
    growth = (math.exp((c["trend"] + c["recent_trend"]) / 12) - 1) * 100
    long_growth = (math.exp(c["trend"] / 12) - 1) * 100
    if abs(growth) >= 0.3:
        out.append(f"{'Growing' if growth > 0 else 'Declining'} trend: {growth:+.1f}% per month recently" + (f" (was {long_growth:+.1f}% earlier)" if abs(growth - long_growth) > 1 else "") + ".")
    wk = np.mean([c.get("dow5", 0), c.get("dow6", 0)]) - np.mean([0, c.get("dow1", 0), c.get("dow2", 0), c.get("dow3", 0)])
    sparse = (s.y == 0).mean() > 0.15  # smoothed before fitting, so weekday effects aren't meaningful
    if abs(wk) > 0.03 and not sparse:
        out.append(f"Weekends sell about {abs(math.expm1(wk)) * 100:.0f}% {'more' if wk > 0 else 'less'} than weekdays.")
    first = pd.Timestamp(fc["monthly"][0]["month"] + "-01")
    days = pd.date_range(first, first + pd.offsets.MonthEnd(0))
    yr = pd.date_range(first - pd.DateOffset(months=6), first + pd.DateOffset(months=6))

    def season(ds):
        doy = ds.dayofyear.values / 365.25 * 2 * np.pi
        return sum(c[f"sin{k}"] * np.sin(k * doy) + c[f"cos{k}"] * np.cos(k * doy) for k in (1, 2, 3))
    sea = math.expm1(np.mean(season(days)) - np.mean(season(yr))) * 100
    if abs(sea) >= 2:
        out.append(f"{first:%B} is usually {abs(sea):.0f}% {'above' if sea > 0 else 'below'} an average month for this selection.")
    horizon_end = pd.Timestamp(fc["monthly"][-1]["month"] + "-01") + pd.offsets.MonthEnd(0)
    seen = set()
    for ev in sorted(events, key=lambda e: e["start"]):
        s0, e0 = pd.Timestamp(ev["start"]), pd.Timestamp(ev["end"])
        if s0 > horizon_end or e0 < first or ev["name"] in seen:
            continue
        seen.add(ev["name"])
        k = ev["kind"]
        coef = c.get("promo", 0) * (ev.get("discount") or 0.1) if k == "promotion" else c.get({"ramadan": "ramadan"}.get(k, k), 0)
        if abs(coef) < 0.04:
            continue
        out.append(f"{ev['name']} ({s0:%d %b}{'' if s0 == e0 else f' – {e0:%d %b}'}): about {math.expm1(coef) * 100:+.0f}% on those days.")
        if len(seen) >= 3:
            break
    if c.get("ad") and s.ad is not None and abs(c["ad"]) > 0.02:
        out.append(f"Ad spend matters: 10% more spend has gone with about {(1.1 ** c['ad'] - 1) * 100:.1f}% more sales.")
    return out[:5]
