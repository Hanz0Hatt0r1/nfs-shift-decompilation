import physics_provider_backend_runtime as backend
import provider_dispatch_static_contract as contract
import specialized_provider_vtable_lifecycle_runtime as lifecycle


def test_static_contract_validates_fail_closed():
    result = contract.validate_contract()
    assert result["ready"] is True
    assert result["errors"] == []


def test_selector_domain_matches_existing_provider_backend():
    slots = backend.provider_slots()
    assert tuple(slot.selector_index for slot in slots) == (0, 1)
    assert tuple(slot.global_slot for slot in slots) == (
        contract.PROVIDERS[0]["selector_global"],
        contract.PROVIDERS[1]["selector_global"],
    )


def test_shipped_vtables_and_dispatch_targets_match_lifecycle_contract():
    for provider_id in (0, 1):
        expected = contract.PROVIDERS[provider_id]
        table = lifecycle.get_vtable_lifecycle(provider_id)
        assert expected["vtable"] == table.vtable_address
        for slot in contract.SLOT_ROLES:
            assert expected["slots"][slot] == table.slots[slot]


def test_solve_cleanup_and_reset_have_exact_conditional_target_sets():
    assert contract.concrete_targets_for_slot(0x18) == (0x007C7200, 0x007CDFC0)
    assert contract.concrete_targets_for_slot(0x1C) == (0x007D3150, 0x007D48A0)
    assert contract.concrete_targets_for_slot(0x20) == (0x007D43C0, 0x007D5600)


def test_dispatch_contract_does_not_invent_unique_runtime_target():
    result = contract.build_contract()
    assert result["graph_effect"]["conditional_target_set_closed"] is True
    assert result["graph_effect"]["unique_runtime_target_known_statically"] is False
    for site in result["dispatch_sites"].values():
        assert site["target_set_evidence_state"] == "verified"
        assert len(site["conditional_targets"]) == 2


def test_instruction_callsites_remain_unknown_until_targeted_export():
    result = contract.build_contract()
    for site in result["dispatch_sites"].values():
        assert site["instruction_address"] is None
        assert site["instruction_evidence_state"] == "unknown"

    plan = result["targeted_export_plan"]
    assert plan["functions"] == ["0x7b2210", "0x7b3820", "0x7b3f40"]
    assert plan["fail_closed"] is True


def test_builtin_fallback_remains_explicit():
    result = contract.build_contract()
    assert result["provider_storage"]["physics_system_offset"] == "0x48"
    assert result["provider_storage"]["null_after_domain"] is True
    assert result["builtin_fallback"] == {
        "condition": "physics_system+0x48 == NULL",
        "target": "0x7b0f20",
        "evidence_state": "proven",
    }


def test_unknown_slot_is_rejected_instead_of_guessed():
    try:
        contract.concrete_targets_for_slot(0x24)
    except ValueError as exc:
        assert "unsupported provider vtable slot" in str(exc)
    else:
        raise AssertionError("unsupported slot must fail closed")
