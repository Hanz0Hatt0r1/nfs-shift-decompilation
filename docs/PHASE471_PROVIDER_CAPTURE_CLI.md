# Phase 471 — specialized-provider capture verification CLI

## Goal

Phase 471 exposes the full provider-capture analysis through one command.

## Pre-solve only

    python tools/verify_specialized_provider_capture.py \
      --pre provider_pre_0_000001.json

This validates the provider geometry and reports the available session summary.

## Pre/post capture

    python tools/verify_specialized_provider_capture.py \
      --pre provider_pre_0_000001.json \
      --post provider_post_0_000001.json \
      --abs-tol 1e-10 \
      --rel-tol 1e-8

This adds the raw pre/post workspace and output mutation diff.

## With retail source

    python tools/verify_specialized_provider_capture.py \
      --pre provider_pre_0_000001.json \
      --post provider_post_0_000001.json \
      --source SHIFT.exe.c \
      --provider 0

This additionally measures the source-derived factor-address overlap against the live provider workspace mutation footprint and runs the Phase 469 reset-delta analysis.

## Status and exit code

The command returns exit code `0` only when the requested structural checks are ready. Numeric divergence is reported as a measured status, not silently converted into success.

Provider identity is never inferred from matrix values: the optional `--provider` argument is an explicit caller assertion checked against the capture.

## Scope boundary

The CLI is an evidence and differential-analysis tool. It does not claim binary equivalence with the retail provider and does not convert packed workspace storage into the older builtin matrix schema.
