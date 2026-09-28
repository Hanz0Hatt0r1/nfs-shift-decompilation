# Phase 465 — source factor writes vs captured provider mutations

## Goal

Phase 465 связывает статический source-derived factor topology с реальным provider capture без попытки превратить обе стороны в одну логическую матрицу.

Каждый source factor edge `(pivot,column)` переводится в абсолютный адрес через `row_pointer[pivot] + 8*column`. Этот набор адресов затем сравнивается с изменёнными packed-workspace адресами из Phase 464.

## Comparison model

`overlap`
— factor address, который реально изменился между provider pre/post snapshots.

`factor_address_not_observed_changed`
— source factor address, который не изменился. Это допустимо: retail write мог записать то же числовое значение или конкретный путь мог не активироваться.

`capture_workspace_change_not_factor`
— изменившийся workspace address, который не является текущим source factor address. Это ожидаемо, поскольку solve выполняет и другие update/staging операции.

## Structural guarantee

The three address sets form an explicit partition of the two measured sets:

`factor = overlap ∪ factor_not_changed`
`capture_changed = overlap ∪ capture_outside_factor`

The validator enforces these identities but does not require a particular overlap ratio.

## Scope boundary

The cross-check is a storage-level correlation. It does not prove that an address represents a particular mathematical matrix coefficient and does not prove retail binary equivalence.

When a real provider capture is available, this report becomes the first direct measurement tying source-derived factor writes to live provider memory mutations.
