import physics_provider_backend_runtime as runtime


class FakeBackend:
    def __init__(self, accept, prefix):
        self.accept = accept
        self.prefix = prefix
        self.calls = []

    def call(self, offset, *args):
        self.calls.append((offset, args))
        if offset == runtime.VTABLE["acceptance_probe"]:
            return self.accept
        if offset == runtime.VTABLE["reset_allocation_state"]:
            return f"{self.prefix}:rows"
        if offset == runtime.VTABLE["replace_primary_storage"]:
            return f"{self.prefix}:graph"
        if offset == runtime.VTABLE["replace_aux_storage"]:
            return f"{self.prefix}:aux"
        if offset == runtime.VTABLE["finalize"]:
            return 17
        raise AssertionError(offset)


def test_provider_probe_order_skips_rejected_slot():
    first = FakeBackend(False, "p0")
    second = FakeBackend(True, "p1")
    released = []
    out = runtime.run_provider_selection(
        scalar_count=40,
        initial_row_table="initial_rows",
        old_matrix="old_matrix",
        old_row_table="old_rows",
        backends=(first, second),
        release_matrix=released.append,
        release_rows=released.append,
    )
    assert out.selected_slot == 1
    assert out.accepted is True
    assert out.fallback is False
    assert released == ["old_matrix", "old_rows"]
    assert [call.vtable_offset for call in out.calls] == [0x14, 0x14, 0x0C, 0x04, 0x08, 0x2C]
    assert out.primary_storage == "p1:rows"
    assert out.graph_storage == "p1:graph"
    assert out.aux_storage == "p1:aux"
    assert out.secondary_domain == 17


def test_rejected_all_enters_generic_fallback_contract():
    first = FakeBackend(False, "p0")
    second = FakeBackend(False, "p1")
    out = runtime.run_provider_selection(
        scalar_count=40,
        initial_row_table="initial_rows",
        old_matrix="old_matrix",
        old_row_table="old_rows",
        backends=(first, second),
        release_matrix=lambda _: None,
        release_rows=lambda _: None,
    )
    assert out.selected_slot is None
    assert out.accepted is False
    assert out.fallback is True
    assert out.secondary_domain == 1600
    assert [call.vtable_offset for call in out.calls] == [0x14, 0x14]


def test_contract_freezes_observed_slots():
    c = runtime.build_fun_007b3820_backend_contract()
    assert c["slots"][0]["global_slot"] == "DAT_00c23da8"
    assert c["slots"][1]["global_slot"] == "DAT_00c23dac"
    assert c["vtable"]["0x14"]["method"] == "acceptance_probe"
    assert c["vtable"]["0x2c"]["observed_use"] == "result -> per-body +0xa8 domain"


def test_execution_summary_keeps_call_trace():
    backend = FakeBackend(True, "p0")
    out = runtime.run_provider_selection(
        scalar_count=4,
        initial_row_table="r",
        old_matrix="m",
        old_row_table="t",
        backends=(backend, None),
        release_matrix=lambda _: None,
        release_rows=lambda _: None,
    )
    summary = runtime.summarize_execution(out)
    assert summary["selected_slot"] == 0
    assert summary["call_trace"][0]["vtable_offset"] == 0x14
    assert summary["state_updates"]["per_body+0xa8"] == 17


def test_summary_preserves_graph_and_aux_slots():
    backend = FakeBackend(True, "p0")
    out = runtime.run_provider_selection(
        scalar_count=2,
        initial_row_table="r",
        old_matrix="m",
        old_row_table="t",
        backends=(backend, None),
        release_matrix=lambda _: None,
        release_rows=lambda _: None,
    )
    summary = runtime.summarize_execution(out)
    assert summary["state_updates"]["physics_system+0x40"] == "p0:graph"
    assert summary["state_updates"]["physics_system+0x44"] == "p0:aux"


def test_provider_2c_result_is_tracked_as_workspace_size():
    contract = runtime.build_fun_007b3820_backend_contract()
    assert contract["workspace_domain"]["provider_return_2c_equals_vtable_24"] is True
    assert contract["workspace_domain"]["provider0_value"] == 1190
    assert contract["workspace_domain"]["provider1_value"] == 746

 
def test_provider_2c_result_is_workspace_size():
    contract = runtime.build_fun_007b3820_backend_contract()
    assert contract["workspace_domain"]["provider_return_2c_equals_vtable_24"] is True
    assert contract["workspace_domain"]["provider0_value"] == 1190
    assert contract["workspace_domain"]["provider1_value"] == 746
