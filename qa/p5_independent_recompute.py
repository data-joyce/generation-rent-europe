"""QA Phase 5.2 + 5.4 (+ 6 inputs): independent recomputation of the Power BI tables from the RAW files.

Method: DuckDB SQL reading the raw Eurostat CSVs directly (all text, codes split with split_part), with NO use of
the notebook, pandas, or the cleaned long_* files. The final CSVs are read with Python's csv module.
Then every cell of country_year.csv, city_rent.csv and dim_country.csv is compared with the recomputation.

Usage: python -I qa/p5_independent_recompute.py   -> prints and writes qa/results/p5_recompute.json
"""
import csv
import json
import math
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path

import duckdb

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "datasets"
FINAL = ROOT / "pipeline/clean/generation-rent"
RES = ROOT / "qa/results"
EU27 = "AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK".split()

RAWFILES = {
    "hpi_a": "eurostat-house-price-index/prc_hpi_a.csv",
    "ptir": "eurostat-house-price-to-income/tipsho60.csv",
    "net_earn": "eurostat-net-earnings/earn_nt_net.csv",
    "city_rents": "eurostat-city-rents/prc_colc_rents.csv",
    "overburden": "eurostat-housing-cost-overburden/ilc_lvho07a.csv",
    "age_leave": "eurostat-age-leaving-home/yth_demo_030.csv",
    "with_parents": "eurostat-young-adults-living-with-parents/ilc_lvps08.csv",
    "hicp": "eurostat-hicp-housing-food/prc_hicp_minr.csv",
}

con = duckdb.connect()   # in-memory, nothing written to disk
for name, rel in RAWFILES.items():
    path = (RAW / rel).as_posix()
    with open(RAW / rel, encoding="utf-8") as f:
        header = next(csv.reader(f))
    sel = []
    for h in header:
        short = h.split(":")[0].strip()
        if short in ("STRUCTURE", "STRUCTURE_ID", "CONF_STATUS", "freq"):
            continue
        q = '"' + h.replace('"', '""') + '"'
        if short == "TIME_PERIOD":
            sel.append(f"{q} AS time")
        elif short == "OBS_VALUE":
            sel.append(f"TRY_CAST(NULLIF({q}, '') AS DOUBLE) AS value")
        elif short == "OBS_FLAG":
            sel.append(f"NULLIF(split_part({q}, ': ', 1), '') AS flag")
        else:
            sel.append(f"split_part({q}, ': ', 1) AS {short}")
            if short in ("geo", "coicop18"):
                sel.append(f"substr({q}, strpos({q}, ': ') + 2) AS {short}_label")
    con.execute(f"CREATE VIEW raw_{name} AS SELECT {', '.join(sel)} FROM read_csv('{path}', all_varchar=true, header=true)")

eu_list = ", ".join(f"'{g}'" for g in EU27 + ["EU27_2020"])
SLICES = {
    "house_price_index_2015": "SELECT geo, time, value, flag FROM raw_hpi_a WHERE purchase='TOTAL' AND unit='I15_A_AVG'",
    "net_earnings_eur": "SELECT geo, time, value, flag FROM raw_net_earn WHERE estruct='NET' AND ecase='P1_NCH_AW100' AND currency='EUR'",
    "net_earnings_pps": "SELECT geo, time, value, flag FROM raw_net_earn WHERE estruct='NET' AND ecase='P1_NCH_AW100' AND currency='PPS'",
    "price_to_income_vs_lt_avg": "SELECT geo, time, value, flag FROM raw_ptir WHERE unit='PTIR_LT_AVG'",
    "overburden_total": "SELECT geo, time, value, flag FROM raw_overburden WHERE sex='T' AND rskpovth='TOTAL' AND age='TOTAL'",
    "overburden_18_24": "SELECT geo, time, value, flag FROM raw_overburden WHERE sex='T' AND rskpovth='TOTAL' AND age='Y18-24'",
    "overburden_25_29": "SELECT geo, time, value, flag FROM raw_overburden WHERE sex='T' AND rskpovth='TOTAL' AND age='Y25-29'",
    "age_leaving_home": "SELECT geo, time, value, flag FROM raw_age_leave WHERE sex='T'",
    "pct_18_34_with_parents": "SELECT geo, time, value, flag FROM raw_with_parents WHERE sex='T' AND age='Y18-34'",
}
for m, q in SLICES.items():
    con.execute(f"CREATE VIEW s_{m} AS {q}")
