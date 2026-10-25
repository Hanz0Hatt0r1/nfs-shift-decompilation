#!/usr/bin/env python3
"""Keep the exact-XEX menu-background archive finding evidence-backed."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_menu_background_archive_sweep_20261025.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.retail-menu-background-archive-sweep.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
scan = evidence["input"]
assert scan["archives_seen"] == 1845
assert scan["archives_parsed"] == scan["archives_seen"]
assert scan["index_failures"] == []

archive_sweep = evidence["archive_member_sweep"]
assert archive_sweep["scene_path_substring_matches"] == []
assert archive_sweep["exact_requested_path_matches"] == []
members = {
    (entry["archive"], entry["path"].casefold())
    for entry in archive_sweep["matches"]
}
assert ("PakFiles/Menu_Background.bff", "gui/menu_background/menu_background.sgx") in members
assert ("PakFiles/Menu_Background.bff", "gui/menu_background/menu_background.enx") in members
assert ("PakFiles/Dir/GUI.bff", "gui/menu_background/lights.xml") in members
assert ("PakFiles/MENUSETUP.bff", "gui/menu_background/defaultcamera.xml") in members

archives = {archive["path"]: archive for archive in archive_sweep["candidate_archives"]}
assert archives["PakFiles/Menu_Background.bff"]["sha256"] == (
    "38346e13ff13f8e3b1fa47afee12fb67ae2b43ab1256476dc6178add55fe8a63"
)
assert sum(archive["menu_background_member_count"] for archive in archives.values()) == len(
    archive_sweep["matches"]
)

print("all 1845 retail archive indexes parsed; requested menu scene XML is absent")
