"""QA Phase 6: Power BI readiness of the final tables (standard library csv + re; read-only).

Checks: primary keys unique & non-null, foreign keys (orphans), per-column type consistency, date columns,
export format (encoding/BOM, delimiter, decimal separator, index columns, column names), additivity of measures.
Usage: python -I qa/p6_powerbi_readiness.py -> prints and writes qa/results/p6_powerbi.json
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "pipeline/clean/generation-rent"
RES = ROOT / "qa/results"

TABLES = {
    "country_year": ["geo", "year"],
    "city_rent": ["city_geo", "year"],
    "dim_country": ["geo"],
    "dim_year": ["year"],
    "hicp_monthly": ["geo", "coicop18", "month"],
}
FKS = [("country_year", "geo", "dim_country", "geo"), ("city_rent", "country_geo", "dim_country", "geo"),
       ("hicp_monthly", "geo", "dim_country", "geo"),
       ("country_year", "year", "dim_year", "year"), ("city_rent", "year", "dim_year", "year"),
       ("hicp_monthly", "year", "dim_year", "year")]
NUM = re.compile(r"^-?\d+(\.\d+)?([eE]-?\d+)?$")
INT = re.compile(r"^-?\d+$")
out = {}


def load(name):
    raw = (CLEAN / f"{name}.csv").read_bytes()
    with open(CLEAN / f"{name}.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    return raw, rows[0], rows[1:]


data = {}
for t, pk in TABLES.items():
    raw, hdr, body = load(t)
    data[t] = (hdr, body)
    idx = [hdr.index(k) for k in pk]
    keys = [tuple(r[i] for i in idx) for r in body]
    types = {}
    for j, c in enumerate(hdr):
        vals = [r[j] for r in body]
        nonblank = [v for v in vals if v != ""]
        kind = ("empty" if not nonblank else
                "integer" if all(INT.match(v) for v in nonblank) else
                "decimal" if all(NUM.match(v) for v in nonblank) else
                "boolean" if set(nonblank) <= {"True", "False"} else
                "year-month text" if all(re.match(r"^\d{4}-\d{2}$", v) for v in nonblank) else
                "ISO date (yyyy-mm-dd)" if all(re.match(r"^\d{4}-\d{2}-\d{2}$", v) for v in nonblank) else "text")
        mixed = kind == "text" and any(NUM.match(v) for v in nonblank) and not all(NUM.match(v) for v in nonblank)
        types[c] = {"inferred": kind, "blanks": len(vals) - len(nonblank), "distinct": len(set(vals)),
                    "mixed_numeric_and_text": mixed, "leading_or_trailing_space": sum(1 for v in nonblank if v != v.strip())}
    out[t] = {
        "rows": len(body), "columns": len(hdr),
        "primary_key": pk,
        "pk_duplicates": sum(n - 1 for n in Counter(keys).values() if n > 1),
        "pk_nulls": sum(1 for k in keys if "" in k),
        "format": {
            "utf8_bom": raw.startswith(b"\xef\xbb\xbf"), "valid_utf8": bool(raw.decode("utf-8")),
            "line_endings": "CRLF" if b"\r\n" in raw[:10000] else "LF",
            "delimiter": ",", "semicolons_in_file": raw.count(b";"),
            "decimal_comma_values": sum(1 for r in body for v in r if re.match(r"^-?\d+,\d+$", v)),
            "index_like_columns": [c for c in hdr if c == "" or c.lower().startswith("unnamed") or c == "index"],
            "bad_column_names": [c for c in hdr if not re.match(r"^[a-z][a-z0-9_]*$", c)],
            "non_ascii_in_data": "".join(sorted({ch for r in body for v in r for ch in v if ord(ch) > 127})),
        },
        "column_types": types,
    }
    if t == "hicp_monthly":
        out[t]["has_unit_column (should be False after pivot)"] = "unit" in hdr
        tm = hdr.index("month")
        out[t]["time_range"] = (min(r[tm] for r in body), max(r[tm] for r in body))
        out[t]["rows_in_latest_month"] = Counter(r[tm] for r in body)[max(r[tm] for r in body)]

fk = {}
for ft, fc, dt, dc in FKS:
    fh, fb = data[ft]
    dh, db = data[dt]
    dvals = {r[dh.index(dc)] for r in db}
    vals = [r[fh.index(fc)] for r in fb]
    orphans = Counter(v for v in vals if v not in dvals)
    fk[f"{ft}.{fc} -> {dt}.{dc}"] = {"rows": len(vals), "orphans": sum(orphans.values()), "orphan_values": dict(orphans)}
out["foreign_keys"] = fk

# dimension usage: which dim rows are never used by a fact (useful for slicers)
dh, db = data["dim_country"]
used = {r[data["country_year"][0].index("geo")] for r in data["country_year"][1]}
out["dim_country_rows_not_in_country_year"] = sorted(r[0] for r in db if r[0] not in used)
iso = dh.index("iso2")
out["dim_country_iso2_non_iso"] = sorted({r[iso] for r in db if r[iso] != "" and not re.match(r"^[A-Z]{2}$", r[iso])})
agg = dh.index("is_aggregate")
out["dim_country_iso2_blank_only_for_aggregates"] = all((r[iso] == "") == (r[agg] == "True") for r in db)
# year coverage per fact (for the calendar/year table)
for t in ("country_year", "city_rent", "hicp_monthly"):
    h, b = data[t]
    ys = sorted({int(r[h.index("year")]) for r in b})
    out[t]["year_range"] = (ys[0], ys[-1])
    out[t]["year_gaps"] = sorted(set(range(ys[0], ys[-1] + 1)) - set(ys))
# country/iso2 duplicated in fact (denormalised) - consistent with dim?
h, b = data["country_year"]
dmap = {r[0]: (r[dh.index("country")], r[iso]) for r in db}
out["country_year_country_iso2_consistent_with_dim"] = all(dmap[r[0]] == (r[h.index("country")], r[h.index("iso2")]) for r in b)

(RES / "p6_powerbi.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
for t in TABLES:
    o = out[t]
    print(f"\n### {t}: {o['rows']} rows x {o['columns']} cols | PK {o['primary_key']} dupes={o['pk_duplicates']} nulls={o['pk_nulls']}")
    print("   format:", o["format"])
    for c, ty in o["column_types"].items():
        print(f"   {c:34} {ty}")
    for k in ("has_unit_column (should be False after pivot)", "time_range", "rows_in_latest_month", "year_range", "year_gaps"):
        if k in o:
            print(f"   {k}: {o[k]}")
print("\n### foreign keys")
for k, v in fk.items():
    print("  ", k, v)
for k in ("dim_country_rows_not_in_country_year", "dim_country_iso2_non_iso", "dim_country_iso2_blank_only_for_aggregates",
          "country_year_country_iso2_consistent_with_dim"):
    print(f"\n{k}: {out[k]}")
