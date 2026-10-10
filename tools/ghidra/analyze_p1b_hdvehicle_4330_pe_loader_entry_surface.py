#!/usr/bin/env python3
"""Bound PE-published/loader-managed entry surfaces for exact HDVehicle+0x4330 carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330PeLoaderEntrySurface/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
CARRIERS = {
    "FUN_00769520": 0x00769520,
    "FUN_0076b130": 0x0076B130,
    "FUN_0076df50": 0x0076DF50,
    "FUN_00768a4d": 0x00768A4D,
    "FUN_00756050": 0x00756050,
    "FUN_00772200": 0x00772200,
    "FUN_00772570": 0x00772570,
    "FUN_007c3b00": 0x007C3B00,
    "FUN_0076b280": 0x0076B280,
    "FUN_007618f0": 0x007618F0,
    "FUN_00769640": 0x00769640,
    "FUN_007567a0": 0x007567A0,
    "FUN_00756bb0": 0x00756BB0,
    "FUN_00771db0": 0x00771DB0,
    "FUN_00771e10": 0x00771E10,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class PEImage:
    def __init__(self, data: bytes):
        self.data = data
        if data[:2] != b"MZ":
            raise ValueError("not an MZ executable")
        self.pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[self.pe:self.pe + 4] != b"PE\0\0":
            raise ValueError("missing PE signature")
        coff = self.pe + 4
        self.section_count = struct.unpack_from("<H", data, coff + 2)[0]
        optional_size = struct.unpack_from("<H", data, coff + 16)[0]
        optional = coff + 20
        if struct.unpack_from("<H", data, optional)[0] != 0x10B:
            raise ValueError("expected PE32")
        self.image_base = struct.unpack_from("<I", data, optional + 28)[0]
        self.entry_rva = struct.unpack_from("<I", data, optional + 16)[0]
        self.directory = optional + 96
        table = optional + optional_size
        self.sections = []
        for index in range(self.section_count):
            off = table + index * 40
            name = data[off:off + 8].split(b"\0", 1)[0].decode("ascii", "replace")
            virtual_size, rva, raw_size, raw_ptr = struct.unpack_from("<IIII", data, off + 8)
            self.sections.append({
                "name": name,
                "rva": rva,
                "span": max(virtual_size, raw_size),
                "raw_size": raw_size,
                "raw_ptr": raw_ptr,
            })

    def data_directory(self, index: int) -> tuple[int, int]:
        return struct.unpack_from("<II", self.data, self.directory + index * 8)

    def rva_to_offset(self, rva: int) -> int:
        for section in self.sections:
            if section["rva"] <= rva < section["rva"] + section["span"]:
                return section["raw_ptr"] + (rva - section["rva"])
        raise ValueError(f"unmapped RVA 0x{rva:08x}")

    def va_to_offset(self, va: int) -> int:
        return self.rva_to_offset(va - self.image_base)

    def c_string(self, rva: int, limit: int = 4096) -> str:
        off = self.rva_to_offset(rva)
        end = self.data.find(b"\0", off, off + limit)
        if end < 0:
            raise ValueError(f"unterminated string at RVA 0x{rva:08x}")
        return self.data[off:end].decode("ascii", "replace")

    def export_surface(self) -> dict:
        export_rva, export_size = self.data_directory(0)
        if not export_rva:
            return {"present": False, "function_count": 0, "named_count": 0, "functions": [], "forwarders": []}
        off = self.rva_to_offset(export_rva)
        fields = struct.unpack_from("<IIHHIIIIIII", self.data, off)
        _, _, _, _, name_rva, ordinal_base, function_count, named_count, funcs_rva, names_rva, ords_rva = fields
        functions = []
        forwarders = []
        for index in range(function_count):
            function_rva = struct.unpack_from("<I", self.data, self.rva_to_offset(funcs_rva) + index * 4)[0]
            va = self.image_base + function_rva if function_rva else 0
            row = {"ordinal": ordinal_base + index, "rva": function_rva, "va": va}
            functions.append(row)
            if export_rva <= function_rva < export_rva + export_size:
                forwarders.append(row)
        names = []
        for index in range(named_count):
            nrva = struct.unpack_from("<I", self.data, self.rva_to_offset(names_rva) + index * 4)[0]
            ordinal_index = struct.unpack_from("<H", self.data, self.rva_to_offset(ords_rva) + index * 2)[0]
            names.append({"name": self.c_string(nrva), "ordinal_index": ordinal_index})
        return {
            "present": True,
            "directory_rva": export_rva,
            "directory_size": export_size,
            "dll_name": self.c_string(name_rva),
            "ordinal_base": ordinal_base,
            "function_count": function_count,
            "named_count": named_count,
            "functions": functions,
            "names": names,
            "forwarders": forwarders,
        }

    def tls_surface(self) -> dict:
        tls_rva, tls_size = self.data_directory(9)
        if not tls_rva:
            return {"present": False, "callbacks": []}
        off = self.rva_to_offset(tls_rva)
        start_raw, end_raw, address_of_index, address_of_callbacks, zero_fill, characteristics = struct.unpack_from(
            "<IIIIII", self.data, off
        )
        callbacks = []
        if address_of_callbacks:
            callback_off = self.va_to_offset(address_of_callbacks)
            index = 0
            while True:
                va = struct.unpack_from("<I", self.data, callback_off + index * 4)[0]
                if va == 0:
                    break
                callbacks.append(va)
                index += 1
                if index > 4096:
                    raise ValueError("unterminated TLS callback array")
        return {
            "present": True,
            "directory_rva": tls_rva,
            "directory_size": tls_size,
            "start_raw_data": start_raw,
            "end_raw_data": end_raw,
            "address_of_index": address_of_index,
            "address_of_callbacks": address_of_callbacks,
            "zero_fill": zero_fill,
            "characteristics": characteristics,
            "callbacks": callbacks,
        }


def analyze(exe: Path) -> dict:
    digest = sha256(exe)
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected retail SHA-256: {digest}")
    image = PEImage(exe.read_bytes())
    if image.image_base != 0x00400000:
        raise ValueError(f"image-base drift: 0x{image.image_base:08x}")
    entry_va = image.image_base + image.entry_rva
    if entry_va != 0x0090488A:
        raise ValueError(f"entrypoint drift: 0x{entry_va:08x}")

    exports = image.export_surface()
    if exports["function_count"] != 509 or exports["named_count"] != 509:
        raise ValueError(f"export-count drift: {exports['function_count']}/{exports['named_count']}")
    if exports["dll_name"] != "GeckoFnl.exe":
        raise ValueError(f"export image-name drift: {exports['dll_name']!r}")
    if exports["forwarders"]:
        raise ValueError(f"unexpected export forwarders: {exports['forwarders']!r}")
    if any(row["va"] == 0 for row in exports["functions"]):
        raise ValueError("zero export function RVA appeared")
    carrier_by_va = {address: name for name, address in CARRIERS.items()}
    export_hits = [
        {"carrier": carrier_by_va[row["va"]], "va": f"0x{row['va']:08x}", "ordinal": row["ordinal"]}
        for row in exports["functions"] if row["va"] in carrier_by_va
    ]
    if export_hits:
        raise ValueError(f"exact carrier exported: {export_hits!r}")

    tls = image.tls_surface()
    if not tls["present"] or tls["directory_rva"] != 0x007672AC or tls["directory_size"] != 0x18:
        raise ValueError(f"TLS directory drift: {tls!r}")
    if tls["address_of_callbacks"] != 0x00AA9990 or tls["callbacks"]:
        raise ValueError(f"TLS callback drift: {tls!r}")

    load_config_rva, load_config_size = image.data_directory(10)
    exception_rva, exception_size = image.data_directory(3)
    if (load_config_rva, load_config_size) != (0, 0):
        raise ValueError(f"load-config directory appeared: {(load_config_rva, load_config_size)!r}")
    if (exception_rva, exception_size) != (0, 0):
        raise ValueError(f"PE exception directory appeared: {(exception_rva, exception_size)!r}")

    entry_is_carrier = entry_va in carrier_by_va
    tls_hits = [va for va in tls["callbacks"] if va in carrier_by_va]
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "retail_pe_headers_and_tables_adjudicate": True,
            "image_base": "0x00400000",
        },
        "upstream_contracts": [
            "SHIFT.P1B.HDVehicle4330WholeImageLiteralPointerSurface/1",
            "SHIFT.P1B.HDVehicle4330X87EipCaptureSurface/1",
        ],
        "entrypoint": {
            "rva": f"0x{image.entry_rva:08x}",
            "va": f"0x{entry_va:08x}",
            "is_exact_carrier": entry_is_carrier,
        },
        "export_surface": {
            "directory_rva": f"0x{exports['directory_rva']:08x}",
            "directory_size": exports["directory_size"],
            "dll_name": exports["dll_name"],
            "function_count": exports["function_count"],
            "named_count": exports["named_count"],
            "forwarder_count": len(exports["forwarders"]),
            "zero_function_rva_count": 0,
            "exact_carrier_export_hit_count": len(export_hits),
            "exact_carrier_export_hits": export_hits,
        },
        "tls_surface": {
            "directory_rva": f"0x{tls['directory_rva']:08x}",
            "directory_size": tls["directory_size"],
            "address_of_callbacks": f"0x{tls['address_of_callbacks']:08x}",
            "callback_count": len(tls["callbacks"]),
            "callbacks": [f"0x{va:08x}" for va in tls["callbacks"]],
            "exact_carrier_callback_hit_count": len(tls_hits),
        },
        "load_config_surface": {
            "directory_rva": "0x00000000",
            "directory_size": 0,
            "present": False,
            "safe_seh_or_guard_tables_available_through_load_config": False,
        },
        "pe_exception_directory": {
            "directory_rva": "0x00000000",
            "directory_size": 0,
            "present": False,
            "note": "This says nothing about x86 MSVC inline EH metadata already handled separately.",
        },
        "adjudication": {
            "exact_carrier_is_pe_entrypoint": False,
            "exact_carrier_export_surface_complete": True,
            "exact_carrier_export_found": False,
            "tls_callback_surface_complete": True,
            "exact_carrier_tls_callback_found": False,
            "load_config_published_handler_surface_complete": True,
            "pe_published_loader_entry_subset_complete": True,
            "runtime_callback_registration_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only PE-published/loader-managed entry surfaces represented by AddressOfEntryPoint, the export address table, TLS callbacks, and the load-config directory.",
            "The absent PE exception directory is not treated as absence of x86 MSVC inline EH cleanup actions.",
            "Runtime callback registration, computed/copied/encoded pointers, and unresolved indirect dispatch remain open."
        ],
        "next_step": "Trace runtime callback-registration APIs and pointer-copy flows that can receive a nonliteral internal code address; keep indirect-entry and manager identity gates fail-closed."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.exe)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
