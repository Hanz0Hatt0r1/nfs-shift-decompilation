import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_manager374_materialized_esp_spill_reload.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_materialized_esp", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sub_esp_normalization_preserves_same_logical_cell():
    data = module().scan_rows([
        (0x401000, "lea", "eax,[ecx+0x374]"),
        (0x401006, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x40100A, "sub", "esp,0x10"),
        (0x40100D, "mov", "edx,DWORD PTR [esp+0x18]"),
        (0x401011, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["esp_relative_spill_count"] == 1
    assert data["surface"]["esp_relative_reload_count"] == 1
    assert data["surface"]["esp_normalization_event_count"] == 1
    spill = data["surface"]["esp_relative_spills"][0]
    reload = data["surface"]["esp_relative_reloads"][0]
    assert spill["logical_offset"] == 8
    assert reload["logical_offset"] == 8
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 1


def test_lea_esp_normalization_preserves_same_logical_cell():
    data = module().scan_rows([
        (0x402000, "lea", "eax,[esi+0x374]"),
        (0x402006, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x40200A, "lea", "esp,[esp-0x20]"),
        (0x40200E, "mov", "ebx,DWORD PTR [esp+0x28]"),
        (0x402012, "lock", "add DWORD PTR [ebx],0x1"),
    ])
    assert data["surface"]["esp_relative_reload_count"] == 1
    assert data["surface"]["esp_normalization_events"][0]["sp_position"] == -0x20
    row = data["surface"]["reload_derived_zero_displacement_write_candidates"][0]
    assert row["address_register"] == "ebx"
    assert row["receiver_register"] == "esi"


def test_add_esp_can_restore_original_coordinate():
    data = module().scan_rows([
        (0x403000, "sub", "esp,0x10"),
        (0x403003, "lea", "eax,[ecx+0x374]"),
        (0x403009, "mov", "DWORD PTR [esp+0x4],eax"),
        (0x40300D, "add", "esp,0x10"),
        (0x403010, "mov", "edx,DWORD PTR [esp-0xc]"),
        (0x403014, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["esp_relative_reload_count"] == 1
    assert data["surface"]["esp_relative_spills"][0]["logical_offset"] == -0xC
    assert data["surface"]["esp_relative_reloads"][0]["logical_offset"] == -0xC


def test_push_is_stack_barrier():
    data = module().scan_rows([
        (0x404000, "lea", "eax,[ecx+0x374]"),
        (0x404006, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x40400A, "push", "esi"),
        (0x40400B, "mov", "edx,DWORD PTR [esp+0xc]"),
        (0x40400F, "mov", "DWORD PTR [edx],ebx"),
    ])
    assert data["surface"]["esp_relative_reload_count"] == 0
    assert data["surface"]["termination_counts"]["stack_barrier"] >= 1


def test_non_mov_esp_reference_is_cell_barrier():
    data = module().scan_rows([
        (0x405000, "lea", "eax,[ecx+0x374]"),
        (0x405006, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x40500A, "cmp", "DWORD PTR [esp+0x20],0x0"),
        (0x40500F, "mov", "edx,DWORD PTR [esp+0x8]"),
    ])
    assert data["surface"]["esp_relative_reload_count"] == 0
    assert data["surface"]["termination_counts"]["esp_memory_reference_barrier"] == 1


def test_overlapping_dword_store_invalidates_tracked_cell():
    data = module().scan_rows([
        (0x406000, "lea", "eax,[ecx+0x374]"),
        (0x406006, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x40600A, "mov", "DWORD PTR [esp+0xa],esi"),
        (0x40600E, "mov", "edx,DWORD PTR [esp+0x8]"),
        (0x406012, "mov", "DWORD PTR [edx],ebx"),
    ])
    assert data["surface"]["esp_relative_reload_count"] == 0
    assert data["surface"]["termination_counts"]["esp_dword_overlap_invalidation"] == 1


def test_nonoverlapping_dword_store_preserves_tracked_cell():
    data = module().scan_rows([
        (0x407000, "lea", "eax,[ecx+0x374]"),
        (0x407006, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x40700A, "mov", "DWORD PTR [esp+0xc],esi"),
        (0x40700E, "mov", "edx,DWORD PTR [esp+0x8]"),
        (0x407012, "mov", "DWORD PTR [edx],ebx"),
    ])
    assert data["surface"]["esp_relative_reload_count"] == 1
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 1


def test_partial_width_stack_access_cannot_transport_pointer():
    data = module().scan_rows([
        (0x408000, "lea", "eax,[ecx+0x374]"),
        (0x408006, "mov", "WORD PTR [esp+0x8],ax"),
        (0x40800A, "mov", "edx,DWORD PTR [esp+0x8]"),
        (0x40800E, "mov", "DWORD PTR [edx],esi"),
    ])
    assert data["surface"]["esp_relative_spill_count"] == 0
    assert data["surface"]["esp_relative_reload_count"] == 0
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 0


def test_arbitrary_esp_write_breaks_old_cell_identity():
    data = module().scan_rows([
        (0x409000, "lea", "eax,[ecx+0x374]"),
        (0x409006, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x40900A, "mov", "esp,ebp"),
        (0x40900C, "mov", "edx,DWORD PTR [esp+0x8]"),
    ])
    assert data["surface"]["esp_relative_reload_count"] == 0
    assert data["surface"]["termination_counts"]["unsupported_esp_write"] >= 1


def test_xchg_second_operand_through_reloaded_pointer_is_write_candidate():
    data = module().scan_rows([
        (0x40A000, "lea", "eax,[ecx+0x374]"),
        (0x40A006, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x40A00A, "mov", "edx,DWORD PTR [esp+0x8]"),
        (0x40A00E, "xchg", "esi,DWORD PTR [edx]"),
    ])
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 1
    row = data["surface"]["reload_derived_zero_displacement_write_candidates"][0]
    assert row["operand_index"] == 1
    assert row["mnemonic"] == "xchg"


def test_read_through_reloaded_pointer_is_not_write_candidate():
    data = module().scan_rows([
        (0x40B000, "lea", "eax,[ecx+0x374]"),
        (0x40B006, "mov", "DWORD PTR [esp+0x8],eax"),
        (0x40B00A, "mov", "edx,DWORD PTR [esp+0x8]"),
        (0x40B00E, "cmp", "DWORD PTR [edx],0x0"),
    ])
    assert data["surface"]["reload_derived_zero_displacement_write_candidate_count"] == 0
    assert data["surface"]["reload_derived_other_dereference_count"] == 1


def test_semantic_gates_remain_fail_closed():
    adjudication = module().scan_rows([])["adjudication"]
    assert adjudication["materialized_plus_374_esp_spill_reload_normalized_subset_complete"] is True
    assert adjudication["esp_reload_write_candidate_receivers_classified"] is False
    assert adjudication["computed_plus_374_address_writer_surface_complete"] is False
    assert adjudication["unknown_or_unrelated_manager_root_alias_surface_complete"] is False
    assert adjudication["global_helper_non_vtable_indirect_setter_surface_complete"] is False
    assert adjudication["global_manager_root_origin_surface_complete"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
