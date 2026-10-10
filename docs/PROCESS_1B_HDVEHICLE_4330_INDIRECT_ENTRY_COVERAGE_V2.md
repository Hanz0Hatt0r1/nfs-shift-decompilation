# Process 1B — HDVehicle+0x4330 bounded indirect-entry coverage v2

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/2` supersedes `/1` and consumes the current exact-carrier seed provenance baseline.

The bounded baseline now contains four classes:

- static/source-visible exact carrier materialization: 4 subclasses, 0 carrier hits;
- canonical computed/loader entry publication: 3 subclasses, 0 carrier hits;
- bounded runtime callback registration: 8 surfaces, 51 physical callsites, 36 possible entrypoints, 0 carrier hits;
- exact preferred-imagebase + exact carrier-RVA immediate synthesis: 2,847,850 decoded instructions over a 16-carrier superset, 0 exact carrier-RVA scalar uses and 0 construction candidates.

This update incorporates the machine-closed `_bsearch` comparator surface and the merged P1A exact `imagebase+RVA` negative proof that were absent from `/1`.

The bounded exact-carrier hit count remains zero.

Global indirect-entry gates remain fail-closed. Split/table-derived RVAs, encoded/XORed arithmetic, delayed module-base consumers, runtime-generated/copied function pointers, runtime patching, remaining callback families and opaque indirect dispatch are outside this bounded contract.

Provider count remains 7.
