#!/usr/bin/env python3
"""Regression checks for the GDB GPU-dispatch to guest-worker correlation."""

from __future__ import annotations

import ast
from pathlib import Path


TRACE = Path(__file__).with_name(
    "trace_linux_post_bink_worker_route_v45_ordered_route_20261027.gdb"
)


class FakeGdb:
    def __init__(self) -> None:
        self.symbol_present = False
        self.value = 0
        self.error: Exception | None = None
        self.expressions: list[str] = []
        self.scheduler_changes: list[str] = []

    def parameter(self, name: str):
        assert name == "scheduler-locking"
        return "replay"

    def execute(self, command: str):
        self.scheduler_changes.append(command)

    def parse_and_eval(self, expression: str):
        if self.error:
            raise self.error
        self.expressions.append(expression)
        if not self.symbol_present:
            raise RuntimeError("unknown dynamic symbol")
        return self.value


def python_blocks(source: str) -> list[str]:
    lines = source.splitlines()
    blocks: list[str] = []
    active = False
    current: list[str] = []
    for line in lines:
        if line == "python":
            active = True
            current = []
        elif line == "end" and active:
            blocks.append("\n".join(current))
            active = False
        elif active:
            current.append(line)
    return blocks


def main() -> None:
    source = TRACE.read_text()
    blocks = python_blocks(source)
    assert len(blocks) == 2, "expected setup and finalizer GDB Python blocks"
    module = ast.parse(blocks[0])
    helper_names = {
        "gpu_dispatch_id_call_expression",
        "sample_gpu_dispatch_id",
        "active_source1_gpu_dispatch_id",
        "gpu_dispatch_event_fields",
        "remember_queue_dispatch_id",
        "take_queue_dispatch_id",
    }
    helpers = [
        node for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in helper_names
    ]
    assert {node.name for node in helpers} == helper_names

    fake_gdb = FakeGdb()
    state = {
        "gpu_dispatch_id_symbol_available": None,
        "gpu_dispatch_id_sample_calls": 0,
        "gpu_dispatch_id_sample_errors": 0,
        "gpu_dispatch_id_warning_emitted": False,
        "active_source1_callbacks": {},
        "active_dequeues": {},
        "active_producers": {},
        "queue_record_dispatch_ids": {},
        "queue_dispatch_id_links": 0,
        "queue_dispatch_id_evictions": 0,
    }
    namespace = {"state": state, "gdb": fake_gdb, "thread_id": lambda: 7}
    exec(compile(ast.fix_missing_locations(ast.Module(body=helpers, type_ignores=[])),
                 str(TRACE), "exec"), namespace)

    sample = namespace["sample_gpu_dispatch_id"]
    assert sample() is None
    assert state["gpu_dispatch_id_symbol_available"] is False
    assert fake_gdb.expressions[-1] == "((unsigned long long (*)()) shift_native_gpu_trace_dispatch_id_v1)()"
    assert fake_gdb.scheduler_changes == [
        "set scheduler-locking on", "set scheduler-locking replay",
    ]
    assert sample() is None
    assert len(fake_gdb.expressions) == 1
    assert len(fake_gdb.scheduler_changes) == 2
    state["gpu_dispatch_id_symbol_available"] = None
    fake_gdb.symbol_present = True
    fake_gdb.value = 0x1234
    assert sample() == 0x1234
    fake_gdb.value = 0
    assert sample() is None
    fake_gdb.error = RuntimeError("temporary inferior-call failure")
    assert sample() is None
    assert state["gpu_dispatch_id_sample_calls"] == 5
    assert state["gpu_dispatch_id_sample_errors"] == 2
    assert len(fake_gdb.scheduler_changes) == 8
    assert fake_gdb.scheduler_changes[-1] == "set scheduler-locking replay"

    state["active_source1_callbacks"][7] = [{"gpu_dispatch_id": 0x55}]
    assert namespace["active_source1_gpu_dispatch_id"]() == 0x55
    assert namespace["active_source1_gpu_dispatch_id"](8) is None
    state["active_dequeues"][7] = [{"parent_gpu_dispatch_id": 0x66}]
    state["active_producers"][7] = [{"parent_gpu_dispatch_id": 0x77}]
    assert namespace["gpu_dispatch_event_fields"]() == {
        "gpu_dispatch_id": 0x55, "parent_gpu_dispatch_id": 0x66,
    }
    state["active_dequeues"].pop(7)
    assert namespace["gpu_dispatch_event_fields"]() == {
        "gpu_dispatch_id": 0x55, "parent_gpu_dispatch_id": 0x77,
    }
    state["active_producers"].pop(7)
    assert namespace["gpu_dispatch_event_fields"]() == {
        "gpu_dispatch_id": 0x55, "parent_gpu_dispatch_id": 0x55,
    }

    remember = namespace["remember_queue_dispatch_id"]
    take = namespace["take_queue_dispatch_id"]
    assert not remember(0x100, 0, 0x200, None)
    assert remember(0x100, 3, 0x200, 0x55)
    assert take(0x100, 3, 0x200) == 0x55
    assert take(0x100, 3, 0x200) is None
    for index in range(16385):
        assert remember(0x300, index, index + 1, index + 1)
    assert len(state["queue_record_dispatch_ids"]) == 16384
    assert state["queue_dispatch_id_evictions"] == 1
    assert take(0x300, 0, 1) is None
    assert state["queue_dispatch_id_links"] == 16386

    classes = {node.name: node for node in module.body if isinstance(node, ast.ClassDef)}
    for class_name in (
        "Source1Callback", "CallbackEnqueue", "QueueDequeue",
        "WorkerCompletion", "KernelEventCall",
    ):
        assert class_name in classes
        class_text = ast.get_source_segment(blocks[0], classes[class_name]) or ""
        assert "gpu_dispatch_id" in class_text, class_name
    for class_name in ("CounterWrite", "QueueFieldWrite"):
        assert class_name in classes
        class_text = ast.get_source_segment(blocks[0], classes[class_name]) or ""
        assert "gpu_dispatch_event_fields(thread)" in class_text, class_name
    assert "parent_gpu_dispatch_id" in (
        ast.get_source_segment(blocks[0], classes["QueueDequeue"]) or ""
    )
    print("GPU dispatch IDs correlate source-1 callbacks through bounded queue records")


if __name__ == "__main__":
    main()
