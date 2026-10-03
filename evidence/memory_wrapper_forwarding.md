# SHIFT memory-wrapper instruction forwarding

`tools/ghidra/analyze_memory_wrapper_forwarding.py` consumes the narrow targeted
instruction export produced by `ShiftFunctionInstructionExporter.java` and
recovers physical argument forwarding for the five retail memory-wrapper
functions around `0x008868c0..0x00886950`.

The output format is `SHIFT-MEMORY-WRAPPER-FORWARDING/1`.

## Why this layer exists

The regular ABI/storage family in `memory_wrapper_family.json` proves function
boundaries, calling conventions, parameter storage and backend call edges. It
does not show which wrapper input becomes which backend argument. Ghidra's
reported semantic types are also not reliable enough for that promotion.

This layer instead follows the selected functions instruction by instruction.
It starts from physical entry storage such as `Stack[0x4]:4`, `ECX:4` and
`DL:1`, then tracks those values through the small x86 wrapper bodies until a
known backend call.

## Modeled x86 subset

The analyzer intentionally supports only the operations needed for small wrapper
forwarding:

- `mov`, `movzx`, `movsx`, `lea`;
- `push`, `pop`;
- `xor reg,reg` zeroing;
- constant/register `add`, `sub`, `and`, `or`;
- `add/sub esp, constant` and `leave`;
- `cmp`, `test`, conditional jumps and `jmp`;
- direct `call`, `ret`, `nop`.

It carries independent symbolic states through control-flow branches and merges
them at joins. Different values at a merge become `unresolved`. Unsupported
instructions poison the incoming state for downstream calls instead of being
ignored or guessed through.

## Known backend storage

The analyzer currently models only direct backend calls already present in the
Ghidra family evidence:

| backend | physical parameters |
| --- | --- |
| `FUN_006382b0` | `ECX:4`, `EDX:4` |
| `FUN_00638020` | `ECX:4`, `EDX:4`, `Stack[0x4]:4` |
| `thunk_FUN_0064f3a0` (`0x0064f4c0`) | `ECX:4`, `DL:1` |
| `FUN_0064f260` | `ECX:4`, `EDX:4` |

For `__fastcall`/`__stdcall` backends, stack-parameter cleanup is included when
propagating state past a call. This matters for create-side wrappers that call
`FUN_00638020` and then take a fallback path into `FUN_006382b0`.

## One-command capture

For the standard five-function retail set, the preferred workflow is now:

```bash
cd /home/pes/nfs-shift-decompilation

git pull

GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_memory_wrapper_forwarding.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/memory_wrapper_forwarding
```

The runner pins the exact five wrapper addresses, invokes the targeted
instruction exporter and its validator, then runs the forwarding analyzer. It
writes:

```text
out/memory_wrapper_forwarding/
  memory_wrapper_instructions.jsonl
  memory_wrapper_forwarding.json
```

The runner is stored executable in Git, so a fresh checkout does not require a
manual `chmod`.

## Manual run

The two stages can still be run separately when a different target set is being
investigated. First export the five wrappers from the already-analyzed Ghidra
project:

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift shift SHIFT.exe \
  out/memory_wrapper_instructions.jsonl \
  FUN_008868c0 FUN_008868d0 FUN_00886900 FUN_00886930 FUN_00886950
```

Then build forwarding evidence:

```bash
python3 tools/ghidra/analyze_memory_wrapper_forwarding.py \
  out/memory_wrapper_instructions.jsonl \
  --json-out out/class_evidence/memory_wrapper_forwarding.json
```

## Promotion rule

A wrapper gets `forwarding_confirmed=true` only when:

1. every required backend call is present;
2. every physical backend argument has a resolved symbolic source;
3. the incoming symbolic state for those calls was not poisoned by unsupported
   instructions or incompatible stack-frame merges.

Sources remain mechanical, for example:

- `input:Stack[0x4]:4`;
- `input:ECX:4`;
- `constant:0x4`;
- `return:0x...`;
- derived expressions such as `low8(...)`.

## Evidence boundary

Even a fully confirmed five-wrapper report proves only physical value forwarding
for the modeled calls. It does **not** prove:

- which input means byte size, alignment, pool selector or allocation flags;
- which release input means delete kind or ownership state;
- compiler `operator new` / `operator delete` identity;
- ownership/reference-counting policy;
- that all allocator paths share one heap or pool implementation.

Those semantic names require independent call-site, diagnostic, runtime or
instruction evidence rather than inference from parameter position.
