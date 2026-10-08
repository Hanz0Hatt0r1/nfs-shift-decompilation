# Process 1 next step after `FUN_00791020` rejection

`SHIFT.Fun00791020HDVehicleRejection/1` removes the raw `receiver+0x938` match from the selected-HDVehicle writer frontier.

The live P1.3 chain remains:

```text
retail input/control producer
  -?-> exact selected-HDVehicle writer
  -?-> HDVehicle+0x938/+0x13b8/+0x1e38/+0x28b8
  -> FUN_00755950
  -> FUN_00758b50
```

Next search rule: candidate stores must first prove a receiver/base alias to selected `HDVehicle`; numeric subobject offsets alone are navigation evidence only.

Provider count remains 7. P1.3 remains incomplete.
