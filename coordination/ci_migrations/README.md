# CI workflow migrations

This directory records incremental migrations from historical phase-numbered GitHub Actions workflows to stable workflow families.

Each migration contract must identify the retired workflow blobs, the stable replacement, the preserved Python/native/CTest/report surface, and whether semantic gates or provider counts change.

A historical workflow may be removed only after its replacement preserves the union of required checks for that migration batch. New runtime coverage belongs in stable workflows, pytest/CTest targets, or data-driven matrices rather than new phase-numbered YAML files.
