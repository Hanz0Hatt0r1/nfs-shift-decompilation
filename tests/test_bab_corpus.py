from bab_corpus import (
    animation_payload_signature,
    build_bab_corpus_report,
    compare_animation_payloads,
)


def _bab(name, payload_sha, payload_size, bones=("Hips", "Spine")):
    return {
        "format": "SHIFT.BAB",
        "version": 1,
        "header": {"name": name},
        "bones": [{"name": b} for b in bones],
        "animation_payload_offset": 128,
        "animation_payload_size": payload_size,
        "animation_payload_sha256": payload_sha,
        "animation_string_hints": [{"text": "clip_idle"}],
    }


def test_bab_animation_signature_is_stable():
    bab = _bab("idle", "aaa", 16)
    sig = animation_payload_signature(bab)
    assert sig["format"] == "SHIFT.BABAnimationSignature/1"
    assert sig["bone_count"] == 2
    assert sig["animation_payload_sha256"] == "aaa"
    assert sig["animation_string_hints"] == ["clip_idle"]


def test_bab_payload_comparison_does_not_guess_animation_grammar():
    a = _bab("idle", "aaa", 16)
    b = _bab("run", "bbb", 24)
    result = compare_animation_payloads(a, b)
    assert result["same_skeleton"] is True
    assert result["same_payload"] is False
    assert result["payload_size_delta"] == -8
    assert result["bone_count_equal"] is True


def test_bab_corpus_groups_by_exact_bone_name_skeleton():
    rows = [
        {"archive": "A.bff", "path": "anim/idle.bab", "analysis": _bab("idle", "aaa", 16)},
        {"archive": "A.bff", "path": "anim/run.bab", "analysis": _bab("run", "bbb", 24)},
        {"archive": "B.bff", "path": "anim/other.bab", "analysis": _bab("other", "ccc", 12, ("Root",))},
        {"archive": "A.bff", "path": "foo.bmt", "analysis": {"format": "SHIFT.BMT"}},
    ]
    report = build_bab_corpus_report(rows)
    assert report["format"] == "SHIFT.BABCorpusReport/1"
    assert report["sample_count"] == 3
    assert report["skeleton_group_count"] == 2
    first = next(g for g in report["skeleton_groups"] if g["sample_count"] == 2)
    assert first["payload_hash_count"] == 2
    assert first["opaque_payloads_vary"] is True
