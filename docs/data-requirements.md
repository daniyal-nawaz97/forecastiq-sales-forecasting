# Data requirements: what to send for a forecast

**Short version:** one Excel or CSV file with one row per sale (or per product per day), covering at least 12 months. 24+ months is ideal.

## Columns

| Column | Required? | Example | Notes |
|---|---|---|---|
| `date` | **Yes** | 2026-09-14 or 14/09/2026 | Any common date format |
| `revenue` | **Yes** (or `quantity` + `unit_price`) | 5400 | Net sales amount for the row |
| `product` | Recommended | Mango Juice 1L | Name or SKU; needed for product forecasts |
| `branch` | Recommended | Lahore (DHA) | Store, outlet, warehouse or channel (e.g. "Online") |
| `quantity` | Recommended | 12 | Units sold; needed for stock-out risk |
| `category` | Optional | Beverages | For category forecasts |
| `unit_cost` | Optional | 300 | Enables margin in scenarios |
| `ad_spend` | Optional | 21000 | Daily marketing spend; lets scenarios estimate its effect |

Column names don't need to match exactly: "Sale Date", "Item", "Store", "Qty", "Net Sales" are recognised. A template is at `sample_data/sales_template.csv` (or **Download our sample format** on the Data page).

## Optional: stock file
For stock-out and overstock warnings: a CSV with `branch, product, on_hand` (current stock).

## Please also tell us about
- **Promotions and sales** (dates and discount %)
- **Price changes** (date, which products, by how much)
- **New branches** opened or closed (dates)
- **Stock shortages** or system outages (dates)

These are added to the events calendar so they explain past sales instead of confusing the forecast.

## What we do with messy data
Duplicates are removed, typing errors (e.g. an extra zero) are left out, long zero-sales runs are treated as stock-outs, and missing days are flagged with a question. Every change is listed on the Data page in plain language.

## Privacy
Your file stays in your own installation, is never sent to outside AI services, and is deleted on request.
