from pathlib import Path
import zipfile

from tools import audit_bff_payload_parity as runtime


def test_normalized_path_is_case_and_separator_insensitive():
    assert runtime._normalized_path(
        r"Render\Shaders\Cache\Example.FXO"
    ) == "render/shaders/cache/example.fxo"


def test_iter_bffs_reads_nested_zip_members(tmp_path: Path):
    archive = tmp_path / "Vehicles.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("cars/A.bff", b"a")
        z.writestr("cars/B.bff", b"b")
        z.writestr("cars/not-a-bff.txt", b"x")

    paths = list(runtime._iter_bffs([archive]))

    assert [path.name for path in paths] == ["A.bff", "B.bff"]


def test_count_extensions_is_deterministic():
    rows = [
        {"path": "a.fxo"},
        {"path": "b.FXO"},
        {"path": "c.dds"},
        {"path": "d"},
    ]

    assert runtime._count_extensions(rows) == {
        ".fxo": 2,
        ".dds": 1,
        "<none>": 1,
    }
