"""Measure forecast accuracy with a rolling backtest (each month forecast using only earlier data).

    python -m scripts.evaluate                       # the demo company
    python -m scripts.evaluate --file client.xlsx    # a client's own sales file

Writes docs/results.md and docs/results.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app import calendar, data, model  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(BASE / "sample_data" / "sahara_mart_sales.csv"))
    ap.add_argument("--months", type=int, default=6)
    args = ap.parse_args()
    demo = args.file.endswith("sahara_mart_sales.csv")
    path = Path(args.file)
    raw = data.read_any(path.name, path.read_bytes())
    daily, health, ad = data.clean(raw, {"missing": "missing"})
    events = calendar.default_events() + (calendar.DEMO_PROMOTIONS if demo else [])
    t0 = time.time()
    results = {}
    selections = [("Whole business", {})] + [(f"Branch: {b}", {"branch": b}) for b in sorted(daily["branch"].unique())] + \
                 [(f"Product: {p}", {"product": p}) for p in sorted(daily["product"].unique())]
    for name, f in selections:
        s = model.build_series(daily, ad, **f)
        bt = model.backtest(s, events, months=args.months)
        results[name] = {"best": bt["best"], "error": bt["error"], "scores": bt["scores"], "simple_method": bt["simple_method"],
                         "simple_error": bt["simple_error"], "improvement": bt["improvement"], "within_range": bt["within_range"], "rows": bt["rows"]}
    total = results["Whole business"]
    pct = lambda v: "—" if v is None else f"{v * 100:.1f}%"  # noqa: E731
    names = {"regression": "Explainable model", "holt_winters": "Holt-Winters", "last_month": "Same as last month", "last_year": "Same month last year"}
    summary = {"date": date.today().isoformat(), "file": path.name, "months_tested": len(total["rows"]), "error": total["error"],
               "accuracy": None if total["error"] is None else round(100 * (1 - total["error"]), 1),
               "simple_method": names.get(total["simple_method"]), "simple_error": total["simple_error"],
               "improvement": total["improvement"], "within_range": total["within_range"], "seconds": round(time.time() - t0, 1),
               "products_easy": sum(1 for k, v in results.items() if k.startswith("Product") and v["error"] is not None and v["error"] < 0.08),
               "products": sum(1 for k in results if k.startswith("Product"))}
    payload = {"summary": summary, "series": results}
    (BASE / "docs" / "results.json").write_text(json.dumps(payload, indent=2, default=str))
    (BASE / "static" / "results.json").write_text(json.dumps(payload, indent=2, default=str))
    md = [f"# Measured results ({summary['date']})", "",
          f"Data: `{path.name}` ({health['rows_read']:,} rows, {health['months']} months, {health['products']} products, {health['branches']} branches). "
          f"Rolling backtest: each of the last {summary['months_tested']} complete months was forecast using only the data before it.", "",
          "## Whole business", "", "| Metric | Result |", "|---|---|",
          f"| Average monthly error | **{pct(total['error'])}** (accuracy {summary['accuracy']}%) |",
          f"| Best simple guess ({summary['simple_method']}) | {pct(total['simple_error'])} error |",
          f"| Better than the simple guess by | **{'—' if total['improvement'] is None else f'{total['improvement'] * 100:.0f}%'}** |",
          f"| Months inside the 80% likely range | {total['within_range']}% |",
          f"| Method chosen | {names[total['best']]} |", "",
          "| Method | Average error |", "|---|---|"] + [f"| {names[k]} | {pct(v)} |" for k, v in sorted(total["scores"].items(), key=lambda x: (x[1] is None, x[1]))] + [
          "", "| Month | Actual | Forecast made beforehand | Error |", "|---|---|---|---|"] + [
          f"| {r['month']} | Rs. {r['actual'] / 1e6:.2f}M | Rs. {r[total['best']] / 1e6:.2f}M | {abs(r[total['best']] - r['actual']) / r['actual'] * 100:.1f}% |" for r in total["rows"]] + [
          "", "## By branch and product", "", "| Selection | Method | Error | Simple guess error |", "|---|---|---|---|"] + [
          f"| {k} | {names[v['best']]} | {pct(v['error'])} | {pct(v['simple_error'])} |" for k, v in results.items() if k != "Whole business"]
    if demo:
        md += ["", "**Honest note.** Sahara Mart is a fictitious company whose sales were generated with patterns similar to what the model looks for "
               "(trend, weekdays, seasons, Ramadan/Eid, promotions, ad spend). These numbers show the method works end to end, but they are "
               "**optimistic**. Real sales have surprises the model can't know about. Run `python -m scripts.evaluate --file their_sales.xlsx` "
               "on a client's own data and quote that result instead; the app's Accuracy screen shows the same test for whatever data is loaded."]
    (BASE / "docs" / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:16]))


if __name__ == "__main__":
    main()
