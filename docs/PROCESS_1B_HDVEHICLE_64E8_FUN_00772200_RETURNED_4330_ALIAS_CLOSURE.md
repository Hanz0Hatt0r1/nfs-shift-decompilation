# Process 1B — FUN_00772200 returned HDVehicle+0x4330 alias closure

`FUN_00772200` captures its receiver in `ESI` and returns it with `0x0077233f mov eax,esi`. The retail direct-call index has exactly two callers.

At `0x0076b247`, `FUN_0076b130` passes the exact `HDVehicle+0x4330` pointer produced at `0x0076b241`. The returned EAX value is not stored or forwarded: the caller prepares `HDVehicle+0x6730`, calls another routine at `0x0076b256`, then explicitly returns the HDVehicle root with `mov eax,esi`.

At `0x00798f5c`, `FUN_00798df0` calls the same constructor with `ECX=EBP-0x238c`, a stack-local object. Its return value is immediately overwritten at `0x00798f61`.

Therefore the receiver-return convention of `FUN_00772200` does not create an escaped exact `HDVehicle+0x4330` alias. Other consumer families remain open. The manager+0x374 join and literal `0x004b86cf` remain fail-closed; provider count remains 7.
