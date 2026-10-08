#!/usr/bin/env python3
"""Generate a fail-closed evidence/doc/test scaffold for a new proof slice."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    if not value:
        raise SystemExit("empty slug")
    return value


def build_payload(contract: str, title: str, blocker: str, next_step: str, owner: str) -> dict:
    return {
        "format": contract,
        "version": 1,
        "ready": False,
        "title": title,
        "blocker": blocker,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1",
            "evidence_kind": "UNRESOLVED",
        },
        "observations": [],
        "adjudication": {
            "proof_complete": False,
            "retail_input_control_provenance_proven": False,
            "external_provider_count": 7,
        },
        "owner": owner,
        "next_step": next_step,
    }


def render_doc(payload: dict) -> str:
    return f"""# {payload['title']}

## BLOCKER

{payload['blocker']}

## Result

Scaffold only. No semantic promotion has been made.

## Evidence

Add exact PC-retail addresses, base provenance, widths, call edges, and hashes here.

## Gate

```text
proof complete                          = false
retail input/control provenance         = false
external provider count                 = 7
```

## NEXT_STEP

{payload['next_step']}
"""


def render_test(slug: str, evidence_rel: str, contract: str) -> str:
    return f'''import json\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nEVIDENCE = ROOT / "{evidence_rel}"\n\n\ndef test_{slug}_scaffold_is_fail_closed():\n    p = json.loads(EVIDENCE.read_text(encoding="utf-8"))\n    assert p["format"] == "{contract}"\n    assert p["ready"] is False\n    assert p["adjudication"]["proof_complete"] is False\n    assert p["adjudication"]["retail_input_control_provenance_proven"] is False\n    assert p["adjudication"]["external_provider_count"] == 7\n'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--blocker", required=True)
    parser.add_argument("--next-step", required=True)
    parser.add_argument("--owner", default="Process 1")
    parser.add_argument("--slug")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    slug = slugify(args.slug or args.contract)
    payload = build_payload(args.contract, args.title, args.blocker, args.next_step, args.owner)

    evidence = args.root / "evidence" / f"{slug}.json"
    doc = args.root / "docs" / f"PROCESS_{slug.upper()}.md"
    test = args.root / "tests" / f"test_{slug}.py"
    for path in (evidence, doc, test):
        if path.exists():
            raise SystemExit(f"refusing to overwrite existing file: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)

    evidence.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    doc.write_text(render_doc(payload), encoding="utf-8")
    evidence_rel = evidence.relative_to(args.root).as_posix()
    test.write_text(render_test(slug, evidence_rel, args.contract), encoding="utf-8")
    print(evidence)
    print(doc)
    print(test)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
