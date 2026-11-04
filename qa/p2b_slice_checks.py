"""QA Phase 2b: profile the exact raw slices that feed the dashboard (standard library only, read-only).

For each measure used in country_year / city_rent, take the raw rows matching the documented filter
and report: rows, EU27 coverage (which countries have no value at all), year range, blanks, flags,
plus targeted anomaly checks found in Phase 2.

Usage: python -I qa/p2b_slice_checks.py   -> prints and writes qa/results/p2b_slices.json
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "datasets"
RES = ROOT / "qa" / "results"

EU27 = sorted("AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK".split())


def load(rel):
    with open(RAW / rel, encoding="utf-8", newline="") as f:
        rdr = csv.reader(f)
        hdr = [h.split(":")[0].strip() for h in next(rdr)]
        for r in rdr:
            d = dict(zip(hdr, r))
            yield {k: (v.split(": ", 1)[0] if k not in ("TIME_PERIOD", "OBS_VALUE") else v) for k, v in d.items()}


SLICES = {
    "house_price_index_2015": ("eurostat-house-price-index/prc_hpi_a.csv", {"purchase": "TOTAL", "unit": "I15_A_AVG"}),
    "net_earnings_eur": ("eurostat-net-earnings/earn_nt_net.csv", {"estruct": "NET", "ecase": "P1_NCH_AW100", "currency": "EUR"}),
    "net_earnings_pps": ("eurostat-net-earnings/earn_nt_net.csv", {"estruct": "NET", "ecase": "P1_NCH_AW100", "currency": "PPS"}),
    "price_to_income_vs_lt_avg": ("eurostat-house-price-to-income/tipsho60.csv", {"unit": "PTIR_LT_AVG"}),
    "overburden_total": ("eurostat-housing-cost-overburden/ilc_lvho07a.csv", {"sex": "T", "rskpovth": "TOTAL", "age": "TOTAL"}),
    "overburden_18_24": ("eurostat-housing-cost-overburden/ilc_lvho07a.csv", {"sex": "T", "rskpovth": "TOTAL", "age": "Y18-24"}),
    "overburden_25_29": ("eurostat-housing-cost-overburden/ilc_lvho07a.csv", {"sex": "T", "rskpovth": "TOTAL", "age": "Y25-29"}),
    "age_leaving_home": ("eurostat-age-leaving-home/yth_demo_030.csv", {"sex": "T"}),
    "pct_18_34_with_parents": ("eurostat-young-adults-living-with-parents/ilc_lvps08.csv", {"sex": "T", "age": "Y18-34"}),
    "hicp_rent_monthly(I15,CP041)": ("eurostat-hicp-housing-food/prc_hicp_minr.csv", {"unit": "I15", "coicop18": "CP041"}),
    "hicp_all_monthly(I15,TOTAL)": ("eurostat-hicp-housing-food/prc_hicp_minr.csv", {"unit": "I15", "coicop18": "TOTAL"}),
    "city_rent_1bed_eur": ("eurostat-city-rents/prc_colc_rents.csv", {"building": "FLAT1", "currency": "EUR"}),
}

cache = {}
report = {}
for name, (rel, flt) in SLICES.items():
    if rel not in cache:
        cache[rel] = list(load(rel))
    rows = [r for r in cache[rel] if all(r[k] == v for k, v in flt.items())]
    in_scope = [r for r in rows if (r["geo"] in EU27 or r["geo"] == "EU27_2020")]
    years = sorted({r["TIME_PERIOD"][:4] for r in in_scope})
    with_val = {r["geo"] for r in in_scope if r["OBS_VALUE"] != ""}
    keys = Counter((r["geo"], r["TIME_PERIOD"]) for r in rows)
    per_geo_years = defaultdict(list)
    for r in in_scope:
        if r["OBS_VALUE"] != "":
            per_geo_years[r["geo"]].append(r["TIME_PERIOD"][:4])
    rep = {
        "filter": flt, "rows_all_geos": len(rows), "rows_eu27_plus_avg": len(in_scope),
        "duplicate_geo_period": sum(n - 1 for n in keys.values() if n > 1),
        "year_range": f"{years[0]}-{years[-1]}" if years else None,
        "eu27_missing_entirely": [g for g in EU27 if g not in with_val],
        "eu27_avg_present": "EU27_2020" in with_val,
        "blank_values": sum(1 for r in in_scope if r["OBS_VALUE"] == ""),
        "flags": dict(Counter(r["OBS_FLAG"].split(":")[0] or "-" for r in in_scope)),
        "first_year_by_geo_min_max": (min((min(v) for v in per_geo_years.values()), default=None),
                                      max((min(v) for v in per_geo_years.values()), default=None)),
        "last_year_by_geo": dict(Counter(max(v) for v in per_geo_years.values())),
    }
    report[name] = rep

# ---- Targeted anomaly checks ---------------------------------------------------------------
ne = cache["eurostat-net-earnings/earn_nt_net.csv"]
net = [r for r in ne if r["estruct"] == "NET" and r["ecase"] == "P1_NCH_AW100"]
anom = {}
anom["net_P1_NCH_AW100_nonpositive"] = [f"{r['geo']} {r['TIME_PERIOD']} {r['currency']} {r['OBS_VALUE']}"
                                       for r in net if float(r["OBS_VALUE"]) <= 0]
anom["TR_EUR_net_2000_2006"] = [f"{r['TIME_PERIOD']}: {r['OBS_VALUE']}" for r in net
                                if r["geo"] == "TR" and r["currency"] == "EUR" and r["TIME_PERIOD"] <= "2006"]
# year-over-year jumps in the EU27 net EUR series
s = defaultdict(dict)
for r in net:
    if r["currency"] == "EUR" and r["geo"] in EU27:
        s[r["geo"]][int(r["TIME_PERIOD"])] = (float(r["OBS_VALUE"]), r["OBS_FLAG"].split(":")[0])
jumps = []
for g, ser in s.items():
    for y in sorted(ser):
        if y - 1 in ser and ser[y - 1][0] > 0:
            ch = ser[y][0] / ser[y - 1][0] - 1
            if abs(ch) > 0.20:
                jumps.append(f"{g} {y-1}->{y}: {ch:+.1%} flag={ser[y][1] or '-'}")
anom["net_eur_EU27_yoy_over_20pct"] = jumps
b2024 = [g for g in EU27 if 2024 in s[g] and s[g][2024][1] == "b"]
anom["net_eur_2024_flag_b_count"] = f"{len(b2024)} of {sum(1 for g in EU27 if 2024 in s[g])} EU27 countries with a 2024 value"
anom["net_eur_EU27_countries_with_gaps"] = {g: sorted(set(range(min(ser), max(ser) + 1)) - set(ser))
                                            for g, ser in s.items() if len(ser) != max(ser) - min(ser) + 1}

ob = cache["eurostat-housing-cost-overburden/ilc_lvho07a.csv"]
anom["overburden_used_slices_blank"] = [f"{r['geo']} {r['TIME_PERIOD']} age={r['age']} flag={r['OBS_FLAG']}" for r in ob
                                        if r["sex"] == "T" and r["rskpovth"] == "TOTAL" and r["age"] in ("TOTAL", "Y18-24", "Y25-29")
                                        and r["OBS_VALUE"] == "" and (r["geo"] in EU27 or r["geo"] == "EU27_2020")]
anom["overburden_used_slices_flag_u"] = Counter(r["age"] for r in ob
                                               if r["sex"] == "T" and r["rskpovth"] == "TOTAL" and r["age"] in ("TOTAL", "Y18-24", "Y25-29")
                                               and "u" in r["OBS_FLAG"].split(":")[0] and (r["geo"] in EU27 or r["geo"] == "EU27_2020"))

hpi = cache["eurostat-house-price-index/prc_hpi_a.csv"]
anom["hpi_a_geos_present"] = sorted({r["geo"] for r in hpi})
anom["hpi_a_blank_TOTAL_I15_EU27"] = [f"{r['geo']} {r['TIME_PERIOD']}" for r in hpi if r["purchase"] == "TOTAL"
                                      and r["unit"] == "I15_A_AVG" and r["OBS_VALUE"] == "" and r["geo"] in EU27]

hc = cache["eurostat-hicp-housing-food/prc_hicp_minr.csv"]
anom["hicp_rows_by_month_2026"] = dict(sorted(Counter(r["TIME_PERIOD"] for r in hc if r["TIME_PERIOD"].startswith("2026")).items()))
anom["hicp_2026_10_geos"] = sorted({r["geo"] for r in hc if r["TIME_PERIOD"] == "2026-10"})
hicp_series = defaultdict(set)
for r in hc:
    hicp_series[(r["unit"], r["coicop18"], r["geo"])].add(r["TIME_PERIOD"])
anom["hicp_series_with_missing_months"] = []
for k, ts in hicp_series.items():
    idx = sorted(int(t[:4]) * 12 + int(t[5:]) - 1 for t in ts)
    if idx[-1] - idx[0] + 1 != len(idx):
        missing = sorted(set(range(idx[0], idx[-1] + 1)) - set(idx))
        anom["hicp_series_with_missing_months"].append(f"{k}: {len(missing)} missing, e.g. {missing[0]//12}-{missing[0]%12+1:02d}")

cr = cache["eurostat-city-rents/prc_colc_rents.csv"]
anom["city_rent_geo_codes"] = sorted({r["geo"] for r in cr})
anom["city_rent_non_capital_codes"] = sorted({r["geo"] for r in cr if not r["geo"].endswith("_CAP")})
anom["EU27_without_CAP_code"] = [g for g in EU27 if f"{g}_CAP" not in {r["geo"] for r in cr}]
report["_anomalies"] = anom

(RES / "p2b_slices.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
for k, v in report.items():
    print(f"\n### {k}")
    for kk, vv in v.items():
        print(f"  {kk}: {vv}")
