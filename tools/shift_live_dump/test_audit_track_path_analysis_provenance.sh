#!/usr/bin/env bash
set -euo pipefail
self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

python3 - "$self_dir/analyze_track_paths.py" "$tmp" <<'PY'
import json
import runpy
import sys
from pathlib import Path

analyzer = Path(sys.argv[1])
out = Path(sys.argv[2])
ns = runpy.run_path(str(analyzer))
manifest = ns["analyzer_evidence_manifest"]()
fingerprint = ns["analyzer_evidence_fingerprint"](manifest)

current = {
    "format": ns["FORMAT"],
    "known_vtables": {
        key: hex(value) for key, value in ns["KNOWN_VTABLES"].items()
    },
    "analyzer_evidence": {
        "fingerprint": fingerprint,
        "manifest": manifest,
    },
}
(out / "current.json").write_text(json.dumps(current), encoding="utf-8")

legacy_stale = {
    "format": ns["FORMAT"],
    "known_vtables": {
        "AISegmentPath": "0xafca70",
    },
}
(out / "legacy-stale.json").write_text(
    json.dumps(legacy_stale), encoding="utf-8"
)

legacy_unversioned = {
    "format": ns["FORMAT"],
    "known_vtables": {
        key: hex(value) for key, value in ns["KNOWN_VTABLES"].items()
    },
}
(out / "legacy-unversioned.json").write_text(
    json.dumps(legacy_unversioned), encoding="utf-8"
)

tampered = json.loads(json.dumps(current))
tampered["analyzer_evidence"]["fingerprint"] = "0" * 64
tampered["analyzer_evidence"]["manifest"]["layouts"]["AISpline"]["length"]["offset"] = 0x18
(out / "tampered.json").write_text(json.dumps(tampered), encoding="utf-8")
PY

python3 "$self_dir/audit_track_path_analysis_provenance.py"   "$tmp/current.json" --json-out "$tmp/current-audit.json" >/dev/null

python3 - "$tmp/current-audit.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
assert report["ready"] is True, report
assert report["status"] == "current", report
assert report["observed_fingerprint"] == report["current_fingerprint"], report
assert report["changed_manifest_sections"] == [], report
assert report["vtable_differences"] == [], report
PY

for name in legacy-stale legacy-unversioned tampered; do
  if python3 "$self_dir/audit_track_path_analysis_provenance.py"     "$tmp/$name.json" --json-out "$tmp/$name-audit.json" >/dev/null; then
      echo "expected $name provenance audit to fail" >&2
      exit 1
  fi
done

python3 - "$tmp/legacy-stale-audit.json" "$tmp/legacy-unversioned-audit.json" "$tmp/tampered-audit.json" <<'PY'
import json
import sys

stale = json.load(open(sys.argv[1], encoding="utf-8"))
unversioned = json.load(open(sys.argv[2], encoding="utf-8"))
tampered = json.load(open(sys.argv[3], encoding="utf-8"))

assert stale["status"] == "legacy-stale", stale
segment = next(
    row for row in stale["vtable_differences"]
    if row["class"] == "AISegmentPath"
)
assert segment["observed"] == "0x00afca70", segment
assert segment["current"] == "0x00afc930", segment
assert segment["kind"] == "changed", segment

assert unversioned["status"] == "legacy-unversioned", unversioned
assert unversioned["ready"] is False, unversioned
assert unversioned["vtable_differences"] == [], unversioned

assert tampered["status"] == "stale", tampered
assert "layouts" in tampered["changed_manifest_sections"], tampered
assert tampered["observed_fingerprint"] != tampered["current_fingerprint"], tampered
PY

echo "track path analysis provenance audit test: PASS"
