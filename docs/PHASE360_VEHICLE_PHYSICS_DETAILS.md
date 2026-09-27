# Phase 360 — vehicle physics details and driveline solver

This phase extends the non-rendering physics track from the resource-root registry into
the concrete High Detail Vehicle (HDV) data model and driveline integration.

## Evidence source

Primary source: recovered retail SHIFT.exe.c.

Source SHA-256:

512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9

Relevant recovered routines:

- FUN_007c3b00 — HDV top-level section loader
- FUN_007be420 — GENERAL parser
- FUN_007bc770 — four wheel-section parser
- FUN_007bdb80 — SUSPENSION parser
- FUN_007bcdf0 — DRIVELINE parser
- FUN_007c3280 — external ENGINE/EDF loader
- FUN_007c3920 — HDV post-load path
- FUN_00764266 — driveline integration
- FUN_007af310 — six-variable linear solver

## HDV section dispatch

FUN_007c3b00 contains an exact section dispatch for GENERAL, FRONTWING, LEFTFENDER,
RIGHTFENDER, REARWING, BODYAERO, DIFFUSER, SUSPENSION, CONTROLS, ENGINE, DRIVELINE,
FRONTLEFT, FRONTRIGHT, REARLEFT, REARRIGHT and BASIC.

The four wheel sections share FUN_007bc770 and are selected with indices 0..3.

ENGINE is not a normal property parser in the same way as GENERAL/SUSPENSION:
the HDV section exposes SpeedLimiter state while the main engine data is loaded from
an external EDF resource by FUN_007c3280.

## GENERAL

The evidence contract freezes 19 named properties. Important vehicle-state fields include:

- Mass at object +0x1C
- Inertia vec3 at +0x30
- DriftInertia vec3 at +0x78
- CGHeight at +0x180
- GraphicalOffset vec3 at +0xC8
- CollisionOffset vec3 at +0x110
- FuelTankPos vec3 at +0x158
- FuelTankMotion vec2 at +0x170

AI-related parameters and Symmetric are also recorded with their exact offsets.

## ENGINE / EDF

FUN_007c3280 registers 30 named engine properties in the HDV object. The recovered
contract includes EngineInertia, idle/launch/rev-limit controls, engine-map ranges and
settings, thermal quantities, lifetime statistics, starter state and other fields.

RPMTorque records begin at +0x1818 with 0x20-byte stride and contain three scalar
components in the observed record. The loader rejects the corpus once existing point
count reaches the observed 127-point boundary and checks the recovered ordering
conditions. Component identities, units and the final interpolation formula remain
unresolved.

FUN_007c3920 builds the external EDF path and performs the post-load engine stage.
The recovered source also reports an Engine-file-open failure from vehload.cpp line
0x6b8.

## SUSPENSION and wheels

The SUSPENSION parser contributes 49 named properties, including the recovered alignment,
track/wheelbase, anti-sway, third-damper, toe-in, caster and fender-flare controls.

The wheel parser contributes 45 named properties reused by four wheel objects. The
contract records bump/rebound travel, bump-stop and damper stages, brake torque/thermal
fields, camber, pressure, ride height, packer, spring, damping and brake-disc/pad
adjustment ranges/settings.

No physical units are invented by this phase.

## DRIVELINE

The DRIVELINE parser contributes 40 named properties. The evidence includes:

- WheelDrive string
- clutch engagement/inertia/torque and wear/friction
- manual/semi-automatic flags
- upshift/downshift timing and throttle controls
- ForwardGears
- final drive and reverse
- eight gear settings
- differential pump/power/coast/preload ranges and settings
- adjustable-gear range/minimum fields

The gear-setting addresses form a regular observed sequence from Gear1 through Gear8.

## Driveline integration

FUN_00764266 builds and solves a 6-variable linear system through FUN_007af310.

FUN_007af310 is reconstructed as a pivoting Gaussian-elimination/Gauss-Jordan style
solver: it selects a non-zero pivot (including lower-row search and row swap), normalizes
the pivot row, eliminates the pivot column from the other rows and reports failure when
no usable pivot exists.

The HDV caller emits the source-backed diagnostic "Could not solve driveline" on solver
failure at hdvehicle.cpp source line 0x1d46 (7494 decimal).

After the solve, five sign/threshold state checks use recovered offsets:

- +0xD0 against +0x770
- +0xCC against +0x11F0
- +0xC8 against +0x1C70
- +0xC4 against +0x26F0
- +0x1C against +0x30

Only the branch behavior is claimed; the physical identities of the six solved variables
and the meaning of the sign states remain unresolved.

## Post-load sequence

The observed HDV post-load call order is preserved exactly:

FUN_007c3920
FUN_007bf0e0 x4
FUN_007bf590
FUN_007bfbe0
FUN_007bdb60
FUN_007bf790
FUN_007bf6e0
FUN_007c2110
FUN_007bf430 x2
FUN_007bf310 x2

## BMW resource linkage

The supplied BMW archive contains the expected vehicle-physics path family, including:

vehicles/physics/chassis/bmw_m3_e36.cdf
vehicles/physics/engines/bmw_m3_e36.edf
vehicles/physics/gearbox/common.gdf
vehicles/physics/suspension/aarm_multilink.sdf

This confirms corpus-level consistency with the Phase 359 root registry. It does not yet
prove byte-level ownership of individual property payloads.

## Verification

The phase adds:

- SHIFT.VehiclePhysicsDetailsRuntime/1
- SHIFT.VehiclePhysicsSourceEvidence/1
- deterministic property-offset tables
- HDV section dispatch evidence
- RPMTorque boundary evidence
- 6-variable driveline-solver evidence
- regression tests covering the recovered tables and source markers

The local focused suite passes 10 tests.

Renderer code and RENDER.bff remain untouched.

## Explicit unknowns

- physical units of individual HDV properties;
- semantic identity of the six driveline solver variables;
- exact final RPMTorque interpolation formula;
- precise meaning of wheel sign-state values -1/0/1;
- concrete cross-file ownership below .cgp/.cdf/.edf/.gdf/.sdf;
- deeper semantics of the remaining post-load helpers.
