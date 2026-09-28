import specialized_provider_execution_schedule_runtime as runtime


def test_lhs_address_direct_and_loop_forms():
    direct = runtime._lhs_address(
        "_DAT_00001000 = x;",
        None,
    )
    loop = runtime._lhs_address(
        "*(double *)(&DAT_00001000 + local_10 * 8) = x;",
        3,
    )
    array = runtime._lhs_address(
        "(&DAT_00001000)[local_10] = x;",
        4,
    )

    assert direct == 0x1000
    assert loop == 0x1018
    assert array == 0x1020


def test_classify_factor_and_future_diagonal():
    factor = runtime._classify_assignment(
        "_DAT_00001008 = _DAT_00001010 * dVar1;",
        provider_id=0,
        current_pivot_diagonal=0x1000,
        future_pivot_diagonals={0x1020},
        loop_index=None,
        terminal=False,
    )
    diagonal = runtime._classify_assignment(
        "_DAT_00001020 = _DAT_00001020 - _DAT_00001018 * _DAT_00001008;",
        provider_id=0,
        current_pivot_diagonal=0x1000,
        future_pivot_diagonals={0x1020},
        loop_index=None,
        terminal=False,
    )

    assert factor == "factor-normalization"
    assert diagonal == "future-diagonal-update"


def test_classify_output_as_forward_rhs_before_terminal():
    kind = runtime._classify_assignment(
        "_DAT_00c23c70 = (_DAT_00c23c70 - _DAT_00001000 * _DAT_00c23c68) * dVar1;",
        provider_id=0,
        current_pivot_diagonal=0x1000,
        future_pivot_diagonals=set(),
        loop_index=None,
        terminal=False,
    )
    assert kind == "forward-rhs"


def test_classify_terminal_output_as_backsubstitution():
    kind = runtime._classify_assignment(
        "DAT_00c23c68 = DAT_00c23c68 - DAT_00c23b38 * DAT_00c23d68;",
        provider_id=0,
        current_pivot_diagonal=0x1000,
        future_pivot_diagonals=set(),
        loop_index=None,
        terminal=True,
    )
    assert kind == "backsubstitution"


def test_validate_schedule_shape():
    report = {
        "provider_id": 0,
        "scalar_count": 2,
        "blocks": [
            {
                "pivot_index": 0,
                "terminal": False,
                "events": [
                    {"kind": "pivot-reciprocal"},
                    {"kind": "factor-normalization"},
                ],
            },
            {
                "pivot_index": 1,
                "terminal": True,
                "events": [
                    {"kind": "pivot-reciprocal"},
                    {"kind": "backsubstitution"},
                ],
            },
        ],
        "errors": [],
    }
    result = runtime.validate_execution_schedule(report)

    assert result["ready"] is True
    assert result["errors"] == []
