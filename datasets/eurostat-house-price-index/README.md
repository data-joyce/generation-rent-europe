# Eurostat – House price index (HPI)

| | |
|---|---|
| Source | Eurostat |
| Tables | `prc_hpi_a` (annual), `prc_hpi_q` (quarterly) |
| Links | https://ec.europa.eu/eurostat/databrowser/view/prc_hpi_a/default/table · https://ec.europa.eu/eurostat/databrowser/view/prc_hpi_q/default/table |
| Licence | CC BY 4.0 – credit "Source: Eurostat" and say if you modified the data (https://ec.europa.eu/eurostat/help/copyright-notice) |
| Last updated by Eurostat | 2026-10-01 |
| Downloaded | 2026-11-04 (full tables, Eurostat SDMX 3.0 API, `format=csvdata&formatVersion=2.0&labels=both`) |
| Coverage | Annual 2005–2025 (6,114 rows) · Quarterly 2005-Q1–2026-Q2 (33,617 rows) · 38 geographies |

## Files
- `prc_hpi_a.csv` (0.9 MB), `prc_hpi_q.csv` (4.9 MB)

## Columns
Headers are `code: label`. Most cell values are also `code: label` (e.g. `PT: Portugal`). Split on the first `: ` to get a clean code and a clean label column.

| Column | Meaning |
|---|---|
| `STRUCTURE`, `STRUCTURE_ID` | SDMX metadata, the same on every row. Drop them. |
| `freq` | `A` annual / `Q` quarterly |
| `purchase` | `TOTAL` all dwellings, `DW_NEW` newly built, `DW_EXST` existing dwellings |
| `unit` | Annual: `I25_A_AVG` index 2025 = 100, `I15_A_AVG` index 2015 = 100, `RCH_A_AVG` % change vs previous year. Quarterly: `I25_Q`, `I15_Q`, `RCH_Q` (% vs previous quarter), `RCH_A` (% vs same quarter last year) |
| `geo` | Country or aggregate (`EU27_2020`, `EA21`, …) |
| `TIME_PERIOD` | `2025` or `2026-Q2` |
| `OBS_VALUE` | The number (index points or %) |
| `OBS_FLAG` | `p` provisional, `e` estimated, `b` break in series, `d` definition differs, empty = normal |
| `CONF_STATUS` | `N` = not for publication (value is empty) |

## Known quirks
- **It is an index, not a price.** You can compare *growth* between countries, not price *levels* ("Portugal is more expensive than Spain" is not possible with this table).
- **Pick one `unit` and one `purchase`** before charting, or you'll mix indices and % changes. For a "since 2015" story use `I15_*` + `TOTAL`.
- Two base years are present (2015 = 100 and 2025 = 100). Eurostat rebased in 2026.
- ~3% of rows have an empty `OBS_VALUE` (confidential or not available).
- Several aggregates overlap (`EU`, `EU27_2020`, `EU28`, `EA`, `EA19/20/21`). Use `EU27_2020` and filter the rest out before summing or ranking countries.
- Not every country reaches the latest period: 35 of 38 geographies have 2026-Q2. A few stop in 2019/2020/2024.
