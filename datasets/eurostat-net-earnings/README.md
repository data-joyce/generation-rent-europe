# Eurostat – Annual net earnings

| | |
|---|---|
| Source | Eurostat (based on the OECD/EC tax-benefit model) |
| Table | `earn_nt_net` |
| Link | https://ec.europa.eu/eurostat/databrowser/view/earn_nt_net/default/table |
| Licence | CC BY 4.0 – credit "Source: Eurostat" |
| Last updated by Eurostat | 2026-10-19 |
| Downloaded | 2026-11-04 (full table, SDMX 3.0 API, labelled CSV) |
| Coverage | 2000–2025, annual, 40 geographies · 199,986 rows |

## File
- `earn_nt_net.csv` (40 MB – the biggest file in the project, but still opens in Excel: < 1,048,576 rows)

## Columns
Headers and values are `code: label`. Split on the first `: `.

| Column | Meaning |
|---|---|
| `STRUCTURE`, `STRUCTURE_ID` | SDMX metadata. Drop them. |
| `freq` | `A` annual |
| `currency` | `EUR` euro · `NAC` national currency · `PPS` purchasing power standard (adjusts for price levels: best for "how far a salary goes") |
| `estruct` | `NET` net earnings · `GRS` gross · `TAX` income tax · `SOC` social security contributions · `FAM` family allowances · `TOTAL` |
| `ecase` | Household type. `P1_NCH_AW100` = **single person, no children, earning 100% of the average wage** (use this as the default). `P1_NCH_AW50/67/80/125/167` = single at 50–167% of average. `CPL_*` = couples, `CH2` = two children |
| `geo` | Country / aggregate |
| `TIME_PERIOD` | Year |
| `OBS_VALUE` | Amount per **year** |
| `OBS_FLAG` | `b` break in series, empty = normal |
| `CONF_STATUS` | Empty |

## Known quirks
- **These are modelled earnings for a "typical" worker**, not survey data on what real people earn. They're right for "what does an average-wage single person take home?", not for salary distributions.
- **Break in series in 2024 for every EU country**: all 27 EU countries carry flag `b` in 2024 (single, average-wage, net, EUR). Example: Portugal jumps from €15,301 (2023) to €20,099 (2024). That's a methodology change, not a real 31% pay rise. **Never present 2023→2024 growth as real.** Compare 2015→2023 and 2024→2025 separately.
- Values of `0` are real for some `estruct` (e.g. no family allowances for a single person).
- Not all countries reach 2025: 30 do, 6 stop in 2023, a few earlier.
- Rows multiply fast (currency × estruct × ecase). **Always filter all three** before aggregating, or you'll double-count.
- Annual amounts. Divide by 12 for monthly comparisons with rents (14 salary payments in PT doesn't matter here: this is an annual total).
