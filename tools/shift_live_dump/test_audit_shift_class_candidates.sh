#!/usr/bin/env bash
set -euo pipefail
self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/SHIFT.exe.c" <<'EOF'
undefined DAT_00b8a004;
undefined DAT_00b8a014;
undefined DAT_00b8a024;
undefined DAT_00b8a034;

void FUN_00100000(void)

{
  int local_8;
  FUN_00631740(&local_8,"Ready");
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
  FUN_00631740(&local_8,"Dynamic");
  _DAT_00c0d110 = &PTR_FUN_00aaa988;
  FUN_00630fe0(&DAT_00c0d114,&local_8);
  _DAT_00c0d118 = &DAT_00bfa608;
  _DAT_00c0d11c = &PTR_PTR_00b8a010;
  FUN_006310c0(&local_8);
  return;
}

void FUN_00100120(void)

{
  int local_8;
  FUN_00631740(&local_8,"Ambiguous");
  _DAT_00c0d120 = &PTR_FUN_00aaa988;
  FUN_00630fe0(&DAT_00c0d124,&local_8);
  _DAT_00c0d128 = &DAT_00bfa608;
  _DAT_00c0d12c = &PTR_PTR_00b8a020;
  FUN_006310c0(&local_8);
  return;
}

void FUN_001001b0(void)

{
  int local_8;
  FUN_00631740(&local_8,"NoFields");
  _DAT_00c0d130 = &PTR_FUN_00aaa988;
  FUN_00630fe0(&DAT_00c0d134,&local_8);
  _DAT_00c0d138 = &DAT_00bfa608;
  _DAT_00c0d13c = &PTR_PTR_00b8a030;
  FUN_006310c0(&local_8);
  return;
}

void FUN_00200000(void)

{
  int local_8;
  int local_c;
  FUN_00631740(&local_8,"alpha");
  FUN_0063a280(&DAT_00b8a004,1,&local_8,0x10,2,&local_c);
  FUN_00631740(&local_8,"beta");
  FUN_0063a280(&DAT_00b8a004,3,&local_8,0x14,3,&local_c);
  return;
}

void FUN_00200080(void)

{
  int local_8;
  int local_c;
  FUN_00631740(&local_8,"dynamic");
  FUN_0063a280(&DAT_00b8a014,1,&local_8,param_1,2,&local_c);
  return;
}

void FUN_00200100(void)

{
  int local_8;
  int local_c;
  FUN_00631740(&local_8,"value");
  FUN_0063a280(&DAT_00b8a024,1,&local_8,0x10,2,&local_c);
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
    (0x00401140, 0x00C0D120),
    (0x00401160, 0x00C0D130),
):
    off = text_raw + (address - text_va)
    blob[off:off + 6] = b"\xB8" + struct.pack("<I", descriptor) + b"\xC3"

rdata_va = image_base + rdata_rva
for vtable, getter in (
    (0x00402100, 0x00401100),
    (0x00402120, 0x00401120),
    (0x00402140, 0x00401140),
    (0x00402160, 0x00401140),
    (0x00402180, 0x00401160),
):
    off = rdata_raw + (vtable - rdata_va)
    struct.pack_into("<II", blob, off, 0x00401080, getter)

out.write_bytes(blob)
PY

python3 "$self_dir/audit_shift_class_candidates.py"   "$tmp/SHIFT.exe.c"   --exe "$tmp/SHIFT.exe"   --json-out "$tmp/report.json"   --csv-out "$tmp/report.csv" >/dev/null

python3 - "$tmp/report.json" "$tmp/report.csv" <<'PY'
import csv
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["format"] == "SHIFT-CLASS-DECOMPILATION-CANDIDATES/1", report
assert report["class_count"] == 4, report
assert report["structural_ready_count"] == 1, report
assert report["blocked_count"] == 3, report
assert report["blocker_counts"]["dynamic_field_offsets"] == 1, report
assert report["blocker_counts"]["non_unique_vtable"] == 1, report
assert report["blocker_counts"]["no_reflected_fields"] == 1, report

rows = {row["class_name"]: row for row in report["candidates"]}
assert rows["Ready"]["structural_ready"] is True, rows
assert rows["Ready"]["blockers"] == [], rows
assert rows["Ready"]["field_count"] == 2, rows
assert rows["Ready"]["unique_vtable"] == 0x00402100, rows

assert rows["Dynamic"]["structural_ready"] is False, rows
assert rows["Dynamic"]["blockers"] == ["dynamic_field_offsets"], rows
assert rows["Dynamic"]["unique_vtable"] == 0x00402120, rows

assert rows["Ambiguous"]["structural_ready"] is False, rows
assert rows["Ambiguous"]["blockers"] == ["non_unique_vtable"], rows
assert rows["Ambiguous"]["vtable_candidates"] == [0x00402140, 0x00402160], rows

assert rows["NoFields"]["structural_ready"] is False, rows
assert rows["NoFields"]["blockers"] == ["no_reflected_fields"], rows

with open(sys.argv[2], newline="", encoding="utf-8") as handle:
    csv_rows = list(csv.DictReader(handle))
assert csv_rows[0]["class_name"] == "Ready", csv_rows
assert csv_rows[0]["structural_ready"] == "True", csv_rows
PY

python3 "$self_dir/audit_shift_class_candidates.py"   "$tmp/SHIFT.exe.c"   --exe "$tmp/SHIFT.exe"   --ready-only   --top 1   --json-out "$tmp/ready.json" >/dev/null

python3 - "$tmp/ready.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["selected_count"] == 1, report
assert report["candidates"][0]["class_name"] == "Ready", report
PY

python3 "$self_dir/audit_shift_class_candidates.py"   "$tmp/SHIFT.exe.c"   --exe "$tmp/SHIFT.exe"   --blocked-only   --prefix Dyn   --json-out "$tmp/blocked.json" >/dev/null

python3 - "$tmp/blocked.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["selected_count"] == 1, report
assert report["candidates"][0]["class_name"] == "Dynamic", report
PY

echo "SHIFT class structural evidence audit test: PASS"
