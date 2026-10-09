# Process 1B: `0x00b04524` computed `+0x374` receiver rejections

Three of the six residual computed-address forwarding paths use the same outer receiver in `FUN_0070fae0` / `FUN_0070f580`.

The constructor captures entry ECX in ESI and explicitly installs vptr `0x00b04524` at `0x0070fb13`. The destructor likewise captures ECX in ESI and reinstalls the same vptr at `0x0070f5a0` before destroying embedded subobjects. Participants Manager uses root vptr `0x00ab9190` and embedded `+0x20` vptr `0x00ab916c`.

Therefore the same ESI base used by:

- `0x0070f62d -> FUN_006310c0`,
- `0x0070fb45 -> FUN_00533e70`,
- `0x0070fdeb -> FUN_006329e0`

is exactly the `0x00b04524` object, not Participants Manager. The three computed `ESI+0x374` receivers cannot target manager `+0x374`.

This reduces the residual destination/receiver forwarding frontier from six to three: `0x005292db`, `0x005f4ffa`, and `0x005f6eda`. No identity is inferred from the shared numeric offset. `0x004b86cf`, P1.3 completion and provider removal remain fail-closed; provider count remains 7.
