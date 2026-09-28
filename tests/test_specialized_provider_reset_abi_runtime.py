import specialized_provider_reset_abi_runtime as runtime


def test_get_reset_abi_provider0():
    result = runtime.get_reset_abi(0)

    assert result["function"] == "FUN_007d3150"
    assert result["signature"] == (
        "void FUN_007d3150(undefined4 param_1)"
    )
    assert result["case_min"] == 0
    assert result["case_max"] == 39


def test_get_reset_abi_provider1():
    result = runtime.get_reset_abi(1)

    assert result["function"] == "FUN_007d48a0"
    assert result["case_min"] == 0
    assert result["case_max"] == 33


def test_validate_reset_dispatch_accepts_complete_case_domain():
    result = runtime.validate_reset_dispatch(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "case_count": 40,
            "cases": list(range(40)),
            "has_default": False,
            "errors": [],
        }
    )

    assert result["ready"] is True


def test_validate_reset_dispatch_rejects_missing_case():
    cases = list(range(40))
    cases.remove(17)
    result = runtime.validate_reset_dispatch(
        {
            "provider_id": 0,
            "scalar_count": 40,
            "case_count": 39,
            "cases": cases,
            "has_default": False,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "case-count-does-not-equal-scalar-count:39:40" in result["errors"]


def test_validate_reset_dispatch_rejects_default_case():
    result = runtime.validate_reset_dispatch(
        {
            "provider_id": 1,
            "scalar_count": 34,
            "case_count": 34,
            "cases": list(range(34)),
            "has_default": True,
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "reset-default-case-present" in result["errors"]


def test_parse_reset_dispatch_requires_exact_header():
    result = runtime.parse_reset_dispatch(
        "void FUN_007d3150(void)\n{\n}\n",
        provider_id=0,
    )

    assert result["ready"] is False
    assert "reset-function-header-not-found" in result["errors"]


def test_parse_reset_dispatch_validates_realistic_fixture():
    fixture = """
void FUN_007d3150(undefined4 param_1)
{
  switch(param_1) {
  case 0:
    DAT_00001000 = 0x3ff0000000000000;
    break;
  case 1:
    DAT_00001008 = 0x3ff0000000000000;
    break;
  }
}
"""
    result = runtime.parse_reset_dispatch(
        fixture,
        provider_id=0,
    )

    assert result["case_count"] == 2
    assert result["cases"] == [0, 1]
    assert result["ready"] is False
    assert any(
        error.startswith("case-domain-mismatch:")
        for error in result["errors"]
    )
