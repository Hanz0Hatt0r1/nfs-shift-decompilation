from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "resource_progress_site" / "sitecustomize.py"
    spec = importlib.util.spec_from_file_location(
        "resource_progress_repo_path_order_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_progress_hook_matches_playable_bootstrap_repo_path_precedence(monkeypatch):
    mod = _load_module()
    sentinel = "sentinel-third-party-path"

    # Python already places the script directory on sys.path. Model the normal
    # tools/bootstrap_playable_linux_slice.py startup before its manual inserts.
    monkeypatch.setattr(mod.sys, "path", [str(mod.TOOLS), sentinel])

    mod._install_repo_paths()

    src_paths = [mod.SRC]
    src_paths.extend(sorted(
        (path for path in mod.SRC.rglob("*") if path.is_dir()),
        key=lambda path: (len(path.parts), str(path)),
    ))
    positions = {value: mod.sys.path.index(str(value)) for value in src_paths}
    root_position = mod.sys.path.index(str(mod.ROOT))
    tools_position = mod.sys.path.index(str(mod.TOOLS))

    assert max(positions.values()) < root_position
    assert root_position < tools_position
    assert tools_position < mod.sys.path.index(sentinel)
