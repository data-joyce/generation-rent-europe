# Eurostat – Young adults living with their parents

| | |
|---|---|
| Source | Eurostat (EU-SILC survey) |
| Table | `ilc_lvps08` – "Persons living with their parents… (population aged 18 to 34 years)" |
| Link | https://ec.europa.eu/eurostat/databrowser/view/ilc_lvps08/default/table |
| Licence | CC BY 4.0 – credit "Source: Eurostat" |
| Last updated by Eurostat | 2026-10-20 |
| Downloaded | 2026-11-04 (full table, SDMX 3.0 API, labelled CSV) |
| Coverage | 2003–2025, annual, 46 geographies · 22,086 rows |

## File
- `ilc_lvps08.csv` (2.8 MB)

## Columns
Headers and values are `code: label`. Split on the first `: `.

| Column | Meaning |
|---|---|
| `STRUCTURE`, `STRUCTURE_ID` | SDMX metadata. Drop them. |
| `freq` | `A` annual |
| `age` | Overlapping age groups: `Y18-34`, `Y18-24`, `Y25-34`, `Y25-29`, `Y20-24`, `Y20-29`, `Y16-19`, `Y16-24`, … |
| `sex` | `T`, `F`, `M` |
| `unit` | `PC` = % of people in that age group |
| `geo` | Country / aggregate |
| `TIME_PERIOD` | Year |
| `OBS_VALUE` | % of the age group living with their parents |
| `OBS_FLAG` | `p` provisional, `e` estimated, `b` break |
| `CONF_STATUS` | Empty |

## Known quirks
- **Age groups overlap**: don't sum them. Headline choice: `Y18-34` or `Y25-34`, `sex = T`.
- Very high values (> 95%) appear for the youngest groups (`Y16-19`) in some countries. That's expected, not an error. Don't let them dominate a chart.
- Example check: Portugal `Y18-34`, total = **61.0% in 2025** (62.4% in 2024).
- 34 of 46 geographies reach 2025.
- Overlapping aggregates (`EU`, `EU27_2020`, `EU28`, `EU27_2007`, `EA*`): keep `EU27_2020`.
