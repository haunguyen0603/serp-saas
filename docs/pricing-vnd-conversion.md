# VND pricing conversion

Implemented and applied locally on **2026-10-11**. Production has not been changed by this work.

## Rate and prices

The user selected exact conversion at **1 USD = 26,070 VND**, using Vietcombank's selling rate retrieved on 2026-10-11. At retrieval, cash buying was 25,660 and transfer buying was 25,690 VND/USD. Sources: [Vietcombank exchange rates](https://www.vietcombank.com.vn/vi-VN/KHCN/Cong-cu-tien-ich/Ty-gia), [official XML feed](https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx). This is a fixed catalog price conversion; prices do not change automatically with later exchange rates.

These are the existing prices verified from the production catalog and local API before conversion, per month:

| Plan            | Previous USD |   New VND |
| --------------- | -----------: | --------: |
| Desktop Free    |            0 |         0 |
| Desktop Starter |           19 |   495,330 |
| Desktop Pro     |          129 | 3,363,030 |
| Mobile Free     |            0 |         0 |
| Mobile Starter  |           39 | 1,016,730 |
| Mobile Pro      |          199 | 5,187,930 |

No rounding to thousands or commercial price adjustment was applied. VND is rendered as `495.330 ₫`, without decimal digits, on English and Vietnamese Pricing, Change Plan, Billing, Admin activation options and Admin history.

## Data behavior

- Migration `0015_vnd_pricing` converts every existing USD catalog amount from cents to dong using `USD cents × 26,070 / 100`, and changes its currency to VND. It preserves any administrator's actual catalog edits; it does not replace amounts with hardcoded defaults. Historical migrations still seed their historical values on a fresh database, which are then converted at this rate.
- Existing subscription snapshots, catalog audit history, usage periods, resource limits, schedules and identities are unchanged. Existing USD subscriptions continue to show their original USD price; new subscriptions use VND terms from the catalog. Extending an existing subscription preserves its saved terms.
- VND amounts are integer dong in `price_monthly_minor_units`; USD remains integer cents. Shared formatting/editor logic derives precision from the currency. Admin VND inputs accept whole dong, with a step of 1, and reject fractional dong.
- The four current paid prices convert exactly. An administrator's historical fractional-cent-derived conversion is rounded to the nearest whole dong, half up. A result above signed 32-bit storage is rejected transactionally. The downgrade converts current VND catalog prices back to USD cents at the same fixed rate; it does not restore a historical price after later edits.
- Replacement subscriptions compare USD and VND at the same pinned rate when recording upgrade/downgrade events, instead of comparing USD cents directly with dong.

## Verification

- Frontend: **296 tests passed in 33 files**, lint/typecheck and formatting checks for changed files passed; production Docker build passed.
- Backend: **30 billing, catalog, currency and migration tests passed**; complete Ruff checks/format and mypy (**145 source files**) passed. Migration tests cover upgrade/downgrade, non-USD preservation, custom catalog edits, and unchanged legacy snapshots/audit records.
- Local images were rebuilt; frontend compatibility was installed before the database conversion and backend restart. Both services are healthy at `localhost:3000` / `localhost:8000`.
- Actual local migration reached `0015_vnd_pricing`; before/after hashes confirmed **68 subscriptions**, **122 usage periods** and **1 existing catalog audit entry** were unchanged. All six current local catalog prices converted to the amounts above. See [migration evidence](verification-artifacts/vnd-pricing/local-migration.json).
- Chrome: **20 cases passed** across 375/768/1024/1440 px, covering English/Vietnamese Pricing, Change Plan, Billing and Admin Plans. Public Pricing uses the real local API; protected views use synthetic authentication/billing fixtures and the real catalog captured from that API. Checks include exact amounts, card/document overflow, CTA alignment, VND editor values and mixed USD/VND subscription display. No real protected account, subscription or payment was modified by browser QA; no page exceptions occurred. See [browser evidence](verification-artifacts/vnd-pricing/browser.json) and [verification script](../frontend/scripts/verify-vnd-pricing-browser.mjs).

## Future production release

Deploy the currency-aware frontend **first**, while the API still returns USD. Then deploy the backend and its migration. This avoids an older frontend dividing new VND prices by 100 during the release. The user has authorized this change and testing locally; a production release of this pricing change requires a new deployment request.
