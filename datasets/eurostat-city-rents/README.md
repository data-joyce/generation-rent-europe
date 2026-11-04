# Eurostat – Average rent per month in cities by type of dwelling

| | |
|---|---|
| Source | Eurostat |
| Table | `prc_colc_rents` |
| Link | https://ec.europa.eu/eurostat/databrowser/view/prc_colc_rents/default/table |
| Licence | CC BY 4.0 – credit "Source: Eurostat" |
| Last updated by Eurostat | 2026-01-06 |
| Downloaded | 2026-11-04 (full table, SDMX 3.0 API, labelled CSV) |
| Coverage | 2013–2025, annual, 44 cities · 5,416 rows · Lisbon (`PT_CAP`) included |

## File
- `prc_colc_rents.csv` (0.6 MB)

## Columns
Headers and values are `code: label`. Split on the first `: `.

| Column | Meaning |
|---|---|
| `STRUCTURE`, `STRUCTURE_ID` | SDMX metadata. Drop them. |
| `freq` | `A` annual |
| `building` | `FLAT1` / `FLAT2` / `FLAT3` = 1-, 2-, 3-bedroom flat · `HOUSE_ND` non-detached house · `HOUSE_D` detached house |
| `currency` | `EUR` or `NAC` (national currency). For euro countries both are identical |
| `geo` | City code: `XX_CAP` = capital city, `XX_DEL*` = other city (e.g. `DE_DEL2` München, `IT_DEL` Varese, `UK_DEL` Culham) |
| `TIME_PERIOD` | Year |
| `OBS_VALUE` | Average rent **per month** (values are rounded, e.g. 1250, 1350) |
| `OBS_FLAG`, `CONF_STATUS` | Empty |

## Known quirks – read before using
- **This is not a general "average rent" for residents.** The table sits in Eurostat's **"Correction coefficients"** group (`prc_colc_*`), which Eurostat uses to adjust **EU officials' salaries** by duty station. That explains the odd city list (Karlsruhe, Bonn, Varese, Culham are sites of EU institutions). The rents likely reflect dwellings typical for EU/international staff, which probably sits above the local average. **Say this in your dashboard** ("rents for internationally mobile staff, not the local average").
- Still useful for comparing **between capitals** on a consistent basis.
- Includes non-EU cities (Tirana, Belgrade, London, Oslo, Ankara…). Filter if you only want the EU.
- Not every city reaches 2025 (41 of 44 do).
- Pair with `earn_nt_net` (annual → divide by 12) for "rent as % of an average net salary". Remember you're comparing a capital-city rent with a **national** average wage.
