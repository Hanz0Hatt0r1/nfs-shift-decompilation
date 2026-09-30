#!/usr/bin/env bash
set -euo pipefail
self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/SHIFT.exe.c" <<'EOF'
void * FUN_006bc3a0(void *this)
{
    *(void ***)this = &PTR_FUN_00afb150;
    return this;
}

void * FUN_006c3a20(void *this)
{
    *(void ***)this = &PTR_FUN_00afc048;
    return this;
}

void * FUN_006cfe70(void *this)
{
    *(void ***)this = &PTR_FUN_00afc930;
    return this;
}

void FUN_006cfc10(void *this)
{
    *(void ***)this = &PTR_FUN_00afbf60;
}

void * FUN_006cc900(void *this)
{
    *(void ***)this = &PTR_FUN_00afc678;
    return this;
}

void FUN_006cc730(void *this)
{
    *(void ***)this = &PTR_FUN_00afbfa8;
}

void FUN_006cdf70(void *this)
{
    *(void ***)this = &PTR_FUN_00afbe28;
}

void * FUN_006d8490(void *param_1)
{
    if (param_1 == &DAT_00c0d668) {
        return FUN_006cfe70(param_1);
    }
    if (param_1 == &DAT_00c0d608) {
        return FUN_006cc900(param_1);
    }
    return 0;
}
EOF

cat >"$tmp/analyzer.py" <<'EOF'
KNOWN_VTABLES = {
    "AIPathInfo": 0x00AFB150,
    "AIArea": 0x00AFC048,
    "AISegmentPath": 0x00AFC930,
    "AIPathNode": 0x00AFBF60,
    "AIPolylinePath": 0x00AFC678,
    "AIPolyPathNode": 0x00AFBFA8,
    "Knot": 0x00AFBE28,
}
EOF

# Build a compact synthetic PE32 whose .text RTTI getters and .rdata vtables
# use the exact retail virtual addresses. AISpline/AISplineInfo intentionally
# have no dedicated RTTI getter/vtable.
python3 - "$tmp/SHIFT.exe" <<'PY'
import struct
import sys
from pathlib import Path

out = Path(sys.argv[1])
image_base = 0x00400000
pe_offset = 0x80
optional_size = 0xE0
text_rva = 0x002B0000
text_raw = 0x200
text_size = 0x20000
rdata_rva = 0x006FB000
rdata_raw = text_raw + text_size
rdata_size = 0x3000
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

getters = {
    0x006BC3E0: 0x00C0D5A4,  # AIPathInfo
    0x006C3C30: 0x00C0D588,  # AIArea
    0x006CC3B0: 0x00C0D608,  # AIPolylinePath
    0x006C3000: 0x00C0D638,  # Knot
    0x006CE680: 0x00C0D668,  # AISegmentPath
    0x006C3950: 0x00C0D678,  # AIPolyPathNode
    0x006C3940: 0x00C0D688,  # AIPathNode
}
text_va = image_base + text_rva
for address, descriptor in getters.items():
    off = text_raw + (address - text_va)
    blob[off:off + 6] = b"\xB8" + struct.pack("<I", descriptor) + b"\xC3"

vtables = {
    0x00AFB150: 0x006BC3E0,
    0x00AFC048: 0x006C3C30,
    0x00AFC678: 0x006CC3B0,
    0x00AFBE28: 0x006C3000,
    0x00AFC930: 0x006CE680,
    0x00AFBFA8: 0x006C3950,
    0x00AFBF60: 0x006C3940,
}
rdata_va = image_base + rdata_rva
for vtable, getter in vtables.items():
    off = rdata_raw + (vtable - rdata_va)
    struct.pack_into("<II", blob, off, 0x006C0100, getter)

out.write_bytes(blob)
PY

