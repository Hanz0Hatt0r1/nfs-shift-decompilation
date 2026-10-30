#!/usr/bin/env python3
"""Guard the exact-XEX run made with PPC memory fences in generated code."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_exact_runtime_ppc_fence_followthrough_20261027.json")
    .read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-exact-runtime-ppc-fence-followthrough.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
codegen = evidence["codegen"]
assert codegen["generated_translation_units_with_fences"] == 224
assert codegen["generated_fence_expressions"] == 2615
assert codegen["lwsync_expression"] == (
    "std::atomic_thread_fence(std::memory_order_acq_rel)"
)
assert codegen["sync_expression"] == (
    "std::atomic_thread_fence(std::memory_order_seq_cst)"
)

binaries = evidence["binaries"]
assert binaries["p1_host"]["sha256"] == (
    "ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178"
)
assert binaries["rexglue_runtime"]["sha256"] == (
    "4d0fb82223695d3e2b76bbc6d6c9a93bad525a4c051a8a2eb585b5422d2373bc"
)
assert binaries["gpu_plugin"]["sha256"] == (
    "771201891a6ae28c0745f57beccf9c6474ce175c7bb3f5edadcce4c457a8a12b"
)

run = evidence["run"]
assert run["guest_memory_written_by_probe"] is False
assert run["mapped_library_hashes_verified_in_inferior"] is True
for key in ("gdb_script", "runner"):
    item = run[key]
    assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]

gdb_script = (ROOT / run["gdb_script"]["path"]).read_text()
for offset in ("0x5D2F30", "0x5D2F60", "0x5D2F90", "0x5D3260"):
    assert offset in gdb_script

bink = run["bink"]
assert (bink["frame_target"], bink["observed_frames"]) == (281, 281)
queue = run["retail_queue"]
assert queue["producer_entries"] == 759
assert queue["producer_counted_entries"] == 1
assert queue["counted_delta"] == 1
assert queue["callback_enqueue_entries"] == 415
assert queue["worker_entries"] == 415
assert queue["worker_tokens"] == {"0xC0000000": 415}
assert queue["counter_writes"] == 208
assert queue["first_counter_values"][:3] == [
    "0x00000001",
    "0x00000000",
    "0xFFFFFFFF",
]
assert queue["event_api_entries"] == {
    "KeSetEvent": 414,
    "KeResetEvent": 414,
    "KeWaitForSingleObject": 296,
}
assert run["final_threads"]["retail_main"]["frame"] == "sub_823B3850"

not_proven = evidence["interpretation"]["not_proven"]
assert any("fence generation caused or fixes" in item for item in not_proven)
assert any("race entry" in item for item in not_proven)

print("exact-XEX PPC-fence build still exposes the original retail worker underflow")
