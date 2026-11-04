"""QA Phase 8 (after the approved fixes of 2026-11-04): regression check, old outputs vs new outputs.

qa/baseline_before_fixes/ holds copies of the 4 changed CSVs and the SHA-256 of all 13 CSVs as they were BEFORE the
fixes, plus the SQL runner's printed output. This script proves that the fixes changed ONLY what they were meant to:
  - long_*.csv            byte-identical (SHA-256)
  - country_year          only iso2 of EU27_2020 blanked (aggregates have no ISO code)
  - city_rent             one new column is_capital (= city_geo ends with _CAP); every other cell identical
  - dim_country           EEA now is_aggregate; iso2 blank for aggregates only; new column in_country_year
  - hicp_monthly          long -> wide: every old (geo, category, month, unit) value and flag is in the new table, and
                          the new table holds nothing else
  - SQL output            lists which query results changed (to be read against the fix list in QA_REPORT.md)
Usage: python -I qa/p8_fix_regression.py -> prints, writes qa/results/p8_regression.json and p8_sql_output_diff.txt
"""
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
OLD = ROOT / "qa/baseline_before_fixes"
NEW = ROOT / "pipeline/clean/generation-rent"
RES = ROOT / "qa/results"
out = {}


def read(p):  # everything as text, blanks as "", so nothing is re-typed or re-rounded
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def cell_diffs(a, b, key):
    """Return {column: [(key, old, new), ...]} for shared columns of two frames aligned on key."""
    m = a.merge(b, on=key, how="outer", suffixes=("_old", "_new"), indicator=True)
    res = {"rows_old": len(a), "rows_new": len(b), "keys_only_old": int((m._merge == "left_only").sum()),
           "keys_only_new": int((m._merge == "right_only").sum())}
    both = m[m._merge == "both"]
    ch = {}
    for c in [c for c in a.columns if c in b.columns and c not in key]:
        d = both[both[f"{c}_old"] != both[f"{c}_new"]]
        if len(d):
            ch[c] = [tuple(r) for r in d[key + [f"{c}_old", f"{c}_new"]].values.tolist()]
    res["changed_cells_by_column"] = {c: len(v) for c, v in ch.items()}
    res["columns_added"] = [c for c in b.columns if c not in a.columns]
    res["columns_removed"] = [c for c in a.columns if c not in b.columns]
    return res, ch, both


# 1. long tables untouched ---------------------------------------------------------------------------
before = dict(reversed(l.split()) for l in (OLD / "sha256_before.txt").read_text().splitlines() if l.strip())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest().upper()  # noqa: E731
out["long_tables_identical"] = {n: sha(NEW / n) == h for n, h in before.items() if n.startswith("long_")}

# 2. country_year ------------------------------------------------------------------------------------
r, ch, _ = cell_diffs(read(OLD / "country_year.csv"), read(NEW / "country_year.csv"), ["geo", "year"])
r["only_iso2_changed"] = set(ch) <= {"iso2"}
r["iso2_changes_all_EU27_2020_to_blank"] = all(g == "EU27_2020" and o == "EU27_2020" and n == "" for g, _, o, n in ch.get("iso2", []))
out["country_year"] = r

# 3. city_rent ---------------------------------------------------------------------------------------
new_cr = read(NEW / "city_rent.csv")
r, ch, _ = cell_diffs(read(OLD / "city_rent.csv"), new_cr, ["city_geo", "year"])
r["no_existing_cell_changed"] = not ch
r["is_capital_equals_CAP_suffix"] = bool((new_cr.is_capital == new_cr.city_geo.str.endswith("_CAP").astype(str)).all())
out["city_rent"] = r

# 4. dim_country -------------------------------------------------------------------------------------
new_dc = read(NEW / "dim_country.csv")
r, ch, both = cell_diffs(read(OLD / "dim_country.csv"), new_dc, ["geo"])
r["changes"] = {c: v for c, v in ch.items()}
r["is_aggregate_change_is_only_EEA_False_to_True"] = ch.get("is_aggregate") == [("EEA", "False", "True")]
r["iso2_changes_only_on_aggregates_to_blank"] = all(n == "" and new_dc.set_index("geo").at[g, "is_aggregate"] == "True"
                                                     for g, o, n in ch.get("iso2", []))
