"""QA Phase 3.1-3.2: compare a fresh top-to-bottom run of the notebook with the saved original.

Prerequisite (done once, see QA_REPORT.md): the unmodified notebook was copied to qa/sandbox/python/ with a copy of
datasets/ in qa/sandbox/datasets/, then executed on a fresh kernel:
    cd qa/sandbox/python; python -m jupyter nbconvert --to notebook --execute generation_rent_01_clean.ipynb --output executed_fresh.ipynb
This script then:
  1. lists errors / warnings / stderr in the fresh run
  2. diffs every cell's text output (saved vs fresh)
  3. checks execution order of the saved notebook (hidden-state signal)
  4. scans the code for hard-coded paths / names used before definition
  5. compares the 13 output CSVs byte-for-byte (SHA-256) with pipeline/clean/generation-rent/
Usage: python -I qa/p3_notebook_run_compare.py
"""
import ast
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SAVED = ROOT / "pipeline/python/generation_rent_01_clean.ipynb"
FRESH = ROOT / "qa/sandbox/python/executed_fresh.ipynb"
ORIG_OUT = ROOT / "pipeline/clean/generation-rent"
NEW_OUT = ROOT / "qa/sandbox/clean/generation-rent"
RES = ROOT / "qa/results"

saved = json.loads(SAVED.read_text(encoding="utf-8"))
fresh = json.loads(FRESH.read_text(encoding="utf-8"))
result = {}


def text_of(outputs):
    parts = []
    for o in outputs:
        if o["output_type"] == "stream":
            # Jupyter splits one print stream into chunks at arbitrary points (timing), so join consecutive chunks
            # of the same stream before comparing; otherwise identical text can look different.
            head = f"[{o['name']}] "
            if parts and parts[-1].startswith(head) and getattr(text_of, "_last_stream", None) == len(parts):
                parts[-1] += "".join(o["text"])
            else:
                parts.append(head + "".join(o["text"]))
            text_of._last_stream = len(parts)
            continue
        elif o["output_type"] in ("execute_result", "display_data"):
            d = o.get("data", {})
            if "text/plain" in d:
                parts.append("".join(d["text/plain"]))
            elif "image/png" in d:
                parts.append("<image/png>")
        elif o["output_type"] == "error":
            parts.append(f"ERROR {o['ename']}: {o['evalue']}")
    return "\n".join(parts)


# 1. errors / warnings ---------------------------------------------------------------
issues = []
for i, c in enumerate(fresh["cells"]):
    if c["cell_type"] != "code":
        continue
    for o in c.get("outputs", []):
        if o["output_type"] == "error":
            issues.append(f"cell {i}: ERROR {o['ename']}: {o['evalue']}")
        if o["output_type"] == "stream" and o["name"] == "stderr":
            issues.append(f"cell {i}: STDERR {''.join(o['text'])[:300]}")
        t = text_of([o])
        if re.search(r"Warning|FutureWarning|SettingWithCopy", t):
            issues.append(f"cell {i}: WARNING text: {t[:300]}")
result["fresh_run_errors_warnings"] = issues or ["none"]
print("1. Errors/warnings in fresh run:", issues or "none")

# 2. output diffs --------------------------------------------------------------------
# The sandbox copy runs from a different folder, so lines that print folder paths legitimately differ.
# Normalise absolute paths and the 'clean\...' vs 'pipeline\clean\...' prefix; everything else must be identical.
def norm(t):
    t = re.sub(r"[A-Za-z]:\\[^\s]+", "<abs-path>", t)
    t = re.sub(r"(outputs to:\s+)\S+", r"\1<out>", t)            # the notebook prints its output folder (relative)
    return re.sub(r"->\s+\S*clean\\generation-rent\\", "-> <out>\\\\", t)


