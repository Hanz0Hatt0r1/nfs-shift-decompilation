import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_manager374_materialized_ebp_spill_reload.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_materialized_ebp", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ebp_spill_reload_then_write_is_new_candidate():
    data = module().scan_rows([
        (0x401000, "lea", "eax,[ecx+0x374]"),
        (0x401006, "mov", "DWORD PTR [ebp-0x8],eax"),
        (0x401009, "mov", "edx,DWORD PTR [ebp-0x8]"),
        (0x40100C, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["ebp_relative_spill_count"] == 1
    assert data["surface"]["ebp_relative_reload_count"] == 1
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 1
    row = data["surface"]["reload_derived_zero_displacement_write_candidates"][0]
    assert row["receiver_register"] == "ecx"
    assert row["address_register"] == "edx"
    assert row["reload_depth"] == 1


def test_direct_materialized_write_without_reload_is_not_new_candidate():
    data = module().scan_rows([
        (0x402000, "lea", "eax,[ecx+0x374]"),
        (0x402006, "mov", "DWORD PTR [eax],edx"),
    ])
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 0


def test_unknown_overwrite_kills_tracked_ebp_cell():
    data = module().scan_rows([
        (0x403000, "lea", "eax,[ecx+0x374]"),
        (0x403006, "mov", "DWORD PTR [ebp-0x4],eax"),
        (0x403009, "mov", "DWORD PTR [ebp-0x4],0x0"),
        (0x403010, "mov", "edx,DWORD PTR [ebp-0x4]"),
        (0x403013, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["ebp_relative_reload_count"] == 0
    assert data["surface"]["termination_counts"]["tracked_ebp_cell_overwrite"] == 1
    assert data["surface"]["termination_counts"]["ebp_memory_write_invalidation"] == 1
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 0


def test_rmw_on_any_ebp_cell_invalidates_tracked_cells_conservatively():
    data = module().scan_rows([
        (0x403100, "lea", "eax,[ecx+0x374]"),
        (0x403106, "mov", "DWORD PTR [ebp-0x8],eax"),
        (0x403109, "add", "DWORD PTR [ebp-0x20],0x1"),
        (0x40310D, "mov", "edx,DWORD PTR [ebp-0x8]"),
        (0x403110, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["ebp_relative_reload_count"] == 0
    assert data["surface"]["termination_counts"]["ebp_memory_write_invalidation"] == 1
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 0


def test_partial_register_spill_cannot_install_pointer_provenance():
    data = module().scan_rows([
        (0x403200, "lea", "eax,[ecx+0x374]"),
        (0x403206, "mov", "WORD PTR [ebp-0x8],ax"),
        (0x40320A, "mov", "edx,DWORD PTR [ebp-0x8]"),
        (0x40320D, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["ebp_relative_spill_count"] == 0
    assert data["surface"]["ebp_relative_reload_count"] == 0
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 0


def test_partial_register_reload_cannot_recover_pointer_provenance():
    data = module().scan_rows([
        (0x403300, "lea", "eax,[ecx+0x374]"),
        (0x403306, "mov", "DWORD PTR [ebp-0x8],eax"),
        (0x40330A, "mov", "dx,WORD PTR [ebp-0x8]"),
        (0x40330E, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["ebp_relative_spill_count"] == 1
    assert data["surface"]["ebp_relative_reload_count"] == 0
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 0


def test_partial_register_copy_cannot_propagate_pointer_provenance():
    data = module().scan_rows([
        (0x403400, "lea", "eax,[ecx+0x374]"),
        (0x403406, "mov", "bx,ax"),
        (0x403409, "mov", "DWORD PTR [ebp-0x8],ebx"),
        (0x40340D, "mov", "edx,DWORD PTR [ebp-0x8]"),
        (0x403410, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["ebp_relative_spill_count"] == 0
    assert data["surface"]["ebp_relative_reload_count"] == 0
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 0


def test_ebp_change_invalidates_cells():
    data = module().scan_rows([
        (0x404000, "lea", "eax,[ecx+0x374]"),
        (0x404006, "mov", "DWORD PTR [ebp-0xc],eax"),
        (0x404009, "mov", "ebp,esi"),
        (0x40400B, "mov", "edx,DWORD PTR [ebp-0xc]"),
        (0x40400E, "mov", "DWORD PTR [edx],eax"),
    ])
    assert data["surface"]["ebp_relative_reload_count"] == 0
    assert data["surface"]["termination_counts"]["ebp_frame_invalidation"] == 1


def test_control_boundary_clears_registers_and_ebp_cells():
    data = module().scan_rows([
        (0x405000, "lea", "eax,[ecx+0x374]"),
        (0x405006, "mov", "DWORD PTR [ebp-0x10],eax"),
        (0x405009, "jne", "0x405020"),
        (0x40500B, "mov", "edx,DWORD PTR [ebp-0x10]"),
        (0x40500E, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["ebp_relative_reload_count"] == 0
    assert data["surface"]["termination_counts"]["control_boundary"] == 1


def test_copy_after_reload_preserves_reload_provenance():
    data = module().scan_rows([
        (0x406000, "lea", "eax,[esi+0x374]"),
        (0x406006, "mov", "DWORD PTR [ebp-0x14],eax"),
        (0x406009, "mov", "edx,DWORD PTR [ebp-0x14]"),
        (0x40600C, "mov", "ebx,edx"),
        (0x40600E, "lock", "add DWORD PTR [ebx],0x1"),
    ])
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 1
    row = data["surface"]["reload_derived_zero_displacement_write_candidates"][0]
    assert row["address_register"] == "ebx"
    assert row["receiver_register"] == "esi"
    assert row["copy_depth"] == 1


def test_partial_register_clobber_after_reload_kills_pointer():
    data = module().scan_rows([
        (0x407000, "lea", "eax,[ecx+0x374]"),
        (0x407006, "mov", "DWORD PTR [ebp-0x18],eax"),
        (0x407009, "mov", "edx,DWORD PTR [ebp-0x18]"),
        (0x40700C, "mov", "dl,0x1"),
        (0x40700E, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 0
    assert data["surface"]["termination_counts"]["tracked_register_clobber"] == 1


def test_esp_spill_is_outside_this_subset():
    data = module().scan_rows([
        (0x408000, "lea", "eax,[ecx+0x374]"),
        (0x408006, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x40800A, "mov", "edx,DWORD PTR [esp+0x8]"),
        (0x40800E, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["ebp_relative_spill_count"] == 0
    assert data["surface"]["ebp_relative_reload_count"] == 0
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 0


def test_semantic_gates_remain_fail_closed():
    adjudication = module().scan_rows([])["adjudication"]
    assert adjudication["materialized_plus_374_ebp_spill_reload_subset_complete"] is True
    assert adjudication["ebp_reload_write_candidate_receivers_classified"] is False
    assert adjudication["computed_plus_374_address_writer_surface_complete"] is False
    assert adjudication["unknown_or_unrelated_manager_root_alias_surface_complete"] is False
    assert adjudication["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adjudication["global_manager_root_origin_surface_complete"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
