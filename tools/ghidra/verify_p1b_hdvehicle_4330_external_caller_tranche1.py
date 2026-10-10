#!/usr/bin/env python3
"""Close the first exact incoming-caller tranche for HDVehicle+0x4330 carriers.

Combines hash-locked retail PE windows with the pinned Ghidra SQLite callgraph.
The proof is intentionally bounded: it closes FUN_00491d86's wrapper chain and
the five exact-carrier calls emitted by FUN_00798df0. Other external callers and
all indirect-entry mechanisms remain open.
"""
from __future__ import annotations
import argparse, hashlib, json, sqlite3, struct
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330ExternalCallerTranche1/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED_SQLITE = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}

EXPECTED_FUNCS = {
    "0x00491d86": ("FUN_00491d86", 12, "3101ad8bdce1930b5b24b989dffc8bdb1d4117fb7bde29030fd6774cb44a122b"),
    "0x00768a30": ("FUN_00768a30", 29, "6c358da05cc3dee220783199a1e8d976ad238bf400e389fd1bc0f4335798fccd"),
    "0x00798df0": ("FUN_00798df0", 1581, "88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16"),
}
WINDOWS = [
    (0x00491D86, "689604a700eb0ccccccccccccccccccccccccce9af6c2d00", "FUN_00491d86 preserves ECX and tail-jumps to FUN_00768a4d"),
    (0x00768A30, "538bdc83ec0883e4f083c404558b6b04896c24048bec6affe93993d2ff", "FUN_00768a30 preserves ECX and tail-jumps to FUN_00491d86"),
    (0x00702748, "685c0bc100b9307ac100e8e9f60600b90037c100e9", "FUN_00702720 writes ECX=0x00c13700 before tail-jump to FUN_00768a30"),
    (0x007027A7, "685c0bc100b9307ac100e88af606005f5eb90037c1005be96d620600", "FUN_00702770 writes ECX=0x00c13700 before tail-jump to FUN_00768a30"),
    (0x0076E1B5, "6a058d4f50518b8eb46600008d9e3043000053508b86b066000050e82b590500", "root-derived FUN_007c3b00 call uses HDVehicle+0x4330 as stack param3"),
    (0x00798F56, "8d8d74dcffffe89f92fdff", "FUN_00798df0 calls FUN_00772200 with ECX=stack local EBP-0x238c"),
    (0x00798F92, "8b4d085150b90037c100e8af4ffdff", "FUN_00798df0 calls FUN_0076df50 with ECX=0x00c13700 exact HDVehicle root"),
    (0x00798FB3, "6a058d5750528b96fc1c00008d8d74dcffff518b8e001d00005052e82dab0200", "first FUN_007c3b00 call passes stack local EBP-0x238c as param3"),
    (0x00798FEB, "5383c050508d8d74dcffff518b8e001d00005752e8fcaa0200", "second FUN_007c3b00 call passes stack local EBP-0x238c as param3"),
    (0x00799039, "6a0183c250528b96fc1c00008d8d74dcffff518b8e001d00005052e8a7aa0200", "third FUN_007c3b00 call passes stack local EBP-0x238c as param3"),
]

class PEImage:
    def __init__(self, data: bytes):
        self.data = data
        if data[:2] != b"MZ":
            raise ValueError("not an MZ executable")
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe:pe+4] != b"PE\0\0":
            raise ValueError("missing PE signature")
        coff = pe + 4
        nsec = struct.unpack_from("<H", data, coff + 2)[0]
        opt_size = struct.unpack_from("<H", data, coff + 16)[0]
        opt = coff + 20
        if struct.unpack_from("<H", data, opt)[0] != 0x10B:
            raise ValueError("expected PE32")
        self.image_base = struct.unpack_from("<I", data, opt + 28)[0]
        table = opt + opt_size
        self.sections = []
        for i in range(nsec):
            off = table + i * 40
            vs, va, rs, rp = struct.unpack_from("<IIII", data, off + 8)
            self.sections.append((va, max(vs, rs), rp))

    def bytes_at_va(self, va: int, size: int) -> bytes:
        rva = va - self.image_base
        for start, span, raw in self.sections:
            if start <= rva < start + span:
                off = raw + (rva - start)
                return self.data[off:off+size]
        raise ValueError(f"VA not mapped: 0x{va:08x}")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def raw_calls(db: sqlite3.Connection) -> list[dict]:
    return [json.loads(row[0]) for row in db.execute("SELECT raw_json FROM calls")]