diffs, path_only = {}, []
for i, (a, b) in enumerate(zip(saved["cells"], fresh["cells"])):
    if a["cell_type"] != "code":
        continue
    ta, tb = text_of(a.get("outputs", [])), text_of(b.get("outputs", []))
    if ta != tb:
        if norm(ta) == norm(tb):
            path_only.append(i)
            continue
        diffs[i] = "\n".join(difflib.unified_diff(ta.splitlines(), tb.splitlines(), "saved", "fresh", lineterm="", n=0))
result["cells_with_changed_output"] = diffs or "none"
result["cells_differing_only_in_printed_folder_paths"] = path_only or "none"
n_code = sum(1 for c in saved["cells"] if c["cell_type"] == "code")
print(f"2. Code cells: {n_code}; cells whose text output changed: {len(diffs)} "
      f"(+ {len(path_only)} differing only in printed folder paths: cells {path_only})")
for i, d in diffs.items():
    print(f"--- cell {i}\n{d[:1500]}")

# 3. execution order of saved notebook -------------------------------------------------
counts = [c.get("execution_count") for c in saved["cells"] if c["cell_type"] == "code"]
sequential = counts == list(range(1, len(counts) + 1))
result["saved_execution_counts"] = counts
result["saved_run_was_sequential_fresh_kernel"] = sequential
print("3. Saved execution counts:", counts, "-> sequential from 1:", sequential)

# 4. static scan: names used before they are defined (by cell order), hard-coded paths ----
src = [("".join(c["source"]), i) for i, c in enumerate(saved["cells"]) if c["cell_type"] == "code"]
defined = set(dir(__builtins__)) | {"display", "get_ipython"}
used_before = []
for code, i in src:
    tree = ast.parse(code)
    assigned_here = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            assigned_here.add(node.name)
            for a in node.args.args + node.args.kwonlyargs:
                assigned_here.add(a.arg)
            if node.args.kwarg:
                assigned_here.add(node.args.kwarg.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            assigned_here.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                assigned_here.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.comprehension):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    assigned_here.add(n.id)
        elif isinstance(node, ast.Lambda):
            for a in node.args.args:
                assigned_here.add(a.arg)
    loads = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    missing = loads - defined - assigned_here
    if missing:
        used_before.append(f"cell {i}: {sorted(missing)}")
    defined |= assigned_here
result["names_used_before_definition"] = used_before or "none"
print("4a. Names used before definition (static, by cell order):", used_before or "none")
paths = [(i, m) for code, i in src for m in re.findall(r"['\"]([A-Za-z]:\\[^'\"]+|/[^'\"]*/[^'\"]+)['\"]", code)]
result["absolute_hardcoded_paths"] = paths or "none"
print("4b. Absolute hard-coded paths:", paths or "none")
root_rule = [code for code, i in src if "Path.cwd()" in code]
result["path_logic"] = ("BASE = cwd.parent if cwd is named 'python' else cwd; datasets/ is searched at BASE and upwards; "
                        "outputs go to BASE/clean/generation-rent" if "BASE.parents" in "".join(code for code, _ in src) else
                        "ROOT = Path.cwd().parent if cwd is named 'python' else Path.cwd() (relative to where the kernel starts)")
print("4c. Path logic:", result["path_logic"])

# 5. output files byte-for-byte --------------------------------------------------------
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


cmp = {}
for p in sorted(ORIG_OUT.glob("*.csv")):
    q = NEW_OUT / p.name
    cmp[p.name] = {"orig_bytes": p.stat().st_size, "fresh_bytes": q.stat().st_size if q.exists() else None,
                   "identical_sha256": q.exists() and sha(p) == sha(q)}
extra = sorted({q.name for q in NEW_OUT.glob("*.csv")} - set(cmp))
result["output_files"] = cmp
result["files_only_in_fresh_run"] = extra
print("5. Output CSVs identical to originals (SHA-256):")
for k, v in cmp.items():
    print(f"   {k:24} {v['orig_bytes']:>10} {v['fresh_bytes']:>10} identical={v['identical_sha256']}")
print("   files only in fresh run:", extra or "none")

(RES / "p3_run_compare.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
