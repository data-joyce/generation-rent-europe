"""QA Phase 4: SQL validation.

1. Executes every statement of the 7 SQL files (sandbox copies, sandbox DuckDB built by the project's own runner)
   and records success / failure.
2. Re-implements EVERY result-producing query in pandas, reading the CSVs directly (no DuckDB), and compares
   the two results cell by cell. ROUND() is replicated with DuckDB's rule (half away from zero on x*10^n).
3. Targeted logic checks: LIKE wildcard, NULL-vs-COUNT(*) denominators, LIMIT ties, join row counts.
4. Opens the ORIGINAL pipeline/sql/generation_rent.duckdb READ-ONLY and checks its tables equal the CSVs.

Usage: python -I qa/p4_sql_validation.py   -> prints and writes qa/results/p4_sql.json
"""
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "qa/sandbox/sql/generation_rent"
SANDBOX_DB = ROOT / "qa/sandbox/sql/generation_rent.duckdb"
ORIG_DB = ROOT / "pipeline/sql/generation_rent.duckdb"
CSV = ROOT / "pipeline/clean/generation-rent"          # originals, read-only
RES = ROOT / "qa/results"


def R(x, n=0):
    """DuckDB ROUND(DOUBLE, n): std::round(x * 10^n) / 10^n  (half away from zero)."""
    x = pd.to_numeric(x, errors="coerce").astype(float)
    m = 10.0 ** n
    return np.sign(x * m) * np.floor(np.abs(x * m) + 0.5) / m


# ---------------- pandas inputs (read straight from CSV) -------------------------------------------
cy = pd.read_csv(CSV / "country_year.csv")
cr = pd.read_csv(CSV / "city_rent.csv")
dc = pd.read_csv(CSV / "dim_country.csv")
hm = pd.read_csv(CSV / "hicp_monthly.csv", dtype={"month": str, "date": str})
lob = pd.read_csv(CSV / "long_overburden.csv", dtype={"time": str})
lne = pd.read_csv(CSV / "long_net_earn.csv", dtype={"time": str})
CAP = cr["is_capital"].astype(bool)                # SQL now uses the is_capital column (checked below vs the code)


def by_year(df, col, y):
    return df[df.year == y].set_index("geo")[col]


def rank_desc(s):
    return s.rank(method="min", ascending=False, na_option="bottom").astype(int)


# ---------------- pandas re-implementations (one per result-producing statement) ------------------
def q01_2():
    return cy[cy.geo == "PT"].sort_values("year", ascending=False).head(5)[
        ["geo", "country", "year", "house_price_index_2015", "net_earnings_eur", "pct_18_34_with_parents"]]

def q01_3():
    return pd.DataFrame([{"geos": cy.geo.nunique(), "first_year": cy.year.min(), "last_year": cy.year.max(), "rows": len(cy)}])

def q01_4():
    s = cy[cy.year.isin([2005, 2010, 2015, 2020, 2024, 2025])]
    return s.groupby("year").agg(has_house_prices=("house_price_index_2015", "count"), has_earnings=("net_earnings_eur", "count"),
                                 has_age_leaving_home=("age_leaving_home", "count"), has_overburden_18_24=("overburden_18_24", "count")).reset_index()

def q01_5():
    s = cy[(cy.year == 2025) & (cy.geo != "EU27_2020") & cy.age_leaving_home.notna()]
    return s.sort_values(["age_leaving_home", "country"], ascending=[False, True]).head(10)[["country", "age_leaving_home"]]

def q01_6():
    return cr.groupby(["city", "country_geo", "is_capital"]).agg(first_year=("year", "min"), last_year=("year", "max"), years=("year", "size")).reset_index().sort_values("city")

