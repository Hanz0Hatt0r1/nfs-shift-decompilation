# Process 1D — Controller #1 native APC primitive frontier

## Result

The remaining Controller #1 timing blocker includes native or indirect APC delivery that is not visible through the ordinary import/name surface.

This lane now has a reproducible Ghidra inventory for two machine-level primitive families:

- x86 PEB/manual export-walk candidates, requiring the same function to show `FS:[0x30]` access plus PE `e_lfanew` (`+0x3c`) and export-directory (`+0x78`) hints;
- direct native transition candidates using `SYSENTER` or `INT 0x2e`.

The exporter is `tools/ghidra/ShiftNativeResolutionPrimitiveExporter.java`. The analyzer is `tools/ghidra/analyze_p1d_controller1_native_apc_primitives.py`.

## Proof boundary

These matches are **candidate-only**.

A PEB/export-offset pattern is not itself proof of manual API resolution. Local data flow must still prove that the function walks loaded modules and the PE export directory, and then identify the resolved target.

Likewise, `SYSENTER` or `INT 0x2e` is not proof of APC injection. The exact native service/syscall identity and its target thread handle must be recovered before the path can affect Controller #1 timing.

An empty result is **not a universal no-APC theorem**. Generated code, WOW64 transitions, imported/native stubs, indirect function pointers, hashed/generated API names, and other syscall mechanisms remain outside this narrow machine-pattern inventory unless separately adjudicated.

## Gate

```text
manual export walking ruled out          = false
native/syscall APC injection ruled out   = false
Controller #1 thread-handle join         = false
Controller #1 timing exhaustive          = false
P1.3D complete                            = false
provider count                            = 7
```

## Workflow

Run the exporter on the authoritative PC retail 1.02 Ghidra program, then analyze the JSONL result:

```text
ShiftNativeResolutionPrimitiveExporter.java out/p1d_native_resolution_primitives.jsonl
python3 tools/ghidra/analyze_p1d_controller1_native_apc_primitives.py \
  out/p1d_native_resolution_primitives.jsonl \
  --output out/p1d_controller1_native_apc_frontier.json
```

Every positive candidate must then be adjudicated against exact Controller #1 worker/thread identity. Only a proven target join may advance the timing gate.
