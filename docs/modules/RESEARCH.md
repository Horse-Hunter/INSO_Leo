# Research — current source/price contract

**Owner:** `src/research/`; read-only collection and aggregation, not procurement or source Sheet writes. Research/TP reuse one Chrome/session/ownership model and the same price provenance contracts.

- Search **original full source MPN** on six sources: IC.net, Findchips, 华强 HQEW, 立创 LCSC, 正能量 Bom.Ai, INSO. Last-two-character fuzzy logic applies only to **returned-model matching**, never truncate real query.
- IC.net: sample first 20 displayed manufacturer values for missing source brand; valid SSCP/ICCP same-MPN inventory <= three times order quantity = `货少`, above = `货多`; unavailable/failed verification = `待验证`, not zero.
- Retain per-site model, brand, currency, stock, date and quote provenance. Normal research uses original 1–6 month logic; TP uses its own 1–12 month lookup. Do not use older/stale quotes as current inventory.
- Prices: valid quote / no valid quote / technical failure are distinct. Convert currency only with evidenced exchange rate, preserve exact original source data and legal minimum/second minimum comparison. No fabricated market price, inventory or estimated total. INSO quotation/display preference follows original validated rules.
- Login/retry, page ownership and manual verification reuse original session/guard; don't close Owner tabs or reset shared CDP. Six-source failures should truthfully yield no confirmed current quote, not an SMTP false incident or silent success.
- Output integrates original Research Excel/detailed mail/TP consumers; no separate scraping scheduler or report-writing system. An interrupted Executor must not resume a duplicate same-order procurement or email.

**Implementation:** `src/research/service.py`, `detailed.py`, `report.py`; [historic source-specific rules and examples](https://github.com/Horse-Hunter/INSO_Leo/blob/0db292fe0cb79d5177f436c3f8cc9b87c75288ee/docs/modules/RESEARCH.md), [product](../PRODUCT_BASELINE.md), [INSO](INSO.md).
