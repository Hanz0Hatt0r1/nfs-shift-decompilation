# Phase 381 — vehicle CDF schema and parser

Этот этап переносит границу загрузки автомобильной физики из retail `SHIFT.exe.c`
в нейтральный Python IR.

## Доказанная граница

Основной загрузчик `FUN_007be420` распознаёт секции:

- `GENERAL`
- `FRONTWING`
- `LEFTFENDER`
- `RIGHTFENDER`
- `REARWING`
- `BODYAERO`
- `DIFFUSER`
- `SUSPENSION`
- `CONTROLS`
- `ENGINE`
- `DRIVELINE`
- `FRONTLEFT`
- `FRONTRIGHT`
- `REARLEFT`
- `REARRIGHT`
- `BASIC`

Переходы из загрузчика зафиксированы на следующие обработчики:

| Секция | Runtime boundary |
|---|---|
| GENERAL | `FUN_007be420` |
| FRONTWING | `FUN_007c0a20` |
| LEFTFENDER | `FUN_007bccc0(type=10)` |
| RIGHTFENDER | `FUN_007bccc0(type=11)` |
| REARWING | `FUN_007c0c00` |
| BODYAERO | `FUN_007c27e0` |
| DIFFUSER | `FUN_007bda10` |
| SUSPENSION | `FUN_007bdb80` |
| CONTROLS | `FUN_007bd290` |
| ENGINE | `SpeedLimiter` через общий section scan |
| DRIVELINE | `FUN_007bcdf0` |
| FRONTLEFT | `FUN_007bc770(index=0)` |
| FRONTRIGHT | `FUN_007bc770(index=1)` |
| REARLEFT | `FUN_007bc770(index=2)` |
| REARRIGHT | `FUN_007bc770(index=3)` |
| BASIC | `FUN_007715f0` + `FUN_007a65e0` |

## Что переносится

`vehicle_cdf_runtime.py` содержит:

- CDF section/key/value parser;
- сохранение исходного `raw` значения;
- числа, bool и tuple parsing;
- обработку range-like троек без назначения физических единиц;
- source-backed property schema;
- destination offsets;
- использованный runtime helper (`FUN_007a6a90`, `FUN_007a75a0`, `FUN_007a6470`, `FUN_007a65e0`, `FUN_007a67b0`, `FUN_007a63e0`);
- сохранение неизвестных свойств и malformed строк;
- strict/non-strict режимы.

Известные wheel, suspension, driveline, controls, aero, fender и diffuser свойства теперь имеют машинно-читаемую связь `CDF key -> helper -> object offset(s)`.

## Важное ограничение

`value_shape` — это форма сохранённого runtime поля, а не утверждение о физических единицах. `tuple3` не объявляет поле координатами автоматически. Семантика допускается только там, где она доказана отдельным runtime-кодом.

Неизвестные keys не отбрасываются. Это важно для игровых CDF, где часть параметров может приходить из версий или модификаций, отсутствующих в текущем source corpus.

## Следующая граница

Следующий практический шаг — извлечь реальный `vehicles/physics/chassis/bmw_m3_e36.cdf` из `BMW_M3_E36.bff`, прогнать через schema parser и получить полный JSON-профиль физики BMW M3 с provenance по каждому параметру.

После CDF следует связать `cdf -> edf -> gdf -> sdf -> cgp/cdp/cdv/csd` через уже восстановленные Physics Manager roots и `FUN_0074d640`.