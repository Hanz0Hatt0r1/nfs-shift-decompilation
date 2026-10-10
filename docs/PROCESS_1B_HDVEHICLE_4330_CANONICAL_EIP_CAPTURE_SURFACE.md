# Process 1B — HDVehicle+0x4330 canonical EIP-capture surface

After the whole-image absolute/RVA literal-pointer scan closes negative, this P1.3B slice checks the canonical position-independent x86 address-synthesis idiom:

```text
call next
next:
pop reg
```

The detector works on instruction boundaries from `objdump -d -M intel`, not raw-byte matches. The PE executable-section table is checked independently and pins the executable sections to `.text` and `.secu`.

## Result

Exactly one instruction-aligned canonical candidate exists:

```text
0x00d31404  call 0x00d31409
0x00d31409  pop ebp
0x00d3140a  sub ebp,0x409
```

The subtraction yields `0x00d31000`, exactly the base of the `.secu` section. The complete machine window through the helper return at `0x00d31442` shows the derived pointer used only for `.secu`-rooted lock/TLS bookkeeping: `EBX=EBP`, `XCHG [EBX],EAX`, and `EBX += 0x40` across a 16-slot search.

No exact `HDVehicle+0x4330` carrier function address is derived.

## Fail-closed boundary

This closes only immediate `CALL next` followed by immediate `POP GPR` on real instruction boundaries. It does not close:

- x87 `FSTENV/FNSTENV` instruction-pointer extraction;
- non-adjacent call/pop constructions;
- transformed-constant address reconstruction;
- function pointers copied from runtime data;
- encoded pointers or unresolved indirect dispatch.

Therefore `runtime_computed_carrier_pointers_ruled_out`, `indirect_entry_into_carriers_ruled_out`, global runtime-derived `+0x4330` alias closure, the manager identity join, final `0x004b86cf`, aggregate P1.3 and provider removal remain false. Provider count remains 7.
