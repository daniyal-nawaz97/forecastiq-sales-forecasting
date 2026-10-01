# Client onboarding and handover

## Onboarding (after they say yes)
1. **Collect 12-24+ months of sales** with date, product, branch, quantity and revenue ([data-requirements.md](data-requirements.md)). Add unit cost for margin and a stock file for stock-out warnings.
2. **Ask about distortions**: promotions, price changes, new branches, stock-outs, system outages. Add them in Settings → Holidays & events.
3. **Upload and review the health check together**: answer the missing-days question; confirm the typing errors.
4. **Agree the level and horizon**: total, products, branches; 1, 3, 6 or 12 months.
5. **Show the Accuracy screen before going live.** Write down the error and "better than a simple guess" number for the case study.
6. **Set the monthly refresh**: who uploads the new month, report day and recipients.
7. **Hand over** with a 5-minute walkthrough video.

## Handover checklist
- [ ] `DEMO_MODE=0`, admin login shared securely, team added with roles
- [ ] Events calendar includes their promotions and openings
- [ ] Accuracy reviewed and recorded
- [ ] Monthly report emailing tested (SMTP in `.env`)
- [ ] Logo and colours set (they appear on screens and PDFs)
- [ ] Retainer terms: monthly refresh date, review call, support response time

## Monthly routine (15 minutes)
1. Upload the new month's export on the Data page.
2. Read the health-check messages.
3. Check Accuracy: last month's forecast vs actual.
4. Generate and send the monthly report; walk through it on the review call.
