# Process 1B — render-manager constructor exact-this escape closure

## Scope

The canonical root is allocated before `DAT_00bc185c` is populated, so constructor `FUN_0045ef50` is a unique pre-global window where the exact freshly allocated outer pointer could theoretically escape into another persistent location.

## Machine result

At entry:

```text
0x0045ef59  mov esi,ecx
```

so `ESI` is the exact constructor `this` pointer for the machine range `0x0045ef50..0x0045f630`.

A whole-range machine scan for uses of `ESI` as a **value** finds no memory store of the exact pointer and no argument transfer of the exact pointer into `ECX`, `EDX`, or the stack after capture. The only relevant value uses are:

```text
0x0045ef57  push esi     ; callee-saved prologue, before ECX->ESI capture
...
0x0045f5ea  mov eax,esi ; return this
```

All other `ESI`-based stores are field writes through `[ESI+offset]`; they initialize the object and do not copy the outer pointer value elsewhere.

## Adjudication

`FUN_0045ef50` does not persist or opaque-forward the exact outer pointer before returning it in `EAX`. The initializer then stores that returned `EAX` into the canonical `DAT_00bc185c` slot.

This closes the constructor-created persistent-copy path negatively. It does not close aliases that may be created later by runtime/external systems.

The manager `+0x374 -> HDVehicle+0x4330` identity join, literal `0x004b86cf`, P1.3 completion and provider removal remain fail-closed. Provider count remains 7.
