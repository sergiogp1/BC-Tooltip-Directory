#!/usr/bin/env python3
"""
Recalculates hasEmpty for every table in data/index.json
based on the current state of data/tables/*.json.

Usage:
  python update_index.py
"""

import json
from pathlib import Path

REPO_ROOT  = Path(__file__).parent
TABLES_DIR = REPO_ROOT / "data" / "tables"
INDEX_FILE = REPO_ROOT / "data" / "index.json"

index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))

updated = 0
for table in index["tables"]:
    path = TABLES_DIR / f"{table['slug']}.json"
    if not path.exists():
        continue
    data      = json.loads(path.read_text(encoding="utf-8"))
    has_empty = any(not f.get("tooltip") for f in data["fields"])
    if table.get("hasEmpty") != has_empty:
        table["hasEmpty"] = has_empty
        updated += 1

INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Done: {updated} tables updated in data/index.json")
