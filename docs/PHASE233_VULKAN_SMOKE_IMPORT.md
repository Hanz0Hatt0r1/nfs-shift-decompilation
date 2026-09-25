# Phase 233 — Linux Vulkan smoke runner import fix

The Linux smoke workflow executes tools/run_linux_vulkan_smoke.py directly. Python places the tools directory first on sys.path in that mode, so repository-root modules such as bmw_vulkan_bundle are not importable by default.

Phase 233 adds an explicit repository-root import path before loading the bundle modules. No rendering or ABI behavior changes.
