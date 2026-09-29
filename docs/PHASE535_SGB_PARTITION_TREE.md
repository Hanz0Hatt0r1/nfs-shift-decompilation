# Phase 535 — source-backed SGB PART partition tree

Phase 535 corrects the binary PART record layout and maps the record into the
runtime partition tree consumed by `FUN_0068a360` and `FUN_00689a30`.

## Correct source record layout

`FUN_006a4d10` starts each record at the first DWORD after the PART chunk
record count. The fixed portion is `0x30` bytes, followed by a variable
child-object reference table.

| Source offset | Field |
|---:|---|
| `+0x00` | partition id |
| `+0x04` | AABB min.x |
| `+0x08` | AABB min.y |
| `+0x0c` | AABB min.z |
| `+0x10` | AABB max.x |
| `+0x14` | AABB max.y |
| `+0x18` | AABB max.z |
| `+0x1c` | child partition id slot 0 |
| `+0x20` | child partition id slot 1 |
| `+0x24` | child partition id slot 2 |
| `+0x28` | child partition id slot 3 |
| `+0x2c` | child object reference count |
| `+0x30...` | variable child object references |

The previous decoder started both AABB and variable child-table fields four
bytes too late. Phase 535 fixes that offset error.

The loader only materializes the four child-partition slots when the first
source slot is non-zero. When present, all four values are forwarded.

## Runtime partition node

The first PART record reaches `FUN_0068a360`. If the scene-manager root field
at `+0x28` is empty, it allocates the first partition node through
`FUN_00688ef0 -> FUN_006886a0`. The constructed node has vtable
`PTR_FUN_00af7a68`.

Proven fields used by the consumer are:

| Runtime node offset | Meaning |
|---:|---|
| `+0x04..+0x0f` | AABB min vec3 |
| `+0x10..+0x1b` | AABB max vec3 |
| `+0x1c/+0x20/+0x24/+0x28` | four child-partition slots |
| `+0x34` | child-wrapper container used by observed virtual kind code 4 |
| `+0x58` | child-partition-id mask |

If a four-slot child partition table is present, `FUN_0068a360` copies all
four source IDs into the runtime slots and ORs the mask with `0x0f`.

## Tree insertion

For every later PART record, `FUN_0068a360` delegates to
`FUN_00689a30`.

`FUN_00689a30` searches the existing tree for a slot whose stored unresolved
ID equals the incoming `partition_id` and whose corresponding mask bit is
still set. It then:

1. allocates a new runtime partition node;
2. replaces the matching ID slot with the new child-node pointer;
3. copies the new record AABB and child partition IDs;
4. clears that slot's mask bit in the parent.

Therefore the four `+0x1c..+0x28` fields are proven dual-state slots:
unresolved child partition IDs before insertion and child partition node
pointers after insertion.

## Child object references

The variable PART table is passed to `FUN_0068a360` as a list of source
integer references. For each entry the retail code calls:

`FUN_006885b0(scene_wrapper_list, source_id - 1)`

The lookup argument is unsigned. Phase 535 therefore records the exact
`(source_id - 1) & 0xffffffff` transform rather than imposing an additional
parser-side validity rule.

The resolved scene wrapper receives a pointer to the partition node AABB
(`partition_node + 0x04`) at wrapper `+0x30`.

The wrapped payload is queried through virtual function offset `+0x04`.
Observed return codes are retained numerically:

- code 1: the first-root path releases the payload through its vtable;
- code 3: the wrapper is appended to the scene-manager container at `+0x58`;
- code 4: the wrapper is appended to the partition-node container at `+0x34`.

Phase 535 does not invent class names for these codes.

## Finalization

After all PART records, `FUN_006a4d10` calls:

- `FUN_0068b9d0(manager, scene_wrapper_list)`;
- `FUN_0068ab70(manager)`.

These calls are retained as source-backed post-load finalization provenance;
their higher-level scene semantics remain separate work.

## Boundary

This phase proves the PART source layout, hierarchical partition-ID replacement
mechanism, AABB storage, wrapper partition pointer and numeric child-dispatch
behavior. It does not assign gameplay/visibility meanings to the partition
tree or class identities to virtual kind codes 1/3/4.
