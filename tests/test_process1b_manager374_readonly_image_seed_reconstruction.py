import importlib.util
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_manager374_readonly_image_seed_reconstruction.py"
TARGET = 0x00BC9FC0


def module():
    spec = importlib.util.spec_from_file_location("p1b_ro_seed", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def reader(mapping):
    def read(address):
        return mapping.get(address)
    return read


def test_readonly_seed_plus_immediate_reconstructs_exact_root():
    mod = module()
    data = mod.scan_rows([
        (0x401000, "mov", "eax,DWORD PTR ds:0x00aa7000"),
        (0x401006, "add", "eax,0x20"),
    ], reader({0x00AA7000: (TARGET - 0x20, ".rdata")}))
    assert data["surface"]["readonly_image_seed_load_count"] == 1
    assert data["surface"]["nontrivial_exact_root_reconstruction_count"] == 1
    row = data["surface"]["nontrivial_exact_root_reconstructions"][0]
    assert row["site"] == "0x00401006"
    assert row["register"] == "eax"
    assert row["sources"][0]["seed_section"] == ".rdata"


def test_gpr_copy_then_lea_preserves_memory_seed_lineage():
    mod = module()
    data = mod.scan_rows([
        (0x402000, "mov", "esi,DWORD PTR [0x00aa8000]"),
        (0x402006, "mov", "eax,esi"),
        (0x402008, "lea", "edx,[eax+0x40]"),
    ], reader({0x00AA8000: (TARGET - 0x40, ".text")}))
    rows = data["surface"]["nontrivial_exact_root_reconstructions"]
    assert len(rows) == 1
    assert rows[0]["register"] == "edx"
    assert rows[0]["kind"] == "lea-base-disp"


def test_two_readonly_seeds_can_merge_with_exact_binary_arithmetic():
    mod = module()
    left = 0x00BC0000
    right = TARGET - left
    data = mod.scan_rows([
        (0x403000, "mov", "eax,DWORD PTR [0x00aa9000]"),
        (0x403006, "mov", "edx,DWORD PTR [0x00aa9004]"),
        (0x40300C, "add", "eax,edx"),
    ], reader({
        0x00AA9000: (left, ".rdata"),
        0x00AA9004: (right, ".rdata"),
    }))
    row = data["surface"]["nontrivial_exact_root_reconstructions"][0]
    assert len(row["sources"]) == 2


def test_direct_exact_root_readonly_seed_is_reported_separately():
    mod = module()
    data = mod.scan_rows([
        (0x404000, "mov", "eax,DWORD PTR [0x00aaa000]"),
    ], reader({0x00AAA000: (TARGET, ".rdata")}))
    assert data["surface"]["exact_root_formation_count"] == 1
    assert data["surface"]["direct_exact_root_seed_count"] == 1
    assert data["surface"]["nontrivial_exact_root_reconstruction_count"] == 0


def test_control_boundary_drops_seed_before_later_arithmetic():
    mod = module()
    data = mod.scan_rows([
        (0x405000, "mov", "eax,DWORD PTR [0x00aab000]"),
        (0x405006, "call", "0x500000"),
        (0x40500B, "add", "eax,0x20"),
    ], reader({0x00AAB000: (TARGET - 0x20, ".rdata")}))
    assert data["surface"]["nontrivial_exact_root_reconstruction_count"] == 0
    assert data["surface"]["control_reset_count"] == 1


def test_unresolved_or_writable_memory_load_is_not_a_seed():
    mod = module()
    data = mod.scan_rows([
        (0x406000, "mov", "eax,DWORD PTR [0x00b82000]"),
        (0x406006, "add", "eax,0x20"),
    ], reader({}))
    assert data["surface"]["readonly_image_seed_load_count"] == 0
    assert data["surface"]["exact_root_formation_count"] == 0


def test_self_xor_breaks_seed_lineage():
    mod = module()
    data = mod.scan_rows([
        (0x407000, "mov", "eax,DWORD PTR [0x00aac000]"),
        (0x407006, "xor", "eax,eax"),
        (0x407008, "add", "eax,0xbc9fc0"),
    ], reader({0x00AAC000: (0x12345678, ".rdata")}))
    assert data["surface"]["exact_root_formation_count"] == 0


def test_partial_register_clobber_kills_exact_seed_value():
    mod = module()
    data = mod.scan_rows([
        (0x408000, "mov", "eax,DWORD PTR [0x00aad000]"),
        (0x408006, "mov", "al,0x1"),
        (0x408008, "add", "eax,0x20"),
    ], reader({0x00AAD000: (TARGET - 0x20, ".rdata")}))
    assert data["surface"]["exact_root_formation_count"] == 0
    assert data["surface"]["unsupported_tracked_clobber_count"] == 1


def test_window_expiry_prevents_late_reconstruction():
    mod = module()
    rows = [(0x409000, "mov", "eax,DWORD PTR [0x00aae000]")]
    rows += [(0x409001 + i, "nop", "") for i in range(mod.WINDOW + 1)]
    rows.append((0x409100, "add", "eax,0x20"))
    data = mod.scan_rows(rows, reader({0x00AAE000: (TARGET - 0x20, ".rdata")}))
    assert data["surface"]["exact_root_formation_count"] == 0
    assert data["surface"]["window_expiration_count"] == 1


def test_cdq_implicit_edx_clobber_kills_seed():
    mod = module()
    data = mod.scan_rows([
        (0x40A000, "mov", "edx,DWORD PTR [0x00aaf000]"),
        (0x40A006, "cdq", ""),
        (0x40A007, "add", "edx,0x20"),
    ], reader({0x00AAF000: (TARGET - 0x20, ".rdata")}))
    assert data["surface"]["exact_root_formation_count"] == 0
    assert data["surface"]["implicit_tracked_clobber_count"] == 1


def test_xchg_clobbers_both_tracked_operands_fail_closed():
    mod = module()
    data = mod.scan_rows([
        (0x40B000, "mov", "eax,DWORD PTR [0x00aaf100]"),
        (0x40B006, "mov", "edx,DWORD PTR [0x00aaf104]"),
        (0x40B00C, "xchg", "eax,edx"),
        (0x40B00E, "add", "edx,0x20"),
    ], reader({
        0x00AAF100: (0x11111111, ".rdata"),
        0x00AAF104: (TARGET - 0x20, ".rdata"),
    }))
    assert data["surface"]["exact_root_formation_count"] == 0
    assert data["surface"]["implicit_tracked_clobber_count"] == 2


def test_leave_invalidates_tracked_ebp():
    mod = module()
    data = mod.scan_rows([
        (0x40C000, "mov", "ebp,DWORD PTR [0x00aaf200]"),
        (0x40C006, "leave", ""),
        (0x40C007, "add", "ebp,0x20"),
    ], reader({0x00AAF200: (TARGET - 0x20, ".rdata")}))
    assert data["surface"]["exact_root_formation_count"] == 0
    assert data["surface"]["implicit_tracked_clobber_count"] == 1


def test_rep_string_instruction_invalidates_tracked_index_and_count_registers():
    mod = module()
    data = mod.scan_rows([
        (0x40D000, "mov", "esi,DWORD PTR [0x00aaf300]"),
        (0x40D006, "mov", "ecx,DWORD PTR [0x00aaf304]"),
        (0x40D00C, "rep", "movsd DWORD PTR es:[edi],DWORD PTR ds:[esi]"),
        (0x40D00E, "add", "esi,0x20"),
    ], reader({
        0x00AAF300: (TARGET - 0x20, ".rdata"),
        0x00AAF304: (0x10, ".rdata"),
    }))
    assert data["surface"]["exact_root_formation_count"] == 0
    assert data["surface"]["implicit_tracked_clobber_count"] >= 2


def make_pe32(path: Path):
    blob = bytearray(0x800)
    blob[:2] = b"MZ"
    struct.pack_into("<I", blob, 0x3C, 0x80)
    pe = 0x80
    blob[pe:pe + 4] = b"PE\0\0"
    struct.pack_into("<H", blob, pe + 6, 2)
    struct.pack_into("<H", blob, pe + 20, 0xE0)
    optional = pe + 24
    struct.pack_into("<H", blob, optional, 0x10B)
    struct.pack_into("<I", blob, optional + 28, 0x00400000)
    table = optional + 0xE0
    blob[table:table + 8] = b".rdata\0\0"
    struct.pack_into("<IIII", blob, table + 8, 0x100, 0x2000, 0x100, 0x400)
    table2 = table + 40
    blob[table2:table2 + 8] = b".data\0\0\0"
    struct.pack_into("<IIII", blob, table2 + 8, 0x100, 0x3000, 0x100, 0x500)
    struct.pack_into("<I", blob, 0x420, TARGET - 0x10)
    struct.pack_into("<I", blob, 0x520, TARGET)
    path.write_bytes(blob)


def test_pe_reader_accepts_rdata_and_rejects_data(tmp_path):
    path = tmp_path / "sample.exe"
    make_pe32(path)
    read_seed, sections = module().pe_readonly_seed_reader(path)
    assert {s["name"] for s in sections} == {".rdata", ".data"}
    assert read_seed(0x00402020) == (TARGET - 0x10, ".rdata")
    assert read_seed(0x00403020) is None


def test_semantic_gates_remain_fail_closed():
    adj = module().scan_rows([], reader({}))["adjudication"]
    assert adj["bounded_readonly_image_memory_seed_reconstruction_subset_complete"] is True
    assert adj["memory_load_or_opaque_runtime_reconstruction_complete"] is False
    assert adj["independent_unnamed_opaque_or_external_runtime_root_synthesis_complete"] is False
    assert adj["unrecognized_runtime_transform_root_origin_surface_complete"] is False
    assert adj["global_manager_root_origin_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_absolute_memory_syntaxes_are_normalized():
    mod = module()
    assert mod.abs_memory_address("DWORD PTR ds:0x00aa7000") == 0x00AA7000
    assert mod.abs_memory_address("DWORD PTR [0x00aa7000]") == 0x00AA7000
    assert mod.abs_memory_address("[eax+0x4]") is None