def incoming(calls: list[dict], target: str) -> list[dict]:
    return [r for r in calls if str(r.get("to") or "").lower() == target.lower() and r.get("indirect") is not True]

def outgoing(calls: list[dict], caller: str, targets: set[str]) -> list[dict]:
    return [r for r in calls if str(r.get("from_function") or "").lower() == caller.lower()
            and str(r.get("to") or "").lower() in targets and r.get("indirect") is not True]

def normalize(rows: list[dict]) -> list[tuple[str,str,str]]:
    return sorted((str(r.get("from_function","")).lower(), str(r.get("instruction","")).lower(),
                   str(r.get("to","")).lower()) for r in rows)

def analyze(exe: Path, database: Path) -> dict:
    exe_hash, db_hash = sha256(exe), sha256(database)
    if exe_hash != RETAIL_SHA256:
        raise ValueError(f"unexpected retail SHA-256: {exe_hash}")
    if db_hash != SQLITE_SHA256:
        raise ValueError(f"unexpected SQLite SHA-256: {db_hash}")
    image = PEImage(exe.read_bytes())
    for va, expected_hex, meaning in WINDOWS:
        actual = image.bytes_at_va(va, len(bytes.fromhex(expected_hex))).hex()
        if actual != expected_hex:
            raise ValueError(f"retail byte drift at 0x{va:08x}: {actual} != {expected_hex} ({meaning})")

    db = sqlite3.connect(database)
    try:
        fmt_row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        fmt = None if fmt_row is None else fmt_row[0]
        if fmt not in SUPPORTED_SQLITE:
            raise ValueError(f"unsupported SQLite format: {fmt!r}")
        for addr, (name, size, digest) in EXPECTED_FUNCS.items():
            row = db.execute("SELECT name,raw_json FROM functions WHERE lower(address)=?", (addr,)).fetchone()
            if row is None:
                raise ValueError(f"missing function {addr}")
            raw = json.loads(row[1])
            if row[0] != name or int(raw.get("size") or -1) != size or raw.get("mnemonic_sha256") != digest:
                raise ValueError(f"function identity drift at {addr}")
        calls = raw_calls(db)

        wrapper_in = incoming(calls, "0x00491d86")
        trampoline_in = incoming(calls, "0x00768a30")
        cluster_in = incoming(calls, "0x00798df0")
        if normalize(wrapper_in) != [("0x00768a30","0x00768a48","0x00491d86")]:
            raise ValueError(f"wrapper incoming drift: {normalize(wrapper_in)!r}")
        if normalize(trampoline_in) != [
            ("0x00702720","0x0070275c","0x00768a30"),
            ("0x00702770","0x007027be","0x00768a30"),
            ("0x0076df50","0x0076e544","0x00768a30"),
        ]:
            raise ValueError(f"trampoline incoming drift: {normalize(trampoline_in)!r}")
        if normalize(cluster_in) != [("0x0074ddc3","0x0074de12","0x00798df0")]:
            raise ValueError(f"cluster incoming drift: {normalize(cluster_in)!r}")

        carrier_targets = {"0x00772200","0x0076df50","0x007c3b00"}
        cluster_calls = outgoing(calls, "0x00798df0", carrier_targets)
        expected_cluster = [
            ("0x00798df0","0x00798f5c","0x00772200"),
            ("0x00798df0","0x00798f9c","0x0076df50"),
            ("0x00798df0","0x00798fce","0x007c3b00"),
            ("0x00798df0","0x00798fff","0x007c3b00"),
            ("0x00798df0","0x00799054","0x007c3b00"),
        ]
        if normalize(cluster_calls) != expected_cluster:
            raise ValueError(f"FUN_00798df0 carrier-call drift: {normalize(cluster_calls)!r}")
    finally:
        db.close()

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": exe_hash,
            "ghidra_sqlite_sha256": db_hash,
            "retail_machine_transfer_adjudicates": True,
            "sqlite_role": "direct-call inventory/fingerprint cross-check only",
        },
        "upstream_contracts": [
            "SHIFT.HDVehicle64e8RootDerived4330MaterializerPersistenceClosure/1",
            "SHIFT.P1B.HDVehicle4330IncomingDirectCallFrontier/1",
        ],
        "fun_00491d86_wrapper_chain": {
            "external_frontier_callsite": "0x00491d99 -> FUN_00768a4d",
            "wrapper_entry": "FUN_00768a30 -> FUN_00491d86 -> FUN_00768a4d",
            "ecx_preserved_across_wrappers": True,
            "direct_entries_to_fun_00768a30": [
                {"site":"0x0070275c","source":"FUN_00702720","receiver":"literal 0x00c13700 HDVehicle root"},
                {"site":"0x007027be","source":"FUN_00702770","receiver":"literal 0x00c13700 HDVehicle root"},
                {"site":"0x0076e544","source":"FUN_0076df50","receiver":"already-admitted exact-root internal path"},
            ],
            "preexisting_hdvehicle_4330_alias_forwarded": False,
            "classification": "exact HDVehicle-root entry to already-proven +0x4330 materializer, not an alternate +0x4330 alias entry",
        },
        "fun_00798df0_cluster": {
            "external_callsite_count": 5,
            "calls": [
                {"site":"0x00798f5c","target":"FUN_00772200","target_exact_4330_parameter":"ECX","actual":"stack local EBP-0x238c","matches_exact_4330":False},
                {"site":"0x00798f9c","target":"FUN_0076df50","target_domain":"HDVehicle root","actual":"literal ECX=0x00c13700","preexisting_4330_alias":False},
                {"site":"0x00798fce","target":"FUN_007c3b00","target_exact_4330_parameter":"stack param3","actual":"stack local EBP-0x238c","matches_exact_4330":False},
                {"site":"0x00798fff","target":"FUN_007c3b00","target_exact_4330_parameter":"stack param3","actual":"stack local EBP-0x238c","matches_exact_4330":False},
                {"site":"0x00799054","target":"FUN_007c3b00","target_exact_4330_parameter":"stack param3","actual":"stack local EBP-0x238c","matches_exact_4330":False},
            ],
            "preexisting_hdvehicle_4330_alias_forwarded": False,
            "classification": "all five calls are exact-root or stack-local argument paths; none forwards an existing HDVehicle+0x4330 pointer",
        },
        "adjudication": {
            "external_caller_tranche1_complete": True,
            "resolved_external_caller_count": 2,
            "resolved_external_callsite_count": 6,
            "remaining_external_caller_count": 5,
            "remaining_external_callers": [
                "FUN_0074da70","FUN_00795d60","FUN_00aa2850","Unwind@00a7063f","Unwind@00a72322"
            ],
            "tranche1_preexisting_4330_alias_found": False,
            "external_receiver_provenance_complete": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the direct FUN_00491d86 wrapper chain and the five exact-carrier calls in FUN_00798df0.",
            "The other five external caller functions remain open.",
            "Indirect entry, callbacks registered elsewhere, runtime-generated/copied pointers and non-root-derived data aliases remain open.",
            "Callgraph reachability is never promoted to HDVehicle+0x4330 identity without retail machine argument provenance.",
        ],
        "next_step": "Adjudicate FUN_0074da70 and FUN_00795d60, then the tiny FUN_00aa2850/Unwind caller set; only after all seven direct callers close should indirect-entry work resume.",
    }

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("exe", type=Path)
    p.add_argument("database", type=Path)
    p.add_argument("--output", type=Path)
    a=p.parse_args()
    try:
        out=analyze(a.exe,a.database)
    except ValueError as e:
        p.error(str(e))
    text=json.dumps(out,indent=2,sort_keys=True)+"\n"
    if a.output: a.output.write_text(text,encoding="utf-8")
    else: print(text,end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
