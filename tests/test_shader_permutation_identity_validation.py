from shader_permutation_identity import validate_shader_permutation_identity


def test_shader_identity_validator_accepts_compact_runtime_identity():
    identity = {
        "format": "SHIFT.ShaderPermutationIdentity/1",
        "identity_sha256": "a" * 64,
    }
    assert validate_shader_permutation_identity(identity) == []


def test_shader_identity_validator_rejects_wrong_format():
    identity = {
        "format": "SHIFT.ShaderPermutationIdentity/999",
        "identity_sha256": "a" * 64,
    }
    assert "format:invalid" in validate_shader_permutation_identity(identity)


def test_shader_identity_validator_rejects_malformed_payload_hash():
    identity = {
        "format": "SHIFT.ShaderPermutationIdentity/1",
        "identity_sha256": "a" * 64,
        "payload": {
            "vertex": {"byte_sha256": "short"},
            "pixel": {"byte_sha256": "b" * 64},
        },
    }
    assert "payload:vertex:byte_sha256:invalid" in validate_shader_permutation_identity(identity)


def test_shader_identity_validator_requires_identity_hash():
    identity = {"format": "SHIFT.ShaderPermutationIdentity/1"}
    assert "identity_sha256:invalid" in validate_shader_permutation_identity(identity)
