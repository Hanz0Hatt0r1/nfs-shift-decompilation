"""Live BFF/resource progress instrumentation for playable bootstrap subprocesses.

This module is loaded through Python's standard ``sitecustomize`` hook only when
``tools/run_playable_from_shift_exe.py`` explicitly prepends this directory to
``PYTHONPATH``.  It does not alter resource admission or parsing semantics: it
wraps the existing BFF class and two orchestration calls only to report real
archive/entry completion counts.
"""
from __future__ import annotations

import os
import sys
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
ENTRY_PROGRESS_INTERVAL = 250


def _install_repo_paths() -> None:
    if SRC.is_dir():
        paths = [SRC]
        paths.extend(sorted(
            (path for path in SRC.rglob("*") if path.is_dir()),
            key=lambda path: (len(path.parts), str(path)),
        ))
        for path in reversed(paths):
            value = str(path)
            if value not in sys.path:
                sys.path.insert(0, value)
    for path in (ROOT, ROOT / "tools"):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)


def _count_bff_inputs(inputs: Sequence[str | Path]) -> int:
    """Count archives exactly as the current input materializer discovers them."""
    total = 0
    for raw in inputs:
        source = Path(raw)
        if source.is_dir():
            total += sum(1 for path in source.rglob("*.bff") if path.is_file())
            continue
        if source.suffix.lower() == ".bff":
            if source.is_file():
                total += 1
            continue
        if source.suffix.lower() == ".zip" and source.is_file():
            with zipfile.ZipFile(source) as archive:
                total += sum(
                    1
                    for name in archive.namelist()
                    if name.lower().endswith(".bff") and not name.endswith("/")
                )
    return total


@dataclass
class _PhaseState:
    name: str
    total: int
    seen: set[Path] = field(default_factory=set)
    done: int = 0
    failed: int = 0


@dataclass
class _ArchiveToken:
    state: _PhaseState
    ordinal: int
    path: Path
    entry_total: int = 0
    entry_highwater: int = 0
    closed: bool = False


class _ProgressTracker:
    def __init__(self, *, entry_interval: int = ENTRY_PROGRESS_INTERVAL) -> None:
        self.entry_interval = max(1, int(entry_interval))
        self._phase: _PhaseState | None = None

    @contextmanager
    def phase(self, name: str, inputs: Sequence[str | Path]) -> Iterator[None]:
        print(
            f"[resource-progress] phase={name} event=discovering-archives",
            flush=True,
        )
        previous = self._phase
        try:
            total = _count_bff_inputs(inputs)
        except Exception as exc:
            print(
                f"[resource-progress] phase={name} event=count-unavailable "
                f"type={type(exc).__name__} error={exc}",
                file=sys.stderr,
                flush=True,
            )
            # Progress reporting is diagnostic-only. If archive discovery cannot
            # be counted safely, disable this phase's tracking and let the
            # wrapped operation execute with its original error semantics.
            self._phase = None
            try:
                yield
            finally:
                self._phase = previous
            return

        state = _PhaseState(name=name, total=total)
        self._phase = state
        print(
            f"[resource-progress] phase={name} event=start archives_total={total}",
            flush=True,
        )
        try:
            yield
        finally:
            processed = state.done + state.failed
            print(
                f"[resource-progress] phase={name} event=complete "
                f"processed={processed}/{state.total} done={state.done} "
                f"failed={state.failed}",
                flush=True,
            )
            self._phase = previous

    def archive_open(self, raw_path: str | Path) -> _ArchiveToken | None:
        state = self._phase
        if state is None:
            return None
        path = Path(raw_path).resolve()
        if path in state.seen:
            return None
        state.seen.add(path)
        ordinal = len(state.seen)
        token = _ArchiveToken(state=state, ordinal=ordinal, path=path)
        percent = (ordinal - 1) * 100.0 / state.total if state.total else 100.0
        print(
            f"[resource-progress] phase={state.name} archive={ordinal}/{state.total} "
            f"status=open done={state.done}/{state.total} percent={percent:.1f} "
            f"name={path.name}",
            flush=True,
        )
        return token

    def archive_header(self, token: _ArchiveToken | None, entry_total: int) -> None:
        if token is None:
            return
        token.entry_total = max(0, int(entry_total))
        print(
            f"[resource-progress] phase={token.state.name} "
            f"archive={token.ordinal}/{token.state.total} status=header "
            f"entries={token.entry_total} name={token.path.name}",
            flush=True,
        )

    def entry(self, token: _ArchiveToken | None, index: int) -> None:
        if token is None or token.entry_total <= 0:
            return
        index = int(index)
        if index <= token.entry_highwater:
            return
        should_report = (
            index == 1
            or index == token.entry_total
            or index % self.entry_interval == 0
        )
        if not should_report:
            return
        token.entry_highwater = index
        percent = index * 100.0 / token.entry_total
        print(
            f"[resource-progress] phase={token.state.name} "
            f"archive={token.ordinal}/{token.state.total} "
            f"entry={index}/{token.entry_total} entry_percent={percent:.1f} "
            f"name={token.path.name}",
            flush=True,
        )

    def archive_failed(self, token: _ArchiveToken | None, error: str) -> None:
        if token is None or token.closed:
            return
        token.closed = True
        token.state.failed += 1
        processed = token.state.done + token.state.failed
        percent = processed * 100.0 / token.state.total if token.state.total else 100.0
        print(
            f"[resource-progress] phase={token.state.name} "
            f"archive={token.ordinal}/{token.state.total} status=failed "
            f"processed={processed}/{token.state.total} percent={percent:.1f} "
            f"name={token.path.name} error={error}",
            flush=True,
        )

    def archive_done(self, token: _ArchiveToken | None) -> None:
        if token is None or token.closed:
            return
        token.closed = True
        token.state.done += 1
        processed = token.state.done + token.state.failed
        percent = processed * 100.0 / token.state.total if token.state.total else 100.0
        print(
            f"[resource-progress] phase={token.state.name} "
            f"archive={token.ordinal}/{token.state.total} status=done "
            f"done={token.state.done}/{token.state.total} "
            f"processed={processed}/{token.state.total} percent={percent:.1f} "
            f"name={token.path.name}",
            flush=True,
        )