def q02_1():
    p = cy.pivot_table(index=["geo", "country"], columns="year", values=["house_price_index_2015", "net_earnings_eur"], aggfunc="max")
    g = pd.DataFrame({"hpi_2015": p[("house_price_index_2015", 2015)], "hpi_2023": p[("house_price_index_2015", 2023)],
                      "hpi_2025": p[("house_price_index_2015", 2025)], "earn_2015": p[("net_earnings_eur", 2015)],
                      "earn_2023": p[("net_earnings_eur", 2023)]}).reset_index()
    g = g[g.hpi_2015.notna() & g.earn_2015.notna() & (g.geo != "EU27_2020")]
    out = pd.DataFrame({"country": g.country,
                        "house_prices_pct_2015_23": R((g.hpi_2023 / g.hpi_2015 - 1) * 100, 1),
                        "net_earnings_pct_2015_23": R((g.earn_2023 / g.earn_2015 - 1) * 100, 1),
                        "then_prices_2023_25": R((g.hpi_2025 / g.hpi_2023 - 1) * 100, 1)})
    out["rank"] = rank_desc(out.house_prices_pct_2015_23 - out.net_earnings_pct_2015_23)
    out["gap_pct_points"] = R(out.house_prices_pct_2015_23 - out.net_earnings_pct_2015_23, 1)
    return out.sort_values(["rank", "country"])[["rank", "country", "house_prices_pct_2015_23", "net_earnings_pct_2015_23", "gap_pct_points", "then_prices_2023_25"]]

def q02_2():
    p = cy.pivot_table(index="country", columns="year", values="price_to_income_vs_lt_avg", aggfunc="max")
    out = pd.DataFrame({"country": p.index, "ratio_2015": p.get(2015).values, "ratio_2025": p.get(2025).values})
    return out[out.ratio_2025.notna()].sort_values(["ratio_2025", "country"], ascending=[False, True])

def q02_3():
    s = cy[(cy.year == 2025) & cy.real_house_price_index_2015.notna()]
    return pd.DataFrame({"country": s.country, "real_hpi_2025": R(s.real_house_price_index_2015, 1)}).sort_values(["real_hpi_2025", "country"], ascending=[False, True])

def _eu_caps():
    m = cr.merge(dc, left_on="country_geo", right_on="geo", how="inner")
    return m[m.is_eu27 & m.is_capital & m.rent_share_of_net_salary_pct.notna()]

def q03_1():
    s = _eu_caps()
    s = s[s.year == 2025].copy()
    s["rank"] = rank_desc(s.rent_share_of_net_salary_pct)
    s["net_salary_eur_month"] = R(s.net_salary_eur_month, 0)
    return s.sort_values(["rank", "city"])[["rank", "city", "country", "rent_1bed_eur_month", "net_salary_eur_month", "rent_share_of_net_salary_pct"]]

def q03_2():
    s = cr[CAP]
    p = s.pivot_table(index="city", columns="year", values="rent_1bed_eur_month", aggfunc="max")
    out = pd.DataFrame({"city": p.index, "rent_2015": p[2015].values, "rent_2025": p[2025].values})
    out = out[out.rent_2015.notna() & out.rent_2025.notna()]
    out["pct_change"] = R((out.rent_2025 / out.rent_2015 - 1) * 100, 1)
    return out.sort_values(["pct_change", "city"], ascending=[False, True])

def q03_3():
    s = _eu_caps().copy()
    s["rank_that_year"] = s.groupby("year")["rent_share_of_net_salary_pct"].rank(method="min", ascending=False).astype(int)
    s["capitals_that_year"] = s.groupby("year")["city"].transform("size")
    return s[s.city == "Lisboa"].sort_values("year")[["year", "city", "rent_1bed_eur_month", "rent_share_of_net_salary_pct", "rank_that_year", "capitals_that_year"]]

def _latest():
    return cy[(cy.year == 2025) & (cy.geo != "EU27_2020") & cy.age_leaving_home.notna()].copy()

def q04_1():
    s = _latest()
    s["leaving_home_group"] = np.where(s.age_leaving_home >= 30, "30+ (late)", np.where(s.age_leaving_home >= 25, "25-29", "under 25 (early)"))
    return s.sort_values(["age_leaving_home", "country"], ascending=[False, True])[["country", "age_leaving_home", "pct_18_34_with_parents", "overburden_18_24", "price_to_income_vs_lt_avg", "leaving_home_group"]]

def q04_2():
    s = _latest()
    s["grp"] = np.where(s.age_leaving_home >= 30, "1. 30+", np.where(s.age_leaving_home >= 25, "2. 25-29", "3. under 25"))
    g = s.groupby("grp").agg(countries=("geo", "size"), which=("geo", lambda x: ", ".join(sorted(x))),
                             avg_pct_with_parents=("pct_18_34_with_parents", "mean"), avg_overburden_18_24=("overburden_18_24", "mean"),
                             avg_net_earnings_pps=("net_earnings_pps", "mean")).reset_index()
    g["avg_pct_with_parents"] = R(g.avg_pct_with_parents, 1)
    g["avg_overburden_18_24"] = R(g.avg_overburden_18_24, 1)
    g["avg_net_earnings_pps"] = R(g.avg_net_earnings_pps, 0)
    return g.sort_values("grp")