python3 "$self_dir/verify_track_path_source_anchors.py"     "$tmp/SHIFT.exe.c" --analyzer "$tmp/analyzer.py"     --exe "$tmp/SHIFT.exe" --json-out "$tmp/pass.json" >/dev/null
python3 - "$tmp/pass.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["ready"] is True, report
assert len(report["anchors"]) == 7, report
assert all(row["analyzer_match"] for row in report["anchors"]), report
assert all(row["rtti_found"] and row["constructor_found"] for row in report["factory_links"]), report
pe = report["pe_rtti_vtables"]
assert pe["ready"] is True, pe
rows = {row["class"]: row for row in pe["rows"]}
assert rows["AIPathInfo"]["getter_addresses"] == [0x006BC3E0], rows
assert rows["AIPathInfo"]["candidate_vtables"] == [0x00AFB150], rows
assert rows["AIArea"]["getter_addresses"] == [0x006C3C30], rows
assert rows["AIArea"]["candidate_vtables"] == [0x00AFC048], rows
assert rows["AISegmentPath"]["candidate_vtables"] == [0x00AFC930], rows
assert rows["AIPolylinePath"]["candidate_vtables"] == [0x00AFC678], rows
assert rows["AIPathNode"]["candidate_vtables"] == [0x00AFBF60], rows
assert rows["AIPolyPathNode"]["candidate_vtables"] == [0x00AFBFA8], rows
assert rows["Knot"]["candidate_vtables"] == [0x00AFBE28], rows
assert rows["AISpline"]["getter_addresses"] == [], rows
assert rows["AISpline"]["candidate_vtables"] == [], rows
assert rows["AISpline"]["expected_dedicated_vtable_absent"] is True, rows
assert rows["AISpline"]["match"] is True, rows
PY

sed 's/0x00AFC930/0x00AFCA70/' "$tmp/analyzer.py" >"$tmp/wrong-analyzer.py"
if python3 "$self_dir/verify_track_path_source_anchors.py"     "$tmp/SHIFT.exe.c" --analyzer "$tmp/wrong-analyzer.py"     --exe "$tmp/SHIFT.exe" --json-out "$tmp/fail.json" >/dev/null; then
    echo "expected wrong AISegmentPath vtable to fail" >&2
    exit 1
fi
python3 - "$tmp/fail.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
segment = next(row for row in report["anchors"] if row["class"] == "AISegmentPath")
pe_segment = next(
    row for row in report["pe_rtti_vtables"]["rows"]
    if row["class"] == "AISegmentPath"
)
assert report["ready"] is False, report
assert segment["expected_vtable"] == 0x00AFC930, segment
assert segment["analyzer_vtable"] == 0x00AFCA70, segment
assert segment["analyzer_match"] is False, segment
assert pe_segment["candidate_vtables"] == [0x00AFC930], pe_segment
assert pe_segment["analyzer_vtable"] == 0x00AFCA70, pe_segment
assert pe_segment["match"] is False, pe_segment
PY

# A fabricated AISpline getter/vtable must violate the retail boundary instead
# of being accepted as a newly "discovered" concrete class identity.
cp "$tmp/SHIFT.exe" "$tmp/bad-spline.exe"
python3 - "$tmp/bad-spline.exe" <<'PY'
import struct
import sys
from pathlib import Path

path = Path(sys.argv[1])
blob = bytearray(path.read_bytes())
text_raw = 0x200
text_va = 0x006B0000
rdata_raw = 0x20200
rdata_va = 0x00AFB000

getter = 0x006C5000
off = text_raw + (getter - text_va)
blob[off:off + 6] = b"\xB8" + struct.pack("<I", 0x00C0D648) + b"\xC3"

vtable = 0x00AFC000
off = rdata_raw + (vtable - rdata_va)
struct.pack_into("<II", blob, off, 0x006C0100, getter)
path.write_bytes(blob)
PY

if python3 "$self_dir/verify_track_path_source_anchors.py"     "$tmp/SHIFT.exe.c" --analyzer "$tmp/analyzer.py"     --exe "$tmp/bad-spline.exe" --json-out "$tmp/bad-spline.json" >/dev/null; then
    echo "expected fabricated AISpline dedicated vtable to fail" >&2
    exit 1
fi
python3 - "$tmp/bad-spline.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
row = next(
    row for row in report["pe_rtti_vtables"]["rows"]
    if row["class"] == "AISpline"
)
assert report["ready"] is False, report
assert row["getter_addresses"] == [0x006C5000], row
assert row["candidate_vtables"] == [0x00AFC000], row
assert row["expected_dedicated_vtable_absent"] is True, row
assert row["match"] is False, row
PY

echo "track path source anchor verifier test: PASS"
