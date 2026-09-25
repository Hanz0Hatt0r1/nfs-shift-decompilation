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
    assert "identity_sha256:missing" in validate_shader_permutation_identity(identity)


def test_shader_identity_validator_accepts_self_consistent_full_payload():
    import hashlib
    import json

    payload = {
        "version": 1,
        "vertex": {"byte_sha256": "v" * 64},
        "pixel": {"byte_sha256": "p" * 64},
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    identity_sha = hashlib.sha256(canonical).hexdigest()
    identity = {
        "format": "SHIFT.ShaderPermutationIdentity/1",
        "identity_sha256": identity_sha,
        "canonical_sha256": identity_sha,
        "payload": payload,
    }
    assert validate_shader_permutation_identity(identity) == []


def test_shader_identity_validator_rejects_tampered_full_payload():
    import hashlib
    import json

    payload = {
        "version": 1,
        "vertex": {"byte_sha256": "v" * 64},
        "pixel": {"byte_sha256": "p" * 64},
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    identity = {
        "format": "SHIFT.ShaderPermutationIdentity/1",
        "identity_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "payload": {**payload, "pixel": {"byte_sha256": "x" * 64}},
    }
    reasons = validate_shader_permutation_identity(identity)
    assert "canonical_sha256:mismatch" in reasons
    assert "identity_sha256:mismatch" in reasons
