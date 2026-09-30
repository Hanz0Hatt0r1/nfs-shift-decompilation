#!/usr/bin/env bash
set -euo pipefail
self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/SHIFT.exe.c" <<'EOF'
undefined DAT_00b8a004;
undefined DAT_00b8a014;

void FUN_00100000(void)

{
  int local_8;

  FUN_00631740(&local_8,"Base");
  _DAT_00c0d100 = &PTR_FUN_00aaa988;
  FUN_00630fe0(&DAT_00c0d104,&local_8);
  _DAT_00c0d108 = &DAT_00bfa608;
  _DAT_00c0d10c = &PTR_PTR_00b8a000;
  FUN_006310c0(&local_8);
  return;
}

void FUN_00100090(void)

{
  int local_8;

  FUN_00631740(&local_8,"Child");
  _DAT_00c0d110 = &PTR_FUN_00aaa988;
  FUN_00630fe0(&DAT_00c0d114,&local_8);
  _DAT_00c0d118 = &DAT_00c0d100;
  _DAT_00c0d11c = &PTR_PTR_00b8a010;
  FUN_006310c0(&local_8);
  return;
}

void FUN_00200000(void)

{
  int local_8;
  int local_c;

  FUN_00631740(&local_8,"baseValue");
  FUN_0063a280(&DAT_00b8a004,1,&local_8,0x10,0,&local_c);
  return;
}

void FUN_00200080(void)

{
  int local_8;
  int local_c;

  FUN_00631740(&local_8,"childValue");
  FUN_0063a280(&DAT_00b8a014,3,&local_8,0x14,2,&local_c);
  FUN_00631740(&local_8,"dynamicValue");
  FUN_0063a280(&DAT_00b8a014,1,&local_8,param_1,0,&local_c);
  return;
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
rdata_rva = 0x2000
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

table = optional + optional_size

def section(index, name, virtual_size, virtual_address, raw_size, raw_offset, characteristics):
    off = table + index * 40
    blob[off:off + 8] = name.encode("ascii").ljust(8, b"\0")
    struct.pack_into(
        "<IIIIIIHHI", blob, off + 8,
        virtual_size, virtual_address, raw_size, raw_offset,
        0, 0, 0, 0, characteristics,
    )

section(0, ".text", text_size, text_rva, text_size, text_raw, 0x60000020)
section(1, ".rdata", rdata_size, rdata_rva, rdata_size, rdata_raw, 0x40000040)

text_va = image_base + text_rva
for address, descriptor in (
    (0x00401100, 0x00C0D100),
    (0x00401120, 0x00C0D110),
):
    off = text_raw + (address - text_va)
    blob[off:off + 6] = b"\xB8" + struct.pack("<I", descriptor) + b"\xC3"

rdata_va = image_base + rdata_rva
for vtable, getter in (
    (0x00402100, 0x00401100),
    (0x00402120, 0x00401120),
):
    off = rdata_raw + (vtable - rdata_va)
    struct.pack_into("<II", blob, off, 0x00401080, getter)

out.write_bytes(blob)
PY

python3 "$self_dir/build_shift_class_manifest.py"   "$tmp/SHIFT.exe.c"   --exe "$tmp/SHIFT.exe"   --json-out "$tmp/report.json"   --csv-out "$tmp/report.csv" >/dev/null

python3 - "$tmp/report.json" "$tmp/report.csv" <<'PY'
import csv
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["format"] == "SHIFT-CLASS-MANIFEST/1", report
assert report["class_count"] == 2, report
assert report["named_class_count"] == 2, report
assert report["reflected_class_count"] == 2, report
assert report["reflection_field_count"] == 3, report
assert report["unique_vtable_count"] == 2, report

rows = {row["name"]: row for row in report["classes"]}
base = rows["Base"]
child = rows["Child"]

assert base["children"] == ["Child"], base
assert base["ancestry"] == [], base
assert base["field_count"] == 1, base
assert base["fields"][0]["field_name"] == "baseValue", base
assert base["fields"][0]["offset"] == 0x10, base
assert base["unique_vtable"] == 0x00402100, base

assert child["parent_class"] == "Base", child
assert child["ancestry"] == ["Base"], child
assert child["children"] == [], child
assert child["field_count"] == 2, child
assert child["resolved_field_name_count"] == 2, child
assert child["static_field_offset_count"] == 1, child
assert child["reflection_functions"] == ["FUN_00200080"], child
assert [field["field_name"] for field in child["fields"]] == [
    "childValue", "dynamicValue"
], child
assert child["fields"][0]["offset"] == 0x14, child
assert child["fields"][1]["offset"] is None, child
assert child["unique_vtable"] == 0x00402120, child

with open(sys.argv[2], newline="", encoding="utf-8") as handle:
    csv_rows = list(csv.DictReader(handle))
assert [row["name"] for row in csv_rows] == ["Base", "Child"], csv_rows
assert csv_rows[1]["ancestry"] == "Base", csv_rows
PY

python3 "$self_dir/build_shift_class_manifest.py"   "$tmp/SHIFT.exe.c"   --exe "$tmp/SHIFT.exe"   --prefix Ch   --only-reflected   --json-out "$tmp/filtered.json" >/dev/null

python3 - "$tmp/filtered.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["selected_class_count"] == 1, report
assert report["classes"][0]["name"] == "Child", report
PY

echo "SHIFT class manifest test: PASS"
