from pathlib import Path
import tempfile
import zipfile

from tools import audit_fxo_shader_corpus as runtime


def test_materialize_bffs_keeps_zip_backing_files_alive():
    from contextlib import ExitStack

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        archive_path = root / "Vehicles.zip"
        with zipfile.ZipFile(archive_path, "w") as z:
            z.writestr("cars/A.bff", b"a")
        with ExitStack() as stack:
            paths = runtime._materialize_bffs([archive_path], stack)
            assert len(paths) == 1
            assert paths[0].exists()
            assert paths[0].read_bytes() == b"a"


def test_profile_payload_aggregates_stage_model_and_opcodes(monkeypatch):
    class Blob:
        offset = 0
        end = 16
        stage = "pixel"
        major = 3
        minor = 0

    class Program:
        stage = "pixel"
        major = 3
        minor = 0
        instructions = [
            type("Instruction", (), {"name": "MOV"})(),
            type("Instruction", (), {"name": "TEX"})(),
        ]
        unsupported_opcodes = []

    monkeypatch.setattr(runtime, "parse_shader_blobs", lambda _payload: [Blob()])
    monkeypatch.setattr(runtime, "parse_program", lambda *args: Program())

    report = runtime._profile_payload(b"shader")

    assert report["blob_count"] == 1
    assert report["instruction_count"] == 2
    assert report["stages"] == {"pixel": 1}
    assert report["shader_models"] == {"3.0": 1}
    assert report["opcodes"] == {"MOV": 1, "TEX": 1}


def test_counted_raw_payloads_can_be_deduplicated_without_decoding():
    assert runtime._sha256(b"x") == runtime._sha256(b"x")
    assert runtime._sha256(b"x") != runtime._sha256(b"y")


def test_profile_shader_corpus_deduplicates_raw_fxo_before_decode(
    monkeypatch,
    tmp_path,
):
    paths = [tmp_path / "A.bff", tmp_path / "B.bff"]

    class Entry:
        def __init__(self, index, path):
            self.index = index
            self.path = path
            self.type = 2
            self.compressed_size = 4
            self.uncompressed_size = 8

    class Archive:
        entries = [Entry(0, "render/shaders/common.fxo")]

        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def raw_payload(self, _entry):
            return b"same"

        def extract_entry(self, _entry, type2="lzx"):
            assert type2 == "lzx"
            return b"decoded"

    decode_calls = []

    monkeypatch.setattr(runtime, "_materialize_bffs", lambda _inputs, _stack: paths)
    monkeypatch.setattr(runtime, "BFF", Archive)
    monkeypatch.setattr(
        runtime,
        "_profile_payload",
        lambda payload: (
            decode_calls.append(payload)
            or {
                "blob_count": 1,
                "program_count": 1,
                "instruction_count": 2,
                "stages": {"pixel": 1},
                "shader_models": {"3.0": 1},
                "opcodes": {"MOV": 1, "TEX": 1},
                "unsupported_opcodes": {},
                "programs": [],
            }
        ),
    )

    report = runtime.profile_shader_corpus(paths)

    assert report["archive_count"] == 2
    assert report["fxo_entry_count"] == 2
    assert report["unique_raw_fxo_payloads"] == 1
    assert report["decoded_unique_payloads"] == 1
    assert decode_calls == [b"decoded"]
    assert report["summary"]["stage_counts"] == {"pixel": 1}