def q04_3():
    s = cy[(cy.year == 2025) & (cy.geo != "EU27_2020")]
    def c(a, b):   # population-correlation on pairwise-complete rows, like DuckDB corr()
        x = s[[a, b]].dropna()
        return np.corrcoef(x[a], x[b])[0, 1]
    return pd.DataFrame([{"vs_net_earnings_pps": float(R(pd.Series([c("age_leaving_home", "net_earnings_pps")]), 2)[0]),
                          "vs_overburden_18_24": float(R(pd.Series([c("age_leaving_home", "overburden_18_24")]), 2)[0]),
                          "vs_price_to_income": float(R(pd.Series([c("age_leaving_home", "price_to_income_vs_lt_avg")]), 2)[0]),
                          "n_pps": len(s[["age_leaving_home", "net_earnings_pps"]].dropna()),
                          "n_overburden": len(s[["age_leaving_home", "overburden_18_24"]].dropna()),
                          "n_price_to_income": len(s[["age_leaving_home", "price_to_income_vs_lt_avg"]].dropna())}])

def q04_4():
    eu = cy[(cy.geo == "EU27_2020") & (cy.year == 2025)].age_leaving_home.iloc[0]
    s = _latest()
    s["years_vs_eu_avg"] = R(s.age_leaving_home - eu, 1)
    return s.sort_values(["years_vs_eu_avg", "country"], ascending=[False, True])[["country", "age_leaving_home", "years_vs_eu_avg"]]

def q05_1():
    pt = cy[(cy.geo == "PT") & (cy.year >= 2010)]
    eu = cy[cy.geo == "EU27_2020"]
    m = pt.merge(eu, on="year", suffixes=("_pt", "_eu"), how="inner")
    return pd.DataFrame({"year": m.year, "pt_house_prices": m.house_price_index_2015_pt, "eu_house_prices": m.house_price_index_2015_eu,
                         "pt_with_parents": m.pct_18_34_with_parents_pt, "eu_with_parents": m.pct_18_34_with_parents_eu,
                         "pt_overburden_25_29": m.overburden_25_29_pt, "eu_overburden_25_29": m.overburden_25_29_eu}).sort_values("year")

def q05_2():
    s = cy[cy.geo.isin(["PT", "EU27_2020"]) & (cy.year >= 2015)].sort_values(["geo", "year"]).copy()
    prev = s.groupby("geo")["house_price_index_2015"].shift(1)
    s["house_prices_yoy_pct"] = R((s.house_price_index_2015 / prev - 1) * 100, 1)
    return s[["geo", "year", "house_price_index_2015", "house_prices_yoy_pct"]]

def q05_3():
    cats = ["TOTAL", "CP011", "CP041", "CP045"]
    s = hm[hm.annual_rate_pct.notna() & hm.geo.isin(["PT", "EU27_2020"]) & hm.coicop18.isin(cats)]
    full = s.groupby(["geo", "month"]).coicop18.nunique()
    latest = full[full == 4].reset_index().groupby("geo").month.max().reset_index()
    out = hm[hm.coicop18.isin(cats)].merge(latest, on=["geo", "month"])
    return out.sort_values(["coicop18", "geo"])[["geo", "month", "coicop18", "coicop18_label", "annual_rate_pct"]]

def q05_4():
    s = cy[(cy.year == 2025) & cy.hicp_rent_index.notna()]
    out = pd.DataFrame({"country": s.country, "rents_2025": R(s.hicp_rent_index, 1), "all_prices_2025": R(s.hicp_all_index, 1),
                        "rents_minus_all": R(s.hicp_rent_index - s.hicp_all_index, 1)})
    return out.sort_values(["rents_minus_all", "country"], ascending=[False, True])

def q06_1():
    g = cy.groupby(["geo", "year"]).size().rename("n").reset_index()
    return g[g.n > 1]

def q06_2():
    s = cy[cy.year == 2025]
    return pd.DataFrame([{"countries": len(s), "missing_house_prices": s.house_price_index_2015.isna().sum(),
                          "missing_earnings": s.net_earnings_eur.isna().sum(), "missing_overburden_18_24": s.overburden_18_24.isna().sum(),
                          "missing_age_leaving_home": s.age_leaving_home.isna().sum()}])

