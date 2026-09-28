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
            Entry("vehicles/physics/turbo/gen_lowrpm_33.tbf", 5),
            Entry("vehicles/physics/turbo/nitrous.bbf", 6),
        ]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def raw_payload(self, entry):
        return self.extract_entry(entry, type2="raw")

    def extract_entry(self, entry, type2="lzx"):
        return {
            ".cdf": b"[GENERAL]\nMass=1000\n",
            ".edf": b"RPMTorque=(1000,10,20)\nRPMTorque=(2000,11,21)\n",
            ".gdf": b"[GEAR_RATIOS]\nratio=(10,35)\n",
            ".sdf": b"[BODY]\nname=body mass=(1) inertia=(1,1,1) pos=(0,0,0) ori=(0,0,0)\n",
            ".tbf": b"Twin Turbo=true\nTurbo1 Size=100\nTurbo1 Engine RPM=6000\n",
            ".bbf": b"Boost=0.5\nBoost Time=2.0\n",
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
    assert set(result["extracted_paths"]) == {"cdf", "edf", "gdf", "sdf", "tbf", "bbf"}
    assert result["entries"]["cdf"]["archive_path"].endswith("bmw_m3_e36.cdf")
    assert len(result["entries"]["cdf"]["raw_sha256"]) == 64
    assert len(result["entries"]["cdf"]["decoded_sha256"]) == 64
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



def test_resolve_default_targets_matches_non_bmw_vehicle_stem():
    class Ford(FakeBFF):
        def __init__(self, path):
            self.path = Path(path)
            self.entries = [
                Entry("vehicles/physics/chassis/ford_mustang_2010.cdf", 1),
                Entry("vehicles/physics/engines/ford_mustang_2010.edf", 2),
                Entry("vehicles/physics/gearbox/common.gdf", 3),
                Entry("vehicles/physics/suspension/aarm_multilink.sdf", 4),
                Entry("vehicles/physics/turbo/gen_lowrpm_33.tbf", 5),
                Entry("vehicles/physics/turbo/nitrous.bbf", 6),
            ]

    archive = Ford("Ford_Mustang_2010.bff")
    result = bundle.resolve_default_targets(archive)

    assert result == {
        "cdf": "vehicles/physics/chassis/ford_mustang_2010.cdf",
        "edf": "vehicles/physics/engines/ford_mustang_2010.edf",
        "gdf": "vehicles/physics/gearbox/common.gdf",
        "sdf": "vehicles/physics/suspension/aarm_multilink.sdf",
        "tbf": "vehicles/physics/turbo/gen_lowrpm_33.tbf",
        "bbf": "vehicles/physics/turbo/nitrous.bbf",
    }


def test_resolve_default_targets_rejects_ambiguous_sdf():
    class AmbiguousSDF(FakeBFF):
        def __init__(self, path):
            super().__init__(path)
            self.entries.extend([
                Entry("vehicles/physics/suspension/alternate.sdf", 7),
            Entry("vehicles/physics/suspension/strut_multilink.sdf", 8),
            ])

    archive = AmbiguousSDF("UnknownVehicle.bff")
    archive.entries = [
        entry for entry in archive.entries
        if not entry.path.endswith("bmw_m3_e36.cdf")
        and not entry.path.endswith("bmw_m3_e36.edf")
    ]
    archive.entries.extend([
        Entry("vehicles/physics/chassis/unknown.cdf", 9),
        Entry("vehicles/physics/engines/unknown.edf", 10),
    ])
    try:
        bundle.resolve_default_targets(archive)
    except ValueError as exc:
        assert "ambiguous SDF" in str(exc), str(exc)
    else:
        raise AssertionError(
            "ambiguous SDF selection must fail closed; "
            f"resolved candidates={bundle.resolve_default_targets.__name__}"
        )
