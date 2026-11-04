"""Print the headline results of every QA phase from qa/results/*.json (read-only).
Usage: python -I qa/summarise_results.py"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parent / "results"
j = lambda n: json.loads((R / n).read_text(encoding="utf-8"))  # noqa: E731

p0 = j("p0_setup.json")
print("p0:", {k: v.get("exit_code") for k, v in p0.items()}, p0["run_in_original_layout"])
p3 = j("p3_run_compare.json")
print("p3 errors/warnings:", p3["fresh_run_errors_warnings"])
print("p3 changed outputs:", p3["cells_with_changed_output"] if p3["cells_with_changed_output"] == "none" else list(p3["cells_with_changed_output"]))
print("p3 path-only diffs:", p3["cells_differing_only_in_printed_folder_paths"])
print("p3 sequential:", p3["saved_run_was_sequential_fresh_kernel"], "| CSV identical:",
      all(v["identical_sha256"] for v in p3["output_files"].values()), len(p3["output_files"]), "| extra:", p3["files_only_in_fresh_run"])
print("p3 hard-coded paths:", p3["absolute_hardcoded_paths"], "| names before def:", p3["names_used_before_definition"])
for n in sorted(R.glob("p3_lineage*.json")) + sorted(R.glob("p4*.json")) + sorted(R.glob("p5_trace*.json")):
    d = j(n.name)
    print(f"\n{n.name}: top-level keys {list(d)[:30]}")
p7 = j("p7_reproducibility.json")
print("\np7:", {k: p7[k] for k in ("requirements_files_in_project", "all_identical", "run_in_original_layout", "original_layout_all_identical", "randomness_or_clock_in_pipeline")})