r["unchanged_columns_ok"] = set(ch) <= {"is_aggregate", "iso2"}
out["dim_country"] = r

# 5. hicp_monthly long -> wide -----------------------------------------------------------------------
old_h = read(OLD / "hicp_monthly.csv")
new_h = read(NEW / "hicp_monthly.csv")
UNIT = {"I15": ("index_2015", "index_2015_flag"), "RCH_A": ("annual_rate_pct", "annual_rate_pct_flag")}
long_from_new = pd.concat([new_h.assign(unit=u, value=new_h[v], flag=new_h[f])[["geo", "coicop18", "coicop18_label", "month", "unit", "value", "flag"]]
                           for u, (v, f) in UNIT.items()])
long_from_new = long_from_new[(long_from_new.value != "") | (long_from_new.flag != "")]  # a cell that existed in the long table
old_k = old_h.rename(columns={"time": "month"})[["geo", "coicop18", "coicop18_label", "month", "unit", "value", "flag"]]
m = old_k.merge(long_from_new, on=["geo", "coicop18", "month", "unit"], how="outer", suffixes=("_old", "_new"), indicator=True)
both = m[m._merge == "both"]
# the old table wrote values as floats (e.g. 68.12); the new one too, but compare numerically to be safe about 100 vs 100.0
num_eq = pd.to_numeric(both.value_old, errors="coerce").eq(pd.to_numeric(both.value_new, errors="coerce")) | ((both.value_old == "") & (both.value_new == ""))
out["hicp_monthly"] = {
    "old_long_rows": len(old_h), "new_wide_rows": len(new_h), "filled_cells_in_new": len(long_from_new),
    "old_units": sorted(old_h.unit.unique()),
    "cells_only_in_old": int((m._merge == "left_only").sum()), "cells_only_in_new": int((m._merge == "right_only").sum()),
    "values_equal": int(num_eq.sum()), "values_text_identical": int((both.value_old == both.value_new).sum()),
    "flags_equal": int((both.flag_old == both.flag_new).sum()), "labels_equal": int((both.coicop18_label_old == both.coicop18_label_new).sum()),
    "compared": len(both),
}

# 6. SQL output: which query blocks changed ----------------------------------------------------------
def blocks(txt):
    """Split the runner's printout into {(file, query comment): text}."""
    res, f, title = {}, "?", "(top)"
    lines = txt.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("====") and i + 1 < len(lines) and lines[i + 1].endswith(".sql"):
            continue
        if l.endswith(".sql") and not l.startswith("--"):
            f, title = l.strip(), "(top)"
            continue
        if l.startswith("-- "):
            title = l[3:].strip()
            continue
        res.setdefault((f, title), []).append(l)
    return {k: "\n".join(v) for k, v in res.items()}


old_txt = (OLD / "run_sql_output_before.txt").read_text(encoding="utf-8")
new_txt = (RES / "run_sql_after_fixes.txt").read_text(encoding="utf-8")
bo, bn = blocks(old_txt), blocks(new_txt)
out["sql_blocks"] = {"old": len(bo), "new": len(bn),
                     "changed": [f"{f} | {t}" for (f, t) in bn if (f, t) in bo and bo[(f, t)] != bn[(f, t)]],
                     "only_new_titles": [f"{f} | {t}" for (f, t) in bn if (f, t) not in bo],
                     "only_old_titles": [f"{f} | {t}" for (f, t) in bo if (f, t) not in bn],
                     "unchanged": sum(1 for k in bn if k in bo and bo[k] == bn[k])}
diff = difflib.unified_diff(old_txt.splitlines(), new_txt.splitlines(), "before_fixes", "after_fixes", lineterm="", n=1)
(RES / "p8_sql_output_diff.txt").write_text("\n".join(diff), encoding="utf-8")

(RES / "p8_regression.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
for k, v in out.items():
    print(f"\n### {k}")
    if isinstance(v, dict):
        for kk, vv in v.items():
            print(f"  {kk}: {vv}")
