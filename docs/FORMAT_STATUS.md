# Форматный статус SHIFT importer

## Проверено на реальных ресурсах

| Формат | Результат |
|---|---|
| BFF v3 | Разбор таблицы/имён/типов/смещений |
| Type 0/1 | Raw + zlib |
| Type 2 | XMem/LZX, включая persistent LZX Huffman state между блоками |
| Reflection XML | Классы, наследование, typed properties, вложенные Fct |
| BMLY/BML | HEAD/ELMT/ATTR/COLL/NUMB/BOOL/STRS |
| BMT | Дерево material/shaderparam/value + DDS refs |
| HLSL | Includes/techniques/samplers/variables |
| DDS | Header/format/dimensions metadata |
| MEB | Реальные vertices/indices/material refs → MGEO |
| CSM/NXS MESH | Реальные collision vertices/triangle indices → CMES |
| VHF XML | CAR/NODE/RESOURCE graph |
| LOD XML | Реальный `tracks.lod`, включая malformed quote, через loose parser |

## Что ещё не является игровым runtime

Это уже полноценный importer/IR слой, но не готовый Android-порт игры. Пока отсутствуют: точная реконструкция FXO shader bytecode; IMB skeletal animation; SGB scenegraph semantics; полный runtime vehicle/track dependency resolution; замена/порт PhysX 2.x dynamics; Android renderer/audio/input/game loop.

## Важный принцип

BFF и оригинальные ресурсы остаются источником истины. Android runtime должен получать преобразованные нейтральные данные, а не знать о внутреннем BFF/XMem формате. Неизвестные ресурсы не отбрасываются: они сохраняются в raw blob с hash, путём, архивом и metadata.
