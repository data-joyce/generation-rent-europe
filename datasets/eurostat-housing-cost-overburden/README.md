# Eurostat – Housing cost overburden rate by age, sex and poverty status

| | |
|---|---|
| Source | Eurostat (EU-SILC survey) |
| Table | `ilc_lvho07a` |
| Link | https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07a/default/table |
| Licence | CC BY 4.0 – credit "Source: Eurostat" |
| Last updated by Eurostat | 2026-10-29 |
| Downloaded | 2026-11-04 (full table, SDMX 3.0 API, labelled CSV) |
| Coverage | 2003–2025, annual, 46 geographies · 127,035 rows |

## File
- `ilc_lvho07a.csv` (18 MB)

## Columns
Headers and values are `code: label`. Split on the first `: `.

| Column | Meaning |
|---|---|
| `STRUCTURE`, `STRUCTURE_ID` | SDMX metadata. Drop them. |
| `freq` | `A` annual |
| `unit` | `PC` = % of the population in that group |
| `rskpovth` | Poverty status: `TOTAL`, `B_60` below the poverty threshold (60% of median income), `A_60` above it |
| `age` | Age groups (17 values, overlapping!): `TOTAL`, `Y_LT18`, `Y18-24`, `Y25-29`, `Y18-64`, `Y_GE65`, … |
| `sex` | `T` total, `F`, `M` |
| `geo` | Country / aggregate |
| `TIME_PERIOD` | Survey year |
| `OBS_VALUE` | % of people living in households where **total housing costs exceed 40% of disposable income** |
| `OBS_FLAG` | `p` provisional, `e` estimated, `b` break, `u` **low reliability** (small sample), combinations `bu`, `pu` |
| `CONF_STATUS` | Empty |

## Known quirks
- **Age groups overlap** (`Y18-24` sits inside `Y18-64`). Never sum across age. Pick the groups you need. For a "young people" story use `Y18-24` and `Y25-29`, `sex = T`, `rskpovth = TOTAL`.
- Treat `u` (low reliability) values carefully: show them, but mark them (e.g. lighter colour).
- Breaks (`b`) happen when a country changes its survey method. Avoid drawing trend lines straight through them.
- "Housing costs" include rent/mortgage interest, utilities and maintenance, net of housing allowances.
- 176 rows have an empty value. 36 of 46 geographies reach 2025.
- Overlapping aggregates (`EU`, `EU27_2020`, `EU28`, `EU27_2007`, `EA*`): keep `EU27_2020`.
