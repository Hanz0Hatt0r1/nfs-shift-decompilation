# Process 1B — render-manager canonical global-slot owner closure

## Scope

This slice closes one specific external/unknown-origin question left after the bounded direct opaque surface reached 17/17: can the canonical render-manager outer-root slot at `0x00bc185c` itself be populated from an external or otherwise unknown source?

PC retail 1.02 machine code is authoritative. Ghidra metadata is navigation/fingerprint support only.

## Whole-text reference classification

Every instruction reference to `0x00bc185c` in retail `.text` falls into exactly one of three classes:

- 112 direct value loads from `[0x00bc185c]`;
- one address-of-slot literal materialization at `0x004fb9af`;
- two writes to the slot, both in the same initializer window.

The address literal is not an independent root producer:

```text
0x004fb9af mov edi,0x00bc185c
0x004fb9b5 mov edi,[edi]
```

It first materializes the slot address and then performs the ordinary value load.

## Canonical slot writer

The only writer window is `0x00d362b9..0x00d362fa`:

```text
0x00d362b9 push 0x46e0
0x00d362be call 0x008868c0
...
0x00d362d3 cmp eax,esi
0x00d362d5 je 0x00d362f3
0x00d362d7 mov ecx,eax
0x00d362d9 call 0x0045ef50
0x00d362ec mov [0x00bc185c],eax
...
0x00d362f3 mov [0x00bc185c],esi
```

On success, the value written into the global slot is the locally allocated `0x46e0`-byte object after `FUN_0045ef50` construction. On failure, the slot receives the local sentinel held in `ESI`.

`FUN_0045ef50` captures the receiver at `0x0045ef59` and writes the already-proven render-manager vtables, including primary vptr `0x00ab5644` at `0x0045ef78`. This joins the initializer value to the existing render-manager object identity without relying on numeric offset coincidence.

## Adjudication

The canonical slot's writer/initializer surface is closed:

- no external initializer writes `DAT_00bc185c`;
- no unknown-origin value is written into the slot;
- the success value is locally allocated and constructed;
- the failure value is the sentinel path.

This does **not** claim that every later copy of the exact root value is closed globally. Unknown-origin copies created through unrelated memory/helper-return paths remain a separate frontier, as does two-unknown-origin reconstruction of `HDVehicle+0x4330`.

The manager `+0x374 -> HDVehicle+0x4330` join, literal `0x004b86cf`, P1.3 completion and provider-count reduction all remain fail-closed. Provider count remains 7.
