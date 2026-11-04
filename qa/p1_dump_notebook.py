"""QA Phase 1 helper: print the source of every notebook cell (read-only).

Usage: python -I qa/p1_dump_notebook.py pipeline/python/generation_rent_01_clean.ipynb
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    nb = json.load(f)

print("kernelspec:", nb["metadata"].get("kernelspec"))
print("cells:", len(nb["cells"]))
for i, c in enumerate(nb["cells"]):
    print(f"\n--- cell {i} [{c['cell_type']}] exec_count={c.get('execution_count')}")
    print("".join(c["source"]))
