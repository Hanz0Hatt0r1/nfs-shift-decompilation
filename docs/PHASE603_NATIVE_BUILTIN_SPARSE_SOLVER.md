# Phase 603 — native builtin sparse solver backend

Phase 602 admits the source-backed participant registry/selector structural ABI
into `SHIFT.NativeRuntimeState/1` without fabricating a concrete retail
participant instance.

Phase 603 ports the already-recovered numeric builtin SDF solver kernel
`FUN_007b0f20` into native C++.

## Scope

New native files:

- `native_runtime/include/shift_builtin_sparse_solver.hpp`;
- `native_runtime/src/builtin_sparse_solver.cpp`;
- `native_runtime/tests/builtin_sparse_solver_check.cpp`.

The implementation mirrors
`src/physics/sdf_builtin_sparse_solver_runtime.py`.

The execution order is preserved:

1. update the current diagonal from lower dependencies;
2. compute the reciprocal diagonal;
3. eliminate later-row column values and store normalized factors;
4. perform forward RHS substitution through the terminal forward record;
5. perform reverse substitution from `n-2` down to zero.

The native contract is tagged with the recovered source function
`FUN_007b0f20`.

## Record contract

The backend consumes the same abstract graph shape as the Python reference:

- `n+1` forward records;
- `n` reverse records;
- forward record `i`, item zero = pivot/lower dependencies;
- remaining forward items = later target rows;
- forward record `n`, item `i` = forward-substitution dependencies;
- reverse record `i` = already-solved upper dependencies.

Here, **sparse** describes those dependency records and the operations selected
by them. It is not a claim that the public matrix ABI is CSR/CSC or another
compressed sparse storage format. The compatibility API still accepts and
returns `std::vector<std::vector<double>>`, while the native factorization hot
path flattens the validated square matrix into one contiguous row-major
`std::vector<double>` work buffer to avoid per-row allocation and pointer
chasing. A future compressed-matrix ABI should only be introduced if retail
storage evidence or measured scene scale makes it necessary.

Invalid cardinality, invalid dependency direction and zero pivots fail closed.

## Native regression

The C++ regression executable validates:

- the known 3×3 case with solution `[1, 2, 3]`;
- an independent deterministic 4×4 case with a known solution;
- rejection of invalid graph cardinality;
- rejection of a zero pivot.

It emits:

`SHIFT.NativeBuiltinSparseSolverCheck/1`

and reports `source_function = FUN_007b0f20`.

CMake exposes the backend as `shift_runtime_physics` and registers
`shift_runtime_builtin_sparse_solver` with CTest. Linux CI runs both CTest and
the JSON-emitting check executable.

## Important boundary

Phase 603 proves the **builtin numerical kernel**, not a complete retail vehicle
physics frame.

The native fixed-step loop does not yet call this solver for BMW state because
the surrounding frame still has separate evidence requirements:

- real per-frame matrix/RHS assembly;
- runtime `FUN_007b2210` diagonal-reset selection flags;
- exact pre/post-solve body-state transport for the native vehicle state;
- provider-present dispatch and provider acceptance state;
- concrete participant/provider runtime identity.

The provider path remains independent: retail provider vtable `+0x18` is not
replaced by the builtin kernel.

## Next gate

The next safe integration step is to build a fail-closed native solver-frame
input contract containing an exact solver graph plus matrix/RHS/reset evidence,
then invoke this backend only when the provider-absent builtin path is proven
for that frame.
