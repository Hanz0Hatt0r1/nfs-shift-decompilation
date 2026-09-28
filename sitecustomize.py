"""Project import-path bootstrap for the src-based layout."""
from __future__ import annotations
import sys
from pathlib import Path
_ROOT=Path(__file__).resolve().parent
_SRC=_ROOT/"src"
if _SRC.is_dir():
    _paths=[_SRC]+sorted((p for p in _SRC.rglob("*") if p.is_dir()),
                         key=lambda p:(len(p.parts),str(p)))
    for _path in reversed(_paths):
        _value=str(_path)
        if _value not in sys.path: sys.path.insert(0,_value)
