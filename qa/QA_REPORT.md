# Generation Rent · Independent QA audit

**Date:** 2026-11-04 · **Scope:** the Generation Rent pipeline in `pipeline/` (raw `datasets/eurostat-*` → pandas notebook → CSVs → DuckDB SQL), checked before the Power BI dashboard is built. `datasets/practice-sales/` is out of scope.
**Method:** every check is code in `qa/` that was actually run. Its output is saved in `qa/results/`. Key numbers were recomputed **with a different tool** from the one the pipeline used:

- the raw-data profile, record traces and Power BI checks use only the Python standard library
- the final tables were rebuilt from the raw files in **DuckDB SQL**, sharing no code with the notebook
- every SQL query was re-implemented in **pandas**

No original file was modified. The notebook and SQL ran on copies in `qa/sandbox/`, the original `.duckdb` was only opened read-only, and the file timestamps confirm nothing changed (P7-06).

**Rerun everything:** open `qa/qa_checks.ipynb` → *Restart & Run All* (≈5–8 min), or run the scripts one by one (`python -I qa/<script>.py` from the project root, in the order listed at the end).

> **Update, same day (2026-11-04): the fixes were approved and applied, then the whole audit was rerun.** Sections 1–8 below are the audit **as it was before the fixes** (kept unchanged as the record). What changed, the new status of every affected check, and the before/after regression proof are in **[§9 Fixes applied and re-audit](#9-fixes-applied-and-re-audit-2026-11-04)**. Current verdict: **READY.** What is left are Power BI settings that can only be applied while building the report (§9.4).

---

## 1. Executive summary

### Verdict: **READY WITH MINOR FIXES**

**The numbers are correct.** Every value that will feed Power BI was rebuilt from the raw Eurostat files by an independent method and matches:

- `country_year`: 588 rows × 9 measures and 9 flags, identical cell for cell. The HICP-based columns agree to about 1e-13, the last digits of floating-point precision.
- `city_rent`: 552 rows. Rent, salary, flag, label and share all match.
- `dim_country`: matches.
- Totals reconcile exactly, all 10 traced records match at every step, and all 27 SQL result queries match their pandas re-implementation.
- The pipeline is deterministic: a fresh rerun gives byte-identical outputs.

**What needs fixing is how the data will be modelled and presented**, plus some pipeline housekeeping. None of it is a calculation error.

### Top issues

| # | Issue | Severity |
|---|---|---|
| 1 | **Power BI may misread the decimals.** The PC locale is **pt-PT (decimal comma)** and the CSVs use dot decimals. If Power BI imports them with the pt-PT locale, `103.34` can turn into `10334`. I could not test this, because Power BI wasn't run. | High |
| 2 | **Non-additive measures.** Every `country_year` measure is an index, a rate, an average or an age. Power BI's default *Sum* would produce nonsense totals (e.g. adding 28 countries' house-price indices). | High |
| 3 | **The rent-share KPI is distorted by the 2024 earnings break.** Lisbon fell from 105.9% (2023) to 78.3% (2025) mainly because Eurostat changed its earnings method; a rough no-break estimate is ~102%. 13 city-years are above 100%, because duty-station rent is compared with a *national* salary. The headline "Lisbon is the least affordable EU capital" still holds *within* 2025. Showing shares as a trend across 2023→2024 would mislead. | High |
| 4 | **No year/date table.** `hicp_monthly` also mixes two units (index and % rate) in one `value` column, and its last month (2026-10) is partial: 21 rows. | Medium |
| 5 | **The notebook can't be rerun where it lives** (`FileNotFoundError`, because it looks for `datasets/` inside `pipeline/`), and there is **no requirements file**. | Medium |
| 6 | **Coverage gaps the dashboard must disclose.** Greece has no house-price data in any year. Cyprus has no earnings for 2008–13 and 2015–16. France has no overburden value for 2021. The Netherlands has no capital city in the rent data (only Den Haag), so "EU capitals" means 26, not 27. | Medium |

---

## 2. Results table

Status values: **PASS**, **FAIL**, **WARNING** (correct as computed but risky or misleading) and **COULD NOT VERIFY**.

