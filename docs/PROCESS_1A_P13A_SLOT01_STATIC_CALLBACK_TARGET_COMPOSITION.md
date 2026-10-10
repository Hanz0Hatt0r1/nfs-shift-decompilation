# Process 1A / P1.3A — static callback/indirect-target composition

## Scope

After the merged 16-carrier call-target composition, the remaining callback/indirect-entry frontier must be split between finite static/exported surfaces and runtime-created paths.

This handoff consumes two merged P1D navigation inventories for the same 16 exact carriers already composed by P1A:

- Ghidra-recorded `CALLIND` edges whose **caller** is an exact carrier;
- exported vtable/static-table literal code pointers whose **target** is an exact carrier.

These are bounded cross-check surfaces only. Existing retail machine contracts remain semantic authority for exact HDVehicle/wheel identity.

## Result

The Ghidra SQLite index contains 19,500 `indirect=true` call edges globally, but **zero** whose caller is one of the 16 exact carriers.

The exported static code-pointer surfaces are also zero-hit:

```text
exact carriers                         16
vtable candidates                    2533
vtable slots                        22416
exact-carrier vtable target hits        0
static-table records                55066
static-table declared bytes        956464
static-table raw bytes             684472
exact-carrier literal pointer hits      0
```

The static-table scanner uses little-endian 32-bit absolute VAs. Both export hashes are pinned by the upstream contract.

## Gate

```text
exact-carrier CALLIND-caller subset complete       = true
exact-carrier CALLIND caller edge found            = false
exact-carrier vtable-target subset complete        = true
exact-carrier static-table pointer subset complete = true
exact-carrier static target hit found              = false
callbacks registered outside carriers ruled out    = false
indirect entry into carriers ruled out              = false
global indirect dispatch ruled out                 = false
runtime-generated selected-wheel stores ruled out  = false
stored-or-escaped aliases ruled out                = false
slot0 complete                                     = false
slot1 complete                                     = false
P1.3 complete                                      = false
provider count                                     = 7
```

## Limits

Zero `CALLIND` rows only bounds indirect calls *originating from* the exact carriers in the Ghidra index. It does not rule out incoming indirect entry into a carrier, callback registration in another function, or runtime-patched/computed call targets.

Zero vtable/static-table carrier addresses only bounds the two finite exported code-pointer inventories. It does not exclude runtime-generated, copied or encoded code pointers, heap/global stores outside the exported table records, nor selected-wheel **data-pointer** persistence.

Therefore no global callback/indirect-entry or stored-or-escaped-alias gate changes in this step.

## Reproduce

```bash
python3 tools/ghidra/build_p1a_slot01_static_callback_target_composition.py \
  --output evidence/p1a_p13a_slot01_static_callback_target_composition.json
```

## Next step

Trace runtime callback registration/incoming indirect-entry joins and runtime-generated/copied selected-wheel data pointers. Any positive escape must be joined to its later consumer before the global alias gates can change.
