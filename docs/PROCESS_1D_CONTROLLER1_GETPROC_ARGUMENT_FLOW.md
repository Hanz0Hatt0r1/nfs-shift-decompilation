# Process 1D — Controller #1 GetProcAddress argument-flow proof

## Result

The Controller #1 worker-reachable direct `GetProcAddress` surface is now closed negative for APC API names by direct PC-retail machine evidence.

The prior Drive Ghidra SQLite analysis reduced the surface to six functions and eleven calls. Local strings were only contextual evidence. This stage reads the authoritative PC retail 1.02 `SHIFT.exe` directly, verifies SHA-256
`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`, resolves IAT `0x00aa62fc` to `KERNEL32.dll!GetProcAddress`, verifies exact argument/call byte windows, and reads every referenced API name from `.rdata`.

Exact recovered calls:

```text
0x009074a0 -> CorExitProcess
0x0090aa7b -> EncodePointer
0x0090aaf2 -> DecodePointer
0x0090abfd -> EncodePointer
0x0090ac0d -> DecodePointer
0x00918a26 -> InitializeCriticalSectionAndSpinCount
0x0091c0bc -> MessageBoxA
0x0091c0d9 -> GetActiveWindow
0x0091c0ee -> GetLastActivePopup
0x0091c123 -> GetUserObjectInformationA
0x0091c13b -> GetProcessWindowStation
```

None is an APC injection API.

Two USER32 callsites (`0x0091c0d9`, `0x0091c0ee`) are important compiler cases: the API name is written with `mov dword ptr [esp], imm32`, then the module handle is pushed, rather than using a simple adjacent PUSH/PUSH pair. The targeted instruction analyzer therefore uses a bounded symbolic x86 stack model and supports exact `[ESP+n]` stack-slot writes; it does not assume all resolver arguments are adjacent pushes.

## Reproducible machine proof

`tools/ghidra/analyze_p1d_controller1_getproc_retail_pe.py` requires only the authoritative retail executable:

```bash
python3 tools/ghidra/analyze_p1d_controller1_getproc_retail_pe.py \
  /path/to/SHIFT.exe \
  --output out/p1d_controller1_getproc_retail_machine_proof.json
```

It validates the exact executable hash, PE import table identity, eleven machine windows, register seeds for EBX/ESI resolver reuse, and the referenced NUL-terminated strings.

The Ghidra path remains available as an independent instruction-level cross-check:

```bash
GHIDRA_HOME=/path/to/ghidra \
  ./tools/ghidra/run_p1d_controller1_getproc_argument_flow.sh \
  /path/to/project-dir SHIFT SHIFT.exe \
  /path/to/shift_ghidra.sqlite out/p1d_controller1_getproc
```

## Closed sub-surface

```text
worker-reachable direct GetProcAddress calls = 11
exact lpProcName values recovered            = 11
APC API names among those calls              = 0
direct named GetProcAddress APC surface      = rejected
```

This does **not** make Controller #1 timing exhaustive. The following stay open:

```text
indirect resolver calls                  = not ruled out
hashed/generated names                   = not ruled out
manual export walking                    = not ruled out
native/syscall APC injection             = not ruled out
Controller #1 timing exhaustive          = false
P1.3D complete                           = false
provider count                           = 7
```

Exact PC-retail machine flow remains semantic authority. The next P1D task is to execute/adjudicate the existing #1699 manual-export/native primitive frontier and join any positive candidate to the exact Controller #1 target thread before changing timing gates.
