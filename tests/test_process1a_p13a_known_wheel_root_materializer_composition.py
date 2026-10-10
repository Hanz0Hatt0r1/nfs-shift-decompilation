import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'ghidra' / 'build_p1a_known_wheel_root_materializer_composition.py'
EVIDENCE = ROOT / 'evidence' / 'p1a_p13a_known_wheel_root_materializer_composition.json'
UPSTREAM = [
    ROOT / 'evidence' / 'p1a_p13a_slot01_wheel_root_materialization_persistence_handoff.json',
    ROOT / 'evidence' / 'p1a_p13a_fun00757d2c_runtime_indexed_wheel_root_persistence.json',
    ROOT / 'evidence' / 'p1a_p13a_fixed_wheel_root_leaf_handoffs.json',
    ROOT / 'evidence' / 'p1a_p13a_trampolined_wheel_root_lifetime.json',
    ROOT / 'evidence' / 'p1a_p13a_fun00760d93_derived_alias_closure.json',
    ROOT / 'evidence' / 'p1a_p13a_fun007572f0_indexed_wheel_root_lifetime.json',
    ROOT / 'evidence' / 'p1a_p13a_fun00757318_interior_alias_closure.json',
]


def module():
    spec = importlib.util.spec_from_file_location('p1a_known_materializers', TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def test_builder_reproduces_committed_evidence():
    m = module()
    upstream = [load(path) for path in UPSTREAM]
    assert m.build(*upstream) == load(EVIDENCE)


def test_composed_surface_counts_and_slot_coverage_are_exact():
    p = load(EVIDENCE)
    assert p['format'] == 'SHIFT.P1A.P13AKnownWheelRootMaterializerComposition/1'
    assert p['wheel_layout'] == {
        'count': 4,
        'roots': ['HDVehicle+0x400', 'HDVehicle+0xe80', 'HDVehicle+0x1900', 'HDVehicle+0x2380'],
        'slots': [0, 1, 2, 3],
        'stride': '+0xa80',
    }
    s = p['bounded_surface']
    assert s['exact_root_materializer_family_count'] == 6
    assert s['derived_alias_group_count'] == 2
    assert s['derived_alias_count'] == 9
    assert s['known_exact_root_persistent_escape_count'] == 0
    assert s['known_derived_alias_persistent_escape_count'] == 0
    assert s['known_derived_alias_wheel_root_reconstruction_count'] == 0


def test_transient_handoff_counts_are_preserved_without_persistence():
    s = load(EVIDENCE)['bounded_surface']
    families = {row['name']: row for row in s['exact_root_materializer_families']}
    assert families['FUN_007582f0']['transient_handoff_count'] == 4
    assert families['FUN_0076ed60']['transient_handoff_count'] == 4
    assert families['FUN_007653f9 -> FUN_00760d70/FUN_00760d93']['transient_handoff_count'] == 6
    assert families['FUN_007572f0/FUN_00757318']['exact_root_forward_count'] == 1
    assert all(row['persistent_exact_root_escape_found'] is False for row in families.values())


def test_composition_promotes_only_bounded_gate():
    a = load(EVIDENCE)['adjudication']
    assert a['p13a_known_wheel_root_materializer_surface_composed'] is True
    assert a['p13a_known_materializer_all_four_wheel_slots_covered'] is True
    assert a['p13a_known_materializer_exact_root_persistent_escape_found'] is False
    assert a['p13a_known_materializer_derived_alias_persistent_escape_found'] is False
    assert a['p13a_known_materializer_derived_alias_wheel_root_reconstruction_found'] is False
    for key in (
        'reconstructed_wheel_pointers_ruled_out',
        'runtime_generated_selected_wheel_pointer_stores_ruled_out',
        'callbacks_and_indirect_entry_ruled_out',
        'stored_or_escaped_aliases_ruled_out',
        'p13a_slot0_complete',
        'p13a_slot1_complete',
        'p1_3_control_producer_complete',
    ):
        assert a[key] is False
    assert a['external_provider_count'] == 7
