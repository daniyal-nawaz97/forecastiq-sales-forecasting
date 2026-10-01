"""Holiday and event calendar (Pakistan defaults). Clients add their own campaigns in Settings."""
from __future__ import annotations

from datetime import date, timedelta

# Islamic dates (approximate, moon sighting can shift a day)
RAMADAN = {2024: (date(2024, 3, 11), date(2024, 4, 9)), 2025: (date(2025, 3, 1), date(2025, 3, 30)),
           2026: (date(2026, 2, 18), date(2026, 3, 19)), 2027: (date(2027, 2, 8), date(2027, 3, 9)), 2028: (date(2028, 1, 28), date(2028, 2, 26))}
EID_FITR = {2024: date(2024, 4, 10), 2025: date(2025, 3, 31), 2026: date(2026, 3, 20), 2027: date(2027, 3, 10), 2028: date(2028, 2, 27)}
EID_ADHA = {2024: date(2024, 6, 17), 2025: date(2025, 6, 7), 2026: date(2026, 5, 27), 2027: date(2027, 5, 17), 2028: date(2028, 5, 5)}


def default_events(years=range(2024, 2029)) -> list[dict]:
    """Events: name, start, end, kind (holiday | promotion | shopping), discount (0-1 for promotions)."""
    ev = []
    for y in years:
        if y in RAMADAN:
            s, e = RAMADAN[y]
            ev.append({"name": "Ramadan", "start": s, "end": e, "kind": "ramadan", "discount": 0})
        if y in EID_FITR:
            d = EID_FITR[y]
            ev.append({"name": "Eid shopping (Chaand Raat week)", "start": d - timedelta(days=7), "end": d - timedelta(days=1), "kind": "eid_shopping", "discount": 0})
            ev.append({"name": "Eid ul Fitr", "start": d, "end": d + timedelta(days=2), "kind": "eid", "discount": 0})
        if y in EID_ADHA:
            d = EID_ADHA[y]
            ev.append({"name": "Eid ul Adha shopping", "start": d - timedelta(days=6), "end": d - timedelta(days=1), "kind": "adha_shopping", "discount": 0})
            ev.append({"name": "Eid ul Adha", "start": d, "end": d + timedelta(days=2), "kind": "eid", "discount": 0})
        ev.append({"name": "Independence Day", "start": date(y, 8, 14), "end": date(y, 8, 14), "kind": "holiday", "discount": 0})
        ev.append({"name": "11.11 Sale", "start": date(y, 11, 11), "end": date(y, 11, 11), "kind": "promotion", "discount": 0.20})
        ev.append({"name": "Year-End Sale", "start": date(y, 12, 26), "end": date(y, 12, 31), "kind": "promotion", "discount": 0.10})
    return ev


# The demo company's own campaigns (a client adds theirs in Settings → Events)
DEMO_PROMOTIONS = [
    {"name": "Summer Mega Sale", "start": date(2025, 6, 20), "end": date(2025, 6, 30), "kind": "promotion", "discount": 0.15},
    {"name": "Ramadan Bachat Week (household)", "start": date(2026, 3, 5), "end": date(2026, 3, 12), "kind": "promotion", "discount": 0.10},
]
