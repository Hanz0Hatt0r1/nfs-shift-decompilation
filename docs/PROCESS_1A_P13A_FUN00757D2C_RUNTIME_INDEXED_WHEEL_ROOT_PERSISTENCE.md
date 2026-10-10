# Process 1A / P1.3A — `FUN_00757d2c` runtime indexed wheel-root persistence

This contract closes one positive reconstructed-wheel path that was outside the earlier fixed-root materialization handoff.

Merged `SHIFT.GlobalVehicleComponentCallsiteStatic/1` proves the runtime entry state for `FUN_00757d2c`:

- `ECX = vehicle`;
- `EAX = slot * 0xA80`;
- vehicle base at the audited callsite is `0x00c13700`;
- slot count is four.

The retail core then executes at `0x00757d2e`:

```text
lea eax,[eax+ecx+0x400]
```

so EAX becomes the exact wheel root `vehicle + 0x400 + slot*0xA80`. This includes P1.3A slot0 (`HDVehicle+0x400`) and slot1 (`HDVehicle+0xe80`), whose selected target spans remain `HDVehicle+0x938..+0x93f` and `HDVehicle+0x13b8..+0x13bf`.

## Exact root lifetime

The complete retail body `0x00757d2c..0x00757e51` is 293 bytes, SHA-256 `587dcc93159ef142ef57d18e657aa3078e5d2748db0febb4ecba32a286bc20fa`.

While EAX still holds the exact root, the machine code only:

- reads `wheel+0x424`;
- writes scalar byte fields `wheel+0x504` and `wheel+0x540`;
- on the slow branch, reads child pointer `[wheel+0x420]`.

The root dies at `0x00757d51` on the fast branch or `0x00757d99` on the slow branch. Before those kills there are zero stores of the root value, zero pushes, zero GPR copies and zero calls/jumps carrying the live root.

The slow-path child pointer is copied to stack slot `[EBP+0x8]`; it is not the wheel-root value and remains a separate alias class.

## Gate effect

Promoted only:

- `p13a_fun00757d2c_runtime_indexed_wheel_root_subset_complete = true`.

Positive reconstruction is retained:

- `runtime_indexed_exact_wheel_root_materialization_found = true`.

Negative within this bounded path:

- exact root persistent escape = false;
- selected slot0/slot1 root store = false.

Global gates deliberately remain fail-closed, including reconstructed wheel pointers, runtime-generated selected-wheel pointer stores, stored/escaped aliases, callbacks/indirect entry, slot0, slot1 and aggregate P1.3. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun00757d2c_runtime_indexed_wheel_root.py \
  /path/to/SHIFT.exe \
  evidence/global_vehicle_component_callsite_phase633.json \
  --output evidence/p1a_p13a_fun00757d2c_runtime_indexed_wheel_root_persistence.json
pytest -q tests/test_process1a_p13a_fun00757d2c_runtime_indexed_wheel_root.py
```

Next P1A work is to classify the remaining exact four-wheel/indexed materializers, especially `FUN_00757318`, `FUN_007582f0`, `FUN_007653f9` and `FUN_0076ed60`, before changing the global runtime-generated selected-wheel pointer gate.
