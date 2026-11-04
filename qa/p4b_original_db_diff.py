"""QA Phase 4b: diagnose differences between the ORIGINAL pipeline/sql/generation_rent.duckdb (opened read-only)
and the CSVs it was loaded from. Compares per column after aligning rows on the table's natural key.

Usage: python -I qa/p4b_original_db_diff.py
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "pipeline/clean/generation-rent"
KEYS = {"country_year": ["geo", "year"], "city_rent": ["city_geo", "year"], "dim_country": ["geo"], "dim_year": ["year"],
        "hicp_monthly": ["geo", "coicop18", "month"],
        "long_overburden": ["geo", "unit", "rskpovth", "age", "sex", "time"],
        "long_net_earn": ["geo", "currency", "estruct", "ecase", "time"],
        "long_with_parents": ["geo", "age", "sex", "unit", "time"]}
TEXT = {"time": str, "month": str, "date": str}

for dbname in ["pipeline/sql/generation_rent.duckdb", "qa/sandbox/sql/generation_rent.duckdb"]:
    con = duckdb.connect(str(ROOT / dbname), read_only=True)
    print(f"\n######## {dbname}")
    for t, key in KEYS.items():
        db = con.execute(f"SELECT * FROM {t}").df()
        cs = pd.read_csv(CSV / f"{t}.csv", dtype=TEXT)
        for c in db.columns:
            if pd.api.types.is_datetime64_any_dtype(db[c]):
                db[c] = db[c].dt.strftime("%Y-%m-%d")              # DuckDB DATE -> CSV text
            elif c in TEXT:
                db[c] = db[c].astype(str)
        m = db.merge(cs, on=key, how="outer", suffixes=("_db", "_csv"), indicator=True)
        print(f"{t}: db rows {len(db)}, csv rows {len(cs)}, key match {m['_merge'].value_counts().to_dict()}")
        if list(db.columns) != list(cs.columns):
            print(f"   COLUMN LIST DIFFERS: db {list(db.columns)} vs csv {list(cs.columns)}")
        for c in [c for c in cs.columns if c not in key]:
            a, b = m[f"{c}_db"], m[f"{c}_csv"]
            if pd.api.types.is_numeric_dtype(b) and not pd.api.types.is_bool_dtype(b):
                a, b = pd.to_numeric(a, errors="coerce").astype(float), b.astype(float)
                diff = ~((a == b) | (a.isna() & b.isna()))
            else:
                # pandas 3 'str' dtype keeps NaN through astype(str), so normalise missing values explicitly
                na = lambda s: s.astype(object).where(s.notna(), "<missing>").astype(str)  # noqa: E731
                diff = na(a) != na(b)
            if diff.any():
                ex = m.loc[diff, key + [f"{c}_db", f"{c}_csv"]].head(3).values.tolist()
                print(f"   column {c}: {int(diff.sum())} differences, e.g. {ex}")
    con.close()
