# Eurostat – Standardised house price-to-income ratio

| | |
|---|---|
| Source | Eurostat (Macroeconomic Imbalance Procedure scoreboard indicator) |
| Table | `tipsho60` |
| Link | https://ec.europa.eu/eurostat/databrowser/view/tipsho60/default/table |
| Licence | CC BY 4.0 – credit "Source: Eurostat" |
| Last updated by Eurostat | 2026-11-03 |
| Downloaded | 2026-11-04 (full table, SDMX 3.0 API, labelled CSV) |
| Coverage | 2000–2025, annual, 27 EU countries + `EU27_2020` + `EA21` · 2,161 rows |

## File
- `tipsho60.csv` (0.3 MB)

## Columns
Headers and values are `code: label`. Split on the first `: `.

| Column | Meaning |
|---|---|
| `STRUCTURE`, `STRUCTURE_ID` | SDMX metadata. Drop them. |
| `freq` | `A` annual |
| `unit` | `PTIR_I25` ratio as index 2025 = 100 · `PTIR_LT_AVG` ratio relative to the country's **long-term average** (100 = normal, > 100 = less affordable than usual) · `RCH_A_AVG` annual % change |
| `geo` | Country |
| `TIME_PERIOD` | Year |
| `OBS_VALUE` | Value |
| `OBS_FLAG` | `p` provisional, `e` estimated, `b` break, `d` definition differs (combinations like `ep`, `dp`) |
| `CONF_STATUS` | Empty everywhere |

## Known quirks
- **Best "affordability" headline in the project**: `PTIR_LT_AVG` answers "are homes less affordable than usual *in this country*?"
- It is still **relative within each country**. A value of 120 in Portugal and 120 in Germany doesn't mean equal affordability in absolute terms.
- "Income" here is disposable income per head from national accounts, not individual salaries. Explain this in the dashboard.
- Recent years are often `p` (provisional) and may be revised.
