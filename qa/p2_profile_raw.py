"""QA Phase 2: raw data profiling of the 9 Eurostat source files.

Independent of the project's pipeline: uses only the Python standard library (csv, re, statistics),
NOT pandas, and never imports or calls the notebook's code. Read-only on datasets/.

Usage (from the project root):
    python -I qa/p2_profile_raw.py
Writes:
    qa/results/p2_profile.md     human-readable profile
    qa/results/p2_profile.json   machine-readable summary (used by the final report)
"""
import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
csv.field_size_limit(10_000_000)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "datasets"
RES = ROOT / "qa" / "results"
RES.mkdir(parents=True, exist_ok=True)

FILES = {
    "hpi_a": RAW / "eurostat-house-price-index" / "prc_hpi_a.csv",
    "hpi_q": RAW / "eurostat-house-price-index" / "prc_hpi_q.csv",
    "ptir": RAW / "eurostat-house-price-to-income" / "tipsho60.csv",
    "net_earn": RAW / "eurostat-net-earnings" / "earn_nt_net.csv",
    "city_rents": RAW / "eurostat-city-rents" / "prc_colc_rents.csv",
    "overburden": RAW / "eurostat-housing-cost-overburden" / "ilc_lvho07a.csv",
    "age_leave": RAW / "eurostat-age-leaving-home" / "yth_demo_030.csv",
    "with_parents": RAW / "eurostat-young-adults-living-with-parents" / "ilc_lvps08.csv",
    "hicp": RAW / "eurostat-hicp-housing-food" / "prc_hicp_minr.csv",
}
# Today's date for the "future period" check
TODAY_YEAR, TODAY_MONTH = 2026, 11
PLACEHOLDERS = {":", "-", "--", "N/A", "n/a", "NA", "na", "null", "NULL", "None", "NaN", "nan", "9999", "99999", "#N/A", "?"}
MOJIBAKE = re.compile(r"Ã.|â€|Â.|�")
CODE_LABEL = re.compile(r"^([^:]+): (.+)$")
TIME_FORMATS = {"annual": re.compile(r"^\d{4}$"), "quarterly": re.compile(r"^\d{4}-Q[1-4]$"),
                "monthly": re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")}
NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
META = ("STRUCTURE", "STRUCTURE_ID", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG", "CONF_STATUS")


def short(col):
    return col.split(":")[0].strip()


def period_index(t):
    """Convert a period string to an integer so gaps can be detected (annual/quarterly/monthly)."""
    if TIME_FORMATS["annual"].match(t):
        return int(t)
    if TIME_FORMATS["quarterly"].match(t):
        return int(t[:4]) * 4 + int(t[-1]) - 1
    if TIME_FORMATS["monthly"].match(t):
        return int(t[:4]) * 12 + int(t[5:7]) - 1
    return None


def is_future(t):
    y = int(t[:4])
    if "-Q" in t:
        return (y, (int(t[-1]) - 1) * 3 + 1) > (TODAY_YEAR, TODAY_MONTH)
    if len(t) == 7:
        return (y, int(t[5:7])) > (TODAY_YEAR, TODAY_MONTH)
    return y > TODAY_YEAR


def quantile(sorted_vals, q):
    if not sorted_vals:
        return None
    i = (len(sorted_vals) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (i - lo)


def profile(name, path):
    raw_bytes = path.read_bytes()
    enc = {
        "size_bytes": len(raw_bytes),
        "utf8_bom": raw_bytes.startswith(b"\xef\xbb\xbf"),
        "crlf_lines": raw_bytes.count(b"\r\n"),
        "lf_lines": raw_bytes.count(b"\n"),
    }
    try:
        text = raw_bytes.decode("utf-8")
        enc["valid_utf8"] = True
    except UnicodeDecodeError as e:
        enc["valid_utf8"] = False
        enc["utf8_error"] = str(e)
        text = raw_bytes.decode("utf-8", errors="replace")
    del raw_bytes
    non_ascii = Counter(ch for ch in text if ord(ch) > 127)
    enc["non_ascii_chars"] = "".join(sorted(non_ascii))
    enc["mojibake_hits"] = len(MOJIBAKE.findall(text))

    rows = list(csv.reader(text.splitlines()))
    del text
    header, body = rows[0], rows[1:]
    ncol = len(header)
    ragged = sum(1 for r in body if len(r) != ncol)
    cols = [short(c) for c in header]
    ci = {c: i for i, c in enumerate(cols)}
    dims = [c for c in cols if c not in META]          # freq + real dimensions + geo

    out = {"file": str(path.relative_to(ROOT)), "rows": len(body), "columns": ncol,
           "header": header, "ragged_rows": ragged, "encoding": enc}

    # ---- per-column profile -------------------------------------------------------------
    colprof = {}
    for c in cols:
        vals = [r[ci[c]] for r in body]
        cnt = Counter(vals)
        p = {
            "distinct": len(cnt),
            "blank": cnt.get("", 0),
            "whitespace_padded": sum(n for v, n in cnt.items() if v != v.strip()),
            "double_spaces": sum(n for v, n in cnt.items() if "  " in v),
            "placeholders": {v: n for v, n in cnt.items() if v.strip() in PLACEHOLDERS},
        }
        if c in dims or c in ("OBS_FLAG", "CONF_STATUS"):
            # code: label structure
            bad = {v: n for v, n in cnt.items() if v and not CODE_LABEL.match(v)}
            code_labels, label_codes = defaultdict(set), defaultdict(set)
            for v in cnt:
                m = CODE_LABEL.match(v)
                if m:
                    code_labels[m.group(1)].add(m.group(2))
                    label_codes[m.group(2)].add(m.group(1))
            lower = Counter(k.lower() for k in code_labels)
            p["not_code_label_format"] = dict(list(bad.items())[:5])
            p["codes"] = len(code_labels)
            p["codes_with_multiple_labels"] = {k: sorted(v) for k, v in code_labels.items() if len(v) > 1}
            p["labels_with_multiple_codes"] = {k: sorted(v) for k, v in label_codes.items() if len(v) > 1}
            p["case_collisions"] = [k for k, n in lower.items() if n > 1]
            p["values"] = dict(cnt.most_common()) if len(cnt) <= 60 else f"{len(cnt)} distinct (not listed)"
        colprof[c] = p
    out["column_profile"] = colprof

    # ---- types ----------------------------------------------------------------------------
    obs = [r[ci["OBS_VALUE"]] for r in body]
    nonblank = [v for v in obs if v != ""]
    not_number = Counter(v for v in nonblank if not NUMBER.match(v))
    out["obs_value"] = {
        "blank": len(obs) - len(nonblank),
        "non_numeric_nonblank": dict(not_number.most_common(10)),
        "with_comma": sum(1 for v in nonblank if "," in v),
        "with_currency_symbol": sum(1 for v in nonblank if re.search(r"[€$£%]", v)),
        "max_decimals": max((len(v.split(".")[1]) for v in nonblank if "." in v), default=0),
        "leading_zero_ints": sum(1 for v in nonblank if re.match(r"^-?0\d", v)),
    }

    # ---- duplicates -----------------------------------------------------------------------
    key_idx = [ci[c] for c in dims] + [ci["TIME_PERIOD"]]
    exact = len(body) - len({tuple(r) for r in body})
    keys = Counter(tuple(r[i] for i in key_idx) for r in body)
    out["duplicates"] = {"exact_duplicate_rows": exact,
                         "duplicate_keys": sum(n - 1 for n in keys.values() if n > 1),
                         "key_columns": [c for c in dims] + ["TIME_PERIOD"]}

    # ---- time ---------------------------------------------------------------------------
    times = Counter(r[ci["TIME_PERIOD"]] for r in body)
    fmt = Counter(next((k for k, rx in TIME_FORMATS.items() if rx.match(t)), "UNPARSEABLE") for t in times.elements())
    series = defaultdict(list)
    sidx = [ci[c] for c in dims]
    for r in body:
        series[tuple(r[i] for i in sidx)].append((period_index(r[ci["TIME_PERIOD"]]), r[ci["OBS_VALUE"]]))
    row_gaps = blank_inside = 0
    for pts in series.values():
        idx = sorted(p for p, _ in pts if p is not None)
        if idx and idx[-1] - idx[0] + 1 != len(set(idx)):
            row_gaps += 1
        # blank values strictly between the first and last non-blank observation
        filled = sorted(p for p, v in pts if v != "" and p is not None)
        if filled:
            blank_inside += sum(1 for p, v in pts if v == "" and filled[0] < p < filled[-1])
    out["time"] = {
        "formats": dict(fmt), "min": min(times), "max": max(times), "distinct_periods": len(times),
        "future_periods": sorted(t for t in times if is_future(t)),
        "series": len(series),
        "series_with_missing_period_rows": row_gaps,
        "blank_values_inside_series_range": blank_inside,
        "rows_per_period_last5": {t: times[t] for t in sorted(times)[-5:]},
    }

    # ---- numeric distribution per unit (or per currency) --------------------------------
    unit_col = "unit" if "unit" in ci else ("currency" if "currency" in ci else None)
    by_unit = defaultdict(list)
    for r in body:
        v = r[ci["OBS_VALUE"]]
        if NUMBER.match(v):
            by_unit[r[ci[unit_col]].split(":")[0] if unit_col else "ALL"].append(
                (float(v), r[ci["geo"]].split(":")[0], r[ci["TIME_PERIOD"]],
                 "|".join(r[i].split(":")[0] for i in sidx if cols[i] not in ("freq", "geo", unit_col))))
    dist = {}
    for u, pts in sorted(by_unit.items()):
        vals = sorted(p[0] for p in pts)
        q1, q3 = quantile(vals, 0.25), quantile(vals, 0.75)
        iqr = q3 - q1
        lo_f, hi_f = q1 - 3 * iqr, q3 + 3 * iqr
        srt = sorted(pts)
        dist[u] = {
            "n": len(vals), "min": vals[0], "p01": quantile(vals, 0.01), "median": statistics.median(vals),
            "mean": round(statistics.fmean(vals), 3), "p99": quantile(vals, 0.99), "max": vals[-1],
            "zeros": sum(1 for v in vals if v == 0), "negatives": sum(1 for v in vals if v < 0),
            "outliers_3iqr": sum(1 for v in vals if v < lo_f or v > hi_f),
            "lowest3": [f"{v} {g} {t} {d}" for v, g, t, d in srt[:3]],
            "highest3": [f"{v} {g} {t} {d}" for v, g, t, d in srt[-3:]],
        }
    out["distribution_by_" + (unit_col or "all")] = dist

    # ---- impossible values (domain rules) -----------------------------------------------
    imp = {}
    for u, pts in by_unit.items():
        if u == "PC":
            imp["PC outside 0-100"] = [f"{v} {g} {t}" for v, g, t, _ in pts if v < 0 or v > 100][:10]
        if u.startswith("I") or u.startswith("PTIR"):
            imp[f"{u} index <= 0"] = [f"{v} {g} {t}" for v, g, t, _ in pts if v <= 0][:10]
    if name == "age_leave":
        imp["age outside 15-45"] = [f"{v} {g} {t}" for p in by_unit.values() for v, g, t, _ in p if not 15 <= v <= 45][:10]
    if name in ("city_rents", "net_earn"):
        imp["amount <= 0 (EUR/NAC/PPS)"] = len([1 for u, p in by_unit.items() for v, *_ in p if v <= 0])
    out["impossible_values"] = imp

    # ---- flags vs values ----------------------------------------------------------------
    fl = Counter((r[ci["OBS_FLAG"]] or "(none)", "blank" if r[ci["OBS_VALUE"]] == "" else "value") for r in body)
    out["flag_by_value_presence"] = {f"{f} / {v}": n for (f, v), n in fl.most_common()}
    cs = Counter(r[ci["CONF_STATUS"]] or "(none)" for r in body)
    out["conf_status"] = dict(cs)
    return out


def to_md(name, p):
    L = [f"## {name}  (`{p['file']}`)", "",
         f"- Rows: **{p['rows']:,}** · Columns: **{p['columns']}** · Ragged rows: {p['ragged_rows']}",
         f"- Encoding: {p['encoding']}",
         f"- Duplicates: {p['duplicates']}",
         f"- OBS_VALUE text check: {p['obs_value']}",
         f"- Time: {p['time']}",
         f"- Flags × value presence: {p['flag_by_value_presence']}",
         f"- CONF_STATUS: {p['conf_status']}",
         f"- Impossible-value rules: {p['impossible_values']}", "",
         "| Column | Distinct | Blank | Padded | Placeholders | Codes w/ >1 label | Labels w/ >1 code | Case collisions | Not 'code: label' |",
         "|---|---|---|---|---|---|---|---|---|"]
    for c, cp in p["column_profile"].items():
        L.append(f"| {c} | {cp['distinct']} | {cp['blank']} | {cp['whitespace_padded']} | {cp['placeholders'] or ''} | "
                 f"{cp.get('codes_with_multiple_labels', '') or ''} | {cp.get('labels_with_multiple_codes', '') or ''} | "
                 f"{cp.get('case_collisions', '') or ''} | {cp.get('not_code_label_format', '') or ''} |")
    dkey = next(k for k in p if k.startswith("distribution_by_"))
    L += ["", f"**Numeric distribution ({dkey})**", "",
          "| Unit | n | min | p01 | median | mean | p99 | max | zeros | neg | outliers(3×IQR) | lowest 3 | highest 3 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for u, d in p[dkey].items():
        L.append(f"| {u} | {d['n']} | {d['min']} | {d['p01']:.2f} | {d['median']} | {d['mean']} | {d['p99']:.2f} | {d['max']} | "
                 f"{d['zeros']} | {d['negatives']} | {d['outliers_3iqr']} | {'<br>'.join(d['lowest3'])} | {'<br>'.join(d['highest3'])} |")
    L += ["", "<details><summary>Distinct values of categorical columns</summary>", ""]
    for c, cp in p["column_profile"].items():
        if isinstance(cp.get("values"), dict) and c not in ("STRUCTURE",):
            L.append(f"- **{c}**: " + "; ".join(f"`{v}` ({n})" for v, n in cp["values"].items()))
        elif "values" in cp:
            L.append(f"- **{c}**: {cp['values']}")
    L += ["", "</details>", ""]
    return "\n".join(L)


if __name__ == "__main__":
    results = {}
    md = ["# QA Phase 2 · Raw data profile", "", "Generated by `qa/p2_profile_raw.py` (standard library only, read-only).", ""]
    for name, path in FILES.items():
        print(f"profiling {name} ...", flush=True)
        results[name] = profile(name, path)
        md.append(to_md(name, results[name]))
    (RES / "p2_profile.json").write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (RES / "p2_profile.md").write_text("\n".join(md), encoding="utf-8")
    # Compact console summary
    print(f"\n{'file':13} {'rows':>9} {'cols':>4} {'ragged':>6} {'bom':>5} {'utf8':>5} {'mojib':>5} "
          f"{'exdup':>5} {'keydup':>6} {'blankV':>7} {'nonnum':>6} {'comma':>5} {'time fmt':>22} {'min':>8} {'max':>8} {'future':>6} {'gapSer':>6}")
    for n, p in results.items():
        print(f"{n:13} {p['rows']:>9,} {p['columns']:>4} {p['ragged_rows']:>6} {str(p['encoding']['utf8_bom']):>5} "
              f"{str(p['encoding']['valid_utf8']):>5} {p['encoding']['mojibake_hits']:>5} "
              f"{p['duplicates']['exact_duplicate_rows']:>5} {p['duplicates']['duplicate_keys']:>6} {p['obs_value']['blank']:>7,} "
              f"{len(p['obs_value']['non_numeric_nonblank']):>6} {p['obs_value']['with_comma']:>5} {str(p['time']['formats']):>22} "
              f"{p['time']['min']:>8} {p['time']['max']:>8} {len(p['time']['future_periods']):>6} {p['time']['series_with_missing_period_rows']:>6}")
    print("\nWrote qa/results/p2_profile.md and qa/results/p2_profile.json")
