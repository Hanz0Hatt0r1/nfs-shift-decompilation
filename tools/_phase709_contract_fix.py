#!/usr/bin/env python3
from pathlib import Path

path = Path("tests/test_native_runtime_contract.py")
text = path.read_text(encoding="utf-8")
old = '    assert "--frames must equal native input script step count" in source\n'
new = '''    assert "--frames must equal native input script step count" in (\n        source\n        + Path("native_runtime/src/runtime_loop_policy.hpp").read_text(encoding="utf-8")\n    )\n'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"expected one Phase 601 cardinality assertion, found {count}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
