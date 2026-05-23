#!/usr/bin/env python3
"""
Extracts field tooltips and field lists from Base Application AL source files.

Sources of truth:
  - Page .al files   -> which fields appear in the UI (Rec.FieldName references)
                       and tooltips defined at page level (override table tooltips)
  - Table .al files  -> field numbers, names, and table-level tooltips (fallback)

Priority: page tooltip > table tooltip > "" (empty, to be filled later)

Usage:
  python scripts/extract_from_al.py [path/to/Base Application.Source]

Output:
  data/tables/{id}_{slug}.json   — one per table that appears in at least one page
  data/search_index.json         — flat index of all fields
"""

import json

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

REPO_ROOT   = Path(__file__).parent
TABLES_DIR  = REPO_ROOT / "data" / "tables"
INDEX_FILE  = REPO_ROOT / "data" / "index.json"

SRC_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT.parent / "Base Application.Source"

if not SRC_DIR.exists():
    print(f"ERROR: Source directory not found: {SRC_DIR}", file=sys.stderr)
    print("Usage: python scripts/extract_from_al.py [path/to/Base Application.Source]", file=sys.stderr)
    sys.exit(1)

# ── Helpers ────────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

def read_file(path: Path) -> str | None:
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return None

def walk_al(root: Path, suffix: str):
    """Yield all .al files with the given suffix under root."""
    for p in root.rglob(f"*{suffix}"):
        yield p

def parse_al_string(src: str, start: int) -> tuple[str, int]:
    """
    Parse a single-quoted AL string starting at src[start] (the opening quote).
    Returns (value, index_after_closing_quote).
    AL escapes single quotes by doubling: '' -> '
    """
    result = []
    i = start + 1
    while i < len(src):
        if src[i] == "'":
            if i + 1 < len(src) and src[i + 1] == "'":
                result.append("'")
                i += 2
            else:
                return ''.join(result), i + 1
        else:
            result.append(src[i])
            i += 1
    return ''.join(result), i

def find_block_end(src: str, open_brace: int) -> int:
    """
    Given the index of an opening '{', return the index just after the matching '}'.
    """
    depth = 1
    i = open_brace + 1
    while i < len(src) and depth > 0:
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
        i += 1
    return i

def flatten_top_level(body: str) -> str:
    """Return only the top-level content of a block body (strips nested blocks)."""
    result = []
    depth = 0
    for ch in body:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        elif depth == 0:
            result.append(ch)
    return ''.join(result)

def extract_tooltip_from_body(body: str) -> str | None:
    """Extract ToolTip value from a field block body."""
    flat = flatten_top_level(body)
    m = re.search(r"ToolTip\s*=\s*'", flat)
    if not m:
        return None
    # Find the actual quote in the original body (same relative position)
    quote_pos = body.find("ToolTip", body.find(m.group(0)) if m.group(0) in body else 0)
    quote_pos = body.find("'", quote_pos)
    if quote_pos == -1:
        return None
    value, _ = parse_al_string(body, quote_pos)
    return value.strip() or None

def parse_field_blocks(src: str):
    """
    Yield (field_decl_args, body) tuples for every field(...) { ... } block in src.
    field_decl_args = the string inside field(...)
    body            = the string inside the following { }
    """
    i = 0
    pattern = re.compile(r'\bfield\s*\(')
    while i < len(src):
        m = pattern.search(src, i)
        if not m:
            break
        # Find matching closing paren for field(
        paren_open = m.end() - 1  # index of '('
        depth = 1
        j = paren_open + 1
        while j < len(src) and depth > 0:
            if src[j] == '(':
                depth += 1
            elif src[j] == ')':
                depth -= 1
            j += 1
        args = src[paren_open + 1:j - 1]

        # Find the opening brace of the field body.
        # Between ) and { only whitespace, line comments (//) and #pragma lines are allowed.
        gap_start = j
        brace_m = re.search(r'\{', src[j:j + 300])
        if not brace_m:
            i = j
            continue
        gap_end = j + brace_m.start()
        gap = src[gap_start:gap_end]
        gap_clean = re.sub(r'//[^\n]*', '', gap)     # strip // comments
        gap_clean = re.sub(r'#[^\n]*', '', gap_clean) # strip #pragma lines
        if re.search(r'\S', gap_clean):
            i = j
            continue

        brace_open = gap_end
        block_end = find_block_end(src, brace_open)
        body = src[brace_open + 1:block_end - 1]

        yield args, body
        i = block_end

# ── Step 1: Scan Table files -> id, name, field numbers ────────────────────────

# table_by_name["Customer"]     = {"id": 18, "name": "Customer", "slug": "18_customer",
#                                   "fields": {"No.": 1, "Name": 2, ...}}
# table_by_id[18]               = same dict

table_by_name: dict[str, dict] = {}
table_by_id:   dict[int, dict] = {}

# table_tooltips[18][1] = "Specifies..."  (tooltip from Table.al)
table_tooltips: dict[int, dict[int, str]] = defaultdict(dict)

print("Scanning Table files…")
table_file_count = 0

