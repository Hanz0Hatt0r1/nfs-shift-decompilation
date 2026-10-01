import json

from tools.list_d3d9_resource_signatures import analyze, fnv1a64


def write_jsonl(path, events):
    path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )


def test_resource_signature_analyzer_derives_old_capture_signatures(tmp_path):
    capture = tmp_path / "capture.jsonl"
    shader_bytes = bytes.fromhex("01020304")

    write_jsonl(
        capture,
        [
            {
                "event": "create_texture",
                "frame": 1,
                "texture_ptr": "0x1000",
                "width": 2800,
                "height": 600,
                "format": 113,
            },
            {
                "event": "set_texture",
                "frame": 2,
                "texture_ptr": "0x1000",
            },
            {
                "event": "create_vertex_shader",
                "frame": 3,
                "shader_ptr": "0x2000",
                "bytes_hex": shader_bytes.hex(),
            },
            {
                "event": "set_vertex_shader",
                "frame": 4,
                "shader_ptr": "0x2000",
            },
        ],
    )

    report = analyze(capture)

    assert report["bound"]["tex:2800x600:113"] == 1
    assert report["created"]["tex:2800x600:113"] == 1

    shader_signature = f"vs:{fnv1a64(shader_bytes)}"
    assert report["created"][shader_signature] == 1
    assert report["bound"][shader_signature] == 1
    assert report["first_frame"][shader_signature] == 3
    assert report["last_frame"][shader_signature] == 4


def test_resource_signature_analyzer_tracks_pointer_reuse_by_latest_generation(tmp_path):
    capture = tmp_path / "capture.jsonl"

    write_jsonl(
        capture,
        [
            {
                "event": "create_vertex_buffer",
                "frame": 10,
                "vertex_buffer_ptr": "0x3000",
                "length": 1024,
            },
            {
                "event": "set_stream_source",
                "frame": 11,
                "vertex_buffer_ptr": "0x3000",
            },
            {
                "event": "create_vertex_buffer",
                "frame": 20,
                "vertex_buffer_ptr": "0x3000",
                "length": 4096,
            },
            {
                "event": "set_stream_source",
                "frame": 21,
                "vertex_buffer_ptr": "0x3000",
            },
        ],
    )

    report = analyze(capture)

    assert report["bound"]["vb:1024"] == 1
    assert report["bound"]["vb:4096"] == 1
    assert report["last_frame"]["vb:4096"] == 21
