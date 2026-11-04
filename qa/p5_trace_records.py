"""QA Phase 5.3: trace 10 randomly chosen records end to end (raw line -> long_*.csv line -> final table).

Standard library only (csv, random with a FIXED seed) so the selection is reproducible and independent of the pipeline.
One record per KPI so every dashboard measure is traced at least once.
Usage: python -I qa/p5_trace_records.py  -> prints and writes qa/results/p5_traces.json and p5_traces.md
"""
import csv
import json
import random
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "datasets"
CLEAN = ROOT / "pipeline/clean/generation-rent"
RES = ROOT / "qa/results"
SEED = 20261104
rng = random.Random(SEED)


def rows(path, enc="utf-8"):
    with open(path, encoding=enc, newline="") as f:
        rdr = csv.reader(f)
        hdr = next(rdr)
        for i, r in enumerate(rdr, start=2):          # line 1 = header
            yield i, dict(zip(hdr, r))


def raw_find(rel, conds):
    """Find the raw row whose code fields match conds; return (line number, row dict)."""
    out = []
    for ln, r in rows(RAW / rel):
        short = {k.split(":")[0].strip(): v for k, v in r.items()}
        if all(short[k].split(": ")[0] == v for k, v in conds.items()):
            out.append((ln, short))
    return out


def long_find(name, conds):
    return [(ln, r) for ln, r in rows(CLEAN / f"long_{name}.csv", "utf-8-sig") if all(r[k] == v for k, v in conds.items())]


final = list(rows(CLEAN / "country_year.csv", "utf-8-sig"))
city = list(rows(CLEAN / "city_rent.csv", "utf-8-sig"))

SPEC = [  # measure, raw file, long name, fixed filters
    ("house_price_index_2015", "eurostat-house-price-index/prc_hpi_a.csv", "hpi_a", {"purchase": "TOTAL", "unit": "I15_A_AVG"}),
    ("net_earnings_eur", "eurostat-net-earnings/earn_nt_net.csv", "net_earn", {"estruct": "NET", "ecase": "P1_NCH_AW100", "currency": "EUR"}),
    ("net_earnings_pps", "eurostat-net-earnings/earn_nt_net.csv", "net_earn", {"estruct": "NET", "ecase": "P1_NCH_AW100", "currency": "PPS"}),
    ("price_to_income_vs_lt_avg", "eurostat-house-price-to-income/tipsho60.csv", "ptir", {"unit": "PTIR_LT_AVG"}),
    ("overburden_18_24", "eurostat-housing-cost-overburden/ilc_lvho07a.csv", "overburden", {"sex": "T", "rskpovth": "TOTAL", "age": "Y18-24"}),
    ("age_leaving_home", "eurostat-age-leaving-home/yth_demo_030.csv", "age_leave", {"sex": "T"}),
    ("pct_18_34_with_parents", "eurostat-young-adults-living-with-parents/ilc_lvps08.csv", "with_parents", {"sex": "T", "age": "Y18-34"}),
]
traces = []
for i, (m, rel, lname, flt) in enumerate(SPEC, start=1):
    ln_f, rec = rng.choice([(ln, r) for ln, r in final if r[m] != ""])
    g, y = rec["geo"], rec["year"]
    raw = raw_find(rel, {**flt, "geo": g, "TIME_PERIOD": y})
    lng = long_find(lname, {**flt, "geo": g, "time": y})
    assert len(raw) == 1 and len(lng) == 1, (m, g, y, len(raw), len(lng))
    (rl, rr), (ll, lr) = raw[0], lng[0]
    match = float(rr["OBS_VALUE"]) == float(lr["value"]) == float(rec[m]) and (rr["OBS_FLAG"].split(": ")[0] or "") == (lr["flag"] or "") == rec[f"{m}_flag"]
    traces.append({"#": i, "measure": m, "geo": g, "year": y,
                   "1 raw": f"{rel} line {rl}: OBS_VALUE='{rr['OBS_VALUE']}' OBS_FLAG='{rr['OBS_FLAG']}'",
                   "2 long": f"long_{lname}.csv line {ll}: value={lr['value']} flag={lr['flag'] or '-'}",
                   "3 final": f"country_year.csv line {ln_f}: {m}={rec[m]} flag={rec[m + '_flag'] or '-'}",
                   "result": "MATCH" if match else "MISMATCH"})

# 8. HICP rent annual index = mean of 12 monthly raw values
ln_f, rec = rng.choice([(ln, r) for ln, r in final if r["hicp_rent_index"] != ""])
g, y = rec["geo"], rec["year"]
months = [(ln, r) for ln, r in raw_find("eurostat-hicp-housing-food/prc_hicp_minr.csv", {"unit": "I15", "coicop18": "CP041", "geo": g})
          if r["TIME_PERIOD"].startswith(y + "-")]