for path in walk_al(SRC_DIR, ".Table.al"):
    src = read_file(path)
    if not src:
        continue

    # table 18 Customer  or  table 36 "Sales Header"
    tm = re.search(r'^table\s+(\d+)\s+"?([^"\n{]+)"?', src, re.MULTILINE)
    if not tm:
        continue

    table_id   = int(tm.group(1))
    table_name = tm.group(2).strip().strip('"')
    slug       = f"{table_id}_{slugify(table_name)}"

    fields: dict[str, int] = {}  # fieldName -> fieldNo

    for args, body in parse_field_blocks(src):
        # Table field: "1; \"No.\"; Code[20]"  or  "2; Name; Text[100]"
        dm = re.match(r'^\s*(\d+)\s*;\s*"?([^";]+)"?\s*;', args)
        if not dm:
            continue
        field_no   = int(dm.group(1))
        field_name = dm.group(2).strip()

        if field_name not in fields:
            fields[field_name] = field_no

        # Extract tooltip from this field block
        tt = extract_tooltip_from_body(body)
        if tt and field_no not in table_tooltips[table_id]:
            table_tooltips[table_id][field_no] = tt

    entry = {"id": table_id, "name": table_name, "slug": slug, "fields": fields}
    table_by_name[table_name] = entry
    table_by_id[table_id]     = entry
    table_file_count += 1

table_tt_count = sum(len(v) for v in table_tooltips.values())
print(f"  {table_file_count} table files -> {len(table_by_name)} tables, {table_tt_count} table-level tooltips")

# ── Step 2: Scan Page files -> field list + page-level tooltips ────────────────

# page_fields[tableId][fieldNo] = page_tooltip or None
page_fields: dict[int, dict[int, str | None]] = defaultdict(dict)

print("Scanning Page files…")
page_count    = 0
page_tt_count = 0

for path in walk_al(SRC_DIR, ".Page.al"):
    src = read_file(path)
    if not src:
        continue

    # SourceTable = Customer;  or  SourceTable = "Sales Header";
    st_m = re.search(r'SourceTable\s*=\s*"?([^";\n]+)"?\s*;', src)
    if not st_m:
        continue

    table_name = st_m.group(1).strip()
    entry      = table_by_name.get(table_name)
    if not entry:
        continue

    table_id  = entry["id"]
    field_map = entry["fields"]   # fieldName -> fieldNo
    pf        = page_fields[table_id]

    page_count += 1

    for args, body in parse_field_blocks(src):
        # Page field: "\"No.\"; Rec.\"No.\""  or  "Name; Rec.Name"
        # We need the Rec.FieldName part (second argument)
        parts = args.split(';', 1)
        if len(parts) < 2:
            continue
        ref = parts[1].strip()

        # Extract field name from Rec."Field Name" or Rec.FieldName
        rec_m = re.match(r'Rec\.(?:"([^"]+)"|([^\s;,\)]+))', ref)
        if not rec_m:
            continue
        field_name = (rec_m.group(1) or rec_m.group(2)).strip()

        field_no = field_map.get(field_name)
        if field_no is None:
            continue

        # Get tooltip from page (may be None)
        tt = extract_tooltip_from_body(body)

        # Register field; page tooltip takes priority, but don't overwrite an
        # existing page tooltip with None
        if field_no not in pf:
            pf[field_no] = tt
            if tt:
                page_tt_count += 1
        elif tt and not pf[field_no]:
            pf[field_no] = tt
            page_tt_count += 1

print(f"  {page_count} page files -> {sum(len(v) for v in page_fields.values())} field slots, {page_tt_count} page-level tooltips")

# ── Step 3: Write output files ─────────────────────────────────────────────────

# Clear existing table JSON files
TABLES_DIR.mkdir(parents=True, exist_ok=True)
for f in TABLES_DIR.glob("*.json"):
    f.unlink()

index_tables = []
tables_written = 0
total_with_tt = 0
total_without_tt = 0

# Only process tables that appear in at least one page
tables_with_pages = {table_id for table_id, pf in page_fields.items() if pf}

for table_id in tables_with_pages:
    entry = table_by_id.get(table_id)
    if not entry:
        continue

    pf = page_fields[table_id]  # page tooltips: fieldNo -> tooltip or None

    fields_out = []
    for field_name, field_no in sorted(entry["fields"].items(), key=lambda x: x[1]):
        # Priority: page tooltip -> table tooltip -> ""
        page_tt  = pf.get(field_no)
        table_tt = table_tooltips[table_id].get(field_no, "")
        tooltip  = page_tt or table_tt

        fields_out.append({
            "no":      field_no,
            "name":    field_name,
            "tooltip": tooltip,
        })

    if not fields_out:
        continue

    table_json = {
        "id":              entry["id"],
        "name":            entry["name"],
        "slug":            entry["slug"],
        "objectNamespace": "Base Application",
        "fields":          fields_out,
    }

    out_path = TABLES_DIR / f"{entry['slug']}.json"
    out_path.write_text(json.dumps(table_json, indent=2, ensure_ascii=False), encoding='utf-8')
    tables_written += 1

    tt = sum(1 for f in fields_out if f["tooltip"])
    total_with_tt    += tt
    total_without_tt += len(fields_out) - tt

    has_empty = any(not f["tooltip"] for f in fields_out)

    index_tables.append({
        "id":         entry["id"],
        "name":       entry["name"],
        "slug":       entry["slug"],
        "fieldCount": len(fields_out),
        "hasEmpty":   has_empty,
    })

index_tables.sort(key=lambda t: t["id"])
INDEX_FILE.write_text(json.dumps({"tables": index_tables}, indent=2, ensure_ascii=False), encoding='utf-8')

total_fields = total_with_tt + total_without_tt
print(f"\nDone:")
print(f"  {tables_written} table JSON files -> data/tables/")
print(f"  {len(index_tables)} tables in data/index.json")
print(f"  {total_fields} fields total: {total_with_tt} with tooltip, {total_without_tt} pending (empty)")
