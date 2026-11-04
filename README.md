# Generation Rent: can young Europeans still afford a home?

An end-to-end analysis of housing affordability for young people in the 27 EU countries, 2005–2025, built on **official open data from Eurostat**.

**Questions:** Have house prices outpaced take-home pay? How much of a salary does a one-bedroom flat in a capital cost? At what age do young people leave home, and is that linked to housing costs? How does Portugal compare with the EU average?

**Tools:** Python (pandas) · SQL (DuckDB) · Power BI *(dashboard in progress)*

---

## Key findings (2025 unless stated)

- **Portugal has the most overvalued housing in the EU relative to incomes.** Its house-price-to-income ratio is **137** against its own long-run average (= 100), ranking first of 27.
- **House prices outran earnings in most countries.** From 2015 to 2023, house prices rose **+106% in Portugal** while net earnings rose **+33%**. Hungary: +173% vs +90%.
- **Lisbon has the highest rent-to-salary ratio of the 26 EU capitals in the data.** A one-bedroom flat costs **~78% of the national average net salary**, compared with 75% in Zagreb and 72% in Prague.
- **Young people leave home latest in the south and east.** The average age is 31.5 in Croatia and 30.9 in Greece and Slovakia, compared with 21.3 in Finland (EU average 26.3, Portugal 28.8).
- Across countries, the age of leaving home is only weakly linked to any single factor: purchasing power r = −0.33, housing-cost overburden of 18–24s r = −0.38, price-to-income r = 0.03.

**Caveats, shown with every figure:**
- City rents are Eurostat's rents for **EU officials' duty stations**, not local market averages.
- Net earnings have an **EU-wide method break in 2024**, so changes across 2023→2024 are not real growth.
- Greece has no house-price data. The Netherlands has no capital city in the rent data.

## Pipeline

```
Eurostat (8 datasets, SDMX-CSV)
   │  datasets/<name>/README.md: source, licence, download date, columns, quirks
   ▼
pipeline/python/generation_rent_01_clean.ipynb          pandas: filter, reshape, join, flag, 11 built-in checks
   ▼
pipeline/clean/generation-rent/*.csv                     analysis-ready star schema
   ├─ country_year   (fact)  27 countries + EU average × 2005–2025, 9 indicators + quality flags
   ├─ city_rent      (fact)  44 cities × 2013–2025: rent, national net salary, rent share
   ├─ hicp_monthly   (fact)  consumer prices by month 1996–2026 (rent, energy, food, all items)
   ├─ dim_country    (dim)   EU27 / aggregate flags, ISO codes
   └─ dim_year       (dim)   1996–2026, marks the 2024 earnings break
   ▼
pipeline/sql/generation_rent/*.sql                       DuckDB: exploration, growth, rankings, correlations, data quality
   ▼
Power BI dashboard                                       (in progress)
```

## Data quality assurance

The pipeline was audited independently before the dashboard was built ([`qa/QA_REPORT.md`](qa/QA_REPORT.md)):
- Every final table was **rebuilt from the raw files with a different tool** (DuckDB SQL instead of pandas) and compared cell by cell.
- Every SQL query was re-implemented in pandas.
- 10 random records were traced from raw file to final table.
- A fresh rerun produces **byte-identical outputs**.
- The fixes found by the audit were checked with a before/after regression test.

To rerun all checks, open `qa/qa_checks.ipynb` and choose *Restart & Run All*.

## Repository structure

| Path | Contents |
|---|---|
| `datasets/` | One folder per Eurostat dataset, each with a README (source link, licence, download date, columns, quirks). Raw CSVs are not stored in the repo, see below |
| `pipeline/python/` | Cleaning notebook and the SQL runner `run_sql.py` |
| `pipeline/clean/generation-rent/` | Final tables used by SQL and Power BI, plus a data dictionary README |
| `pipeline/sql/generation_rent/` | 7 query files and a README with results |
| `qa/` | Audit scripts, results and report |
| `requirements.txt` | Pinned Python package versions |

## How to reproduce

```bash
pip install -r requirements.txt
```

1. **Get the raw data.** Each `datasets/<name>/README.md` gives the Eurostat link and the expected file name. Save each CSV into its folder. The analysis uses the versions downloaded on **2026-11-04**. Eurostat revises its data, so a new download can differ slightly.
2. **Clean:** run `pipeline/python/generation_rent_01_clean.ipynb` top to bottom.
3. **Query:** `python pipeline/python/run_sql.py "pipeline/sql/generation_rent/*.sql"` builds a DuckDB database and prints every result.

## Data source and licence

- **Data:** © European Union, Eurostat, reused under [CC BY 4.0](https://ec.europa.eu/eurostat/help/copyright-notice). Source: Eurostat. The datasets used are:
  - `prc_hpi_a`, `tipsho60`, `earn_nt_net`, `prc_colc_rents`, `ilc_lvho07a`, `yth_demo_030`, `ilc_lvps08`, `prc_hicp_minr`
  - The derived tables in `pipeline/clean/` are modified versions: filtered, reshaped and joined.
- **Code:** MIT licence (see `LICENSE`).
