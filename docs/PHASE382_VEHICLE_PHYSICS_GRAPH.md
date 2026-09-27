# Phase 382 — vehicle physics resource graph and SDF runtime topology

Этот этап объединяет четыре реальных physics resources BMW M3 в один machine-readable
runtime profile:

- `CDF` — секции, keys, helpers и destination offsets;
- `EDF` — engine properties и 41 `RPMTorque` point;
- `GDF` — gearbox ratio records и source comparator `FUN_00771320`;
- `SDF` — BODY/JOINT/HINGE/BAR/JOINT&HINGE topology и ссылки тел.

## Что теперь proven

1. `BMW_M3_E36.bff` содержит отдельные CDF/EDF/GDF/SDF entries, все Type 2 XMem/LZX.
2. CDF сохраняется без потери неизвестных keys.
3. EDF сохраняет source/storage order `RPM, brake, throttle` -> `brake, throttle, RPM`.
4. RPMTorque interpolation и peak-power scan реализованы как отдельные deterministic helpers.
5. GDF ratio pairs имеют отдельный derived sort view по `second/first` ascending.
6. SDF multi-assignment lines разбираются losslessly.
7. SDF BODY references проверяются до compiled topology.
8. `FUN_007b3150` теперь представлен через neutral topology IR: Joint/Hinge/Bar flags, body indices, endpoint references и proven record strides.

## Граница

PhysX class names, constructor call sequence, SDK object ownership и физические единицы
пока не назначаются. Это следующий source-backed target вокруг `FUN_007b3150`,
`FUN_007b3670` и последующего `FUN_007b3820` processing.

## Reproducible entry point

    python vehicle_physics_bundle.py BMW_M3_E36.bff out/bmw_physics

Скрипт извлекает только нужные physics entries и сохраняет identity/provenance в
JSON. Retail binary/text payloads не добавляются в Git.