vals = [float(r["OBS_VALUE"]) for _, r in months]
lng = [r for _, r in long_find("hicp", {"unit": "I15", "coicop18": "CP041", "geo": g}) if r["time"].startswith(y + "-")]
traces.append({"#": 8, "measure": "hicp_rent_index", "geo": g, "year": y,
               "1 raw": f"prc_hicp_minr.csv lines {months[0][0]}-{months[-1][0]}: {len(vals)} months = {vals}",
               "2 long": f"long_hicp.csv: {len(lng)} monthly rows, same values: {[float(r['value']) for r in lng] == vals}",
               "3 final": f"country_year.csv line {ln_f}: hicp_rent_index={rec['hicp_rent_index']} ; hand mean (statistics.fmean)={statistics.fmean(vals)!r}",
               "result": "MATCH" if len(vals) == 12 and abs(statistics.fmean(vals) - float(rec["hicp_rent_index"])) < 1e-9 else "MISMATCH"})

# 9. real house price index = HPI / HICP all-items annual avg * 100
ln_f, rec = rng.choice([(ln, r) for ln, r in final if r["real_house_price_index_2015"] != ""])
g, y = rec["geo"], rec["year"]
(hl, hr), = raw_find("eurostat-house-price-index/prc_hpi_a.csv", {"purchase": "TOTAL", "unit": "I15_A_AVG", "geo": g, "TIME_PERIOD": y})
am = [float(r["OBS_VALUE"]) for _, r in raw_find("eurostat-hicp-housing-food/prc_hicp_minr.csv", {"unit": "I15", "coicop18": "TOTAL", "geo": g})
      if r["TIME_PERIOD"].startswith(y + "-")]
hand = float(hr["OBS_VALUE"]) / statistics.fmean(am) * 100
traces.append({"#": 9, "measure": "real_house_price_index_2015", "geo": g, "year": y,
               "1 raw": f"prc_hpi_a.csv line {hl}: HPI={hr['OBS_VALUE']} ; prc_hicp_minr.csv TOTAL I15 {len(am)} months, mean={statistics.fmean(am)!r}",
               "2 long": "(derived only in country_year)",
               "3 final": f"country_year.csv line {ln_f}: real_house_price_index_2015={rec['real_house_price_index_2015']} ; hand calc={hand!r}",
               "result": "MATCH" if abs(hand - float(rec["real_house_price_index_2015"])) < 1e-9 else "MISMATCH"})

# 10. city rent share = rent / (national net EUR / 12) * 100, rounded to 1 dp
ln_c, crow = rng.choice([(ln, r) for ln, r in city if r["rent_share_of_net_salary_pct"] != ""])
cg, y = crow["city_geo"], crow["year"]
(rl, rr), = raw_find("eurostat-city-rents/prc_colc_rents.csv", {"building": "FLAT1", "currency": "EUR", "geo": cg, "TIME_PERIOD": y})
(nl, nr), = raw_find("eurostat-net-earnings/earn_nt_net.csv", {"estruct": "NET", "ecase": "P1_NCH_AW100", "currency": "EUR", "geo": cg.split("_")[0], "TIME_PERIOD": y})
share = float(rr["OBS_VALUE"]) / (float(nr["OBS_VALUE"]) / 12) * 100
traces.append({"#": 10, "measure": "rent_share_of_net_salary_pct", "geo": cg, "year": y,
               "1 raw": f"prc_colc_rents.csv line {rl}: rent={rr['OBS_VALUE']} ; earn_nt_net.csv line {nl}: net annual={nr['OBS_VALUE']} flag='{nr['OBS_FLAG']}'",
               "2 long": f"net/12={float(nr['OBS_VALUE'])/12!r} ; share unrounded={share!r}",
               "3 final": f"city_rent.csv line {ln_c}: rent={crow['rent_1bed_eur_month']} net_salary_month={crow['net_salary_eur_month']} share={crow['rent_share_of_net_salary_pct']}",
               "result": "MATCH" if round(share, 1) == float(crow["rent_share_of_net_salary_pct"]) and float(crow["net_salary_eur_month"]) == float(nr["OBS_VALUE"]) / 12 else "MISMATCH"})

(RES / "p5_traces.json").write_text(json.dumps({"seed": SEED, "traces": traces}, indent=1, ensure_ascii=False), encoding="utf-8")
md = [f"Random seed: {SEED}", "", "| # | Measure | Geo | Year | Raw source | Long table | Final table | Result |", "|---|---|---|---|---|---|---|---|"]
for t in traces:
    md.append(f"| {t['#']} | {t['measure']} | {t['geo']} | {t['year']} | {t['1 raw']} | {t['2 long']} | {t['3 final']} | {t['result']} |")
(RES / "p5_traces.md").write_text("\n".join(md), encoding="utf-8")
for t in traces:
    print(f"\n#{t['#']} {t['measure']} {t['geo']} {t['year']} -> {t['result']}")
    for k in ("1 raw", "2 long", "3 final"):
        print(f"   {k}: {t[k]}")
