#!/usr/bin/env bash
set -euo pipefail
self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/SHIFT.exe.c" <<'EOF'
undefined DAT_00b8a014;

void FUN_00100090(void)

{
  int local_8;

  FUN_00631740(&local_8,"Child");
  _DAT_00c0d110 = &PTR_FUN_00aaa988;
  FUN_00630fe0(&DAT_00c0d114,&local_8);
  _DAT_00c0d118 = &DAT_00bfa608;
  _DAT_00c0d11c = &PTR_PTR_00b8a010;
  FUN_006310c0(&local_8);
  return;
}

undefined4 FUN_00200000(void)

{
  undefined4 *puVar2;
  uint uVar1;
  int local_c;
  int local_8;

  FUN_00631740(&local_c,&DAT_00aa9b60);
  FUN_00631740(&local_8,"Speed");
  FUN_0063a280(&DAT_00b8a014,1,&local_8,0x10,2,&local_c);
  FUN_006310c0(&local_8);
  FUN_006310c0(&local_c);

  FUN_00631740(&local_c,&DAT_00aa9b60);
  FUN_00631740(&local_8,&DAT_00afb120);
  FUN_0063a280(&DAT_00b8a014,3,&local_8,0x14,2,&local_c);
  FUN_006310c0(&local_8);
  FUN_006310c0(&local_c);

  FUN_00631740(&local_c,&DAT_00aa9b60);
  FUN_00631740(&local_8,(void *)*puVar2);
  FUN_0063a280(&DAT_00b8a014,0xd,&local_8,uVar1,2,&local_c);
  FUN_006310c0(&local_8);
  FUN_006310c0(&local_c);
  return 1;
}
EOF

python3 - "$tmp/SHIFT.exe" <<'PY'
import struct
import sys
from pathlib import Path

out = Path(sys.argv[1])
image_base = 0x00400000
pe_offset = 0x80
optional_size = 0xE0
text_rva = 0x1000
text_raw = 0x200
text_size = 0x1000
rdata_rva = 0x006FB000
rdata_raw = text_raw + text_size
rdata_size = 0x1000
blob = bytearray(rdata_raw + rdata_size)

blob[:2] = b"MZ"
struct.pack_into("<I", blob, 0x3C, pe_offset)
blob[pe_offset:pe_offset + 4] = b"PE\0\0"
struct.pack_into("<H", blob, pe_offset + 4, 0x14C)
struct.pack_into("<H", blob, pe_offset + 6, 2)
struct.pack_into("<H", blob, pe_offset + 20, optional_size)
optional = pe_offset + 24
struct.pack_into("<H", blob, optional, 0x10B)
struct.pack_into("<I", blob, optional + 28, image_base)

section_table = optional + optional_size

def section(index, name, virtual_size, virtual_address, raw_size, raw_offset, characteristics):
    off = section_table + index * 40
    blob[off:off + 8] = name.encode("ascii").ljust(8, b"\0")
    struct.pack_into(
        "<IIIIIIHHI", blob, off + 8,
        virtual_size, virtual_address, raw_size, raw_offset,
        0, 0, 0, 0, characteristics,
    )

section(0, ".text", text_size, text_rva, text_size, text_raw, 0x60000020)
section(1, ".rdata", rdata_size, rdata_rva, rdata_size, rdata_raw, 0x40000040)

rdata_va = image_base + rdata_rva
name_off = rdata_raw + (0x00AFB120 - rdata_va)
blob[name_off:name_off + 6] = b"Count\0"

out.write_bytes(blob)
PY

python3 "$self_dir/extract_shift_reflection_fields.py"   "$tmp/SHIFT.exe.c" --exe "$tmp/SHIFT.exe"   --json-out "$tmp/report.json" --csv-out "$tmp/fields.csv" >/dev/null

python3 - "$tmp/report.json" "$tmp/fields.csv" <<'PY'
import csv
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["format"] == "SHIFT-REFLECTION-FIELDS/1", report
assert report["field_call_count"] == 3, report
assert report["mapped_class_count"] == 3, report
assert report["resolved_field_name_count"] == 2, report
assert report["static_type_count"] == 3, report
assert report["static_offset_count"] == 2, report
assert report["static_flags_count"] == 3, report

rows = report["fields"]
assert [row["class_name"] for row in rows] == ["Child"] * 3, rows
assert [row["reflection_function"] for row in rows] == ["FUN_00200000"] * 3, rows

speed, count, dynamic = rows
assert speed["field_name"] == "Speed", speed
assert speed["type_code"] == 1, speed
assert speed["offset"] == 0x10, speed
assert speed["flags"] == 2, speed

assert count["field_name"] == "Count", count
assert count["field_name_token"] == "&DAT_00afb120", count
assert count["type_code"] == 3, count
assert count["offset"] == 0x14, count

assert dynamic["field_name"] is None, dynamic
assert dynamic["field_name_token"] == "(void *)*puVar2", dynamic
assert dynamic["type_code"] == 0xD, dynamic
assert dynamic["offset"] is None, dynamic
assert dynamic["offset_expression"] == "uVar1", dynamic

with open(sys.argv[2], newline="", encoding="utf-8") as handle:
    csv_rows = list(csv.DictReader(handle))
assert len(csv_rows) == 3, csv_rows
assert csv_rows[0]["field_name"] == "Speed", csv_rows
assert csv_rows[1]["field_name"] == "Count", csv_rows
PY

python3 "$self_dir/extract_shift_reflection_fields.py"   "$tmp/SHIFT.exe.c" --exe "$tmp/SHIFT.exe" --class-name Child   --json-out "$tmp/filtered.json" >/dev/null
python3 - "$tmp/filtered.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["selected_field_count"] == 3, report
assert all(row["class_name"] == "Child" for row in report["fields"]), report
PY

echo "SHIFT reflection field extractor test: PASS"
