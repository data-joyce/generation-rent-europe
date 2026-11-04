"""Run one or more .sql files against the Generation Rent DuckDB database and print every result.

Usage (from the project root, i.e. the DataStudy folder):
    python pipeline/python/run_sql.py pipeline/sql/generation_rent/00_setup.sql
    python pipeline/python/run_sql.py pipeline/sql/generation_rent/02_prices_vs_earnings.sql
    python pipeline/python/run_sql.py "pipeline/sql/generation_rent/*.sql"   # run everything in order

File paths may be given relative to where you run the command OR relative to the folder above this script
(so "sql/generation_rent/*.sql" also works). If a pattern matches no .sql file, the script stops with an error.

The database file is <folder above this script>/sql/generation_rent.duckdb (created by 00_setup.sql).
You can also open that file in DBeaver or the DuckDB CLI and run the same queries there.
"""
import glob
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "sql" / "generation_rent.duckdb"


SILENT = {"CREATE", "INSERT", "DROP", "UPDATE", "DELETE", "ALTER", "COPY", "SET", "TRANSACTION"}


def comment_title(text: str) -> str:
    """Pick a title from comment lines: prefer a numbered one like '-- 2. …', skip '-- ====' rules."""
    lines = [l.strip()[2:].strip() for l in text.splitlines() if l.strip().startswith("--")]
    lines = [l for l in lines if any(ch.isalnum() for ch in l)]
    numbered = [l for l in lines if l[:1].isdigit()]
    return (numbered or lines or [""])[-1]


def run_file(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    print(f"\n{'=' * 100}\n{path.relative_to(ROOT)}\n{'=' * 100}")
    text = path.read_text(encoding="utf-8")
    statements = duckdb.extract_statements(text)
    # The first statement's title sits in the file header, before any statement text
    first_line = statements[0].query.strip().splitlines()[0] if statements else ""
    header = text[: text.find(first_line)] if first_line else ""
    title = comment_title(header.split("=====")[-1])
    for stmt in statements:
        # DuckDB returns each statement plus the text that follows it (the next statement's comments).
        # Peel trailing blank/comment lines off the end, then drop the final ';'.
        lines = stmt.query.rstrip().splitlines()
        tail_lines = []
        while lines and (not lines[-1].strip() or lines[-1].strip().startswith("--")):
            tail_lines.insert(0, lines.pop())
        body = "\n".join(lines).rstrip().rstrip(";")
        tail = "\n".join(tail_lines)
        if stmt.type.name in SILENT:
            con.execute(body)
        else:
            print(f"\n-- {title}")
            con.sql(body).show(max_rows=40, max_width=200)
        title = comment_title(tail)


def main(args: list[str]) -> None:
    if not args:
        sys.exit(__doc__)
    # Windows consoles default to cp1252, which can't print DuckDB's table borders or 'München'
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # Resolve each pattern relative to the current folder first, then relative to ROOT
    files = set()
    for a in args:
        found = [p for p in glob.glob(a) if p.endswith(".sql")] or \
                [p for p in glob.glob(str(ROOT / a)) if p.endswith(".sql")]
        if not found:
            sys.exit(f"No .sql files match {a!r} (looked in {Path.cwd()} and {ROOT})")
        files |= {Path(p).resolve() for p in found}
    files = sorted(files)
    os.chdir(ROOT)                               # CSV paths in 00_setup.sql are relative to ROOT
    with duckdb.connect(str(DB)) as con:
        for f in files:
            run_file(con, f)


if __name__ == "__main__":
    main(sys.argv[1:])
