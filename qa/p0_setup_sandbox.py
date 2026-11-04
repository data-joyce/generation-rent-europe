"""QA step 0: (re)build the sandboxes so the project's pipeline can run WITHOUT touching the originals.

  qa/sandbox/          copy of datasets/ (minus practice-sales), the notebook, run_sql.py and the SQL files.
                       The unmodified notebook is executed here on a fresh kernel, then the SQL runner builds a fresh DuckDB.
  qa/sandbox_inplace/  the notebook alone, in the same layout it has in pipeline/ (no datasets/ next to it),
                       to test whether it runs where it actually lives. Since the 2026-11-04 fix the notebook searches
                       upwards for datasets/ (finds the project's, read-only) and writes to qa/sandbox_inplace/clean/.
Only folders inside qa/ are deleted/created. Originals are only read (copied).

Usage: python -I qa/p0_setup_sandbox.py   -> writes qa/results/p0_setup.json
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
QA = ROOT / "qa"
SB, SBI = QA / "sandbox", QA / "sandbox_inplace"
RES = QA / "results"
RES.mkdir(exist_ok=True)

for d in (SB, SBI):
    assert QA in d.resolve().parents, d          # safety: never delete outside qa/
    if d.exists():
        shutil.rmtree(d)

shutil.copytree(ROOT / "datasets", SB / "datasets", ignore=shutil.ignore_patterns("practice-sales"))
(SB / "python").mkdir(parents=True)
shutil.copy2(ROOT / "pipeline/python/generation_rent_01_clean.ipynb", SB / "python")
shutil.copy2(ROOT / "pipeline/python/run_sql.py", SB / "python")
shutil.copytree(ROOT / "pipeline/sql/generation_rent", SB / "sql/generation_rent")
(SBI / "python").mkdir(parents=True)
shutil.copy2(ROOT / "pipeline/python/generation_rent_01_clean.ipynb", SBI / "python")

log = {}
nbconvert = [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
             "generation_rent_01_clean.ipynb", "--ExecutePreprocessor.timeout=900"]
p = subprocess.run(nbconvert + ["--output", "executed_fresh.ipynb"], cwd=SB / "python", capture_output=True, text=True)
log["fresh_run_in_sandbox"] = {"exit_code": p.returncode, "stderr_tail": p.stderr[-600:]}
p = subprocess.run([sys.executable, "-I", "python/run_sql.py", "sql/generation_rent/*.sql"], cwd=SB, capture_output=True,
                   text=True, encoding="utf-8")
(RES / "p4_run_sql_output.txt").write_text(p.stdout, encoding="utf-8")
log["run_sql_all_files"] = {"exit_code": p.returncode, "stderr_tail": p.stderr[-600:]}
p = subprocess.run(nbconvert + ["--output", "executed_inplace.ipynb"], cwd=SBI / "python", capture_output=True, text=True)
err = [l for l in p.stderr.splitlines() if "Error" in l]
log["run_in_original_layout"] = {"exit_code": p.returncode, "first_error_lines": err[-3:]}
(RES / "p0_setup.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
for k, v in log.items():
    print(k, v)