| Check ID | Phase | What was checked | Status | Evidence (real output) | Severity | Proposed fix |
|---|---|---|---|---|---|---|
| P1-01 | 1 | Inventory and pipeline map | PASS | 9 raw CSVs, 1 notebook (14 code cells), 1 runner script, 7 SQL files, 13 CSV outputs, 1 `.duckdb`. Map reviewed and confirmed before the audit continued. | – | – |
| P2-01 | 2 | Row and column counts, ragged rows | PASS | hpi_a 6,114×10 · hpi_q 33,617×10 · ptir 2,161×9 · net_earn 199,986×11 · city_rents 5,416×10 · overburden 127,035×12 · age_leave 2,331×10 · with_parents 22,086×11 · hicp 266,075×10. 0 ragged rows. | – | – |
| P2-02 | 2 | Types: numbers or dates stored as text, IDs and leading zeros | PASS | All 9 files: 0 non-numeric non-blank `OBS_VALUE`, 0 leading-zero values, at most 2 decimals. `TIME_PERIOD` is 100% valid (annual `YYYY`, `YYYY-Qn` or `YYYY-MM`). There are no numeric IDs (codes are text, e.g. `PT`). The pipeline reads everything as text (`dtype=str`), so no codes are mis-typed. | – | – |
| P2-03 | 2 | Nulls, blanks and placeholders (`N/A`, `-`, `:`, 9999, padding) | PASS | 0 placeholder values and 0 padded values in all files. Blanks appear only in `OBS_VALUE`: hpi_a 156 and hpi_q 864 (all flagged `N: not for publication`), overburden 176 (all flagged `u`). Zeros (e.g. 720 in overburden, 27 in with_parents) are valid 0.0% values in small subgroups. | – | – |
| P2-04 | 2 | Exact duplicate rows and duplicate keys | PASS | 0 exact duplicates and 0 duplicate keys (all dimensions + period) in all 9 files. | – | – |
| P2-05 | 2 | Distributions, outliers, impossible values | PASS | PC values always between 0 and 100. Ages 17.5–36.2. Indices > 0. Negatives appear only where they are legitimate: rate-of-change units, and TAX/FAM earnings components (tax credits). In the slice used, NET earnings of a single person at average wage: 0 values ≤ 0. 3×IQR outliers are real (e.g. Türkiye HPI up to 1,842). | – | – |
| P2-06 | 2 | Türkiye earnings in EUR | WARNING | TR EUR net earnings for 2000–2003 = 6,874,930,772 … 5,235,964,722, then 5,463 in 2004. This is old-lira data before the redenomination. It isn't in any Power BI table, only in `long_net_earn`. | Low | Note it in the `long_net_earn` README, or filter TR before 2004 if that table is ever used. |
| P2-07 | 2 | Categorical consistency (spelling, case, spaces, code↔label) | PASS | 0 codes with more than one label, 0 labels with more than one code, 0 case collisions, 0 padded values. Lisboa appears only as `PT_CAP: Lisboa`. | – | – |
| P2-08 | 2 | Dates: format, parsing, range, future periods, gaps | WARNING | No day/month ambiguity (no daily dates), no time zones, 0 future periods. Ranges: hpi_a 2005–2025, hicp 1996-01 to 2026-10. Missing years inside series in the slices used: **CY earnings 2008–13 and 2015–16**, **FR overburden 2021**. HICP months are missing only for NO and EEA (not used). | Medium | Disclose the gaps in the dashboard notes. Don't interpolate (consistent with the project rule). |
| P2-09 | 2 | Encoding and locale | PASS | All files are valid UTF-8, no BOM, 0 mojibake. Accented characters are correct (`ü–èëø`, e.g. Türkiye, Genève). Dot decimals, 0 comma decimals, 0 thousands separators, 0 currency symbols. | – | – |
| P2-10 | 2 | Coverage of each slice used (EU27) | WARNING | HPI: **EL missing in every year**, 38 not-for-publication blanks (2005–09: AT, CZ, IT, PL, PT, RO…), and only 13 of 27 countries in 2005. City rents: **NL has no `_CAP` city** (only `NL_DEL` Den Haag). HICP 2026-10: only 25 geos (flash estimate). Every other slice covers all 27 + the EU average. | Medium | Add a coverage note. Start HPI charts in 2010, or show "n countries" next to each year. |
| P3-01 | 3 | Fresh kernel, top to bottom | PASS | `nbconvert --execute` on an unmodified copy: exit 0, 14/14 cells, 0 errors, 0 Python warnings (only Jupyter's own transport messages on stderr). | – | – |
| P3-02 | 3 | Outputs changed vs the saved notebook | PASS | 0 of 14 code cells have different text output. *Limitation:* the one chart is compared by presence only, not pixel by pixel. | – | – |
| P3-03 | 3 | Hidden state (out-of-order execution, names used before definition) | PASS | Saved execution counts are `[1..14]` in order. A static scan found 0 names used before definition. The fresh-kernel run reproduces every output. | – | – |
| P3-04 | 3 | Hard-coded paths | FAIL | 0 absolute paths, but `ROOT = cwd.parent if cwd is 'python'`. From `pipeline/python/` this gives `ROOT=pipeline/` → **`FileNotFoundError: ...\datasets\eurostat-age-leaving-home\yth_demo_030.csv`** (reproduced in `qa/sandbox_inplace/`). | Medium | Point `ROOT` at the project root explicitly (e.g. walk up the folders until `datasets/` is found), or move the files back to `python/`. |
| P3-05 | 3 | Row count before and after every step | PASS | 53 steps, each change explained (see §3). No row is lost by accident. | – | – |
| P3-06 | 3 | Merges: key uniqueness, row explosion, unmatched rows | PASS | 9 outer merges each passed `validate="one_to_one"`; result = left + right − both every time. The `dim_country` merge passed `many_to_one` with 0 unmatched. The city_rent → earnings merge passed `many_to_one` with **90 unmatched city-years kept on purpose** (share = NaN): AL 13, BA 12, ME 13, MK 13, RS 13, UK 8, XK 5, CH 4, CY 3, IS 2, NO 2, TR 2. | – | – |
| P3-07 | 3 | `pick()` filters give exactly one series | PASS | 0 duplicate geo-years after every pick, and no dimension still varies after filtering (so no hidden double counting). | – | – |
| P3-08 | 3 | pandas pitfalls | PASS | pandas 3.1.0 (Copy-on-Write always on, so no SettingWithCopy risk). 0 NaN keys in groupby. 0 NaN months inside HICP mean groups (`count == size`). 0 text→NaN coercions in any file. `year` is int64. Values stay float64, so there is no overflow risk. | – | – |
| P3-09 | 3 | Filter logic (boundaries, AND/OR) | PASS | Year filter `between("2005","2025")` on strings is identical to an integer filter (checked on all 832 rows). It includes both ends. The 12-month HICP rule drops only partial years (2026: 88 groups; first years of some series). The geo filter is `is_eu27 OR geo == EU27_2020`, as intended. | – | – |
| P3-10 | 3 | Calculated columns, line by line | PASS | `real_house_price_index_2015 = HPI / HICP_all × 100`: max diff vs formula 0.0. `net_salary_eur_month = annual / 12` and the rent share were recomputed independently (P5-05). 2015 sanity: HPI 100.0–100.0, HICP 99.99–100.0, real HPI 100.0–100.01. | – | – |
| P3-11 | 3 | `dim_country` flags | WARNING | `is_eu27` exactly matches the official 27. `is_aggregate` uses the regex `^(EU\|EA)`, which **misses `EEA`**. No effect on current tables (EEA is filtered out everywhere), but it's fragile. `iso2` for aggregates is not ISO (e.g. `EU27_2020`, `EA19`). | Low | Add EEA explicitly. Set `iso2` to blank for aggregates. |
| P4-01 | 4 | Every SQL file executes | PASS | Project runner on the sandbox: exit 0. All 7 files and all statements ran with 0 errors (`qa/results/p4_run_sql_output.txt`). | – | – |
| P4-02 | 4 | SQL results recomputed in pandas | PASS | **27/27** result queries match: 23 identical including row order, 4 identical as a set (01.Q5, 04.Q1, 04.Q4, 05.Q4 differ only in order among tied values). The `DESCRIBE` and setup metadata queries were not compared. | – | – |
| P4-03 | 4 | JOIN types, lost or duplicated rows | PASS | 03.Q1/Q3 INNER JOIN to `dim_country`: 0 orphan keys, so nothing is lost. 05.Q1 INNER self-join: the EU row exists for every PT year (0 dropped). 05.Q3 joins to one month per geo, so no duplication. | – | – |
| P4-04 | 4 | NULL handling (COUNT, AVG, corr, WHERE) | PASS | `COUNT(column)` is used deliberately for coverage. In 2025, `COUNT(*)` = 27 = the non-NULL pairs used by `corr()` and by every `AVG()`, so the "countries" columns are correct *for 2025*. No `= NULL` comparisons; `IS NOT NULL` is used. | Low | If 04.Q2/Q3 are rerun for other years, use `COUNT(x)` or `regr_count(x, y)` instead of `COUNT(*)`. |
| P4-05 | 4 | WHERE/HAVING, GROUP BY, integer division, windows | PASS | HAVING on aliases is valid in DuckDB. GROUP BY is complete. `/` on BIGINT returns DOUBLE (03.Q2 matches pandas float division). LAG is partitioned by geo and ordered by year, with no year gaps (2015–2025 complete for PT and the EU). RANK has no ties in 02.Q1. No LIMIT cut-off falls inside a tie (01.Q5: 27.4 vs 27.3; 06.Q4: 19 vs 15). | – | – |
| P4-06 | 4 | `LIKE '%_CAP'` | WARNING | In LIKE, `_` is a wildcard. On this data it matches exactly the literal `_CAP` codes (0 extra matches), but it's fragile. | Low | Use `right(city_geo, 4) = '_CAP'` or `LIKE '%\_CAP' ESCAPE '\'`. |
| P4-07 | 4 | EU average inside country rankings | WARNING | 02.Q1 ranks "EU average (27)" 15th among countries. 02.Q2 and 02.Q3 also list it. | Low | Exclude `EU27_2020` from rankings and show it as a reference line. |
| P4-08 | 4 | Stale paths in comments and docs | WARNING | `run_sql.py` docstring and `00_setup.sql` say `python python/run_sql.py sql/...` from the root, which doesn't exist. The runner switches into its own root before expanding the glob, so a root-relative glob silently runs 0 files (reproduced: exit 0, empty output). | Low | Update the docstrings. Make the runner fail when the glob matches nothing. |
| P4-09 | 4 | Original `.duckdb` equals the CSVs | PASS | Opened read-only. 7 tables (country_year 588×25, city_rent 552×8, dim_country 52×5, hicp_monthly 196,331×10, long_overburden 127,035×14, long_net_earn 199,986×12, long_with_parents 22,086×12): every key matched and 0 differing cells. | – | – |
| P5-01 | 5 | KPI definitions | PASS | Written out in §5. | – | – |
| P5-02 | 5 | country_year rebuilt from raw (DuckDB SQL) | PASS | Same 588 keys (28 geos × 21 years). All 9 measures and 9 flag columns are **exact in 588/588 rows**. `hicp_rent_index`, `hicp_all_index` and `real_house_price_index_2015`: 0 NULL mismatches and max abs diff **≤ 5.7e-14** (floating-point summation order of the 12-month mean). Equal to about 13 significant digits, but not bit-identical. | – | – |
| P5-03 | 5 | Labels and ISO codes | PASS | 0 country-label mismatches vs the raw labels, 0 `iso2` mismatches (EL→GR as intended). | – | – |
| P5-04 | 5 | Reconciliation: raw totals = final totals | PASS | For each measure, the count and exact sum (`math.fsum`) of the raw slice (EU27 + EU average, 2005–2025, non-blank) equal the final column. E.g. HPI 529 values, sum 64,434.83 = 64,434.83. Net EUR 558, 11,260,996.09 = 11,260,996.09. HICP: 7,056 monthly rows = 12 × 588 annual rows. The only filtering is documented (blanks marked not-for-publication: 38 HPI). The "sum of categories = grand total" check doesn't apply: the measures are rates and indices, and Eurostat's EU average is weighted. Instead, the EU27 value lies within the member min/max in every year for all 11 measures. | – | – |
| P5-05 | 5 | city_rent rebuilt from raw | PASS | 552/552 rows. Rent, monthly salary (exact float), flag and city label all match. Share: 462/462 non-NULL rows match with *both* round-half-even (pandas) and round-half-up (Excel, DAX, SQL), so 0 rows are rounding-sensitive. 90/90 NULL shares match. | – | – |
| P5-06 | 5 | dim_country rebuilt | PASS | 52 unique geos. `is_eu27` = the official list. 0 city or country geos missing from the dimension. | – | – |
| P5-07 | 5 | 10 random records traced end to end | PASS | 10/10 MATCH at every step (§4, seed 20261104). | – | – |
| P5-08 | 5 | Headline claims in the notes | PASS | PT price-to-income 2025 = 136.97, rank 1 of 27. Lisbon rent share 2025 = 78.3%, rank 1 of 26 capitals. Latest leavers 2025: HR 31.5, EL 30.9, SK 30.9, ES 30.2, IT 30.2. PT real HPI 2025 = 211.4 (highest). PT net earnings €15,301 (2023) → €20,099 (2024). All reproduced. | – | – |
| P5-09 | 5 | Rent share and the 2024 earnings break | WARNING | Lisbon: 105.9% (2023) → 78.3% (2025), while rent rose 1,300→1,400 (raw). Earnings jump +31.4% in 2024, flagged `b` in **27/27** countries (BG +29%, SK +30.5%, SI +29.9%, LV +28.8%). Rough estimate if 2025 earnings had grown at the 2015–23 rate: €16,421 instead of €21,449 → Lisbon share ~102%. Rankings *within* 2025 are fine (every country uses the new method). Shares *across* 2023/2024 are not comparable. | High | Show the rent share for one year at a time (2025 ranking) and never as a 2013–2025 trend line. Or draw two separate series (2013–2023 and 2024–2025) with a "method break" marker. Put the caveat on the visual. |
| P5-10 | 5 | Rent share above 100% | WARNING | 13 city-years > 100%: LV_CAP 2013 139.2%, LV_CAP 2014 132.2%, RO_CAP 2013 127.2%, RO_CAP 2014 117.1%, PT_CAP 2023 105.9%, PT_CAP 2020 102.1%, PT_CAP 2018 101.6%, BG_CAP 2016 102.4%, HU_CAP 2019 102.2% … It's arithmetically correct, but it shows the metric is "EU-officials' duty-station rent vs *national* average salary", not local affordability. | Medium | Rename it in the dashboard (e.g. "EU duty-station 1-bed rent as % of national net salary") and keep the caveat beside it. |
| P5-11 | 5 | Volatile small-base series and low reliability | WARNING | Overburden for young people jumps on tiny bases, e.g. MT 18–24: 0.2%→1.2% (2007→08) and 1.7%→6.7% (2022→23); SK 25–29: 2.2%→8.3% (2020→21). Each overburden slice has 5 `u` (low reliability) and 1 `bu` values. | Low | Show the flags (e.g. hollow markers) and avoid "% change" wording for overburden. Use percentage points. |
| P5-12 | 5 | Plausibility of magnitudes | PASS | 2025 ranges: HPI 99.0 (FI) to 366.6 (HU). Net EUR €13,877 (RO) to €55,877 (LU). Age leaving home 21.3 (FI) to 31.5 (HR). With parents 16.6% (FI) to 75.3% (HR). Price-to-income mean per country = 100.0 (as defined). London's 2015 = 2025 rent (€2,350) follows the GBP/EUR rate (€1,750 in 2017–18). Nothing implausible. | – | – |
| P6-01 | 6 | Primary keys unique and not null | PASS | country_year (geo, year) 588 · city_rent (city_geo, year) 552 · dim_country (geo) 52 · hicp_monthly (geo, unit, coicop18, time) 196,331. 0 duplicates and 0 nulls in each. | – | – |
| P6-02 | 6 | Foreign keys (orphans) | PASS | country_year.geo, city_rent.country_geo and hicp_monthly.geo → dim_country.geo: 0 orphans (588, 552 and 196,331 rows). | – | – |
| P6-03 | 6 | Star schema | WARNING | It works as two facts (country_year, city_rent) plus one dimension (dim_country). But there's no year/date dimension. `country`/`iso2` are copied into the fact table (consistent with the dimension: True). `dim_country` has 24 geos with no country_year data (AL, CH, NO, TR, UK, aggregates…), which would appear in slicers. | Medium | Add `dim_year`. Hide `country`/`iso2` in the fact table and use the dimension. Filter slicers to `is_eu27` or the EU average. |
| P6-04 | 6 | One consistent type per column, real dates and numbers | PASS | Every column has one type (integer, decimal, boolean or text). 0 mixed columns, 0 padded values. `year` is an integer. `hicp_monthly.time` is `YYYY-MM` text (see P6-05). | – | – |
| P6-05 | 6 | Calendar/date table | WARNING | None exists. Years needed: 2005–2025 (country_year), 2013–2025 (city_rent), 1996-01 to 2026-10 (hicp_monthly). | Medium | Create `dim_year` (1996–2026). For hicp, add a real date (`time` + "-01" → Date) and a `dim_date` (month grain) linked to `dim_year`. |
| P6-06 | 6 | Export format | PASS | All 4 tables: UTF-8 **with BOM**, CRLF, comma delimiter, 0 semicolons, **dot decimals** (0 comma decimals), 0 index columns, every column name matches `^[a-z][a-z0-9_]*$`. | – | – |
| P6-07 | 6 | Power BI import locale | COULD NOT VERIFY | Windows culture **pt-PT**, decimal separator `,`, group separator space. Power BI wasn't run in this audit, so the actual parsing is untested. | High | In Power BI Desktop, set *File → Options → Regional settings → Import locale = English (United States)*, or use *Change type → Using locale → English (US)*. Then check one value, e.g. FI 2018 HPI = **103.34**. |
| P6-08 | 6 | Precalculated metrics that should be DAX measures | WARNING | `rent_share_of_net_salary_pct` is rounded to 1 dp in the CSV and can't be re-aggregated. `real_house_price_index_2015`, `net_salary_eur_month`, and all growth % and gap values in the SQL files are ratios. | Medium | Keep the base columns. Write DAX measures (examples in §5) and set *Don't summarize* on all value columns. |
| P6-09 | 6 | Non-additive columns vs default summarization | WARNING | Every `country_year` measure is an index, rate, average or age. Power BI defaults numbers to **Sum**. | High | Set *Summarize by = None* for every measure column. Show values with explicit measures (`SELECTEDVALUE` or `AVERAGE` within one country-year). |
| P6-10 | 6 | `hicp_monthly` structure | WARNING | Two units in one `value` column: I15 index 99,835 rows and RCH_A % 96,496 rows. The latest month (2026-10) has only 21 rows (flash). | Medium | Split it into two tables or columns (`index_2015`, `annual_rate_pct`), or always filter `unit` in the measure. Use the "latest complete month" logic from 05.Q3. |
| P7-01 | 7 | Rerun from raw gives identical outputs | PASS | 13/13 CSVs **SHA-256 identical** to the originals, on two separate reruns (nbconvert fresh kernel, then again via `qa_checks.ipynb`). The SQL rebuild gives a DB equal to the original (P4-09). | – | – |
| P7-02 | 7 | Runs from where it lives | FAIL | See P3-04: `FileNotFoundError` when run from `pipeline/python/` (`qa/results/p0_setup.json`). | Medium | Fix the `ROOT` path logic (P3-04). |
| P7-03 | 7 | Library versions documented | FAIL | No `requirements.txt`, `environment.yml` or `pyproject.toml` in the project. The audit environment was Python 3.13.17, pandas 3.1.0, numpy 2.5.4, duckdb 2.0.0, matplotlib 3.11.2, nbconvert 7.17.2, ipykernel 7.4.0. | Medium | Add a `requirements.txt` that pins these versions. |
| P7-04 | 7 | Random seeds | PASS | No randomness or clock-dependent code in the pipeline (searched the .py, .sql and notebook code). The QA trace sample uses a fixed seed (20261104). | – | – |
| P7-05 | 7 | Frozen inputs | WARNING | Raw files are stored locally (downloaded 2026-11-04, per each README). Eurostat revises data, so a re-download would *not* reproduce these numbers. | Low | Keep the raw files (already the rule) and quote the download date in the dashboard footer. |
| P7-06 | 7 | Originals untouched by the audit | PASS | 0 files in `datasets/`, `pipeline/`, `cloud/` or `notes/` modified after the audit started. `generation_rent.duckdb` still 6,565,888 bytes, modified at 19:57:32. | – | – |

---

## 3. Row-count lineage (Phase 3)

These counts come from re-playing each step of the notebook's own code in `qa/sandbox/` (`p3_lineage_and_pitfalls.py`).

| Step | Rows before | Rows after | Change | Explanation |
|---|---:|---:|---:|---|
| read+clean hpi_a → long_hpi_a | 6,114 | 6,114 | 0 | `clean_eurostat()` only renames and splits columns, with no row filter (same for all 9 files) |
| read+clean hpi_q → long_hpi_q | 33,617 | 33,617 | 0 | " |
| read+clean ptir → long_ptir | 2,161 | 2,161 | 0 | " |
| read+clean net_earn → long_net_earn | 199,986 | 199,986 | 0 | " |
| read+clean city_rents → long_city_rents | 5,416 | 5,416 | 0 | " |
| read+clean overburden → long_overburden | 127,035 | 127,035 | 0 | " |
| read+clean age_leave → long_age_leave | 2,331 | 2,331 | 0 | " |
| read+clean with_parents → long_with_parents | 22,086 | 22,086 | 0 | " |
| read+clean hicp → long_hicp | 266,075 | 266,075 | 0 | " |
| HPI: purchase = TOTAL | 6,114 | 2,257 | −3,857 | keep 1 of 3 purchase types |
| HPI: unit = I15_A_AVG | 2,257 | 759 | −1,498 | keep 1 of 3 units (2015 = 100) |
| net EUR: estruct = NET | 199,986 | 33,331 | −166,655 | keep 1 of 6 earnings components |
| net EUR: ecase = P1_NCH_AW100 | 33,331 | 2,603 | −30,728 | keep 1 of 13 household types |
| net EUR: currency = EUR | 2,603 | 892 | −1,711 | keep 1 of 3 currencies |
| net PPS: same 3 filters, currency = PPS | 199,986 | 892 | −199,094 | same as above with PPS |
| PTIR: unit = PTIR_LT_AVG | 2,161 | 730 | −1,431 | keep 1 of 3 units |
| overburden_total: sex = T | 127,035 | 42,345 | −84,690 | keep 1 of 3 sexes |
| overburden_total: rskpovth = TOTAL | 42,345 | 14,115 | −28,230 | keep 1 of 3 poverty groups |
| overburden_total: age = TOTAL | 14,115 | 833 | −13,282 | keep 1 of 17 age classes |
| overburden_18_24 (same, age = Y18-24) | 127,035 | 833 | −126,202 | " |
| overburden_25_29 (same, age = Y25-29) | 127,035 | 833 | −126,202 | " |
| age_leaving_home: sex = T | 2,331 | 777 | −1,554 | keep 1 of 3 sexes |
| with_parents: sex = T | 22,086 | 7,362 | −14,724 | keep 1 of 3 sexes |
| with_parents: age = Y18-34 | 7,362 | 826 | −6,536 | keep 1 of 9 age classes |
| HICP: unit = I15 and coicop in (CP041, TOTAL) | 266,075 | 28,260 | −237,815 | index unit; rents + all items only |
| HICP: group by geo-year-coicop (mean) | 28,260 | 2,411 | −25,849 | monthly → 1 row per geo-year-category |
| HICP: keep years with 12 months | 2,411 | 2,285 | −126 | drops partial years (2026: 88; first years of series) |
| HICP: pivot categories to columns | 2,285 | 1,191 | −1,094 | 2 categories → 2 columns |
| outer merge + net_earnings_eur | 759 | 1,007 | +248 | one_to_one; 644 both, 115 left only, 248 right only |
| outer merge + net_earnings_pps | 1,007 | 1,007 | 0 | one_to_one; same keys as EUR |
| outer merge + price_to_income | 1,007 | 1,030 | +23 | one_to_one; 23 new geo-years |
| outer merge + overburden_total | 1,030 | 1,112 | +82 | one_to_one; 82 new geo-years |
| outer merge + overburden_18_24, + overburden_25_29 | 1,112 | 1,112 | 0 | one_to_one; same keys |
| outer merge + age_leaving_home | 1,112 | 1,131 | +19 | one_to_one; 19 new geo-years |
| outer merge + pct_18_34_with_parents | 1,131 | 1,131 | 0 | one_to_one; same keys |
| outer merge + hicp_wide | 1,131 | 1,313 | +182 | one_to_one; 182 new geo-years |
| left merge + dim_country | 1,313 | 1,313 | 0 | many_to_one; 0 unmatched |
| filter: EU27 + EU27_2020 | 1,313 | 832 | −481 | drops 24 non-EU and aggregate geos (AL, BA, CH, EA*, EEA, EU, EU15, EU27_2007, EU28, GE, IS, JP, ME, MK, NO, RS, TR, UK, US, XK) |
| filter: years 2005–2025 | 832 | 588 | −244 | drops 1996–2004 |
| **country_year.csv** | 588 | **588** | 0 | = 28 geos × 21 years, a complete grid |
| city_rents: currency = EUR | 5,416 | 2,708 | −2,708 | drop national-currency copies |
| city_rents: building = FLAT1 | 2,708 | 552 | −2,156 | keep 1-bedroom flats |
| city_rents: left merge net EUR on (country_geo, year) | 552 | **552** | 0 | many_to_one; 90 city-years without earnings kept (share = NaN) |
| hicp_monthly: geo in EU27 + EU27_2020 | 266,075 | **196,331** | −69,744 | all units and categories kept |
| dim_country | (unique geos of 8 files) | **52** | – | one row per geo code |

---

## 4. Ten traced records (Phase 5)

Seed `20261104`, one record per KPI so that every dashboard measure is traced (`p5_trace_records.py`). Line numbers count the header as line 1.

| # | Measure | Geo · Year | 1. Raw source | 2. Cleaned long table | 3. Final table | Result |
|---|---|---|---|---|---|---|
| 1 | house_price_index_2015 | FI 2018 | `prc_hpi_a.csv` line 4202: `OBS_VALUE='103.34'`, flag '' | `long_hpi_a.csv` line 4202: 103.34, flag – | `country_year.csv` line 246: 103.34, flag – | MATCH |
| 2 | net_earnings_eur | LT 2005 | `earn_nt_net.csv` line 29406: `'3137.2'` | `long_net_earn.csv` line 29406: 3137.2 | `country_year.csv` line 359: 3137.2 | MATCH |
| 3 | net_earnings_pps | LV 2012 | `earn_nt_net.csv` line 160919: `'7395.32'` | `long_net_earn.csv` line 160919: 7395.32 | `country_year.csv` line 408: 7395.32 | MATCH |
| 4 | price_to_income_vs_lt_avg | RO 2011 | `tipsho60.csv` line 1371: `'100.59'` | `long_ptir.csv` line 1371: 100.59 | `country_year.csv` line 512: 100.59 | MATCH |
| 5 | overburden_18_24 | AT 2025 | `ilc_lvho07a.csv` line 106272: `'4.5'` | `long_overburden.csv` line 106272: 4.5 | `country_year.csv` line 22: 4.5 | MATCH |
| 6 | age_leaving_home | FI 2012 | `yth_demo_030.csv` line 1858: `'21.9'` | `long_age_leave.csv` line 1858: 21.9 | `country_year.csv` line 240: 21.9 | MATCH |
| 7 | pct_18_34_with_parents | LV 2012 | `ilc_lvps08.csv` line 11896: `'54.2'` | `long_with_parents.csv` line 11896: 54.2 | `country_year.csv` line 408: 54.2 | MATCH |
| 8 | hicp_rent_index | AT 2011 | `prc_hicp_minr.csv` lines 27684–27695: 12 months 83.97 … 87.10 | `long_hicp.csv`: the same 12 values | `country_year.csv` line 8: 85.59916666666668 = mean by hand (`statistics.fmean`) 85.59916666666668 | MATCH |
| 9 | real_house_price_index_2015 | CY 2022 | `prc_hpi_a.csv` line 3939: HPI 123.22. HICP TOTAL, 12 months, mean 110.17416666666666 | (derived only) | `country_year.csv` line 82: 111.84110007639418 = 123.22 / 110.174… × 100 by hand | MATCH |
| 10 | rent_share_of_net_salary_pct | IE_CAP 2014 | `prc_colc_rents.csv` line 268: rent 1150. `earn_nt_net.csv` line 29315: IE net 31,687.39 | net / 12 = 2,640.6158…, share unrounded 43.5504… | `city_rent.csv` line 268: rent 1150, salary 2640.6158333333333, share **43.6** | MATCH |

---

## 5. KPI definitions (Phase 5)

All data: Eurostat, CC BY 4.0 ("Source: Eurostat"). Grain: one country (EU27 or `EU27_2020` = "EU average (27)") × one year, 2005–2025, unless stated otherwise. None of these values can be added up across countries or years.

| KPI | Plain-language definition | Calculation | Source and filter | Caveats |
|---|---|---|---|---|
| **House price index** | How expensive homes are compared with 2015 (100 = 2015 price level) | Taken as published | `prc_hpi_a`, purchase = TOTAL (new + existing dwellings), unit = I15_A_AVG | No Greece. Only 13 countries in 2005. Flags `b`/`p`/`e`/`d`. |
| **Real house price index** | House prices after removing general inflation (> 100 = homes got dearer faster than everything else since 2015) | HPI ÷ HICP all-items annual average × 100 | derived | Blank wherever HPI is blank. Best as a DAX measure. |
| **Net earnings (EUR)** | Yearly take-home pay of a single person without children on an average wage, in euros | Taken as published | `earn_nt_net`, estruct = NET, ecase = P1_NCH_AW100, currency = EUR | **EU-wide method break in 2024 (`b`)**: never show 2023→2024 growth. CY gaps. |
| **Net earnings (PPS)** | Same as above, in purchasing power standards (corrects for price levels between countries) | Taken as published | same, currency = PPS | Same break. Use for cross-country comparisons. |
| **Price-to-income ratio vs long-term average** | Are homes more or less affordable than is normal *for that country*? 100 = the country's long-run average; 137 = 37% less affordable than usual | Taken as published | `tipsho60`, unit = PTIR_LT_AVG | Each country is relative to itself, so 137 in PT ≠ 137 in DE in absolute terms. Many `e` (estimated) values. |
| **Housing cost overburden rate (total / 18–24 / 25–29)** | % of people living in a household that spends more than 40% of its disposable income on housing | Taken as published | `ilc_lvho07a`, sex = T, rskpovth = TOTAL, age = TOTAL / Y18-24 / Y25-29 | Survey (EU-SILC): `u` flags, volatile in small countries. FR 2021 missing. Compare in percentage points. |
| **Average age of leaving the parental home** | Estimated average age at which young people move out | Taken as published | `yth_demo_030`, sex = T | `b` breaks (55 in scope). |
| **% of 18–34 year-olds living with parents** | Share of young adults still living in their parents' home | Taken as published | `ilc_lvps08`, sex = T, age = Y18-34 | EU-SILC flags. |
| **HICP rents index / HICP all-items index** | How much rents (actual rentals paid by tenants) and all consumer prices have risen since 2015 | Mean of the 12 monthly indices (2015 = 100). Year kept only if all 12 months exist | `prc_hicp_minr`, unit = I15, coicop18 = CP041 / TOTAL | HICP flags (300 `e` values in scope) are **not carried** into country_year. |
| **1-bedroom rent (EUR/month)** | Monthly rent for a 1-bedroom flat in a city, *as used by Eurostat to set EU officials' pay* | Taken as published | `prc_colc_rents`, building = FLAT1, currency = EUR | **Not the local average rent.** Includes non-capital duty stations (Munich, Bonn, Karlsruhe, Varese, Geneva, Culham, Den Haag). NL has no capital. |
| **Net monthly salary (EUR)** | National net earnings ÷ 12 | net_earnings_eur / 12 | derived | National, not city-level. Same 2024 break. |
| **Rent as % of net salary** | How much of an average national take-home pay a 1-bed duty-station flat would cost | rent ÷ (net annual ÷ 12) × 100, rounded to 1 dp | derived | > 100% in 13 city-years. Only comparable **within a year**. Break in 2024. |
| *SQL-only derived figures* | Growth % 2015→2023 (prices, earnings), gap in percentage points, rent growth 2015→2025, house-price YoY %, rents minus all-items, latest monthly inflation rates, correlations | Ratios and differences of the KPIs above | `sql/generation_rent/02–05` | Build these as DAX measures, not columns. |

**Suggested DAX shape** (illustration only, not built): `Rent share % = DIVIDE(SUM(city_rent[rent_1bed_eur_month]), SUM(city_rent[net_salary_eur_month])) * 100`, used at city-year grain. `Real HPI = DIVIDE(SELECTEDVALUE(country_year[house_price_index_2015]), SELECTEDVALUE(country_year[hicp_all_index])) * 100`. Growth measures should use `CALCULATE(…, dim_year[year] = 2015)` against `dim_year[year] = 2023`.

---

## 6. Prioritised fixes (as proposed before approval; for what was done see §9)

**A. Before building the dashboard**

1. **Import locale** (P6-07, High): set the Power BI import locale to *English (United States)*, or use "Using locale" on every numeric column. Check FI 2018 HPI = 103.34 after import.
2. **Summarization** (P6-09, High): set *Don't summarize* on every value column of `country_year` and `city_rent`, and use explicit DAX measures.
3. **Year/date table** (P6-05, Medium): add `dim_year` (1996–2026) and relate it to `country_year[year]` and `city_rent[year]`. If HICP months are used, add a `dim_date` (month grain).
4. **hicp_monthly** (P6-10, Medium): separate the two units (or always filter `unit`), and use the latest *complete* month.

**B. Before publishing (LinkedIn / portfolio)**

5. **Rent-share framing** (P5-09, P5-10, High/Medium): show it as a 2025 ranking, not a trend across 2024. Rename it "EU duty-station 1-bed rent as % of national net salary". Keep the caveats on the visual.
6. **Coverage notes** (P2-08, P2-10, Medium): no Greek HPI, few countries with HPI before 2010, CY earnings gaps, FR overburden 2021, 26 EU capitals (no NL).
7. **Rankings** (P4-07, Low): exclude the EU average from rank visuals and show it as a reference line.
8. **Flags** (P5-11, Low): show `b`/`u` flags on the charts, and use percentage points for overburden.

**C. Pipeline housekeeping (these change files, so they were held for approval)**

9. **Notebook path** (P3-04 / P7-02, Medium): make `ROOT` find the project root, or move `pipeline/*` back to `python/`, `sql/` and `clean/`.
10. **requirements.txt** (P7-03, Medium): pin the versions listed in P7-03.
11. **dim_country** (P3-11, P6-03, Low): mark EEA as an aggregate, blank out non-ISO `iso2` values, optionally add a `has_country_year_data` flag for slicers.
12. **SQL tidy-up** (P4-06, P4-08, P4-04, Low): replace `LIKE '%_CAP'`, add tie-breakers to `ORDER BY`, fix the stale `python python/run_sql.py` docstrings, and make the runner stop when its glob matches no files.
13. **Optional precision** (P6-08, Low): export the rent share unrounded (round only for display), and carry the HICP flags into `country_year`.

---

## 7. What I could not verify, and why

- **Power BI import behaviour (P6-07).** Power BI Desktop wasn't run, so the locale risk is a strong expectation, not an observed failure.
- **Eurostat accuracy.** The local raw files were treated as the source of truth. They weren't re-downloaded or compared with the Eurostat website, and Eurostat may have revised the data since 2026-11-04.
- **The notebook's chart.** It was checked as present in the fresh run, not compared pixel by pixel.
- **Floating-point identity.** HICP annual means and real HPI from DuckDB vs pandas differ by ≤ 5.7e-14, so they are not bit-identical. Everything else matched exactly.

## 8. Files in `qa/`

| File | What it does |
|---|---|
| `qa_checks.ipynb` | Runs everything below in order (Restart & Run All) |
| `p0_setup_sandbox.py` | Rebuilds `qa/sandbox/` and `qa/sandbox_inplace/`, runs the original notebook and SQL there |
| `p1_dump_notebook.py` | Phase 1: prints the notebook's code cells |
| `p2_profile_raw.py`, `p2b_slice_checks.py` | Phase 2: raw profile (stdlib) and the slices used |
| `p3_notebook_run_compare.py`, `p3_lineage_and_pitfalls.py` | Phase 3 |
| `p4_sql_validation.py`, `p4b_original_db_diff.py` | Phase 4 |
| `p5_independent_recompute.py`, `p5_trace_records.py` | Phase 5 |
| `p6_powerbi_readiness.py` | Phase 6 |
| `p7_reproducibility.py` | Phase 7 |
| `p8_fix_regression.py` | Phase 8 (after the fixes): old outputs vs new outputs, proves only the intended cells changed |
| `summarise_results.py` | Prints the headline result of every phase from `results/*.json` |
| `baseline_before_fixes/` | Copies of the 4 changed CSVs, SHA-256 of all 13 CSVs and the SQL printout **from before the fixes** (input for p8) |
| `results/` | Every output: `p2_profile.md` (full profile), `p4_run_sql_output.txt`, `p5_traces.md`, `run_sql_after_fixes.txt`, `p8_sql_output_diff.txt` and one JSON file per script |
| `sandbox/`, `sandbox_inplace/` | Throwaway copies (≈107 MB of raw data). Safe to delete; `p0` rebuilds them. |

---

## 9. Fixes applied and re-audit (2026-11-04)

All proposed fixes were approved, and the PC's number format was switched to English. Before changing anything, the 4 CSVs that would change, the SHA-256 of all 13 CSVs and the SQL printout were saved to `qa/baseline_before_fixes/`. Raw data in `datasets/` was **not** touched.

### 9.1 What was changed

| Fix (§6 #) | Files | Change |
|---|---|---|
| Notebook path (9) · P3-04, P7-02 | `pipeline/python/generation_rent_01_clean.ipynb` | Searches for `datasets/` at its own base folder and upwards, writes to `<base>/clean/generation-rent/`. Runs from `pipeline/python/` and from the root. Re-executed in place, so the saved outputs are current. |
| Merge safety · P3-06 | notebook | Every merge now has `validate=` (one_to_one / many_to_one), so a duplicate key raises an error instead of silently multiplying rows. |
| dim_country (11) · P3-11, P6-03 | notebook → `dim_country.csv` | `EEA` is now an aggregate (11 aggregates). `iso2` is blank for aggregates (also `EU27_2020` in `country_year`). New `in_country_year` flag for slicers (28 geos). |
| Year table (3) · P6-03, P6-05 | notebook → **new `dim_year.csv`** | 1996–2026, with `earnings_series` ("up to 2023" / "2024+ (new method)") to label the break, and `in_country_year` (2005–2025). |
| hicp_monthly (4) · P6-10 | notebook → `hicp_monthly.csv` | Pivoted to one row per geo × category × month: `index_2015`, `annual_rate_pct` (+ a flag each), `month` (`YYYY-MM`), `date` (first of month, real date), `year`. 196,331 → 99,856 rows; no unit mixing. |
| City type · P4-06 | notebook → `city_rent.csv` | New `is_capital` column (true for `_CAP` codes). SQL uses it instead of `LIKE '%_CAP'`. |
| Notebook checks | notebook | 11 automatic checks at the end (EU27 set, key uniqueness for every table, all FKs in `dim_country` / `dim_year`, no ISO code on aggregates); all PASS. |
| SQL tidy-up (12, 7) · P4-04, P4-07, P4-08 | `pipeline/sql/generation_rent/*.sql`, `run_sql.py` | `ORDER BY` tie-breakers; 02.Q1 ranks countries only (EU average removed); 04.Q3 reports the real pair counts (`regr_count`); 05.Q3 uses the new wide table; `00_setup.sql` loads `dim_year` and types `month`/`date`. Runner: works with root-relative paths and **stops with an error** if a pattern matches no `.sql` file; docstrings corrected. DB rebuilt: 7/7 files OK (`results/run_sql_after_fixes.txt`). |
| requirements (10) · P7-03 | **new `requirements.txt`** (project root) | Pins pandas 3.1.0, numpy 2.5.4, duckdb 2.0.0, matplotlib 3.11.2, jupyter_client 8.10.0, ipykernel 7.4.0, nbconvert 7.17.2, nbformat 5.11.1. |
| Docs | `pipeline/clean/generation-rent/README.md`, `pipeline/sql/generation_rent/README.md` | All tables and columns, caveats, coverage gaps (P2-08, P2-10), Türkiye old-lira note (P2-06), and Power BI steps (locale check, relationships, Summarize by None, hide `country`/`iso2` in the fact). |
| Locale · P6-07 | Windows user settings | Regional format switched from **pt-PT to English (Ireland)** (`Set-Culture en-IE`): decimal `.`, thousands `,`, € currency, dd/MM/yyyy dates. Keyboard unchanged. The **display language** is still Portuguese: only pt-PT is installed and changing it needs admin rights (see §9.4). |

**Not done (optional, §6 #13):** the rent share is still exported rounded to 1 dp, and HICP flags are not carried into `country_year`. Both are harmless if Power BI measures are built from the base columns.

### 9.2 Re-audit: changed statuses (all phases rerun via `qa_checks.ipynb`, exit 0)

| ID | Before | After | Evidence (rerun) |
|---|---|---|---|
| P3-04 Hard-coded paths | FAIL | **PASS** | `p0`: run in the original layout exit 0, no errors. `p3`: 0 absolute paths, path logic = search upwards for `datasets/`. |
| P7-02 Runs where it lives | FAIL | **PASS** | `p7`: `run_in_original_layout` exit 0, and its 14 output CSVs are **SHA-256 identical** to `pipeline/clean/`. |
| P7-03 Versions documented | FAIL | **PASS** | `p7`: `requirements_files_in_project = ['requirements.txt']`. |
| P3-11 dim_country flags | WARNING | **PASS** | `p3`: aggregates missed by regex = none; `p5`: `is_aggregate` = hand-written list of 11, 0 aggregates with `iso2`, every country's `iso2` correct (EL→GR, UK→GB). |
| P4-06 `LIKE '%_CAP'` | WARNING | **PASS** | `p4`: no SQL file uses it; `is_capital` = literal `_CAP` suffix in 552/552 rows. |
| P4-07 EU average in rankings | WARNING | **PASS** (02.Q1) | `p4`: 02.Q1 25 rows, EU average included: False. 02.Q2/02.Q3 still list it on purpose (comparison tables, not ranks). |
| P4-08 Stale paths / silent 0-file runs | WARNING | **PASS** | Runner exits with an error on an empty match; docstrings corrected. |
| P4-02 SQL vs pandas | PASS | **PASS** (stronger) | **27/27** result queries identical *including row order* (before: 4 matched only as a set, because of ties). |
| P4-04 COUNT(*) vs pairs | PASS (Low note) | **PASS** | 04.Q3 now prints `n_pps`, `n_overburden`, `n_price_to_income` = 27 each. |
| P6-03 Star schema | WARNING | **PASS** | `p6`: 6 FK paths, 0 orphans: 3 to `dim_country.geo`, 3 to `dim_year.year` (country_year, city_rent, hicp_monthly). `in_country_year` lets slicers hide the 24 unused geos. |
| P6-05 Calendar table | WARNING | **PASS** | `dim_year` 31 rows (1996–2026) = exact span of every fact table's years; `hicp_monthly.date` is an ISO date in all 99,856 rows. |
| P6-10 hicp_monthly structure | WARNING | **PASS** | `p6`: PK (geo, coicop18, month) unique, no `unit` column. `p5`: rebuilt from raw in DuckDB, **99,856/99,856 rows** identical in both values, both flags, label, date and year; 196,331 filled cells = 196,331 raw rows in scope. Latest month 2026-10 still has 21 rows (flash), so keep the "latest complete month" rule (05.Q3 → 2026-09). |
| P6-07 Power BI import locale | COULD NOT VERIFY | **Risk reduced, still not verified** | PC format is now English (Ireland), so Power BI's default import locale reads `103.34` as 103.34. Still check FI 2018 HPI = 103.34 after the first import. |
| P7-06 Originals untouched | PASS | **Changed by approval** | The audit itself still modified nothing; afterwards the files in §9.1 were changed with approval. `datasets/` is untouched (long_* outputs byte-identical, below). |

Every other check keeps its earlier status. Their numbers were rerun and are unchanged: country_year 588 rows exact; HICP-based columns ≤ 5.7e-14; city_rent 552/552; 10/10 traces MATCH; outputs deterministic.

### 9.3 Regression proof: the fixes changed only what they were meant to (`p8_fix_regression.py`)

| Output | Result |
|---|---|
| 9 `long_*.csv` | SHA-256 **identical** to before. |
| `country_year` | 588 = 588 rows, same keys and columns. Only **21 cells** changed: `iso2` of `EU27_2020` → blank. |
| `city_rent` | 552 = 552 rows. **0 existing cells changed**; one column added (`is_capital`, equal to the `_CAP` suffix in every row). |
| `dim_country` | 52 = 52 rows. Changes: `is_aggregate` EEA False→True (1 cell); `iso2` → blank on the 11 aggregates only; column `in_country_year` added. |
| `hicp_monthly` | All 196,331 old long rows found in the new wide table, and nothing extra. Values identical as text 196,331/196,331, flags 196,331/196,331, labels 196,331/196,331. |
| SQL printout | 27 of 37 result blocks identical. The 9 changed blocks: setup table list (new `dim_year`, column counts); 01.Q5, 03.Q2, 04.Q1, 04.Q4 (only the order of tied rows); 01.Q6 (`is_capital` column); 02.Q1 (EU average removed, ranks 15–26 shift up by one); 04.Q3 (pair counts; correlations unchanged −0.33 / −0.38 / 0.03); 05.Q3 (`time` renamed `month`, values unchanged). There is also an invisible byte-order mark at the top of the new printout. Full diff: `results/p8_sql_output_diff.txt`. |

### 9.4 Still to do (yours, when building the dashboard)

1. **Power BI:**
   - After importing, check FI 2018 HPI = **103.34** (P6-07).
   - Set *Summarize by: None* on every value column and use DAX measures (P6-09, P6-08).
   - Create the relationships `dim_country[geo]` → facts and `dim_year[year]` → facts, and hide `country`/`iso2` in `country_year` (P6-03).
2. **Presentation:**
   - Show the rent share as a ranking within one year, not as a trend across 2023→2024 (P5-09, P5-10).
   - Add coverage notes (P2-08, P2-10).
   - Show the `b`/`u` flags, and use percentage points for overburden (P5-11).
   - Show the download date in the footer (P7-05).
3. **Windows display language (optional):** needs admin rights.
   - Through Settings: *Settings → Time & language → Language & region → Add a language → English (United Kingdom or United States) → tick "Set as my Windows display language"*, then sign out and back in.
   - Or in an **elevated** PowerShell: `Install-Language en-GB -CopyToSettings`.
   - Number and date formats are already English, so this only changes menu text.
   - Restart Power BI / Excel once so they pick up the new number format.
