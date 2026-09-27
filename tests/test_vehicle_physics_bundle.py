from pathlib import Path

import vehicle_physics_bundle as bundle


class Entry:
    def __init__(self, path, index, typ=2):
        self.path = path
        self.index = index
        self.type = typ
        self.compressed_size = 10
        self.uncompressed_size = 20


class FakeBFF:
    def __init__(self, path):
        self.path = Path(path)
        self.entries = [
            Entry("vehicles/physics/chassis/bmw_m3_e36.cdf", 1),
            Entry("vehicles/physics/engines/bmw_m3_e36.edf", 2),
            Entry("vehicles/physics/gearbox/common.gdf", 3),
            Entry("vehicles/physics/suspension/aarm_multilink.sdf", 4),
        ]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def extract_entry(self, entry, type2="lzx"):
        return {
            ".cdf": b"[GENERAL]\nMass=1000\n",
            ".edf": b"RPMTorque=(1000,10,20)\nRPMTorque=(2000,11,21)\n",
            ".gdf": b"[GEAR_RATIOS]\nratio=(10,35)\n",
            ".sdf": b"[BODY]\nname=body mass=(1) inertia=(1,1,1) pos=(0,0,0) ori=(0,0,0)\n",
        }[Path(entry.path).suffix]


def test_extract_bundle_resolves_default_vehicle_physics_entries(monkeypatch, tmp_path):
    monkeypatch.setattr(bundle, "BFF", FakeBFF)
    monkeypatch.setattr(
        bundle,
        "build_profile",
        lambda **kwargs: {"format": "SHIFT.VehiclePhysicsAssetGraph/1", "ready": True, "status": "ready"},
    )
    bff = tmp_path / "BMW_M3_E36.bff"
    bff.write_bytes(b"fixture")
    result = bundle.extract_bundle(bff, tmp_path / "out")
    assert result["ready"] is True
    assert set(result["extracted_paths"]) == {"cdf", "edf", "gdf", "sdf"}
    assert result["entries"]["cdf"]["archive_path"].endswith("bmw_m3_e36.cdf")
    assert (tmp_path / "out" / "resources" / "bmw_m3_e36.cdf").is_file()
    assert (tmp_path / "out" / "vehicle_physics_asset_graph.json").is_file()


def test_find_entry_rejects_ambiguous_basename(monkeypatch, tmp_path):
    class Ambiguous(FakeBFF):
        def __init__(self, path):
            super().__init__(path)
            self.entries.append(Entry("other/bmw_m3_e36.cdf", 5))
    monkeypatch.setattr(bundle, "BFF", Ambiguous)
    bff = tmp_path / "BMW_M3_E36.bff"
    bff.write_bytes(b"fixture")
    with bundle.BFF(bff) as archive:
        try:
            bundle._find_entry(archive, "missing/bmw_m3_e36.cdf")
        except ValueError as exc:
            assert "exactly one" in str(exc)
        else:
            raise AssertionError("ambiguous basename must be rejected")