def q06_3():
    return cy[cy.net_earnings_eur_flag == "b"].groupby("year").size().rename("geos_flagged_b").reset_index()

def q06_4():
    s = lob[lob.flag.fillna("").str.contains("u") & (lob.sex == "T")]
    return s.groupby(["rskpovth", "age"]).size().rename("low_reliability_values").reset_index().sort_values("low_reliability_values", ascending=False).head(5)

def q06_5():
    s = lob[lob.flag.fillna("").str.contains("u") & (lob.sex == "T") & (lob.rskpovth == "B_60") & lob.age.isin(["Y18-24", "Y25-29"]) & (lob.time == "2025")]
    return s.rename(columns={"time": "year"}).sort_values(["age", "geo"])[["geo", "year", "age", "value", "flag", "flag_label"]]

def q06_6():
    a = lob[(lob.geo == "PT") & (lob.time == "2025")]
    b = a[(a.sex == "T") & (a.rskpovth == "TOTAL") & (a.age == "TOTAL")]
    return pd.DataFrame([{"approach": "no filters (WRONG)", "rows_used": len(a), "avg_value": float(R(pd.Series([a.value.mean()]), 1)[0])},
                         {"approach": "all dimensions fixed (RIGHT)", "rows_used": len(b), "avg_value": float(R(pd.Series([b.value.mean()]), 1)[0])}])

def q06_7():
    return lob.groupby(["age", "age_label"]).size().rename("rows").reset_index().sort_values("age")

def q06_8():
    s = lne[(lne.geo == "PT") & (lne.time == "2025")]
    return pd.DataFrame([{"rows_for_PT_2025": len(s), "currencies": s.currency.nunique(), "earnings_parts": s.estruct.nunique(), "household_types": s.ecase.nunique()}])


PANDAS = {
    "01_explore.sql": [None, q01_2, q01_3, q01_4, q01_5, q01_6],
    "02_prices_vs_earnings.sql": [q02_1, q02_2, q02_3],
    "03_rent_vs_salary.sql": [q03_1, q03_2, q03_3],
    "04_leaving_home.sql": [q04_1, q04_2, q04_3, q04_4],
    "05_portugal_vs_eu.sql": [q05_1, q05_2, q05_3, q05_4],
    "06_data_quality.sql": [q06_1, q06_2, q06_3, q06_4, q06_5, q06_6, q06_7, q06_8],
}
SILENT = {"CREATE", "INSERT", "DROP", "UPDATE", "DELETE", "ALTER", "COPY", "SET", "TRANSACTION"}


def compare(a: pd.DataFrame, b: pd.DataFrame):
    """Cell-by-cell equality (NaN == NaN). Returns (status, detail)."""
    a, b = a.reset_index(drop=True), b.reset_index(drop=True)
    if list(a.columns) != list(b.columns):
        return "MISMATCH", f"columns differ: {list(a.columns)} vs {list(b.columns)}"
    if a.shape != b.shape:
        return "MISMATCH", f"shape {a.shape} vs {b.shape}"

    def eq(x, y):
        bad = 0
        for c in x.columns:
            xs, ys = x[c], y[c]
            if pd.api.types.is_numeric_dtype(xs) and pd.api.types.is_numeric_dtype(ys) and not pd.api.types.is_bool_dtype(xs):
                xv, yv = xs.astype(float).to_numpy(), ys.astype(float).to_numpy()
                bad += int((~((xv == yv) | (np.isnan(xv) & np.isnan(yv)))).sum())
            else:
                bad += int((nastr(xs) != nastr(ys)).sum())
        return bad
    bad = eq(a, b)
    if bad == 0:
        return "EXACT", f"{a.shape[0]} rows x {a.shape[1]} cols identical, same order"
    sa, sb = canon(a), canon(b)
    bad_set = eq(sa, sb)
    if bad_set == 0:
        return "EXACT (order differs within ties)", f"{a.shape[0]} rows identical as a set; ordered compare differed in {bad} cells (tied sort keys)"
    return "MISMATCH", f"{bad_set} differing cells even after sorting"


def canon(df):
    """Numeric columns as float, then sort by every column -> order-independent comparison."""
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):          # DuckDB DATE -> same text as the CSV
            out[c] = out[c].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_numeric_dtype(out[c]) and not pd.api.types.is_bool_dtype(out[c]):
            out[c] = out[c].astype(float)
        else:
            out[c] = nastr(out[c])
    return out.sort_values(list(out.columns), na_position="last").reset_index(drop=True)


