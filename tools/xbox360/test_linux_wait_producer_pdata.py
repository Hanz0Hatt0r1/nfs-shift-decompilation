#!/usr/bin/env python3
"""Guard the PDATA classification without inferring a runtime invocation."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_wait_producer_pdata_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-wait-producer-pdata.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["analysis_image"]["sha256"] == (
    "2ffe352bda115285e58661cb5fc5ebe0a8c845d1e7a9ae07bee89e514636c00c"
)
assert evidence["decoder_reference"]["record_type"] == "IMAGE_CE_RUNTIME_FUNCTION"
assert evidence["observations"]["code_bytes"].startswith("7D8802A64833515D")
assert evidence["observations"]["big_endian_begin_address_occurrences_in_image"] == 1
assert evidence["observations"]["pdata_record_address"] == "0x82159D50"
records = evidence["observations"]["pdata_records"]
assert [record["begin_address"] for record in records] == [
    "0x823A4640",
    "0x823A4758",
    "0x823A4908",
]
assert [record["function_length_dwords"] for record in records] == [69, 107, 114]
assert all(record["prolog_length"] == 3 for record in records)
assert all(record["thirty_two_bit"] and not record["exception_flag"] for record in records)
assert evidence["observations"]["ghidra_reference_manager_incoming_references_to_code_address"] == 0

interpretation = " ".join(evidence["interpretation"]["supported"])
assert "not evidence of a call" in interpretation
limits = " ".join(evidence["interpretation"]["not_proven"])
assert "Which runtime path invokes" in limits
assert "runtime or computed dispatch" in " ".join(evidence["limitations"])

print("live-ELF PDATA record is classified without inferring producer invocation")
