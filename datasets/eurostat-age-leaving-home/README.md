# Eurostat – Estimated average age of young people leaving the parental household

| | |
|---|---|
| Source | Eurostat (estimated from the Labour Force Survey) |
| Table | `yth_demo_030` |
| Link | https://ec.europa.eu/eurostat/databrowser/view/yth_demo_030/default/table |
| Licence | CC BY 4.0 – credit "Source: Eurostat" |
| Last updated by Eurostat | 2026-04-16 |
| Downloaded | 2026-11-04 (full table, SDMX 3.0 API, labelled CSV) |
| Coverage | 2000–2025, annual, 36 geographies (incl. `EU27_2020`, `EA21`) · 2,331 rows |

## File
- `yth_demo_030.csv` (0.2 MB) – the smallest and easiest file. Good for a first Excel/Power BI chart.

## Columns
Headers and values are `code: label`. Split on the first `: `.

| Column | Meaning |
|---|---|
| `STRUCTURE`, `STRUCTURE_ID` | SDMX metadata. Drop them. |
| `freq` | `A` annual |
| `unit` | `AVG` average (years of age) |
| `sex` | `T` total, `F` females, `M` males |
| `geo` | Country / aggregate |
| `TIME_PERIOD` | Year |
| `OBS_VALUE` | Average age in years (e.g. 26.3) |
| `OBS_FLAG` | `b` break in series, empty = normal |
| `CONF_STATUS` | Empty |

## Known quirks
- It's an **estimate** (modelled from survey data), so small year-to-year changes (±0.2) are noise.
- Women leave home earlier than men in almost every country. A nice secondary chart.
- 33 of 36 geographies reach 2025.
- Breaks (`b`) mark method changes.
