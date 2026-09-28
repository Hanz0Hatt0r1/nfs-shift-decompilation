import specialized_provider_storage_runtime as runtime


def test_provider0_storage_chain_is_contiguous():
    layout = runtime.get_storage_layout(0)
    assert layout.row_pointer_base == 0x00C21698
    assert layout.row_pointer_bytes == 160
    assert layout.factor_workspace_base == 0x00C21738
    assert layout.factor_workspace_doubles == 1190
    assert layout.factor_workspace_base + layout.factor_workspace_bytes == layout.output_vector_base
    assert layout.output_vector_base == 0x00C23C68
    assert layout.output_vector_doubles == 40
    assert runtime.validate_storage_layout(layout)["ready"]


def test_provider1_storage_chain_is_contiguous():
    layout = runtime.get_storage_layout(1)
    assert layout.row_pointer_bytes == 136
    assert layout.factor_workspace_base == 0x00C1FE38
    assert layout.factor_workspace_doubles == 746
    assert layout.factor_workspace_base + layout.factor_workspace_bytes == layout.output_vector_base
    assert layout.output_vector_base == 0x00C21588
    assert layout.output_vector_doubles == 34
    assert runtime.validate_storage_layout(layout)["ready"]


def test_plus_24_constants_are_exact_workspace_double_counts():
    c = runtime.build_storage_contract()
    p0, p1 = c["providers"]
    assert p0["accessors"]["+0x24"]["returns"] == 1190
    assert p1["accessors"]["+0x24"]["returns"] == 746


def test_plus_28_constants_are_exact_scalar_counts():
    c = runtime.build_storage_contract()
    p0, p1 = c["providers"]
    assert p0["accessors"]["+0x28"]["returns"] == 40
    assert p1["accessors"]["+0x28"]["returns"] == 34


def test_accessor_04_08_0c_return_exact_region_bases():
    c = runtime.build_storage_contract()
    p0, p1 = c["providers"]
    assert p0["accessors"]["+0x04"]["returns"] == "0xc23c68"
    assert p0["accessors"]["+0x08"]["returns"] == "0xc21738"
    assert p0["accessors"]["+0x0c"]["returns"] == "0xc21698"
    assert p1["accessors"]["+0x04"]["returns"] == "0xc21588"
    assert p1["accessors"]["+0x08"]["returns"] == "0xc1fe38"
    assert p1["accessors"]["+0x0c"]["returns"] == "0xc1fdb0"


def test_plus_2c_globals_remain_opaque():
    c = runtime.build_storage_contract()
    p0, p1 = c["providers"]
    assert p0["accessors"]["+0x2c"]["returns_global"] == "DAT_00b8d8ec"
    assert p1["accessors"]["+0x2c"]["returns_global"] == "DAT_00b8d8f0"