class _ProgressEntries:
    def __init__(
        self,
        entries: Any,
        tracker: _ProgressTracker,
        token: _ArchiveToken | None,
    ) -> None:
        self._entries = entries
        self._tracker = tracker
        self._token = token

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: Any) -> Any:
        return self._entries[index]

    def __iter__(self):
        for index, entry in enumerate(self._entries, 1):
            self._tracker.entry(self._token, index)
            yield entry


def _progress_bff_type(original_bff: type, tracker: _ProgressTracker) -> type:
    class ProgressBFF:
        def __init__(self, path: str | os.PathLike[str], *args: Any, **kwargs: Any):
            self.path = Path(path)
            self._token = tracker.archive_open(self.path)
            try:
                self._inner = original_bff(path, *args, **kwargs)
            except Exception as exc:
                tracker.archive_failed(self._token, type(exc).__name__)
                raise
            tracker.archive_header(self._token, len(self._inner.entries))

        @property
        def entries(self) -> _ProgressEntries:
            return _ProgressEntries(self._inner.entries, tracker, self._token)

        def __enter__(self):
            try:
                self._inner.__enter__()
            except Exception as exc:
                tracker.archive_failed(self._token, type(exc).__name__)
                raise
            return self

        def __exit__(self, exc_type, exc, tb):
            try:
                result = self._inner.__exit__(exc_type, exc, tb)
            except Exception as inner_exc:
                tracker.archive_failed(self._token, type(inner_exc).__name__)
                raise
            if exc_type is None:
                tracker.archive_done(self._token)
            else:
                tracker.archive_failed(self._token, exc_type.__name__)
            return result

        def close(self):
            try:
                result = self._inner.close()
            except Exception as exc:
                tracker.archive_failed(self._token, type(exc).__name__)
                raise
            tracker.archive_done(self._token)
            return result

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

    ProgressBFF.__name__ = f"Progress{original_bff.__name__}"
    ProgressBFF.__qualname__ = ProgressBFF.__name__
    return ProgressBFF


_TRACKER = _ProgressTracker()


def _install_progress_hooks() -> None:
    _install_repo_paths()
    import offline_resource_pipeline as resource_pipeline
    import offline_runtime_bootstrap as runtime_bootstrap
    import shift_importer

    if getattr(runtime_bootstrap, "_shift_resource_progress_installed", False):
        return

    progress_bff = _progress_bff_type(shift_importer.BFF, _TRACKER)
    shift_importer.BFF = progress_bff
    resource_pipeline.BFF = progress_bff

    original_pipeline = runtime_bootstrap.run_offline_pipeline
    original_scene_ir = runtime_bootstrap.build_scene_ir

    def run_offline_pipeline_with_progress(
        inputs: Sequence[str | Path],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        with _TRACKER.phase("resource-catalog", inputs):
            return original_pipeline(inputs, *args, **kwargs)

    def build_scene_ir_with_progress(
        inputs: Sequence[str | Path],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        with _TRACKER.phase("scene-ir", inputs):
            return original_scene_ir(inputs, *args, **kwargs)

    runtime_bootstrap.run_offline_pipeline = run_offline_pipeline_with_progress
    runtime_bootstrap.build_scene_ir = build_scene_ir_with_progress
    runtime_bootstrap._shift_resource_progress_installed = True
    print(
        f"[resource-progress] event=hooks-installed "
        f"entry_interval={ENTRY_PROGRESS_INTERVAL}",
        flush=True,
    )


if os.environ.get("SHIFT_RESOURCE_PROGRESS", "").strip().lower() in {
    "1", "true", "yes", "on"
}:
    try:
        _install_progress_hooks()
    except Exception as exc:  # diagnostics must never weaken/block the bootstrap
        print(
            f"[resource-progress] event=hook-error type={type(exc).__name__} "
            f"error={exc}",
            file=sys.stderr,
            flush=True,
        )
