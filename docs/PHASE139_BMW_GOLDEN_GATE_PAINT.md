# Phase 139 — BMW golden gate paint-contract integration

`SHIFT.BMWGoldenRenderGate/1` now consumes the `paint_contract` emitted by `compile_material()`.

For every BMW golden submesh, an unready paint contract or explicit material blocker is copied into the gate's `blocking_reasons`. A ready contract adds no blocker.

This closes the static evidence path:

`BMW M3 golden MEB → DrawPacket → compile_material → BMW paint contract → StaticDraw → BMWGoldenRenderGate`.

The gate still requires unique FXO/shader selection and linked shader pair evidence. It does not claim runtime frame/object attribution.

## Next

Feed a real extracted M3 `resource_analysis` + material binding report into `build_draw_packets`, then run the gate against the committed BMW golden manifest. The remaining external blocker is obtaining/processing the actual BFF bytes in the execution environment and, separately, runtime D3D9 capture.