# BFF corpus audit

Структурный аудит реальных архивов, выполненный 27 сентября 2026 года, показывает:

| Архив | Размер | Entries | Type 0 | Type 1 | Type 2 | Type 3 | X12d |
|---|---:|---:|---:|---:|---:|---:|---:|
| BMW_M3_E36.bff | 18,934,688 | 1122 | 1 | 0 | 1121 | 0 | 0 |
| BMW_M3_E36_Cockpit.bff | 9,956,064 | 1043 | 1 | 0 | 1042 | 0 | 0 |
| RENDER.bff | 2,985,696 | 694 | 0 | 0 | 694 | 0 | 0 |

Вместе это 2859 ресурсов. Во всех трёх архивах основной контейнерный путь — Type 2 XMem/LZX; `X12d == 2` на этих реальных файлах не наблюдается.

## BMW_M3_E36.bff

Основные расширения:

- `.fxo` — 831
- `.meb` — 162
- `.dds` — 72
- `.bmt` — 32
- `.aud` — 4
- `.xml` — 3
- `.bab`, `.bas`, `.cdp`, `.cdv`, `.cgp`, `.csd`, `.vhf`, `.cdf` — по 1

Отдельно важны четыре `.aud` ресурса автомобиля и `vehicles/physics/chassis/bmw_m3_e36.cdf`: они пока не имеют полноценного нейтрального runtime-парсера.

## BMW_M3_E36_Cockpit.bff

Основные расширения:

- `.fxo` — 876
- `.dds` — 75
- `.bmt` — 43
- `.meb` — 44
- `.bad`, `.bas`, `.cpt`, `.vhf`, `.bml` — по 1

Это хороший следующий набор для связки cockpit mesh/material/animation без использования большого trace.

## RENDER.bff

Состав:

- `.fxo` — 592
- `.fx` — 81
- `.fxh` — 21

То есть `RENDER.bff` практически полностью является shader corpus. Следующий приоритет — автоматический inventory `.fx/.fxh/.fxo` и установление связей `source FX -> FXO permutation -> material BMT`.

## Инструмент

Добавлен `bff_audit.py`. По умолчанию он не распаковывает ресурсы, а быстро строит индекс BFF. Дорогой decode включается отдельно:

    python bff_audit.py BMW_M3_E36.bff audit.json
    python bff_audit.py RENDER.bff audit.json --decode --decode-extension .fx --decode-extension .fxh

Для больших архивов можно ограничить число декодируемых записей:

    python bff_audit.py BMW_M3_E36.bff audit.json --decode --decode-extension .meb --max-decode 20

Неизвестные расширения и ошибки декодирования сохраняются в отчёте, а не отбрасываются.

## Следующий практический этап

После структурного inventory логично автоматизировать декодирование только `MEB/BMT/DDS/FX/FXH/FXO/VHF/BML/BAB/BAS/CGP/CSM` и построить dependency graph по трём архивам. Это даст карту реальных игровых ресурсов без необходимости возвращаться к монолитному 2.9 GiB trace.