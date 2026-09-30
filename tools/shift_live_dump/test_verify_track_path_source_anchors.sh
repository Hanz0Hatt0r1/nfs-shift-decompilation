#!/usr/bin/env bash
set -euo pipefail
self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/SHIFT.exe.c" <<'EOF'
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
    "AISegmentPath": 0x00AFC930,
    "AIPathNode": 0x00AFBF60,
    "AIPolylinePath": 0x00AFC678,
    "AIPolyPathNode": 0x00AFBFA8,
    "Knot": 0x00AFBE28,
}
EOF

python3 "$self_dir/verify_track_path_source_anchors.py"     "$tmp/SHIFT.exe.c" --analyzer "$tmp/analyzer.py" --json-out "$tmp/pass.json" >/dev/null
python3 - "$tmp/pass.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["ready"] is True, report
assert len(report["anchors"]) == 5, report
assert all(row["analyzer_match"] for row in report["anchors"]), report
assert all(row["rtti_found"] and row["constructor_found"] for row in report["factory_links"]), report
PY

sed 's/0x00AFC930/0x00AFCA70/' "$tmp/analyzer.py" >"$tmp/wrong-analyzer.py"
if python3 "$self_dir/verify_track_path_source_anchors.py"     "$tmp/SHIFT.exe.c" --analyzer "$tmp/wrong-analyzer.py" --json-out "$tmp/fail.json" >/dev/null; then
    echo "expected wrong AISegmentPath vtable to fail" >&2
    exit 1
fi
python3 - "$tmp/fail.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
segment = next(row for row in report["anchors"] if row["class"] == "AISegmentPath")
assert report["ready"] is False, report
assert segment["expected_vtable"] == 0x00AFC930, segment
assert segment["analyzer_vtable"] == 0x00AFCA70, segment
assert segment["analyzer_match"] is False, segment
PY

echo "track path source anchor verifier test: PASS"