con.execute("""CREATE VIEW s_hicp AS
    SELECT geo, substr(time,1,4) AS time, coicop18, AVG(value) AS value, COUNT(value) AS n
    FROM raw_hicp WHERE unit='I15' AND coicop18 IN ('CP041','TOTAL') GROUP BY ALL HAVING COUNT(value)=12""")

joins = "\n".join(f"LEFT JOIN s_{m} AS {m} ON {m}.geo=k.geo AND {m}.time=k.time" for m in SLICES)
cols = ",\n".join(f"{m}.value AS {m}, {m}.flag AS {m}_flag" for m in SLICES)
con.execute(f"""CREATE TABLE recomputed AS
WITH k AS (SELECT g.geo, CAST(y AS VARCHAR) AS time FROM (SELECT unnest([{eu_list}]) AS geo) g, range(2005, 2026) t(y))
SELECT k.geo, CAST(k.time AS INTEGER) AS year, {cols},
       hr.value AS hicp_rent_index, ha.value AS hicp_all_index,
       house_price_index_2015.value / ha.value * 100 AS real_house_price_index_2015
FROM k {joins}
LEFT JOIN s_hicp hr ON hr.geo=k.geo AND hr.time=k.time AND hr.coicop18='CP041'
LEFT JOIN s_hicp ha ON ha.geo=k.geo AND ha.time=k.time AND ha.coicop18='TOTAL'""")
# (the grid of 28 geos x 21 years is checked against the final key set below)

report = {}


