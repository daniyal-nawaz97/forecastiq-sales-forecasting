# Measured results (2026-10-01)

Data: `sahara_mart_sales.csv` (29,293 rows, 30 months, 12 products, 3 branches). Rolling backtest: each of the last 6 complete months was forecast using only the data before it.

## Whole business

| Metric | Result |
|---|---|
| Average monthly error | **2.3%** (accuracy 97.7%) |
| Best simple guess (Same as last month) | 6.5% error |
| Better than the simple guess by | **65%** |
| Months inside the 80% likely range | 100% |
| Method chosen | Explainable model |

| Method | Average error |
|---|---|
| Explainable model | 2.3% |
| Holt-Winters | 4.3% |
| Same as last month | 6.5% |
| Same month last year | 16.3% |

| Month | Actual | Forecast made beforehand | Error |
|---|---|---|---|
| 2026-04 | Rs. 6.39M | Rs. 6.44M | 0.8% |
| 2026-05 | Rs. 6.96M | Rs. 7.06M | 1.5% |
| 2026-06 | Rs. 6.74M | Rs. 6.60M | 2.0% |
| 2026-07 | Rs. 7.11M | Rs. 7.05M | 1.0% |
| 2026-08 | Rs. 6.99M | Rs. 7.32M | 4.8% |
| 2026-09 | Rs. 6.64M | Rs. 6.88M | 3.6% |

## By branch and product

| Selection | Method | Error | Simple guess error |
|---|---|---|---|
| Branch: Islamabad (F-7) | Holt-Winters | 8.5% | 12.0% |
| Branch: Karachi (Clifton) | Explainable model | 4.6% | 10.1% |
| Branch: Lahore (DHA) | Explainable model | 1.0% | 10.1% |
| Product: Basmati Rice 5kg | Explainable model | 4.1% | 14.1% |
| Product: Body Lotion 300ml | Explainable model | 4.4% | 14.4% |
| Product: Chocolate Cookies 12-Pack | Explainable model | 5.2% | 10.2% |
| Product: Detergent Powder 2kg | Holt-Winters | 5.3% | 5.1% |
| Product: Dishwash Liquid 750ml | Holt-Winters | 3.8% | 2.9% |
| Product: Green Tea 25 Bags | Explainable model | 6.3% | 16.7% |
| Product: Herbal Shampoo 400ml | Explainable model | 4.6% | 3.4% |
| Product: Mango Juice 1L | Explainable model | 6.6% | 11.5% |
| Product: Mineral Water 1.5L | Explainable model | 4.1% | 12.4% |
| Product: Potato Chips Family Pack | Explainable model | 4.9% | 4.8% |
| Product: Premium Dates 500g | Explainable model | 9.9% | 10.0% |
| Product: Sunscreen SPF50 | Holt-Winters | 12.2% | 15.9% |

**Honest note.** Sahara Mart is a fictitious company whose sales were generated with patterns similar to what the model looks for (trend, weekdays, seasons, Ramadan/Eid, promotions, ad spend). These numbers show the method works end to end, but they are **optimistic**. Real sales have surprises the model can't know about. Run `python -m scripts.evaluate --file their_sales.xlsx` on a client's own data and quote that result instead; the app's Accuracy screen shows the same test for whatever data is loaded.
