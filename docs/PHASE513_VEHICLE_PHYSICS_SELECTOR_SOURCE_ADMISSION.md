# Phase 513 — selector source-record admission and scheduling

## Goal

Record how an upstream source record becomes eligible for population into the
selector descriptor table owned by DAT_00bbc600.

Contract:

SHIFT.VehiclePhysicsSelectorSourceAdmission/1

## Admission mask

thunk_FUN_00d758d0 derives:

(source_record+0x10) & 0xf

and forms a single-bit mask:

1 << selector_key

The source record is admitted only when the corresponding bit is already set in
owner+0x4f0. On a hit the routine:

1. ensures DAT_00bbc600 is initialized;
2. calls thunk_FUN_00409290(&DAT_00bbc600, source_record);
3. clears the same bit with XOR.

When the bit is not set, no selector-population call is made.

## Reset/resynchronization

FUN_004d4d40 initializes owner+0x4f0 to zero.

Two observed reset paths both call thunk_FUN_00496cf0(&DAT_00bbc600, param_1)
and clear the same mask:

- FUN_004b6b30;
- thunk_FUN_00d75a20.

The latter also calls thunk_FUN_00d752b0(param_1).

## Relation to descriptor population

Phase 512 showed that thunk_FUN_00409290 then gates actual descriptor
population on:

selector context+0x1c < selector context+0x28

and calls thunk_FUN_00d36a00.

Therefore the mask gate and capacity gate are independent observed conditions:

mask admission -> descriptor population attempt -> capacity check.

The mask bit alone does not prove that population succeeded.

## Evidence boundary

The low-nibble value is treated only as an observed routing key. The owning
object is described structurally, without assigning an engine/gameplay class.
