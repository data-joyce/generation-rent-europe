"""QA Phase 3.3-3.7: row-count lineage, merge validation and pandas-pitfall checks.

Runs the notebook's own code cells (unmodified, from the sandbox copy) in a namespace, then re-plays each
transformation step one at a time to record the row count before/after, validating every merge with
pandas `validate=` and `indicator=True`. Reads only qa/sandbox/ (a copy of the raw data).

Usage: python -I qa/p3_lineage_and_pitfalls.py   -> prints and writes qa/results/p3_lineage.json
"""
import json
import os
import sys
import warnings
from functools import reduce
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SANDBOX_NB = ROOT / "qa/sandbox/python/generation_rent_01_clean.ipynb"
RES = ROOT / "qa/results"

# ---- run the notebook code in a namespace, recording any warnings ------------------------
nb = json.loads(SANDBOX_NB.read_text(encoding="utf-8"))
os.chdir(SANDBOX_NB.parent)
ns = {"display": lambda *a, **k: None}
caught = []
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    for c in nb["cells"]:
        if c["cell_type"] == "code":
            exec(compile("".join(c["source"]), "nb", "exec"), ns)
    caught = [f"{x.category.__name__}: {x.message}" for x in w]
print("Warnings while executing notebook code (all categories, 'always' filter):", caught or "none")

d, measures, FILES = ns["data"], ns["measures"], ns["FILES"]
EU27 = ns["EU27"]
lineage = []


def log(step, before, after, note):
    lineage.append({"step": step, "rows_before": before, "rows_after": after, "change": after - before, "explanation": note})


# ---- 1. raw -> long (clean_eurostat) -------------------------------------------------------
for name, path in FILES.items():
    raw_rows = sum(1 for _ in open(path, encoding="utf-8")) - 1
    log(f"read+clean {name} -> long_{name}", raw_rows, len(d[name]),
        "clean_eurostat() only renames/splits columns; no row filter")

# ---- 2. pick() filters, one condition at a time ---------------------------------------------
PICKS = [
    ("hpi_a", "house_price_index_2015", dict(purchase="TOTAL", unit="I15_A_AVG")),
    ("net_earn", "net_earnings_eur", dict(estruct="NET", ecase="P1_NCH_AW100", currency="EUR")),
    ("net_earn", "net_earnings_pps", dict(estruct="NET", ecase="P1_NCH_AW100", currency="PPS")),
    ("ptir", "price_to_income_vs_lt_avg", dict(unit="PTIR_LT_AVG")),
    ("overburden", "overburden_total", dict(sex="T", rskpovth="TOTAL", age="TOTAL")),
    ("overburden", "overburden_18_24", dict(sex="T", rskpovth="TOTAL", age="Y18-24")),
    ("overburden", "overburden_25_29", dict(sex="T", rskpovth="TOTAL", age="Y25-29")),
    ("age_leave", "age_leaving_home", dict(sex="T")),
    ("with_parents", "pct_18_34_with_parents", dict(sex="T", age="Y18-34")),
]
pick_dupes = {}
for (src, name, flt), m in zip(PICKS, measures):
    sub = d[src]
    for col, val in flt.items():
        before = len(sub)
        sub = sub[sub[col] == val]
        log(f"pick {name}: {col}=={val}", before, len(sub), f"keep one {col} of {d[src][col].nunique()}")
    assert len(sub) == len(m), (name, len(sub), len(m))
    pick_dupes[name] = int(sub.duplicated(["geo", "time"]).sum())
    # any remaining dimension with >1 value would mean silent double counting
    dims_left = [c for c in sub.columns if c not in ("geo", "geo_label", "time", "value", "flag", "flag_label")
                 and not c.endswith("_label") and sub[c].nunique() > 1]
    if dims_left:
        print(f"!! {name}: dimensions still varying after filter: {dims_left}")
print("Duplicate geo-year after each pick (must be 0):", pick_dupes)

# ---- 3. HICP monthly -> annual ------------------------------------------------------------
hicp = d["hicp"]
h = hicp[(hicp.unit == "I15") & hicp.coicop18.isin(["CP041", "TOTAL"])].copy()
log("hicp: unit==I15 & coicop18 in (CP041, TOTAL)", len(hicp), len(h), "keep 2 of 10 categories, index unit only")
h["year"] = h["time"].str[:4]
g = h.groupby(["geo", "year", "coicop18"], dropna=False)["value"].agg(["mean", "count", "size"]).reset_index()
log("hicp: groupby geo-year-coicop (mean of months)", len(h), len(g), "monthly rows -> 1 row per geo-year-category")
nan_keys = int(h[["geo", "year", "coicop18"]].isna().any(axis=1).sum())
count_ne_size = int((g["count"] != g["size"]).sum())
full = g[g["count"] == 12]
log("hicp: keep years with 12 monthly values", len(g), len(full), "drops partial years (first year of each series, 2026)")
dropped_years = g[g["count"] != 12].groupby("year").size().to_dict()
pivot = full.pivot(index=["geo", "year"], columns="coicop18", values="mean")
log("hicp: pivot categories to columns", len(full), len(pivot), "2 categories -> 2 columns")
assert len(pivot) == len(ns["hicp_wide"])

