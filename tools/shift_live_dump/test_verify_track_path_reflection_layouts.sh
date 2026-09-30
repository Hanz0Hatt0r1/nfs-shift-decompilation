#!/usr/bin/env bash
set -euo pipefail
self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/SHIFT.exe.c" <<'EOF'
undefined DAT_00b8b1bc;

void FUN_00a84460(void)

{
  int local_8;

  FUN_00631740(&local_8,"AISpline");
  _DAT_00c0d648 = &PTR_FUN_00aaa988;
  FUN_00630fe0(&DAT_00c0d64c,&local_8);
  _DAT_00c0d650 = &DAT_00bfa608;
  _DAT_00c0d654 = &PTR_PTR_00b8b1b8;
  FUN_006310c0(&local_8);
  return;
}

undefined4 FUN_006ce2f0(void)

{
  int local_c;
  int local_8;

  FUN_00631740(&local_c,&DAT_00aa9b60);
  FUN_00631740(&local_8,"length");
  FUN_0063a280(&DAT_00b8b1bc,1,&local_8,0x14,2,&local_c);
  FUN_006310c0(&local_8);
  FUN_006310c0(&local_c);

  FUN_00631740(&local_8,&DAT_00aa9b60);
  FUN_00631740(&local_c,"StepDist");
  FUN_0063a280(&DAT_00b8b1bc,1,&local_c,0x1c,2,&local_8);
  FUN_006310c0(&local_c);
  FUN_006310c0(&local_8);

  FUN_00631740(&local_8,&DAT_00aa9b60);
  FUN_00631740(&local_c,"knot count");
  FUN_0063a280(&DAT_00b8b1bc,3,&local_c,0x18,2,&local_8);
  FUN_006310c0(&local_c);
  FUN_006310c0(&local_8);

  FUN_00631740(&local_8,&DAT_00aa9b60);
  FUN_00631740(&local_c,"knot array");
  FUN_0063a280(&DAT_00b8b1bc,6,&local_c,0x10,2,&local_8);
  FUN_006310c0(&local_c);
  FUN_006310c0(&local_8);
  return 1;
}
EOF

cat >"$tmp/analyzer.py" <<'EOF'
SPLINE = {
    "array": (0x10, "I"),
    "length": (0x14, "f"),
    "knots": (0x18, "I"),
    "step_dist": (0x1c, "f"),
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

out.write_bytes(blob)
PY

python3 "$self_dir/verify_track_path_reflection_layouts.py"   "$tmp/SHIFT.exe.c" --exe "$tmp/SHIFT.exe"   --analyzer "$tmp/analyzer.py" --class-name AISpline   --json-out "$tmp/pass.json" >/dev/null

python3 - "$tmp/pass.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["ready"] is True, report
assert report["class_count"] == 1, report
assert report["binding_count"] == 4, report
assert report["matched_binding_count"] == 4, report
assert {row["reflected_field"] for row in report["bindings"]} == {
    "knot array", "length", "knot count", "StepDist"
}, report
assert all(row["match"] for row in report["bindings"]), report
PY

sed 's/"length": (0x14, "f")/"length": (0x18, "f")/'   "$tmp/analyzer.py" >"$tmp/wrong-analyzer.py"

if python3 "$self_dir/verify_track_path_reflection_layouts.py"   "$tmp/SHIFT.exe.c" --exe "$tmp/SHIFT.exe"   --analyzer "$tmp/wrong-analyzer.py" --class-name AISpline   --json-out "$tmp/fail.json" >/dev/null; then
    echo "expected wrong AISpline length offset to fail" >&2
    exit 1
fi

python3 - "$tmp/fail.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["ready"] is False, report
row = next(item for item in report["bindings"] if item["reflected_field"] == "length")
assert row["analyzer_offset"] == 0x18, row
assert row["source_offsets"] == [0x14], row
assert row["source_type_codes"] == [1], row
assert row["match"] is False, row
PY

echo "track path reflection layout verifier test: PASS"