def read_final(name):
    with open(FINAL / f"{name}.csv", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(s):
    return None if s == "" else float(s)


# ---- country_year: cell-by-cell -------------------------------------------------------------
fin = read_final("country_year")
rec = {(r[0], r[1]): r for r in con.execute("SELECT * FROM recomputed").fetchall()}
rcols = [d[0] for d in con.description]
fin_keys = {(r["geo"], int(r["year"])) for r in fin}
report["country_year_keys"] = {"final_rows": len(fin), "recomputed_rows": len(rec),
                               "keys_only_in_final": sorted(fin_keys - set(rec))[:5], "keys_only_in_recomputed": sorted(set(rec) - fin_keys)[:5]}
cell = {}
for c in rcols[2:]:
    exact = mism = null_mism = 0
    maxdiff = 0.0
    examples = []
    for r in fin:
        a = r[c]
        b = rec[(r["geo"], int(r["year"]))][rcols.index(c)]
        if c.endswith("_flag"):
            ok = (a or None) == b
        else:
            fa = num(a)
            if (fa is None) != (b is None):
                null_mism += 1
                ok = False
            else:
                ok = fa == b
                if not ok and fa is not None:
                    maxdiff = max(maxdiff, abs(fa - b))
        if ok:
            exact += 1
        else:
            mism += 1
            if len(examples) < 3:
                examples.append(f"{r['geo']} {r['year']}: final={a!r} recomputed={b!r}")
    cell[c] = {"exact": exact, "mismatch": mism, "null_mismatch": null_mism, "max_abs_diff": maxdiff, "examples": examples}
report["country_year_cells"] = cell
# labels / iso2
lab = dict(con.execute("SELECT DISTINCT geo, geo_label FROM (SELECT geo, geo_label FROM raw_hpi_a UNION ALL SELECT geo, geo_label FROM raw_net_earn UNION ALL SELECT geo, geo_label FROM raw_overburden)").fetchall())
bad_lab = [(r["geo"], r["country"]) for r in fin if r["geo"] != "EU27_2020" and r["country"] != lab.get(r["geo"])]
expected_iso = lambda g: "" if g == "EU27_2020" else {"EL": "GR"}.get(g, g)   # noqa: E731  aggregates have no ISO code
bad_iso = [(r["geo"], r["iso2"]) for r in fin if r["iso2"] != expected_iso(r["geo"])]
report["country_year_labels"] = {"country_label_mismatches": bad_lab[:5], "iso2_mismatches": bad_iso[:5],
                                 "EU27_2020 country label": sorted({r["country"] for r in fin if r["geo"] == "EU27_2020"})}

# ---- reconciliation of totals: count and exact sum per measure, raw slice vs final --------------
recon = {}
for m in list(SLICES) + ["hicp_rent_index", "hicp_all_index"]:
    if m.startswith("hicp"):
        cat = "CP041" if m == "hicp_rent_index" else "TOTAL"
        raw_vals = [v for (v,) in con.execute(f"SELECT value FROM s_hicp WHERE coicop18='{cat}' AND geo IN ({eu_list}) AND time BETWEEN '2005' AND '2025'").fetchall()]
        months = con.execute(f"SELECT COUNT(*), SUM(value) FROM raw_hicp WHERE unit='I15' AND coicop18='{cat}' AND geo IN ({eu_list}) AND time BETWEEN '2005-01' AND '2025-12'").fetchone()
    else:
        raw_vals = [v for (v,) in con.execute(f"SELECT value FROM s_{m} WHERE geo IN ({eu_list}) AND time BETWEEN '2005' AND '2025' AND value IS NOT NULL").fetchall()]
        months = None
    fin_vals = [float(r[m]) for r in fin if r[m] != ""]
    recon[m] = {"raw_count": len(raw_vals), "final_count": len(fin_vals),
                "raw_sum_fsum": math.fsum(raw_vals), "final_sum_fsum": math.fsum(fin_vals),
                "sums_equal": math.fsum(raw_vals) == math.fsum(fin_vals)}
    if months:
        recon[m]["monthly_rows_2005_2025"] = months[0]
        recon[m]["check: 12 x annual rows == monthly rows"] = 12 * len(raw_vals) == months[0]
        recon[m]["sum(12 x annual avg) vs sum(months), abs diff"] = abs(12 * math.fsum(raw_vals) - months[1])
# raw blanks inside scope that become NaN in final (documented: 'not for publication')
recon["hpi_blank_raw_rows_in_scope"] = con.execute(f"SELECT COUNT(*) FROM s_house_price_index_2015 WHERE value IS NULL AND geo IN ({eu_list}) AND time BETWEEN '2005' AND '2025'").fetchone()[0]
report["reconciliation"] = recon

# ---- EU average plausibility: EU27_2020 value must lie inside [min, max] of the members ---------
outside = {}
for m in list(SLICES) + ["hicp_rent_index", "hicp_all_index"]:
    rows = con.execute(f"""SELECT r.year, e.{m}, MIN(r.{m}), MAX(r.{m}) FROM recomputed r JOIN recomputed e
                           ON e.year=r.year AND e.geo='EU27_2020' WHERE r.geo<>'EU27_2020' AND e.{m} IS NOT NULL
                           GROUP BY r.year, e.{m} HAVING e.{m} < MIN(r.{m}) OR e.{m} > MAX(r.{m})""").fetchall()
    outside[m] = rows or "always inside member range"
report["eu_average_within_member_range"] = outside

# ---- city_rent ----------------------------------------------------------------------------------
con.execute("""CREATE TABLE rec_city AS
SELECT r.geo AS city_geo, r.geo_label AS city, split_part(r.geo, '_', 1) AS country_geo, CAST(r.time AS INTEGER) AS year,
       r.value AS rent, n.value / 12 AS net_salary_eur_month, r.value / (n.value / 12) * 100 AS share_unrounded, n.flag AS net_flag
FROM raw_city_rents r LEFT JOIN s_net_earnings_eur n ON n.geo = split_part(r.geo, '_', 1) AND n.time = r.time
WHERE r.building='FLAT1' AND r.currency='EUR'""")
fc = read_final("city_rent")
rc = {(r[0], r[3]): r for r in con.execute("SELECT * FROM rec_city").fetchall()}
c_ok = {"rows_final": len(fc), "rows_recomputed": len(rc), "rent_exact": 0, "salary_exact": 0, "flag_exact": 0, "city_label_exact": 0,
        "is_capital_exact": 0, "share_vs_round_half_even": 0, "share_vs_round_half_up": 0, "share_null_match": 0}
share_diffs = []
for r in fc:
    x = rc[(r["city_geo"], int(r["year"]))]
    c_ok["is_capital_exact"] += r["is_capital"] == str(r["city_geo"].endswith("_CAP"))
    c_ok["rent_exact"] += float(r["rent_1bed_eur_month"]) == x[4]
    c_ok["salary_exact"] += (r["net_salary_eur_month"] == "" and x[5] is None) or (r["net_salary_eur_month"] != "" and float(r["net_salary_eur_month"]) == x[5])
    c_ok["flag_exact"] += (r["net_earnings_eur_flag"] or None) == x[7]
    c_ok["city_label_exact"] += r["city"] == x[1]
    if x[6] is None:
        c_ok["share_null_match"] += r["rent_share_of_net_salary_pct"] == ""
        continue
    d = Decimal(repr(x[6]))
    he, hu = float(d.quantize(Decimal("0.1"), ROUND_HALF_EVEN)), float(d.quantize(Decimal("0.1"), ROUND_HALF_UP))
    fval = float(r["rent_share_of_net_salary_pct"])
    c_ok["share_vs_round_half_even"] += fval == he
    c_ok["share_vs_round_half_up"] += fval == hu
    if he != hu or fval != hu:
        share_diffs.append(f"{r['city_geo']} {r['year']}: unrounded={x[6]!r} csv={fval} half-even={he} half-up(Excel/DAX/SQL)={hu}")
c_ok["rows_with_null_share"] = sum(1 for x in rc.values() if x[6] is None)
c_ok["rounding_sensitive_rows"] = share_diffs
report["city_rent"] = c_ok

# ---- dim_country --------------------------------------------------------------------------------
fd = read_final("dim_country")
AGG = {"EA", "EA18", "EA19", "EA20", "EA21", "EEA", "EU", "EU15", "EU27_2007", "EU27_2020", "EU28"}   # written out by hand
report["dim_country"] = {
    "rows": len(fd), "distinct_geo": len({r['geo'] for r in fd}),
    "is_eu27_true": sorted(r["geo"] for r in fd if r["is_eu27"] == "True"),
    "is_eu27_matches_official_list": sorted(r["geo"] for r in fd if r["is_eu27"] == "True") == sorted(EU27),
    "is_aggregate_true": sorted(r["geo"] for r in fd if r["is_aggregate"] == "True"),
    "is_aggregate_matches_hand_list": {r["geo"] for r in fd if r["is_aggregate"] == "True"} == AGG,
    "aggregates_with_iso2": sorted(r["geo"] for r in fd if r["is_aggregate"] == "True" and r["iso2"] != ""),
    "countries_iso2_ok": all(r["iso2"] == {"EL": "GR", "UK": "GB"}.get(r["geo"], r["geo"]) for r in fd if r["is_aggregate"] == "False"),
    "in_country_year_matches_country_year_geos": {r["geo"] for r in fd if r["in_country_year"] == "True"} == {r["geo"] for r in fin},
    "city_rent_country_geo_missing_in_dim": sorted({r["country_geo"] for r in fc} - {r["geo"] for r in fd}),
    "country_year_geo_missing_in_dim": sorted({r["geo"] for r in fin} - {r["geo"] for r in fd}),
}

# ---- hicp_monthly: rebuilt from RAW in DuckDB (pivot of unit) and compared cell by cell -----------
con.execute(f"""CREATE TABLE rec_hicp AS
SELECT geo, coicop18, time AS month,
       MAX(value) FILTER (WHERE unit='I15')   AS index_2015,   MAX(flag) FILTER (WHERE unit='I15')   AS index_2015_flag,
       MAX(value) FILTER (WHERE unit='RCH_A') AS annual_rate_pct, MAX(flag) FILTER (WHERE unit='RCH_A') AS annual_rate_pct_flag,
       COUNT(*) AS n_raw_rows
FROM raw_hicp WHERE geo IN ({eu_list}) GROUP BY geo, coicop18, time""")
labels = dict(con.execute("SELECT DISTINCT coicop18, coicop18_label FROM raw_hicp").fetchall())
rh = {(r[0], r[1], r[2]): r for r in con.execute("SELECT * FROM rec_hicp").fetchall()}
fh = read_final("hicp_monthly")
h_ok = {"rows_final": len(fh), "rows_recomputed": len(rh), "max_raw_rows_per_key (must be <= 2)": max(r[7] for r in rh.values()),
        "keys_only_in_final": 0, "index_exact": 0, "rate_exact": 0, "flags_exact": 0, "label_exact": 0, "date_and_year_exact": 0}
for r in fh:
    x = rh.get((r["geo"], r["coicop18"], r["month"]))
    if x is None:
        h_ok["keys_only_in_final"] += 1
        continue
    h_ok["index_exact"] += (num(r["index_2015"]) == x[3]) or (r["index_2015"] == "" and x[3] is None)
    h_ok["rate_exact"] += (num(r["annual_rate_pct"]) == x[5]) or (r["annual_rate_pct"] == "" and x[5] is None)
    h_ok["flags_exact"] += (r["index_2015_flag"] or None) == x[4] and (r["annual_rate_pct_flag"] or None) == x[6]
    h_ok["label_exact"] += r["coicop18_label"] == labels[r["coicop18"]]
    h_ok["date_and_year_exact"] += r["date"] == r["month"] + "-01" and r["year"] == r["month"][:4]
h_ok["filled_cells_final"] = sum((r["index_2015"] != "") + (r["annual_rate_pct"] != "") for r in fh)
h_ok["raw_rows_in_scope"] = con.execute(f"SELECT COUNT(*) FROM raw_hicp WHERE geo IN ({eu_list})").fetchone()[0]
report["hicp_monthly"] = h_ok

# ---- dim_year -------------------------------------------------------------------------------------
fy = read_final("dim_year")
years_all = {int(r["year"]) for r in fin} | {int(r["year"]) for r in fc} | {int(r["year"]) for r in fh}
report["dim_year"] = {
    "rows": len(fy), "range": (fy[0]["year"], fy[-1]["year"]),
    "is_exact_span_of_all_fact_years": [int(r["year"]) for r in fy] == list(range(min(years_all), max(years_all) + 1)),
    "earnings_series_rule_ok": all(r["earnings_series"] == ("2024+ (new method)" if int(r["year"]) >= 2024 else "up to 2023") for r in fy),
    "in_country_year_rule_ok": all((r["in_country_year"] == "True") == (2005 <= int(r["year"]) <= 2025) for r in fy),
}

# ---- 5.4 sanity checks on the final values ------------------------------------------------------
san = {}
q = lambda s: con.execute(s).fetchall()  # noqa: E731
san["2025 ranges (min, max) per measure, EU27 only"] = {m: q(f"SELECT ROUND(MIN({m}),1), ROUND(MAX({m}),1), arg_min(geo,{m}), arg_max(geo,{m}) FROM recomputed WHERE year=2025 AND geo<>'EU27_2020'")[0]
                                                          for m in list(SLICES) + ["hicp_rent_index", "hicp_all_index", "real_house_price_index_2015"]}
san["PT price_to_income 2025 and EU rank"] = q("""SELECT geo, price_to_income_vs_lt_avg, RANK() OVER (ORDER BY price_to_income_vs_lt_avg DESC) FROM recomputed
                                                 WHERE year=2025 AND geo<>'EU27_2020' AND price_to_income_vs_lt_avg IS NOT NULL ORDER BY 2 DESC LIMIT 5""")
san["rent share 2025, EU27 *_CAP, top 5 (unrounded)"] = q("""SELECT city_geo, city, ROUND(share_unrounded,2), rent, ROUND(net_salary_eur_month,2) FROM rec_city
                                                         WHERE year=2025 AND right(city_geo,4)='_CAP' AND country_geo IN (SELECT unnest(['""" + "','".join(EU27) + """'])) ORDER BY share_unrounded DESC LIMIT 5""")
san["Lisboa share if 2025 salary were 2023 salary grown at 2015-23 CAGR (break sensitivity)"] = q("""
    WITH p AS (SELECT MAX(CASE WHEN time='2015' THEN value END) e15, MAX(CASE WHEN time='2023' THEN value END) e23,
                      MAX(CASE WHEN time='2024' THEN value END) e24, MAX(CASE WHEN time='2025' THEN value END) e25 FROM s_net_earnings_eur WHERE geo='PT')
    SELECT e15, e23, e24, e25, ROUND(e23 * power(e23/e15, 2.0/8), 0) AS e25_no_break_est,
           ROUND(1400 / (e25/12) * 100, 1) AS share_reported, ROUND(1400 / ((e23 * power(e23/e15, 2.0/8))/12) * 100, 1) AS share_no_break_est FROM p""")
san["year-on-year jumps > 25% in final measures (EU27, excl. 2023->2024 earnings)"] = q("""
    WITH u AS (UNPIVOT recomputed ON house_price_index_2015, net_earnings_eur, net_earnings_pps, price_to_income_vs_lt_avg,
               overburden_total, overburden_18_24, overburden_25_29, age_leaving_home, pct_18_34_with_parents INTO NAME measure VALUE v),
    l AS (SELECT geo, year, measure, v, LAG(v) OVER (PARTITION BY geo, measure ORDER BY year) pv, LAG(year) OVER (PARTITION BY geo, measure ORDER BY year) py FROM u)
    SELECT geo, measure, py, year, ROUND(pv,1), ROUND(v,1), ROUND((v/pv-1)*100,1) FROM l
    WHERE pv IS NOT NULL AND pv<>0 AND abs(v/pv-1) > 0.25 AND NOT (measure LIKE 'net_earnings%' AND year=2024) AND geo<>'EU27_2020'
    ORDER BY abs(v/pv-1) DESC LIMIT 25""")
san["series gaps: country-years where value missing between first and last year"] = q("""
    WITH u AS (""" + " UNION ALL ".join(f"SELECT geo, year, '{m}' AS measure, {m} AS v FROM recomputed" for m in
                       ["house_price_index_2015", "net_earnings_eur", "price_to_income_vs_lt_avg", "overburden_total", "age_leaving_home", "pct_18_34_with_parents"]) + """),
    b AS (SELECT geo, measure, MIN(year) FILTER (WHERE v IS NOT NULL) f, MAX(year) FILTER (WHERE v IS NOT NULL) l FROM u GROUP BY ALL)
    SELECT u.measure, u.geo, list(u.year ORDER BY u.year) FROM u JOIN b USING (geo, measure) WHERE u.v IS NULL AND u.year BETWEEN b.f AND b.l GROUP BY ALL ORDER BY 1,2""")
san["overburden_18_24 below 0 or above 100 / age outside 15-40"] = q("""SELECT COUNT(*) FILTER (WHERE overburden_18_24<0 OR overburden_18_24>100), COUNT(*) FILTER (WHERE age_leaving_home NOT BETWEEN 15 AND 40) FROM recomputed""")[0]
san["rent share > 100% (any city, any year)"] = q("SELECT city_geo, year, ROUND(share_unrounded,1) FROM rec_city WHERE share_unrounded > 100 ORDER BY 3 DESC")
san["real_hpi 2015 should be ~100 (HPI and HICP both 2015=100)"] = q("SELECT ROUND(MIN(real_house_price_index_2015),2), ROUND(MAX(real_house_price_index_2015),2) FROM recomputed WHERE year=2015")[0]
san["hicp_all 2015 annual average should be ~100"] = q("SELECT ROUND(MIN(hicp_all_index),2), ROUND(MAX(hicp_all_index),2) FROM recomputed WHERE year=2015")[0]
san["hpi 2015 should be exactly ~100"] = q("SELECT ROUND(MIN(house_price_index_2015),2), ROUND(MAX(house_price_index_2015),2) FROM recomputed WHERE year=2015")[0]
san["PTIR_LT_AVG long-run mean per country (should be ~100 by definition)"] = q("SELECT ROUND(MIN(a),1), ROUND(MAX(a),1) FROM (SELECT geo, AVG(value) a FROM s_price_to_income_vs_lt_avg GROUP BY geo)")[0]
report["sanity"] = san

(RES / "p5_recompute.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
for k, v in report.items():
    print(f"\n### {k}")
    if isinstance(v, dict):
        for kk, vv in v.items():
            print(f"  {kk}: {vv}")
    else:
        print(" ", v)
