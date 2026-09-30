# SHIFT structural class candidate audit

This note records the evidence gate used to identify registered classes whose
basic runtime structure can be recovered without guessing a vtable or a
reflected field offset.

## Source identity

- `SHIFT.exe` SHA-256:
  `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- `SHIFT.exe.c` SHA-256:
  `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`

## Audit

`tools/shift_live_dump/audit_shift_class_candidates.py` consumes the joined
class manifest and marks a class `structural_ready` only when all of the
following hold:

- the class name is resolved;
- reflection metadata is registered and contains at least one direct field;
- exactly one PE vtable candidate survives the descriptor-returning RTTI getter
  correlation;
- every direct field name is resolved;
- every direct field has a static reflection type code, byte offset and flags;
- the reflection builder function is identified.

Failures remain explicit through the `blockers` array. Current blocker labels
include `no_reflection_metadata`, `no_reflected_fields`,
`non_unique_vtable`, `unresolved_field_names`,
`dynamic_field_offsets`, `dynamic_field_types`,
`dynamic_field_flags`, and `unresolved_reflection_function`.

## Retail result

Running the audit on the supplied retail source/executable pair yields **227
structural-ready classes**. The count is unchanged after removing 743
thunk/non-thunk duplicate reflection calls; only per-class direct-field totals
were corrected. Rows are ordered with ready classes first and then by direct
reflected field count, so large layouts are easy to inspect; that ordering is
not a claim about subsystem importance or implementation priority.

Representative high-field-count ready rows include:

| Class | Direct fields | Unique vtable |
|---|---:|---:|
| `DriverAITweaker` | 189 | `0x00b07820` |
| `GamerProfile` | 181 | `0x00aada98` |
| `VehicleDetails` | 74 | `0x00abbc48` |
| `CockpitRender` | 67 | `0x00ab6890` |
| `Participants` | 58 | `0x00ab9190` |
| `CHUD` | 47 | `0x00ab43b0` |
| `CarSoundConfig` | 47 | `0x00ab0db8` |
| `TrackDetails` | 44 | `0x00abb208` |

Subsystem filters such as `--prefix AI`, `--prefix Vehicle`, or repeated
`--class-name` arguments can narrow the evidence pool before manual
constructor/call-site analysis.

## Boundary

`structural_ready` means only that the class identity, concrete vtable and
direct reflected layout are source/PE-backed. It does **not** establish object
size, ownership, array semantics, update order, constructor defaults, virtual
method meanings or gameplay behavior. Those still require constructor/factory,
call-site and, where relevant, runtime-capture evidence before code is promoted
into the decompiled implementation.