def nastr(s):
    """Text with an explicit marker for missing values (pandas 3 'str' dtype keeps NaN through astype(str))."""
    return s.astype(object).where(s.notna(), "<missing>").astype(str)


con = duckdb.connect(str(SANDBOX_DB), read_only=True)
results, mismatches = [], {}
for f in sorted(SQL_DIR.glob("*.sql")):
    stmts = duckdb.extract_statements(f.read_text(encoding="utf-8"))
    selects = [s for s in stmts if s.type.name not in SILENT]
    fns = PANDAS.get(f.name, [])
    for i, s in enumerate(selects):
        qid = f"{f.name[:2]}.Q{i + 1}" if f.name != "00_setup.sql" else "00.check"
        try:
            sql_df = con.execute(s.query).df()
            ok = "RUNS"
        except Exception as e:                       # noqa: BLE001
            results.append({"id": qid, "runs": f"ERROR {e}"})
            continue
        fn = fns[i] if i < len(fns) else None
        if fn is None:
            results.append({"id": qid, "runs": ok, "rows": len(sql_df), "pandas_match": "n/a (metadata query)"})
            continue
        pd_df = fn()
        # align dtypes of integer counts coming from pandas
        status, detail = compare(sql_df, pd_df)
        results.append({"id": qid, "runs": ok, "rows": len(sql_df), "pandas_match": status, "detail": detail})
        if status == "MISMATCH":
            mismatches[qid] = {"sql": sql_df.head(15).to_string(), "pandas": pd_df.head(15).to_string()}
    # file-level: count of statements (incl. silent) executed by runner = all statements parsed
print(f"{'query':8} {'runs':6} {'rows':>5}  pandas recomputation")
for r in results:
    print(f"{r['id']:8} {r['runs']:6} {r.get('rows', ''):>5}  {r.get('pandas_match', '')}  {r.get('detail', '')}")
for k, v in mismatches.items():
    print(f"\n!! {k}\nSQL:\n{v['sql']}\nPANDAS:\n{v['pandas']}")

# ---------------- targeted logic checks ---------------------------------------------------------
chk = {}
bad_cap = con.execute("SELECT city_geo, is_capital FROM city_rent WHERE is_capital <> (right(city_geo, 4) = '_CAP')").fetchall()
chk["is_capital agrees with the literal '_CAP' suffix (no LIKE wildcard)"] = bad_cap or "yes, all 552 rows"
chk["SQL files still using LIKE '%_CAP'"] = [f.name for f in SQL_DIR.glob("*.sql") if "LIKE '%_CAP'" in f.read_text(encoding="utf-8")] or "none"
eu_caps_2025 = con.execute("""SELECT r.country_geo FROM city_rent r JOIN dim_country d ON d.geo=r.country_geo
                              WHERE r.year=2025 AND d.is_eu27 AND r.is_capital AND r.rent_share_of_net_salary_pct IS NOT NULL""").fetchall()
chk["03.Q1 EU27 countries with no capital row in 2025"] = sorted(set(dc[dc.is_eu27].geo) - {g for (g,) in eu_caps_2025})
chk["03.Q1 non-null shares 2025 (EU27 capitals)"] = len(eu_caps_2025)
q021 = q02_1()
chk["02.Q1 rows (incl. EU average row?)"] = f"{len(q021)} rows; EU average included: {'EU average (27)' in set(q021.country)}"
chk["02.Q1 EU27 countries excluded (no 2015 HPI or earnings)"] = sorted(set(dc[dc.is_eu27].country) - set(q021.country))
chk["02.Q1 rows with NULL growth (sorted last by DuckDB)"] = q021[q021.house_prices_pct_2015_23.isna() | q021.net_earnings_pct_2015_23.isna()].country.tolist()
chk["02.Q1 rank ties"] = q021[q021.duplicated("rank", keep=False)][["rank", "country"]].values.tolist()
chk["02.Q2 / 02.Q3 include EU average row"] = bool("EU average (27)" in set(q02_2().country)) and bool("EU average (27)" in set(q02_3().country))
s25 = cy[(cy.year == 2025) & (cy.geo != "EU27_2020")]
chk["04.Q3 COUNT(*) vs non-null pairs used by corr()"] = {
    "COUNT(*)": len(s25),
    "pairs age~pps": int(s25[["age_leaving_home", "net_earnings_pps"]].dropna().shape[0]),
    "pairs age~overburden_18_24": int(s25[["age_leaving_home", "overburden_18_24"]].dropna().shape[0]),
    "pairs age~ptir": int(s25[["age_leaving_home", "price_to_income_vs_lt_avg"]].dropna().shape[0])}
