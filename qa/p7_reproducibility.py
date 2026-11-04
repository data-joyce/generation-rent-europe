"""QA Phase 7: reproducibility evidence.

Collects: library versions used by this audit, presence of a requirements/environment file, use of randomness or
clock-dependent code in the pipeline, the result of the fresh re-run (hash comparison from p3) and of the run in the
notebook's real layout (from p0). Read-only.
Usage: python -I qa/p7_reproducibility.py -> prints and writes qa/results/p7_reproducibility.json
"""
import importlib.metadata as md
import json
import platform
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "qa/results"
out = {}
out["python"] = platform.python_version()
out["platform"] = platform.platform()
out["libraries"] = {p: md.version(p) for p in ["pandas", "numpy", "duckdb", "matplotlib", "nbconvert", "nbformat", "ipykernel", "jupyter_client"]}
req = [str(p.relative_to(ROOT)) for pat in ("requirements*.txt", "environment*.yml", "pyproject.toml", "Pipfile*", "*.lock")
       for p in ROOT.rglob(pat) if "qa" not in p.relative_to(ROOT).parts]
out["requirements_files_in_project"] = req or "none"
code = []
for p in list((ROOT / "pipeline").rglob("*.py")) + list((ROOT / "pipeline").rglob("*.sql")) + list((ROOT / "pipeline").rglob("*.ipynb")):
    txt = p.read_text(encoding="utf-8")
    if p.suffix == ".ipynb":
        txt = "\n".join("".join(c["source"]) for c in json.loads(txt)["cells"] if c["cell_type"] == "code")
    for pat in (r"\brandom\b", r"\bsample\(", r"\bseed\b", r"shuffle", r"now\(\)", r"today\(\)", r"current_date", r"\bRANDOM\(\)"):
        if re.search(pat, txt, re.I):
            code.append(f"{p.relative_to(ROOT)}: {pat}")
out["randomness_or_clock_in_pipeline"] = code or "none found (no seeds needed)"
p3 = json.loads((RES / "p3_run_compare.json").read_text(encoding="utf-8"))
out["fresh_rerun_outputs_identical"] = {k: v["identical_sha256"] for k, v in p3["output_files"].items()}
out["all_identical"] = all(out["fresh_rerun_outputs_identical"].values())
p0f = RES / "p0_setup.json"
out["run_in_original_layout"] = json.loads(p0f.read_text())["run_in_original_layout"] if p0f.exists() else "p0 not run yet"
# outputs of the run in the original layout (qa/sandbox_inplace) vs the project's outputs, byte for byte
import hashlib  # noqa: E402
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
ORIG, INPL = ROOT / "pipeline/clean/generation-rent", ROOT / "qa/sandbox_inplace/clean/generation-rent"
out["original_layout_outputs_identical"] = {p.name: (INPL / p.name).exists() and sha(p) == sha(INPL / p.name)
                                            for p in sorted(ORIG.glob("*.csv"))}
out["original_layout_all_identical"] = bool(out["original_layout_outputs_identical"]) and all(out["original_layout_outputs_identical"].values())
out["external_inputs_frozen"] = "Raw Eurostat CSVs are stored locally (download date 2026-11-04 in each README); re-downloading would give newer data, not the same."
(RES / "p7_reproducibility.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
for k, v in out.items():
    print(f"{k}: {v}")
