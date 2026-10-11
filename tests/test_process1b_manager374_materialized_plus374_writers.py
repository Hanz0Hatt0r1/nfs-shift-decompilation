import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_manager374_materialized_plus374_writers.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_materialized_plus374", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_lea_then_zero_displacement_store_is_candidate():
    data = module().scan_rows([
        (0x401000, "lea", "eax,[ecx+0x374]"),
        (0x401006, "mov", "DWORD PTR [eax],edx"),
    ])
    assert data["surface"]["materialized_plus_374_seed_count"] == 1
    assert data["surface"]["zero_displacement_write_candidate_count"] == 1
    row = data["surface"]["zero_displacement_write_candidates"][0]
    assert row["receiver_register"] == "ecx"
    assert row["materializer_site"] == "0x00401000"


def test_gpr_copy_preserves_materialized_address():
    data = module().scan_rows([
        (0x402000, "lea", "eax,[esi+0x374]"),
        (0x402006, "mov", "ebx,eax"),
        (0x402008, "mov", "DWORD PTR [ebx],ecx"),
    ])
    assert data["surface"]["materialized_plus_374_copy_count"] == 1
    assert data["surface"]["zero_displacement_write_candidate_count"] == 1
    row = data["surface"]["zero_displacement_write_candidates"][0]
    assert row["address_register"] == "ebx"
    assert row["copy_depth"] == 1


def test_arithmetic_clobber_kills_exact_address():
    data = module().scan_rows([
        (0x403000, "lea", "eax,[ecx+0x374]"),
        (0x403006, "add", "eax,0x4"),
        (0x403009, "mov", "DWORD PTR [eax],edx"),
    ])
    assert data["surface"]["zero_displacement_write_candidate_count"] == 0
    assert data["surface"]["termination_counts"]["tracked_register_clobber"] == 1


def test_partial_register_clobber_kills_exact_address():
    data = module().scan_rows([
        (0x404000, "lea", "eax,[ecx+0x374]"),
        (0x404006, "mov", "al,0x1"),
        (0x404008, "mov", "DWORD PTR [eax],edx"),
    ])
    assert data["surface"]["zero_displacement_write_candidate_count"] == 0
    assert data["surface"]["termination_counts"]["tracked_register_clobber"] == 1


def test_control_boundary_stops_exact_address_carry():
    data = module().scan_rows([
        (0x405000, "lea", "eax,[ecx+0x374]"),
        (0x405006, "jne", "0x405010"),
        (0x405008, "mov", "DWORD PTR [eax],edx"),
    ])
    assert data["surface"]["zero_displacement_write_candidate_count"] == 0
    assert data["surface"]["termination_counts"]["control_boundary"] == 1


def test_implicit_cmpxchg_eax_clobber_stops_stale_address():
    data = module().scan_rows([
        (0x406000, "lea", "eax,[ecx+0x374]"),
        (0x406006, "cmpxchg", "DWORD PTR [edi],edx"),
        (0x406009, "mov", "DWORD PTR [eax],ebx"),
    ])
    assert data["surface"]["zero_displacement_write_candidate_count"] == 0
    assert data["surface"]["termination_counts"]["implicit_tracked_register_clobber"] == 1


def test_popad_clobbers_materialized_address_register():
    data = module().scan_rows([
        (0x406100, "lea", "ebx,[ecx+0x374]"),
        (0x406106, "popad", ""),
        (0x406107, "mov", "DWORD PTR [ebx],eax"),
    ])
    assert data["surface"]["zero_displacement_write_candidate_count"] == 0
    assert data["surface"]["termination_counts"]["implicit_tracked_register_clobber"] >= 1


def test_indexed_lea_is_not_exact_receiver_plus374_seed():
    data = module().scan_rows([
        (0x407000, "lea", "eax,[ecx+edx*4+0x374]"),
        (0x407007, "mov", "DWORD PTR [eax],ebx"),
    ])
    assert data["surface"]["materialized_plus_374_seed_count"] == 0
    assert data["surface"]["zero_displacement_write_candidate_count"] == 0


def test_lock_prefixed_write_through_materialized_address_is_candidate():
    data = module().scan_rows([
        (0x408000, "lea", "ebx,[esi+0x374]"),
        (0x408006, "lock", "add DWORD PTR [ebx],0x1"),
    ])
    assert data["surface"]["zero_displacement_write_candidate_count"] == 1
    row = data["surface"]["zero_displacement_write_candidates"][0]
    assert row["mnemonic"] == "add"
    assert row["prefixes"] == ["lock"]


def test_semantic_gates_remain_fail_closed():
    adjudication = module().scan_rows([])["adjudication"]
    assert adjudication["whole_image_lea_materialized_plus_374_same_region_subset_complete"] is True
    assert adjudication["materialized_plus_374_candidate_receivers_classified"] is False
    assert adjudication["computed_plus_374_address_writer_surface_complete"] is False
    assert adjudication["unknown_or_unrelated_manager_root_alias_surface_complete"] is False
    assert adjudication["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adjudication["global_manager_root_origin_surface_complete"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
