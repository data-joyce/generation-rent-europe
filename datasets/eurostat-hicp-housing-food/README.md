# Eurostat – HICP inflation: housing, energy and food (filtered extract)

| | |
|---|---|
| Source | Eurostat |
| Table | `prc_hicp_minr` – HICP, ECOICOP ver.2, indices and rates of change, monthly |
| Link | https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table |
| Licence | CC BY 4.0 – credit "Source: Eurostat"; note that this is a filtered extract |
| Last updated by Eurostat | 2026-11-04 |
| Downloaded | 2026-11-04 – **filtered**, not the full table (the full table has 22.5 M values) |
| Filter used | `coicop18` ∈ {TOTAL, CP01, CP011, CP041, CP0411, CP045, CP0451, CP0452, CP11, SERV_HOUS} · `unit` ∈ {I15, RCH_A} · all countries, all months |
| Coverage | 1996-01 – 2026-10, monthly, 46 geographies · 266,075 rows |

Reproduce: `https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/prc_hicp_minr/1.0?format=csvdata&formatVersion=2.0&compress=false&labels=both&c[coicop18]=TOTAL,CP01,CP011,CP041,CP0411,CP045,CP0451,CP0452,CP11,SERV_HOUS&c[unit]=I15,RCH_A`

## File
- `prc_hicp_minr.csv` (38 MB)

## Columns
Headers and values are `code: label`. Split on the first `: `.

| Column | Meaning |
|---|---|
| `STRUCTURE`, `STRUCTURE_ID` | SDMX metadata. Drop them. |
| `freq` | `M` monthly |
| `unit` | `I15` index 2015 = 100 · `RCH_A` annual rate of change (%, vs same month last year = "inflation") |
| `coicop18` | Product category: `TOTAL` all items · `CP01` food & non-alcoholic beverages · `CP011` food · `CP041` actual rentals for housing · `CP0411` rent paid by tenants for main residence · `CP045` electricity, gas & other fuels · `CP0451` electricity · `CP0452` gas · `CP11` restaurants & accommodation · `SERV_HOUS` services related to housing |
| `geo` | Country / aggregate |
| `TIME_PERIOD` | `YYYY-MM` |
| `OBS_VALUE` | Index value or % |
| `OBS_FLAG` | `e` estimated, `u` low reliability, `b` break, `d` definition differs |
| `CONF_STATUS` | Empty |

## Known quirks
- **New classification since 2026 (ECOICOP ver.2)**: codes differ from older tutorials and from the frozen tables `prc_hicp_midx` / `prc_hicp_manr` (which stop in 2025). Don't mix the two.
- **The latest month is a flash/early estimate for some countries**: in this extract 25 geographies have 2026-10 and 19 stop at 2026-09. Compare countries on the same month.
- **HICP rents (`CP041`) track rents paid by all tenants, mostly people on existing contracts**, not asking rents for new lets. So they usually rise much more slowly than the rents advertised in Lisbon or Dublin. Explain this when you put HICP rents next to house prices.
- Owner-occupied housing costs (mortgages, buying a home) are **not** in the HICP at all.
- Some sub-indices (e.g. `CP0452` gas) are missing in early years for some countries.
