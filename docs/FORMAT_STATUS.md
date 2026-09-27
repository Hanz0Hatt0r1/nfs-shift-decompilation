# Форматный статус SHIFT importer

## Поддержка и верификация

| Формат | Результат |
|---|---|
| BFF v3 | Реальные архивы: разбор таблицы/имён/типов/смещений |
| Type 0/1 | Реальные ресурсы: Raw + zlib |
| Type 2 | Реальные ресурсы: XMem/LZX, включая persistent LZX Huffman state между блоками |
| Type 3 | Реализовано: OodleLZ_Decompress через внешний runtime; синтетический dispatch-test |
| X12d==2 | Реализовано и покрыто синтетическим тестом: RC4 для record table, name table и каждого payload |
| Reflection XML | Классы, наследование, typed properties, вложенные Fct |
| BMLY/BML | HEAD/ELMT/ATTR/COLL/NUMB/BOOL/STRS |
| BMT | Дерево material/shaderparam/value + DDS refs |
| HLSL | Includes/techniques/samplers/variables |
| DDS | Header/format/dimensions metadata |
| MEB | Реальные vertices/indices/material refs → MGEO |
| CSM/NXS MESH | Реальные collision vertices/triangle indices → CMES |
| VHF XML | CAR/NODE/RESOURCE graph |
| LOD XML | Реальный `tracks.lod`, включая malformed quote, через loose parser |
| Vehicle CDF | Source-backed section/property schema + lossless parser; physical units intentionally unresolved |

## Что ещё не является игровым runtime

Это уже полноценный importer/IR слой, но не готовый Android-порт игры. Пока отсутствуют: точная реконструкция FXO shader bytecode; IMB skeletal animation; SGB scenegraph semantics; полный runtime vehicle/track dependency resolution; замена/порт PhysX 2.x dynamics; Android renderer/audio/input/game loop.

## Ограничения BFF вариантов

`X12d==1` остаётся явно неподдерживаемым вариантом; canonical `nfsshift.bms 0.2.5` также останавливается на таком архиве. Для Type 3 Oodle библиотека намеренно не поставляется в репозитории: задайте `SHIFT_OODLE_LIB` на установленный совместимый runtime.

## Важный принцип

BFF и оригинальные ресурсы остаются источником истины. Android runtime должен получать преобразованные нейтральные данные, а не знать о внутреннем BFF/XMem формате. Неизвестные ресурсы не отбрасываются: они сохраняются в raw blob с hash, путём, архивом и metadata.
