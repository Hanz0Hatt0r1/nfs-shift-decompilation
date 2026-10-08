# Acceleration checklist

Use this before starting a new reverse-engineering slice:

- refresh `main` and inspect `coordination/decomp_blockers.json`;
- choose an unowned/non-overlapping blocker;
- use the SQLite Ghidra index for navigation, not semantic promotion;
- create new proof boilerplate with `tools/research/scaffold_proof.py`;
- keep new evidence fail-closed until exact PC-retail provenance is established;
- run focused pytest locally;
- require existing full merge gates before reducing provider count or promoting runtime readiness.