# ---- 4. outer merges, validated -------------------------------------------------------------
frames = measures + [ns["hicp_wide"]]
names = [p[1] for p in PICKS] + ["hicp_wide"]
acc = frames[0]
merge_checks = []
for nm, f in zip(names[1:], frames[1:]):
    before = len(acc)
    m = acc.merge(f, on=["geo", "year"], how="outer", validate="one_to_one", indicator=True)
    ind = m["_merge"].value_counts().to_dict()
    merge_checks.append({"merge": f"outer + {nm}", "validate": "one_to_one OK", "left_rows": before, "right_rows": len(f),
                         "result_rows": len(m), "both": ind.get("both", 0), "left_only": ind.get("left_only", 0),
                         "right_only": ind.get("right_only", 0),
                         "expected_rows(left+right-both)": before + len(f) - ind.get("both", 0)})
    log(f"outer merge + {nm}", before, len(m), f"one_to_one validated; {ind.get('right_only', 0)} new geo-years added, 0 rows lost (outer)")
    acc = m.drop(columns="_merge")
before = len(acc)
dimc = ns["dim_country"][["geo", "country", "iso2", "is_eu27"]]
m = acc.merge(dimc, on="geo", how="left", validate="many_to_one", indicator=True)
ind = m["_merge"].value_counts().to_dict()
merge_checks.append({"merge": "left + dim_country", "validate": "many_to_one OK", "left_rows": before, "right_rows": len(dimc),
                     "result_rows": len(m), "both": ind.get("both", 0), "left_only (no country match)": ind.get("left_only", 0)})
log("left merge + dim_country", before, len(m), f"many_to_one validated; unmatched geos: {ind.get('left_only', 0)}")
acc = m.drop(columns="_merge")

geo_keep = acc["is_eu27"] | (acc["geo"] == "EU27_2020")
log("filter: EU27 countries + EU27_2020", len(acc), int(geo_keep.sum()),
    f"drops {acc.loc[~geo_keep, 'geo'].nunique()} non-EU / aggregate geos: {sorted(acc.loc[~geo_keep, 'geo'].unique())}")
acc2 = acc[geo_keep]
yr_keep = acc2["year"].between("2005", "2025")
yr_keep_int = acc2["year"].astype(int).between(2005, 2025)
log("filter: year 2005-2025 (string between)", len(acc2), int(yr_keep.sum()),
    f"drops years {sorted(acc2.loc[~yr_keep, 'year'].unique())[:3]}...{sorted(acc2.loc[~yr_keep, 'year'].unique())[-2:]}")
string_vs_int_between_equal = bool((yr_keep == yr_keep_int).all())
cy = ns["country_year"]
assert int(yr_keep.sum()) == len(cy)
log("final country_year", len(cy), len(cy), "derived column + column reorder; no row change")

# ---- 5. city_rent ----------------------------------------------------------------------------
cr = d["city_rents"]
rent = cr[cr.currency == "EUR"]
log("city_rents: currency==EUR", len(cr), len(rent), "drop NAC (national currency) duplicates")
rent2 = rent[rent.building == "FLAT1"].copy()
log("city_rents: building==FLAT1", len(rent), len(rent2), "keep 1-bedroom flats only")
rent2["country_geo"] = rent2["geo"].str.split("_").str[0]
rent2 = rent2.rename(columns={"geo": "city_geo", "time": "year"})
net_eur = measures[1].rename(columns={"geo": "country_geo"})
mm = rent2.merge(net_eur, on=["country_geo", "year"], how="left", validate="many_to_one", indicator=True)
unmatched = mm[mm["_merge"] == "left_only"]
log("city_rents: left merge net earnings (EUR) on country_geo+year", len(rent2), len(mm),
    f"many_to_one validated; {len(unmatched)} city-years without a national earnings value (kept, share = NaN)")
merge_checks.append({"merge": "city_rent left + net_earnings_eur", "validate": "many_to_one OK", "left_rows": len(rent2),
                     "right_rows": len(net_eur), "result_rows": len(mm), "left_only (no earnings)": len(unmatched),
                     "unmatched_by_country": unmatched.groupby("country_geo").size().to_dict()})