l = _latest()
chk["04.Q2 AVG denominators vs COUNT(*) (NULLs skipped by AVG)"] = {
    "countries with age 2025": len(l), "null pct_with_parents": int(l.pct_18_34_with_parents.isna().sum()),
    "null overburden_18_24": int(l.overburden_18_24.isna().sum()), "null net_earnings_pps": int(l.net_earnings_pps.isna().sum())}
chk["04 queries: EU27 countries with no 2025 age_leaving_home (silently excluded)"] = sorted(set(cy[(cy.year == 2025) & (cy.geo != "EU27_2020")].geo) - set(l.geo))
top = _latest().sort_values("age_leaving_home", ascending=False)
chk["01.Q5 LIMIT 10 tie at the cut-off"] = f"10th value {top.age_leaving_home.iloc[9]}, 11th value {top.age_leaving_home.iloc[10]} -> tie: {top.age_leaving_home.iloc[9] == top.age_leaving_home.iloc[10]}"
g4 = lob[lob.flag.fillna('').str.contains('u') & (lob.sex == 'T')].groupby(['rskpovth', 'age']).size().sort_values(ascending=False)
chk["06.Q4 LIMIT 5 tie at the cut-off"] = f"5th {g4.iloc[4]}, 6th {g4.iloc[5]} -> tie: {g4.iloc[4] == g4.iloc[5]}"
a = lob[(lob.geo == "PT") & (lob.time == "2025")]
chk["06.Q6 rows_used COUNT(*) includes NULL values?"] = f"{a.value.isna().sum()} NULL values among {len(a)} rows"
chk["06.Q3 2024 flagged b"] = f"{int(((cy.year == 2024) & (cy.net_earnings_eur_flag == 'b')).sum())} geos (27 countries + EU average = 28 expected)"
eu_years = set(cy[cy.geo == "EU27_2020"].year)
chk["05.Q1 inner self-join drops PT years without EU row"] = sorted(set(cy[(cy.geo == "PT") & (cy.year >= 2010)].year) - eu_years) or "none"
chk["05.Q2 LAG over gaps in years (PT/EU)"] = {g: sorted(set(range(2015, 2026)) - set(cy[cy.geo == g].year)) or "no gaps" for g in ["PT", "EU27_2020"]}
chk["05.Q3 latest complete month"] = q05_3()[["geo", "month"]].drop_duplicates().values.tolist()
chk["integer division risk"] = "DuckDB '/' on BIGINT returns DOUBLE (03.Q2 rent ints) - verified by exact match of 03.Q2 with pandas float division"
types = con.execute("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_name IN ('country_year','city_rent','dim_country','dim_year','hicp_monthly') ORDER BY table_name, ordinal_position").df()
chk["duckdb_inferred_types"] = types.groupby("table_name").apply(lambda t: dict(zip(t.column_name, t.data_type)), include_groups=False).to_dict()
con.close()

# ---------------- original DB (read-only) vs CSVs -------------------------------------------------
orig = duckdb.connect(str(ORIG_DB), read_only=True)
odb = {}
for t, path in [("country_year", "country_year.csv"), ("city_rent", "city_rent.csv"), ("dim_country", "dim_country.csv"),
                ("dim_year", "dim_year.csv"), ("hicp_monthly", "hicp_monthly.csv"), ("long_overburden", "long_overburden.csv"),
                ("long_net_earn", "long_net_earn.csv"), ("long_with_parents", "long_with_parents.csv")]:
    db = orig.execute(f"SELECT * FROM {t}").df()
    csvdf = pd.read_csv(CSV / path, dtype={"time": str, "month": str, "date": str})
    st, det = compare(canon(db), canon(csvdf))
    odb[t] = f"{len(db)} rows x {db.shape[1]} cols: {st} ({det})"
orig.close()
chk["original_duckdb_tables_vs_csv (string compare)"] = odb

print("\nTARGETED CHECKS")
for k, v in chk.items():
    print(f"  {k}: {v}")
(RES / "p4_sql.json").write_text(json.dumps({"queries": results, "mismatches": mismatches, "checks": chk}, indent=1,
                                            ensure_ascii=False, default=str), encoding="utf-8")
