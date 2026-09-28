import specialized_provider_rhs_stencil_runtime as runtime


def test_locate_workspace_and_output_addresses():
    workspace = runtime._locate_address(0x00C21808, 0)
    output = runtime._locate_address(0x00C23C68, 0)

    assert workspace.domain == "workspace"
    assert workspace.row == 1
    assert workspace.column == 1
    assert output.domain == "output_vector"
    assert output.index == 0


def test_rhs_references_resolve_row_pointer_flat_and_output_forms():
    rhs = (
        "*(double *)(*(int *)(&DAT_00c21698 + local_10 * 4) + 0x10) "
        "* *(double *)(&DAT_00c23c68 + local_10 * 8) "
        "+ (&DAT_00c21738)[local_10]"
    )
    refs = runtime._rhs_references(
        rhs,
        provider_id=0,
        loop_index=2,
    )

    assert [
        (ref.domain, ref.form, ref.row, ref.column, ref.index)
        for ref in refs
    ] == [
        ("workspace", "row-pointer-offset", 2, 2, None),
        ("output_vector", "flat-pointer", None, None, 2),
        ("workspace", "flat-array", 0, 2, None),
    ]


def test_assignment_statements_keep_loop_context_across_multiline_rhs():
    lines = [
        "for (local_10 = 1; local_10 < 3; local_10 = local_10 + 1) {",
        "  _DAT_00c21808 = _DAT_00c21800 -",
        "    *(double *)(&DAT_00c21738 + local_10 * 8);",
        "}",
        "DAT_00c21810 = 1.0;",
    ]

    statements = runtime._assignment_statements(lines)

    assert statements[0][0] == 1
    assert statements[0][2] == (1, 3)
    assert "_DAT_00c21808 =" in statements[0][1]
    assert statements[1][0] == 4
    assert statements[1][2] is None


def test_destination_candidates_resolve_flat_array_across_row_boundary():
    destination = runtime._destination_candidates(
        "(&DAT_00c23330)[local_10] = 0.0;",
        provider_id=0,
        loop_index=0x1F,
    )[0]

    assert destination.domain == "workspace"
    assert destination.row == 31
    assert destination.column == 1
    assert destination.form == "loop-array-lhs"


def test_summary_counts_destination_domains():
    report = {
        "provider_id": 0,
        "scalar_count": 2,
        "stencils": [
            {"destination": {"domain": "workspace"}, "rhs": []},
            {"destination": {"domain": "output_vector"}, "rhs": [{"x": 1}]},
            {"destination": {"domain": "global"}, "rhs": [1, 2]},
        ],
        "ready": True,
    }

    summary = runtime.summarize_rhs_stencils(report)

    assert summary["stencil_count"] == 3
    assert summary["workspace_destination_stencils"] == 1
    assert summary["output_destination_stencils"] == 1
    assert summary["global_destination_stencils"] == 1
    assert summary["max_rhs_reference_count"] == 2


def test_validate_rhs_stencils_requires_coordinates_for_workspace_refs():
    result = runtime.validate_rhs_stencils(
        {
            "provider_id": 0,
            "stencils": [
                {
                    "destination": {
                        "domain": "workspace",
                        "row": 0,
                        "column": 0,
                    },
                    "rhs": [
                        {"domain": "workspace"},
                    ],
                }
            ],
            "errors": [],
        }
    )

    assert result["ready"] is False
    assert "workspace-rhs-reference-missing-row-column" in result["errors"]


def test_rhs_references_preserve_mixed_source_order():
    rhs = (
        "DAT_00c21808 + (&DAT_00c21738)[local_10] "
        "+ DAT_00c21810 + *(double *)(&DAT_00c23c68 + local_10 * 8)"
    )
    refs = runtime._rhs_references(
        rhs,
        provider_id=0,
        loop_index=1,
    )

    assert [ref.form for ref in refs] == [
        "direct",
        "flat-array",
        "direct",
        "flat-pointer",
    ]