assert len(mm) == len(ns["city_rent"])

hm_long = hicp[hicp.geo.isin(EU27 + ["EU27_2020"])]
log("hicp_monthly: geo in EU27 + EU27_2020", len(hicp), len(hm_long), "all units and categories kept")
hm = ns["hicp_monthly"]
filled = int(hm[["index_2015", "annual_rate_pct"]].notna().sum().sum())
log("hicp_monthly: pivot unit (I15, RCH_A) to 2 columns", len(hm_long), len(hm),
    f"1 row per geo-category-month; filled value cells {filled:,} == long rows {len(hm_long):,}: {filled == len(hm_long)}")
dy = ns["dim_year"]
log("dim_year: one row per year", 0, len(dy), f"years {dy.year.min()}-{dy.year.max()} (span of all facts)")

# ---- 6. pitfalls --------------------------------------------------------------------------
pit = {}
pit["pandas_version"] = pd.__version__
pit["copy_on_write_default"] = "pandas >= 3.0: Copy-on-Write is always on, so chained assignment cannot silently modify a parent frame"
pit["warnings_captured"] = caught or "none"
pit["groupby_nan_keys_in_hicp"] = nan_keys
pit["hicp_months_with_NaN_value_inside_groups"] = count_ne_size
pit["hicp_partial_years_dropped_by_year"] = {k: v for k, v in sorted(dropped_years.items())}
pit["year_string_between_equals_int_between"] = string_vs_int_between_equal
pit["value_parse_coercions"] = {}
for name, path in FILES.items():
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    vcol = [c for c in raw.columns if c.startswith("OBS_VALUE")][0]
    nonblank = raw[vcol] != ""
    coerced = int((nonblank & d[name]["value"].isna()).sum())
    pit["value_parse_coercions"][name] = coerced          # non-blank text that became NaN
pit["dtypes_country_year"] = {c: str(t) for c, t in cy.dtypes.items()}
pit["dtypes_city_rent"] = {c: str(t) for c, t in ns["city_rent"].dtypes.items()}
# label consistency for dim_country: drop_duplicates('geo') keeps the first label it sees
labs = pd.concat([df[["geo", "geo_label"]] for k, df in d.items() if k != "city_rents"]).drop_duplicates()
pit["geo_codes_with_conflicting_labels"] = labs[labs.duplicated("geo", keep=False)].sort_values("geo").values.tolist()
dc = ns["dim_country"]
pit["dim_country_is_aggregate_true"] = sorted(dc.loc[dc.is_aggregate, "geo"])
agg_like = dc.geo.str.match(r"^(EU|EA|EEA)\d*(_\d{4})?$|^EU\d+$")      # any EU/EA/EEA grouping code
pit["dim_country_aggregates_missed_by_regex"] = sorted(dc.loc[agg_like & ~dc.is_aggregate, "geo"]) or "none"
pit["dim_country_iso2_not_2_letters (non-empty)"] = sorted(dc.loc[dc.iso2.notna() & (dc.iso2.str.len() != 2), "iso2"]) or "none"
pit["dim_country_aggregates_with_iso2"] = sorted(dc.loc[dc.is_aggregate & dc.iso2.notna(), "geo"]) or "none"
# 'percentages between 0 and 100' check in the notebook: does it include NaN-only columns silently?
pct_cols = ["overburden_total", "overburden_18_24", "overburden_25_29", "pct_18_34_with_parents"]
pit["notebook_check_inputs_non_null"] = {c: int(cy[c].notna().sum()) for c in pct_cols + ["age_leaving_home"]}
pit["rent_share_rounding"] = "rent_share_of_net_salary_pct rounded to 1 decimal in the CSV (precalculated)"
# float rounding: is real_house_price_index_2015 exactly HPI/HICP*100 with no rounding?
pit["real_hpi_max_abs_diff_vs_formula"] = float((cy["real_house_price_index_2015"] - cy["house_price_index_2015"] / cy["hicp_all_index"] * 100).abs().max())
# integer columns
pit["year_dtype"] = str(cy["year"].dtype)

out = {"lineage": lineage, "merge_checks": merge_checks, "pitfalls": pit}
(RES / "p3_lineage.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

print(f"\n{'step':72} {'before':>9} {'after':>9} {'change':>9}  explanation")
for r in lineage:
    print(f"{r['step'][:72]:72} {r['rows_before']:>9,} {r['rows_after']:>9,} {r['change']:>+9,}  {r['explanation'][:140]}")
print("\nMERGE CHECKS")
for mc in merge_checks:
    print(" ", mc)
print("\nPITFALLS")
for k, v in pit.items():
    print(f"  {k}: {v}")
