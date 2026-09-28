from render_submission_gate import validate_native_submission


def _command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "ready": True,
        "validation": {"valid": True, "blocking_reasons": []},
        "submeshes": [{
            "shader": {
                "source_payload_sha256": "a" * 64,
                "permutation_identity": {
                    "format": "SHIFT.ShaderPermutationIdentity/1",
                    "identity_sha256": "b" * 64,
                },
            },
        }],
    }


def test_native_submission_requires_complete_shader_provenance():
    result = validate_native_submission(_command())
    assert result["ready"] is True
    assert result["blocking_reasons"] == []


def test_native_submission_blocks_missing_payload_identity():
    command = _command()
    command["submeshes"][0]["shader"].pop("source_payload_sha256")
    result = validate_native_submission(command)
    assert result["ready"] is False
    assert "native-submission:shader-payload-identity-missing:0" in result["blocking_reasons"]


def test_native_submission_blocks_invalid_permutation_identity():
    command = _command()
    command["submeshes"][0]["shader"]["permutation_identity"] = {
        "format": "SHIFT.ShaderPermutationIdentity/1",
        "identity_sha256": "bad",
    }
    result = validate_native_submission(command)
    assert result["ready"] is False
    assert "native-submission:permutation-identity-invalid-sha256:0" in result["blocking_reasons"]


def test_native_submission_preserves_render_command_blockers():
    command = _command()
    command["ready"] = False
    command["validation"] = {
        "valid": False,
        "blocking_reasons": ["shader:pixel-source-missing"],
    }
    result = validate_native_submission(command)
    assert result["ready"] is False
    assert "render-command:not-ready" in result["blocking_reasons"]
    assert "shader:pixel-source-missing" in result["blocking_reasons"]
