# Process 1 — static provider dispatch closure

This block narrows one of the remaining static gaps inside the persistent BODY
update chain without launching the game or consuming runtime capture data.

The result composes already recovered source/PE facts into a fail-closed contract
and adds a targeted Ghidra instruction analyzer for the remaining callsite-address
freeze.

## Evidence basis

The existing static evidence establishes all of the following independently:

- `FUN_007b3820` enumerates provider selector indices `0`, then `1` through
  `FUN_007d2e70`; the selector returns null after those two shipped candidates;
- an accepted candidate is stored at `physics_system+0x48`;
- shipped provider vtables are `0x00b0fc5c` and `0x00b0fc8c`;
- both vtables have the same recovered dispatch layout;
- `FUN_007b3f40` dispatches provider cleanup at `+0x20` and provider solve at
  `+0x18` when `physics_system+0x48` is non-null;
- `FUN_007b2210`, called per active constraint scalar from the solve path,
  dispatches provider reset at `+0x1c`;
- with a null provider, `FUN_007b3f40` reaches builtin solver `FUN_007b0f20`.

The provider vtable words already recovered from PE `.rdata` give the exact
conditional targets:

| Slot | Role | provider 0 | provider 1 | State |
|---:|---|---:|---:|---|
| `+0x14` | acceptance | `FUN_007c6e50` | `FUN_007cdb40` | `verified` |
| `+0x18` | solve | `FUN_007c7200` | `FUN_007cdfc0` | `verified` |
| `+0x1c` | per-scalar reset | `FUN_007d3150` | `FUN_007d48a0` | `verified` |
| `+0x20` | cleanup | `FUN_007d43c0` | `FUN_007d5600` | `verified` |

This closes the *conditional target set*.  It does **not** claim which provider
is selected on any particular tick.

## Machine-readable ABI / dispatch contract

`src/physics/providers/provider_dispatch_static_contract.py` publishes
`SHIFT.ProviderDispatchStaticContract/1`.

The contract separates these evidence states:

- provider storage at physics-system `+0x48`: `proven` by the recovered selection
  and execution source path;
- concrete words in each shipped provider vtable: `verified` against PE `.rdata`;
- conditional target set for each virtual slot: `verified`;
- unique provider target for an arbitrary execution: deliberately not promoted;
- exact machine instruction VA for the four virtual callsites: `unknown` until a
  targeted instruction export is checked.

The contract also keeps the null-provider fallback explicit:

```text
physics_system+0x48 == NULL
  -> builtin FUN_007b0f20
```

and the provider path finite:

```text
FUN_007b3820
  -> FUN_007d2e70(0 | 1)
  -> accepted provider -> physics_system+0x48

FUN_007b3f40
  -> provider +0x20 -> { FUN_007d43c0, FUN_007d5600 }
  -> common constraint/BODY preparation
  -> FUN_007b2210
       -> provider +0x1c -> { FUN_007d3150, FUN_007d48a0 }
  -> provider +0x18 -> { FUN_007c7200, FUN_007cdfc0 }
  -> FUN_007b4110 post-solve feedback
  -> FUN_007b2270
       -> FUN_007bab70 persistent BODY integration
```

The braces mean a verified finite set selected by the runtime provider pointer,
not an ambiguous guess between unrelated functions.

## Targeted Ghidra instruction freeze

`tools/ghidra/analyze_provider_dispatch_callsites.py` consumes
`SHIFT.GhidraFunctionInstructions/2` and requires these four virtual slots:

```text
FUN_007b3820  +0x14 acceptance
FUN_007b2210  +0x1c per-scalar reset
FUN_007b3f40  +0x20 cleanup
FUN_007b3f40  +0x18 solve
```

Generate only the required instruction export:

```bash
GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/provider_dispatch_instructions.jsonl \
  0x007b3820 0x007b2210 0x007b3f40

python3 tools/ghidra/analyze_provider_dispatch_callsites.py \
  out/provider_dispatch_instructions.jsonl \
  --json-out out/provider_dispatch_callsites.json
```

The analyzer records, for every candidate:

- function address;
- exact instruction address;
- raw instruction/operand;
- vtable base register;
- exact slot displacement;
- p-code for the call instruction;
- preceding instruction/p-code context;
- slot evidence state;
- pointer/object identity state.

It fails closed if a required function is absent, an expected slot is absent, or
a function contains multiple matching calls for a slot.  A matching slot never
proves provider ownership by itself: `provider_identity_state` remains `unknown`
in this syntactic layer.

## Persistent-motion graph impact

Before this block, current Process A documentation still described two indirect
calls in `FUN_007b3f40` as unresolved.  The stronger statement supported by the
existing provider evidence is now:

- the provider branch and its virtual slot roles are proven;
- the shipped implementation target set behind each relevant slot is verified;
- the selected concrete target remains runtime-dependent;
- exact callsite instruction VAs still require the narrow targeted export above.

Therefore the solver portion of the persistent state graph no longer needs an
open-ended “unknown indirect target” edge.  It can use a finite conditional edge
while preserving the null builtin fallback.

## Native-port-ready handoff

The dispatch/interface layer is ready to hand to native implementation with the
following contract:

```text
static evidence
  -> physics_system+0x48 provider state
  -> dynamic provider interface with +0x20/+0x1c/+0x18 slots
  -> exact shipped target sets per slot
  -> builtin FUN_007b0f20 fallback when provider is null
```

A native implementation must preserve dynamic provider selection.  It must not
hard-code provider 0 or provider 1 from this static evidence.

Provider numerical algorithms remain separate implementation work and are not
implemented by this block.

## Evidence policy / unresolved blockers

Still unresolved here:

1. exact x86 instruction addresses for the four indirect callsites until the
   targeted export is analyzed;
2. runtime-selected provider identity for any particular tick;
3. retail C++ provider class names/inheritance;
4. higher-level input/control ownership and rendered-frame cadence.

No field or class is renamed from offset similarity, no ownership is inferred
from pointer similarity, and no frame cadence or physical unit is invented.

## Tests

The block adds tests for both the composed static contract and the Ghidra
callsite analyzer:

```bash
pytest -q \
  tests/test_provider_dispatch_static_contract.py \
  tests/test_ghidra_provider_dispatch_callsites.py
```
