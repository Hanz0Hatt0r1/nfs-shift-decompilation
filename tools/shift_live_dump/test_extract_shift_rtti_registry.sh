#!/usr/bin/env bash
set -euo pipefail
self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/SHIFT.exe.c" <<'EOF'
undefined DAT_00b8a004;
undefined DAT_00b8a014;
undefined DAT_00b8a024;

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

void FUN_00100120(void)
{
  int local_8;
  FUN_00631740(&local_8,&DAT_00afb100);
  _DAT_00c0d120 = &PTR_FUN_00aaa988;
  FUN_00630fe0(&DAT_00c0d124,&local_8);
  _DAT_00c0d128 = &DAT_00bfa608;
  _DAT_00c0d12c = &PTR_PTR_00b8a020;
  FUN_006310c0(&local_8);
  return;
}

void FUN_00200000(void)
{
  FUN_0063a280(&DAT_00b8a004,1,&local_8,0x10,2,&local_c);
  FUN_0063a280(&DAT_00b8a014,1,&local_8,0x14,2,&local_c);
  FUN_0063a280(&DAT_00b8a024,1,&local_8,0x18,2,&local_c);
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

text_va = image_base + text_rva
getters = {
    0x00401100: 0x00C0D110,
    0x00401120: 0x00C0D120,
}
for address, descriptor in getters.items():
    off = text_raw + (address - text_va)
    blob[off:off + 6] = b"\xB8" + struct.pack("<I", descriptor) + b"\xC3"

rdata_va = image_base + rdata_rva
name_off = rdata_raw + (0x00AFB100 - rdata_va)
blob[name_off:name_off + 5] = b"Knot\0"

for vtable, getter in ((0x00AFB300, 0x00401100), (0x00AFB320, 0x00401120)):
    off = rdata_raw + (vtable - rdata_va)
    struct.pack_into("<II", blob, off, 0x00401080, getter)

out.write_bytes(blob)
PY

python3 "$self_dir/extract_shift_rtti_registry.py"   "$tmp/SHIFT.exe.c" --exe "$tmp/SHIFT.exe" --json-out "$tmp/report.json" >/dev/null

python3 - "$tmp/report.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["format"] == "SHIFT-RTTI-REGISTRY/1", report
assert report["class_count"] == 3, report
assert report["resolved_name_count"] == 3, report
rows = {row["name"]: row for row in report["classes"]}

base = rows["Base"]
assert base["descriptor"] == 0x00C0D100, base
assert base["registration_function"] == "FUN_00100000", base
assert base["reflection_metadata_symbol"] == "DAT_00b8a004", base
assert base["rtti_getter_addresses"] == [], base
assert base["vtable_candidates"] == [], base
assert base["unique_vtable"] is None, base

child = rows["Child"]
assert child["parent_descriptor"] == 0x00C0D100, child
assert child["parent_class"] == "Base", child
assert child["reflection_metadata_symbol"] == "DAT_00b8a014", child
assert child["rtti_getter_addresses"] == [0x00401100], child
assert child["vtable_candidates"] == [0x00AFB300], child
assert child["unique_vtable"] == 0x00AFB300, child

knot = rows["Knot"]
assert knot["name_source_symbol"] == "DAT_00afb100", knot
assert knot["reflection_metadata_symbol"] == "DAT_00b8a024", knot
assert knot["rtti_getter_addresses"] == [0x00401120], knot
assert knot["vtable_candidates"] == [0x00AFB320], knot
assert knot["unique_vtable"] == 0x00AFB320, knot
PY

python3 "$self_dir/extract_shift_rtti_registry.py"   "$tmp/SHIFT.exe.c" --exe "$tmp/SHIFT.exe" --prefix Ch   --json-out "$tmp/prefix.json" >/dev/null
python3 - "$tmp/prefix.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["selected_class_count"] == 1, report
assert [row["name"] for row in report["classes"]] == ["Child"], report
PY

python3 "$self_dir/extract_shift_rtti_registry.py"   "$tmp/SHIFT.exe.c" --exe "$tmp/SHIFT.exe" --name Knot   --json-out "$tmp/name.json" >/dev/null
python3 - "$tmp/name.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["selected_class_count"] == 1, report
assert report["classes"][0]["name"] == "Knot", report
PY

echo "SHIFT RTTI registry extractor test: PASS"
