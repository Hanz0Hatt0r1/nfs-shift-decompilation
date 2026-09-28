# Phase 497 — repository-wide Python syntax audit

## Goal

Phase 497 adds `tests/test_python_source_syntax.py`, which parses every repository `.py` source with Python's AST parser.

## Why

Recent GDB probe work exposed a class of regression where a single-character syntax error can remain hidden because GDB-only modules are not imported by ordinary unit tests.

The new audit catches such failures without importing project dependencies or the `gdb` module.

## Coverage

The test includes files under `tools/` and GDB-facing scripts. It ignores only `.git` and `__pycache__` paths.

Each syntax failure is reported with relative path, line, column and Python parser message.

## Scope boundary

This is a syntax-only guard. It does not prove imports resolve, GDB is available, runtime memory reads succeed, or the decompilation behavior is correct.