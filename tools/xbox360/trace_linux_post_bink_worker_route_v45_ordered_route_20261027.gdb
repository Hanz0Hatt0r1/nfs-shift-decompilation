set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set debuginfod enabled off
handle SIGSEGV nostop noprint pass

python
import hashlib
import json
import os
import signal
import shlex
import time
from pathlib import Path

import gdb

out = Path(os.environ.get(
    "SHIFT_QUEUE_TRACE_OUT",
    "/dev/shm/nfs-shift-p1-post-bink-worker-route-v45-ordered-route-20261027",
))
out.mkdir(parents=True, exist_ok=True)
gdb.execute(f"set logging file {out / 'gdb.log'}")
gdb.execute("set logging overwrite on")
gdb.execute("set logging enabled on")
gdb.execute(f"set environment LD_LIBRARY_PATH {out / 'bin'}")
gdb.execute("set environment SDL_GAMECONTROLLER_IGNORE_DEVICES 0x045e/0x0b12")
gpu_plugin_name = os.environ.get("SHIFT_QUEUE_TRACE_GPU_PLUGIN_NAME", "shift-native")
trace_event_write_shd = os.environ.get("SHIFT_QUEUE_TRACE_EVENT_WRITE_SHD", "0") == "1"
game_data_root = os.environ.get(
    "SHIFT_QUEUE_TRACE_GAME_DATA_ROOT",
    "/home/pes/work/process2-retail-isolated-irq-20261023/game-data",
)
user_data_root = out / "user"
cache_root = out / "cache"
gdb.execute(
    "set environment SHIFT_NATIVE_VULKAN_TRACE_RING "
    + ("1" if gpu_plugin_name == "shift-native" else "0")
)
gdb.execute(
    "set args "
    + " ".join(shlex.quote(str(value)) for value in (
        f"--game_data_root={game_data_root}",
        f"--user_data_root={user_data_root}",
        f"--cache_root={cache_root}",
        f"--gpu_plugin={gpu_plugin_name}",
        "--no-async_shader_compilation",
        "--fullscreen=false",
    ))
)

started = time.monotonic()
wall_started_ms = int(time.time() * 1000)
state = {
    "bink_target": None,
    "bink_target_polls": 0,
    "bink_target_last": None,
    "bink_target_max_progress": 0,
    "bink_target_samples": [],
    "event_write_shd_packet_events": [],
    "manager": None,
    "worker_queues": set(),
    "enqueue_events": [],
    "dequeue_events": [],
    "completion_events": [],
    "producer_events": [],
    "producer_call_events": [],
    "submission_route_events": [],
    "source1_callback_events": [],
    "source1_callback_ordinal": 0,
    "event_call_events": [],
    "counter_write_events": [],
    "worker72_write_events": [],
    "controller_update_events": [],
    "controller_return_events": [],
    "host_input_events": [],
    "xam_input_events": [],
    "xam_input_return_events": [],
    "bink_complete_events": [],
    "input_gate_events": [],
    "scene_function_events": [],
    "scene_function_return_events": [],
    "scene_state_events": [],
    "retail_queue_wait_events": [],
    "retail_queue_wait_return_events": [],
    "queue_field_write_events": [],
    "ke_wait_calls": 0,
    "ke_wait_return_events": [],
    "producer_calls": 0,
    "next_id": 0,
    "trace_sequence": 0,
    "active_dequeues": {},
    "active_producers": {},
    "active_source1_callbacks": {},
    "queue_record_dispatch_ids": {},
    "gpu_dispatch_id_symbol_available": None,
    "gpu_dispatch_id_sample_calls": 0,
    "gpu_dispatch_id_sample_errors": 0,
    "gpu_dispatch_id_warning_emitted": False,
    "queue_dispatch_id_links": 0,
    "queue_dispatch_id_evictions": 0,
    "finishers": [],
    "mapped_hashes": {},
    "guest_base": None,
    "event_breakpoints_installed": False,
    "worker72_watch": None,
    "queue_field_watches": [],
    "queue_field_watches_armed": False,
    "last_dequeue_by_thread": {},
    "last_host_button_mask": None,
    "input_trace_until": 0.0,
    "input_gate_emitted": False,
    "post_bink_scene_cleared": False,
    "host_input_breakpoints_installed": False,
    "xam_input_calls": 0,
    "controller_update_call_counts": {},
    "last_controller_update_state": {},
}


def read_le(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), "little")


def read_be(base, address, size=4):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(base + address, size)), "big")


def read_be_host(address, size=4):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), "big")


def context_base():
    return int(gdb.parse_and_eval("$rdi")), int(gdb.parse_and_eval("$rsi"))


def ppc_reg(context, index):
    offset = {0: 8, 1: 16, 2: 24, 3: 0}.get(index, index * 8)
    return read_le(context + offset, 4)


def thread_id():
    thread = gdb.selected_thread()
    return thread.global_num if thread else -1


def thread_name():
    thread = gdb.selected_thread()
    return thread.name if thread else "?"


def gpu_dispatch_id_call_expression():
    return "((unsigned long long (*)()) shift_native_gpu_trace_dispatch_id_v1)()"


def sample_gpu_dispatch_id():
    state["gpu_dispatch_id_sample_calls"] += 1
    if state["gpu_dispatch_id_symbol_available"] is False:
        return None
    try:
        expression = gpu_dispatch_id_call_expression()
        if expression is None:
            state["gpu_dispatch_id_symbol_available"] = False
            if not state["gpu_dispatch_id_warning_emitted"]:
                print("WORKER_RING_GPU_DISPATCH_ID_UNAVAILABLE "
                      "shift_native_gpu_trace_dispatch_id_v1 not resolved")
                state["gpu_dispatch_id_warning_emitted"] = True
            return None
        scheduler_locking = gdb.parameter("scheduler-locking")
        gdb.execute("set scheduler-locking on")
        try:
            dispatch_id = int(gdb.parse_and_eval(expression)) & 0xFFFFFFFFFFFFFFFF
        finally:
            gdb.execute(f"set scheduler-locking {scheduler_locking}")
        state["gpu_dispatch_id_symbol_available"] = True
        return dispatch_id if dispatch_id else None
    except Exception as exc:
        state["gpu_dispatch_id_symbol_available"] = False
        state["gpu_dispatch_id_sample_errors"] += 1
        if not state["gpu_dispatch_id_warning_emitted"]:
            print(f"WORKER_RING_GPU_DISPATCH_ID_ERROR {exc}")
            state["gpu_dispatch_id_warning_emitted"] = True
        return None


def active_source1_gpu_dispatch_id(thread=None):
    if thread is None:
        thread = thread_id()
    stack = state["active_source1_callbacks"].get(thread, [])
    return stack[-1].get("gpu_dispatch_id") if stack else None


def gpu_dispatch_event_fields(thread=None):
    if thread is None:
        thread = thread_id()
    active_dequeues = state["active_dequeues"].get(thread, [])
    active_producers = state["active_producers"].get(thread, [])
    parent_dispatch_id = next((dispatch_id for dispatch_id in (
        active_dequeues[-1].get("parent_gpu_dispatch_id") if active_dequeues else None,
        active_producers[-1].get("parent_gpu_dispatch_id") if active_producers else None,
        active_source1_gpu_dispatch_id(thread),
    ) if dispatch_id is not None), None)
    return {
        "gpu_dispatch_id": active_source1_gpu_dispatch_id(thread),
        "parent_gpu_dispatch_id": parent_dispatch_id,
    }


def remember_queue_dispatch_id(queue, producer_index, record, dispatch_id):
    if not isinstance(dispatch_id, int) or dispatch_id <= 0:
        return False
    key = (queue, producer_index, record)
    records = state["queue_record_dispatch_ids"]
    records.pop(key, None)
    records[key] = dispatch_id
    state["queue_dispatch_id_links"] += 1
    while len(records) > 16384:
        del records[next(iter(records))]
        state["queue_dispatch_id_evictions"] += 1
    return True


def take_queue_dispatch_id(queue, consumer_index, record):
    return state["queue_record_dispatch_ids"].pop(
        (queue, consumer_index, record), None,
    )


def next_id():
    state["next_id"] += 1
    return state["next_id"]


def emit(kind, fields):
    state["trace_sequence"] += 1
    record = {
        "kind": kind,
        "trace_sequence": state["trace_sequence"],
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "wall_clock_epoch_ms": int(time.time() * 1000),
    }
    record.update(fields)
    print("WORKER_RING " + json.dumps(record, sort_keys=True))
    if sum(len(state[key]) for key in (
        "enqueue_events", "dequeue_events", "completion_events",
        "producer_events", "producer_call_events", "submission_route_events",
        "source1_callback_events", "event_call_events", "counter_write_events",
        "worker72_write_events", "controller_update_events", "controller_return_events",
        "host_input_events", "xam_input_events", "xam_input_return_events",
        "bink_complete_events", "input_gate_events",
        "scene_function_events", "scene_function_return_events", "scene_state_events",
        "retail_queue_wait_events", "retail_queue_wait_return_events",
        "queue_field_write_events",
        "ke_wait_return_events",
    )) < 12000:
        state[kind + "_events"].append(record)
    return record


def keep_finisher(finisher):
    state["finishers"].append(finisher)
    return finisher


def release_finisher(finisher):
    try:
        state["finishers"].remove(finisher)
    except ValueError:
        pass


def queue_snapshot(base, queue):
    head = read_be(base, queue + 56)
    tail = read_be(base, queue + 60)
    slots = [read_be(base, queue + 64 + index * 4) for index in range(4)]
    return {"queue": queue, "producer": head, "consumer": tail, "slots": slots}


def mapped_hashes():
    pid = gdb.selected_inferior().pid
    if not pid:
        return
    for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
        parts = line.split(None, 5)
        if len(parts) != 6 or parts[2] != "00000000":
            continue
        path = parts[5]
        if not path.endswith(("/librexruntime.so", f"/librexgpu-{gpu_plugin_name}.so")):
            continue
        try:
            digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        except OSError:
            continue
        state["mapped_hashes"][path] = digest
        print(f"WORKER_RING_MAPPED path={path} sha256={digest}")


def install_event_breakpoints():
    if state["event_breakpoints_installed"]:
        return
    pid = gdb.selected_inferior().pid
    bias = None
    for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
        parts = line.split(None, 5)
        if len(parts) == 6 and parts[2] == "00000000" and parts[5].endswith("/librexruntime.so"):
            bias = int(parts[0].split("-", 1)[0], 16)
            break
    if bias is None:
        print("WORKER_RING_EVENT_MAP_ERROR librexruntime.so not mapped")
        return
    offsets = {
        "KeSetEvent": 0x5D2F30,
        "KeResetEvent": 0x5D2F90,
        "KeWaitForSingleObject": 0x5D3260,
    }
    for symbol, offset in offsets.items():
        KernelEventCall(symbol, bias + offset)
    state["event_breakpoints_installed"] = True
    print(f"WORKER_RING_EVENT_BREAKPOINTS bias={bias:#x} offsets={offsets}")


class BinkTarget(gdb.Breakpoint):
    def __init__(self):
        super().__init__("sub_82679510", internal=True)

    def stop(self):
        try:
            context, base = context_base()
            wrapper = read_le(context, 4)
            movie = read_be(base, wrapper + 4) if wrapper else 0
            target = read_be(base, movie + 8) if movie else 0
            progress = read_be(base, movie + 12) if movie else 0
            poll = {
                "movie": movie,
                "target": target,
                "progress": progress,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
            state["bink_target_polls"] += 1
            state["bink_target_last"] = poll
            state["bink_target_max_progress"] = max(
                state["bink_target_max_progress"], progress,
            )
            if len(state["bink_target_samples"]) < 8:
                state["bink_target_samples"].append(poll)
            if target == 281 and progress >= 281 and state["bink_target"] is None:
                state["bink_target"] = {
                    "progress": progress,
                    "target": target,
                    "movie": movie,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                }
                emit("bink_complete", dict(state["bink_target"]))
                print("WORKER_RING_BINK " + json.dumps(state["bink_target"], sort_keys=True))
                mapped_hashes()
                install_event_breakpoints()
                if os.environ.get("SHIFT_QUEUE_TRACE_INPUT_REPLAY") == "1":
                    install_input_breakpoints()
        except gdb.error as exc:
            print(f"WORKER_RING_BINK_ERROR {exc}")
        return False


TARGET_CONTROLLER_OBJECT = 0xBCAEB260


class HostInputReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, user, state_ptr):
        super().__init__(frame, internal=True)
        self.user = user
        self.state_ptr = state_ptr

    def stop(self):
        try:
            status = int(gdb.parse_and_eval("$eax")) & 0xFFFFFFFF
            raw = bytes(gdb.selected_inferior().read_memory(self.state_ptr, 16))
            packet = int.from_bytes(raw[0:4], "big")
            buttons = int.from_bytes(raw[4:6], "big")
            if buttons != state["last_host_button_mask"]:
                state["last_host_button_mask"] = buttons
                # Keep tracing XAM state returns briefly after each host input
                # transition. The frontend gate may never be reached, but the
                # trace still needs to show whether a replayed button reached
                # the guest input API.
                state["input_trace_until"] = time.monotonic() + 6.0
                emit("host_input", {
                    "user": self.user,
                    "status": status,
                    "packet": packet,
                    "buttons": buttons,
                    "buttons_hex": f"0x{buttons:04X}",
                    "raw_state": raw.hex(),
                })
        except gdb.error as exc:
            print(f"WORKER_RING_HOST_INPUT_RETURN_ERROR {exc}")
        return False


class InputSystemGetState(gdb.Breakpoint):
    def __init__(self, spec):
        super().__init__(spec, internal=True)

    def stop(self):
        try:
            user = int(gdb.parse_and_eval("$rsi")) & 0xFFFFFFFF
            state_ptr = int(gdb.parse_and_eval("$rdx"))
            if user == 0 and state_ptr:
                HostInputReturn(gdb.newest_frame(), user, state_ptr)
        except gdb.error as exc:
            print(f"WORKER_RING_HOST_INPUT_CALL_ERROR {exc}")
        return False


class XamInputEntry(gdb.Breakpoint):
    def __init__(self, spec):
        super().__init__(spec, internal=True)

    def stop(self):
        try:
            user = int(gdb.parse_and_eval("$rdi")) & 0xFFFFFFFF
            flags = int(gdb.parse_and_eval("$rsi")) & 0xFFFFFFFF
            state_ptr = int(gdb.parse_and_eval("$rdx"))
            state["xam_input_calls"] += 1
            if state_ptr:
                XamInputReturn(gdb.newest_frame(), state["xam_input_calls"], user, flags, state_ptr)
            if (state["xam_input_calls"] <= 8 or state["input_gate_emitted"]
                    or time.monotonic() <= state["input_trace_until"]):
                guest_state_ptr = state_ptr
                if state["guest_base"] and state_ptr >= state["guest_base"]:
                    guest_state_ptr = (state_ptr - state["guest_base"]) & 0xFFFFFFFF
                emit("xam_input", {
                    "call": state["xam_input_calls"],
                    "user": user,
                    "flags": flags,
                    "state_guest_address": guest_state_ptr,
                    "after_input_gate": state["input_gate_emitted"],
                })
        except Exception as exc:
            print(f"WORKER_RING_XAM_INPUT_ERROR {exc}")
        return False


class XamInputReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, call, user, flags, state_ptr):
        super().__init__(frame, internal=True)
        self.call = call
        self.user = user
        self.flags = flags
        self.state_ptr = state_ptr

    def stop(self):
        try:
            if (self.call > 8 and not state["input_gate_emitted"]
                    and time.monotonic() > state["input_trace_until"]):
                return False
            base = state["guest_base"]
            status = int(gdb.parse_and_eval("$eax")) & 0xFFFFFFFF
            raw_state = b""
            guest_state_ptr = self.state_ptr
            if base and self.state_ptr:
                host_state_ptr = self.state_ptr
                if self.state_ptr >= base:
                    guest_state_ptr = (self.state_ptr - base) & 0xFFFFFFFF
                else:
                    host_state_ptr = base + self.state_ptr
                raw_state = bytes(gdb.selected_inferior().read_memory(host_state_ptr, 16))
            emit("xam_input_return", {
                "call": self.call,
                "user": self.user,
                "flags": self.flags,
                "status": status,
                "state_guest_address": guest_state_ptr,
                "packet": int.from_bytes(raw_state[0:4], "big") if raw_state else None,
                "buttons": int.from_bytes(raw_state[4:6], "big") if raw_state else None,
                "left_trigger": raw_state[6] if raw_state else None,
                "right_trigger": raw_state[7] if raw_state else None,
                "state_read": bool(raw_state),
            })
        except Exception as exc:
            print(f"WORKER_RING_XAM_INPUT_RETURN_ERROR call={self.call} {exc}")
        return False


class ControllerReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, method, obj, base):
        super().__init__(frame, internal=True)
        self.method = method
        self.obj = obj
        self.base = base

    def stop(self):
        try:
            current = read_be(self.base, self.obj + 128)
            previous = read_be(self.base, self.obj + 132)
            edge_bytes = bytes(
                gdb.selected_inferior().read_memory(self.base + self.obj + 140, 25)
            )
            edge_key = (self.method, current, previous, edge_bytes)
            if edge_key != state.get("last_controller_return_state"):
                state["last_controller_return_state"] = edge_key
                emit("controller_return", {
                    "method": self.method,
                    "object": self.obj,
                    "current": current,
                    "previous": previous,
                    "edge": current ^ previous,
                    "edge_bytes": edge_bytes.hex(),
                })
        except gdb.error as exc:
            print(f"WORKER_RING_CONTROLLER_RETURN_ERROR {exc}")
        return False


class ControllerMethod(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        self.calls = 0
        super().__init__(symbol, internal=True)

    def stop(self):
        try:
            context, base = context_base()
            state["guest_base"] = base
            obj = ppc_reg(context, 3)
            if obj != TARGET_CONTROLLER_OBJECT:
                return False
            self.calls += 1
            state["controller_update_call_counts"][self.symbol] = (
                state["controller_update_call_counts"].get(self.symbol, 0) + 1
            )
            current = read_be(base, obj + 128)
            previous = read_be(base, obj + 132)
            state_key = (current, previous)
            if state_key != state["last_controller_update_state"].get(self.symbol):
                state["last_controller_update_state"][self.symbol] = state_key
                emit("controller_update", {
                    "method": self.symbol,
                    "object": obj,
                    "current": current,
                    "previous": previous,
                    "edge": current ^ previous,
                })
            if (state["bink_target"] is not None and self.symbol == "sub_82308E60"
                    and self.calls % 4 == 1):
                ControllerReturn(gdb.newest_frame(), self.symbol, obj, base)
        except gdb.error as exc:
            print(f"WORKER_RING_CONTROLLER_UPDATE_ERROR method={self.symbol} {exc}")
        return False


SCENE_MANAGER_OBJECT = 0x831E6184


def scene_manager_snapshot(base):
    return {
        "object": SCENE_MANAGER_OBJECT,
        "list_count_36": read_be(base, SCENE_MANAGER_OBJECT + 36),
        "state_348": read_be(base, SCENE_MANAGER_OBJECT + 348),
        "update_count_356": read_be(base, SCENE_MANAGER_OBJECT + 356),
        "child_words_264": [
            read_be(base, SCENE_MANAGER_OBJECT + offset)
            for offset in (264, 268, 272, 276)
        ],
    }


def maybe_emit_input_gate(method, snapshot):
    if state["bink_target"] is None:
        return
    if snapshot["state_348"] == 0:
        state["post_bink_scene_cleared"] = True
    if (state["post_bink_scene_cleared"]
            and snapshot["state_348"] == 1
            and snapshot["update_count_356"] >= 1
            and all(snapshot["child_words_264"])
            and not state["input_gate_emitted"]):
        state["input_gate_emitted"] = True
        emit("input_gate", {
            "method": method,
            "gate": "scene manager updated after post-Bink clear with populated children",
            "state_348": snapshot["state_348"],
            "update_count_356": snapshot["update_count_356"],
            "child_words_264": snapshot["child_words_264"],
        })
        print(
            "GPU_COMPARE_INPUT_GATE elapsed=%.3f method=%s state=%d updates=%d"
            % (time.monotonic() - started, method,
               snapshot["state_348"], snapshot["update_count_356"]),
            flush=True,
        )


class RetailQueueWait(gdb.Breakpoint):
    def __init__(self):
        self.calls = 0
        self.last_condition = None
        super().__init__("sub_823B34A0", internal=True)

    def stop(self):
        if state["bink_target"] is None:
            return False
        try:
            context, base = context_base()
            manager = ppc_reg(context, 3)
            head_pointer = read_be(base, manager + 0x2A90)
            snapshot = {
                "thread": thread_id(),
                "thread_name": thread_name(),
                "arguments_r3_r6": [ppc_reg(context, index) for index in range(3, 7)],
                "wait_target_r30": ppc_reg(context, 30),
                "manager": manager,
                "head_pointer": head_pointer,
                "head": read_be(base, head_pointer) if head_pointer else None,
                "tail": read_be(base, manager + 0x2A9C),
                "predicate_byte": read_be(base, manager + 0x2ABD, 1),
            }
            snapshot["completion_mask_set"] = bool(snapshot["predicate_byte"] & 0x02)
            condition = tuple(snapshot[key] for key in (
                "manager", "head_pointer", "head", "tail", "predicate_byte",
            ))
            self.calls += 1
            is_main_thread = snapshot["thread_name"].startswith("Core 0/0: Main")
            if (is_main_thread or self.calls <= 8 or condition != self.last_condition
                    or self.calls % 100 == 0):
                entry = emit("retail_queue_wait", {"call": self.calls, **snapshot})
                self.last_condition = condition
                if is_main_thread:
                    queue_depth = (snapshot["tail"] - snapshot["head"]) & 0xFFFFFFFF
                    alias_probe = os.environ.get("SHIFT_QUEUE_TRACE_QUEUE_FIELD_ALIAS_PROBE", "")
                    should_arm_queue_watches = (
                        alias_probe in ("software_head", "physical_head_counter")
                        or (32 <= queue_depth <= 64 and not snapshot["completion_mask_set"])
                    )
                    if not state["queue_field_watches_armed"] and should_arm_queue_watches:
                        arm_queue_field_watches(
                            base, manager, head_pointer, self.calls,
                        )
                    keep_finisher(RetailQueueWaitReturn(
                        gdb.newest_frame(), context, base, entry,
                    ))
        except gdb.error as exc:
            print(f"WORKER_RING_QUEUE_WAIT_ERROR {exc}")
        return False


class RetailQueueWaitReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, entry):
        super().__init__(frame, internal=True)
        self.context, self.base, self.entry = context, base, entry

    def stop(self):
        try:
            manager = self.entry["manager"]
            head_pointer = self.entry["head_pointer"]
            emit("retail_queue_wait_return", {
                "call": self.entry["call"],
                "thread": self.entry["thread"],
                "thread_name": self.entry["thread_name"],
                "manager": manager,
                "head_pointer": head_pointer,
                "head_at_return": read_be(self.base, head_pointer) if head_pointer else None,
                "tail_at_return": read_be(self.base, manager + 0x2A9C),
                "predicate_byte_at_return": read_be(self.base, manager + 0x2ABD, 1),
                "return_r3": ppc_reg(self.context, 3),
                "entry_elapsed_seconds": self.entry["elapsed_seconds"],
                "duration_seconds": round(time.monotonic() - started - self.entry["elapsed_seconds"], 3),
            })
        except gdb.error as exc:
            print(f"WORKER_RING_QUEUE_WAIT_RETURN_ERROR call={self.entry.get('call')} {exc}")
        release_finisher(self)
        return False


class QueueFieldWrite(gdb.Breakpoint):
    def __init__(self, base, label, guest_address, size, initial_value,
                 host_address=None, alias_name="guest_base"):
        self.base = base
        self.label = label
        self.guest_address = guest_address
        self.size = size
        self.previous = initial_value
        self.host_address = host_address if host_address is not None else base + guest_address
        self.alias_name = alias_name
        ctype = "unsigned char" if size == 1 else "unsigned int"
        super().__init__("*(%s*)%#x" % (ctype, self.host_address),
                         type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE,
                         internal=True)

    def stop(self):
        try:
            after = read_be_host(self.host_address, self.size)
            host_pc = int(gdb.parse_and_eval("$pc"))
            host_symbol = gdb.execute("info symbol $pc", to_string=True).strip()
            stack = gdb.execute("bt 8", to_string=True).splitlines()[:8]
            import re
            guest_function = None
            for candidate in (host_symbol, *stack):
                match = re.search(r"sub_([0-9A-Fa-f]{8})", candidate)
                if match:
                    guest_function = "0x" + match.group(1).upper()
                    break
            thread = thread_id()
            active_dequeues = state["active_dequeues"].get(thread, [])
            active_producers = state["active_producers"].get(thread, [])
            emit("queue_field_write", {
                "field": self.label,
                "guest_address": self.guest_address,
                "host_address": self.host_address,
                "memory_alias": self.alias_name,
                "size": self.size,
                "before": self.previous,
                "after": after,
                **gpu_dispatch_event_fields(thread),
                "parent_dequeue_id": active_dequeues[-1].get("id") if active_dequeues else None,
                "parent_record": active_dequeues[-1].get("slot_value") if active_dequeues else None,
                "parent_producer_id": active_producers[-1].get("id") if active_producers else None,
                "thread": thread,
                "thread_name": thread_name(),
                "host_pc": host_pc,
                "host_symbol": host_symbol,
                "guest_function_candidate": guest_function,
                "host_stack": stack,
            })
            self.previous = after
        except (gdb.error, OSError, OverflowError) as exc:
            print("WORKER_RING_QUEUE_FIELD_WRITE_ERROR field=%s error=%r" %
                  (self.label, exc))
        return False


class EventWriteShdPacket(gdb.Breakpoint):
    def __init__(self):
        self.calls = 0
        super().__init__("shift::xbox::decode_guest_event_write_shd", internal=True)

    def stop(self):
        try:
            packet_pointer = int(gdb.parse_and_eval("$rdi"))
            packet_length = int(gdb.parse_and_eval("$rsi"))
            if packet_length != 16:
                return False
            raw = bytes(gdb.selected_inferior().read_memory(packet_pointer, 16))
            words = [int.from_bytes(raw[offset:offset + 4], "big") for offset in range(0, 16, 4)]
            encoded_address = words[2]
            guest_address = encoded_address & ~3
            if guest_address != 0x17AF4000:
                return False
            if len(state["event_write_shd_packet_events"]) >= 4096:
                return False
            self.calls += 1
            stack_pointer = int(gdb.parse_and_eval("$rsp"))
            return_pc = int.from_bytes(
                bytes(gdb.selected_inferior().read_memory(stack_pointer, 8)), "little",
            )
            try:
                head_before = read_be_host(0x217AF4000)
            except gdb.error:
                head_before = None
            try:
                caller = gdb.execute(
                    "info symbol %#x" % return_pc, to_string=True,
                ).strip()
            except gdb.error:
                caller = None
            record = {
                "index": self.calls - 1,
                "thread": thread_id(),
                "thread_name": thread_name(),
                "packet_pointer": packet_pointer,
                "packet_length": packet_length,
                "packet_bytes": raw.hex(),
                "packet_words": ["0x%08x" % word for word in words],
                "initiator": "0x%08x" % words[1],
                "guest_address": "0x%08x" % guest_address,
                "endian_mode": encoded_address & 3,
                "packet_value": "0x%08x" % words[3],
                "head_before": head_before,
                "caller_return_pc": return_pc,
                "caller": caller,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "wall_clock_epoch_ms": int(time.time() * 1000),
            }
            if len(state["event_write_shd_packet_events"]) < 4096:
                state["event_write_shd_packet_events"].append(record)
            print("WORKER_RING_EVENT_WRITE_SHD " + json.dumps(record, sort_keys=True))
        except (gdb.error, OSError, OverflowError) as exc:
            print("WORKER_RING_EVENT_WRITE_SHD_ERROR %r" % exc)
        return False


def guest_queue_field_aliases(base, guest_address):
    if not 0xA0000000 <= guest_address < 0xC0000000:
        return [("virtual_a", base + guest_address)]
    physical_offset = guest_address - 0xA0000000
    return [
        ("virtual_a", base + guest_address),
        ("physical", base + 0x100000000 + physical_offset),
        ("virtual_c", base + 0xC0000000 + physical_offset),
        ("virtual_e", base + 0xE0000000 + physical_offset),
    ]


def arm_queue_field_watches(base, manager, head_pointer, trigger_call):
    if state["queue_field_watches_armed"]:
        return
    state["queue_field_watches_armed"] = True
    alias_probe = os.environ.get("SHIFT_QUEUE_TRACE_QUEUE_FIELD_ALIAS_PROBE", "")
    if alias_probe in ("software_head", "physical_head_counter"):
        watch_keys = ("counter_watch", "worker72_watch") if alias_probe == "software_head" else ("worker72_watch",)
        for watch_key in watch_keys:
            watch = state.get(watch_key)
            if watch is not None:
                watch.enabled = False
        if alias_probe == "physical_head_counter":
            if state.get("counter_watch") is None:
                counter_address = manager + 11012
                state["counter_watch"] = CounterWrite(base, counter_address)
            state["counter_watch"].enabled = True
        expected = read_be(base, head_pointer)
        aliases = guest_queue_field_aliases(base, head_pointer)
        if alias_probe == "physical_head_counter":
            aliases = [alias for alias in aliases if alias[0] == "physical"]
        for alias_name, host_address in aliases:
            try:
                initial = read_be_host(host_address)
                if initial != expected:
                    print("WORKER_RING_QUEUE_FIELD_ALIAS_MISMATCH alias=%s host=%#x guest_base_value=%#x alias_value=%#x" %
                          (alias_name, host_address, expected, initial))
                    continue
                watch = QueueFieldWrite(
                    base, "software_head", head_pointer, 4, initial,
                    host_address=host_address, alias_name=alias_name,
                )
                state["queue_field_watches"].append(watch)
                print("WORKER_RING_QUEUE_FIELD_ALIAS_WATCH field=software_head alias=%s guest=%#x host=%#x initial=%#x trigger_call=%d" %
                      (alias_name, head_pointer, host_address, initial, trigger_call))
            except gdb.error as exc:
                print("WORKER_RING_QUEUE_FIELD_ALIAS_WATCH_ERROR alias=%s host=%#x error=%r" %
                      (alias_name, host_address, str(exc)))
        return
    # The manager counter watch remains armed; retire the worker+72 watch to
    # leave three x86 hardware slots for the guest queue gates.
    worker_watch = state.get("worker72_watch")
    if worker_watch is not None:
        worker_watch.enabled = False
    for label, address, size in (
        ("software_head", head_pointer, 4),
        ("software_tail", manager + 0x2A9C, 4),
        ("completion_predicate", manager + 0x2ABD, 1),
    ):
        try:
            initial = read_be(base, address, size)
            watch = QueueFieldWrite(base, label, address, size, initial)
            state["queue_field_watches"].append(watch)
            print("WORKER_RING_QUEUE_FIELD_WATCH field=%s guest=%#x size=%d initial=%#x trigger_call=%d" %
                  (label, address, size, initial, trigger_call))
        except gdb.error as exc:
            print("WORKER_RING_QUEUE_FIELD_WATCH_ERROR field=%s guest=%#x error=%r" %
                  (label, address, str(exc)))


class SceneFunction(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        self.calls = 0
        self.last_arguments = None
        self.last_snapshot = None
        super().__init__(symbol, internal=True)

    def stop(self):
        if state["bink_target"] is None:
            return False
        try:
            context, base = context_base()
            state["guest_base"] = base
            args = [ppc_reg(context, index) for index in range(3, 9)]
            self.calls += 1
            capture_return = self.calls <= 16 or (
                self.calls <= 256 and args != self.last_arguments
            )
            if capture_return:
                self.last_arguments = args
                entry = emit("scene_function", {
                    "function": self.symbol,
                    "call": self.calls,
                    "arguments_r3_r8": args,
                })
                keep_finisher(SceneFunctionReturn(
                    gdb.newest_frame(), self.symbol, context, base, entry,
                ))
            if self.symbol == "sub_82DDD1C8":
                snapshot = scene_manager_snapshot(base)
                if snapshot != self.last_snapshot:
                    self.last_snapshot = snapshot
                    emit("scene_state", snapshot)
                maybe_emit_input_gate(self.symbol, snapshot)
        except gdb.error as exc:
            print(f"WORKER_RING_SCENE_ERROR function={self.symbol} {exc}")
        return False


class SceneFunctionReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, symbol, context, base, entry):
        super().__init__(frame, internal=True)
        self.symbol, self.context, self.base, self.entry = symbol, context, base, entry

    def stop(self):
        try:
            args = self.entry["arguments_r3_r8"]
            function_state = None
            if self.symbol == "sub_82F38158" and args[0]:
                function_state = {
                    "frontend_mode_2cc": read_be(self.base, args[0] + 0x2cc),
                    "frontend_ready_2d0": read_be(self.base, args[0] + 0x2d0),
                }
            elif self.symbol == "sub_82F33810" and args[0]:
                function_state = {
                    "state_value_at_param": read_be(self.base, args[0]),
                    "requested_state_r4": args[1],
                }
            elif self.symbol == "sub_82FD5658" and args[0]:
                function_state = {
                    "state_word_plus4": read_be(self.base, args[0] + 4),
                }
            return_value = (
                ppc_reg(self.context, 3)
                if self.symbol == "sub_82FD5658" else None
            )
            self.entry.update({
                "return_value": return_value,
                "return_elapsed_seconds": round(time.monotonic() - started, 3),
                "return_wall_clock_epoch_ms": int(time.time() * 1000),
                "function_state_at_return": function_state,
            })
            manager_snapshot = scene_manager_snapshot(self.base)
            self.entry["scene_manager_at_return"] = manager_snapshot
            if self.symbol == "sub_82DDC6F0":
                maybe_emit_input_gate(self.symbol, manager_snapshot)
            emit("scene_function_return", {
                "function": self.symbol,
                "call": self.entry["call"],
                "elapsed_seconds": self.entry["return_elapsed_seconds"],
                "wall_clock_epoch_ms": self.entry["return_wall_clock_epoch_ms"],
                "arguments_r3_r8": self.entry["arguments_r3_r8"],
                "return_value": return_value,
                "function_state_at_return": function_state,
                "scene_manager_at_return": manager_snapshot,
            })
        except gdb.error as exc:
            print(f"WORKER_RING_SCENE_RETURN_ERROR function={self.symbol} {exc}")
        return False


def install_input_breakpoints():
    if state["host_input_breakpoints_installed"]:
        return
    pid = gdb.selected_inferior().pid
    bias = None
    for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
        parts = line.split(None, 5)
        if len(parts) == 6 and parts[2] == "00000000" and parts[5].endswith("/librexruntime.so"):
            bias = int(parts[0].split("-", 1)[0], 16)
            break
    if bias is None:
        print("WORKER_RING_INPUT_MAP_ERROR librexruntime.so not mapped")
        return
    get_state_offset = int(os.environ.get("SHIFT_QUEUE_TRACE_INPUT_GET_STATE_OFFSET", "0"), 0)
    xam_offset = int(os.environ.get("SHIFT_QUEUE_TRACE_XAM_INPUT_OFFSET", "0"), 0)
    if not get_state_offset or not xam_offset:
        print("WORKER_RING_INPUT_SYMBOL_ERROR missing exported runtime offsets")
        return
    InputSystemGetState(f"*{bias + get_state_offset:#x}")
    XamInputEntry(f"*{bias + xam_offset:#x}")
    state["host_input_breakpoints_installed"] = True
    print(
        f"WORKER_RING_INPUT_BREAKPOINTS bias={bias:#x} get_state={get_state_offset:#x} xam={xam_offset:#x}"
    )


class WorkerLoop(gdb.Breakpoint):
    def __init__(self):
        super().__init__("sub_823B8AC8", internal=True)

    def stop(self):
        try:
            context, base = context_base()
            state["guest_base"] = base
            if not state["mapped_hashes"]:
                mapped_hashes()
            queue = ppc_reg(context, 3)
            state["worker_queues"].add(queue)
            if len(state["worker_queues"]) <= 8:
                print(f"WORKER_RING_WORKER_LOOP queue={queue:#x} event={queue + 32:#x}")
        except gdb.error as exc:
            print(f"WORKER_RING_WORKER_LOOP_ERROR {exc}")
        return False


class EnqueueFinish(gdb.FinishBreakpoint):
    def __init__(self, frame, saved):
        super().__init__(frame, internal=True)
        self.saved = saved

    def stop(self):
        try:
            after = [queue_snapshot(self.saved["base"], queue)
                     for queue in self.saved["candidate_queues"]]
            matches = []
            for before, current in zip(self.saved["before"], after):
                slot_index = before["producer"] & 3
                if (current["producer"] == before["producer"] + 1 and
                        current["slots"][slot_index] == self.saved["record"]):
                    matches.append({
                        "queue": current["queue"],
                        "producer_index": before["producer"],
                        "consumer_before": before["consumer"],
                        "consumer_after": current["consumer"],
                        "slot_index": slot_index,
                        "record": self.saved["record"],
                        "slot_after": current["slots"][slot_index],
                        "slots_after": current["slots"],
                    })
            parent_dispatch_id = self.saved.get("parent_gpu_dispatch_id")
            for match in matches:
                remember_queue_dispatch_id(
                    match["queue"], match["producer_index"], match["record"],
                    parent_dispatch_id,
                )
            emit("enqueue", {
                "id": self.saved["id"],
                "gpu_dispatch_id": self.saved.get("gpu_dispatch_id"),
                "parent_gpu_dispatch_id": parent_dispatch_id,
                "thread": self.saved["thread"],
                "manager": self.saved["manager"],
                "record": self.saved["record"],
                "record_words": self.saved["record_words"],
                "matches": matches,
                "match_count": len(matches),
                "candidates_before": self.saved["before"],
                "candidates_after": after,
            })
        except gdb.error as exc:
            print(f"WORKER_RING_ENQUEUE_FINISH_ERROR id={self.saved['id']} error={exc}")
        release_finisher(self)
        return False


class CallbackEnqueue(gdb.Breakpoint):
    def __init__(self):
        super().__init__("sub_823B8C60", internal=True)

    def stop(self):
        if state["bink_target"] is None:
            return False
        try:
            context, base = context_base()
            record = ppc_reg(context, 3)
            manager = ppc_reg(context, 4)
            if state["manager"] is None:
                state["manager"] = manager
            candidate_queues = [manager + 11328 + cpu * 80 for cpu in range(6)]
            before = [queue_snapshot(base, queue) for queue in candidate_queues]
            record_words = [read_be(base, record + offset) for offset in range(0, 32, 4)] if record else []
            saved = {
                "id": next_id(),
                "context": context,
                "base": base,
                "manager": manager,
                "record": record,
                "record_words": record_words,
                "candidate_queues": candidate_queues,
                "before": before,
                "thread": thread_id(),
                "gpu_dispatch_id": active_source1_gpu_dispatch_id(),
                "parent_gpu_dispatch_id": active_source1_gpu_dispatch_id(),
            }
            keep_finisher(EnqueueFinish(gdb.newest_frame(), saved))
        except gdb.error as exc:
            print(f"WORKER_RING_ENQUEUE_ERROR {exc}")
        return False


class DequeueFinish(gdb.FinishBreakpoint):
    def __init__(self, frame, saved):
        super().__init__(frame, internal=True)
        self.saved = saved

    def stop(self):
        try:
            context = self.saved["context"]
            base = self.saved["base"]
            result = ppc_reg(context, 3)
            after = queue_snapshot(base, self.saved["queue"])
            thread = self.saved["thread"]
            stack = state["active_dequeues"].get(thread, [])
            if stack and stack[-1]["id"] == self.saved["id"]:
                stack.pop()
            self.saved["event"].update({
                "entry_elapsed_seconds": self.saved["event"]["elapsed_seconds"],
                "entry_wall_clock_epoch_ms": self.saved["event"]["wall_clock_epoch_ms"],
                "return_wall_clock_epoch_ms": int(time.time() * 1000),
                "phase": "return",
                "status_returned": result,
                "producer_after": after["producer"],
                "consumer_after": after["consumer"],
                "slots_after": after["slots"],
                "consumer_advanced": after["consumer"] == self.saved["consumer"] + 1,
                "thread_name": thread_name(),
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
            state["last_dequeue_by_thread"][thread] = {
                "id": self.saved["id"],
                "queue": self.saved["queue"],
                "slot_value": self.saved["slot_value"],
                "gpu_dispatch_id": self.saved.get("gpu_dispatch_id"),
                "parent_gpu_dispatch_id": self.saved.get("parent_gpu_dispatch_id"),
                "phase": "return",
                "consumer_before": self.saved["consumer"],
            }
        except gdb.error as exc:
            print(f"WORKER_RING_DEQUEUE_FINISH_ERROR id={self.saved['id']} error={exc}")
        release_finisher(self)
        return False


class QueueDequeue(gdb.Breakpoint):
    def __init__(self):
        super().__init__("sub_823B87B0", internal=True)

    def stop(self):
        if state["bink_target"] is None:
            return False
        try:
            context, base = context_base()
            queue = ppc_reg(context, 3)
            worker = read_be(base, queue)
            arm_worker72_watch(base, worker, "queue+0 before dequeue")
            head = read_be(base, queue + 56)
            tail = read_be(base, queue + 60)
            if head == tail:
                return False
            slot_index = tail & 3
            slot_value = read_be(base, queue + 64 + slot_index * 4)
            parent_dispatch_id = take_queue_dispatch_id(queue, tail, slot_value)
            active_dispatch_id = active_source1_gpu_dispatch_id()
            if parent_dispatch_id is None:
                parent_dispatch_id = active_dispatch_id
            saved = {
                "id": next_id(),
                "context": context,
                "base": base,
                "queue": queue,
                "producer": head,
                "consumer": tail,
                "slot_index": slot_index,
                "slot_value": slot_value,
                "gpu_dispatch_id": active_dispatch_id,
                "parent_gpu_dispatch_id": parent_dispatch_id,
                "thread": thread_id(),
                "known_worker_queue": queue in state["worker_queues"],
            }
            saved["event"] = emit("dequeue", {
                "id": saved["id"],
                "gpu_dispatch_id": saved["gpu_dispatch_id"],
                "parent_gpu_dispatch_id": saved["parent_gpu_dispatch_id"],
                "phase": "entry",
                "thread": saved["thread"],
                "thread_name": thread_name(),
                "queue": queue,
                "known_worker_queue": saved["known_worker_queue"],
                "producer_before": head,
                "consumer_before": tail,
                "slot_index": slot_index,
                "slot_value": slot_value,
            })
            state["active_dequeues"].setdefault(saved["thread"], []).append(saved)
            keep_finisher(DequeueFinish(gdb.newest_frame(), saved))
        except gdb.error as exc:
            print(f"WORKER_RING_DEQUEUE_ERROR {exc}")
        return False


class CompletionFinish(gdb.FinishBreakpoint):
    def __init__(self, frame, saved):
        super().__init__(frame, internal=True)
        self.saved = saved

    def stop(self):
        try:
            base = self.saved["base"]
            worker = self.saved["worker"]
            after = read_be(base, worker + 64)
            self.saved["counter_after"] = after
            self.saved["field72_after"] = read_be(base, worker + 72)
            self.saved["signed_delta"] = ((after - self.saved["counter_before"] + 0x80000000) & 0xFFFFFFFF) - 0x80000000
            self.saved["expected_delta"] = -1 if (
                self.saved["token"] == 0xC0000000 and self.saved["field72_before"] == 0
            ) else 0
            self.saved["event"].update({
                "entry_elapsed_seconds": self.saved["event"]["elapsed_seconds"],
                "entry_wall_clock_epoch_ms": self.saved["event"]["wall_clock_epoch_ms"],
                "return_wall_clock_epoch_ms": int(time.time() * 1000),
                "phase": "return",
                "counter_after": after,
                "field72_after": self.saved["field72_after"],
                "signed_delta": self.saved["signed_delta"],
                "expected_delta": self.saved["expected_delta"],
                "thread_name": thread_name(),
                "elapsed_seconds": round(time.monotonic() - started, 3),
            })
        except gdb.error as exc:
            print(f"WORKER_RING_COMPLETION_FINISH_ERROR id={self.saved['id']} error={exc}")
        release_finisher(self)
        return False


class WorkerCompletion(gdb.Breakpoint):
    def __init__(self):
        super().__init__("sub_823B85D0", internal=True)

    def stop(self):
        if state["bink_target"] is None:
            return False
        try:
            context, base = context_base()
            worker = ppc_reg(context, 3)
            arm_worker72_watch(base, worker, "sub_823B85D0 r3")
            ring_queue = ppc_reg(context, 4)
            stream = ppc_reg(context, 5)
            token = read_be(base, stream) if stream else 0
            active_dequeues = state["active_dequeues"].get(thread_id(), [])
            active_dispatch_id = active_source1_gpu_dispatch_id()
            parent_dispatch_id = (
                active_dequeues[-1].get("parent_gpu_dispatch_id")
                if active_dequeues else active_dispatch_id
            )
            saved = {
                "id": next_id(),
                "thread": thread_id(),
                "thread_name": thread_name(),
                "worker": worker,
                "ring_queue": ring_queue,
                "stream": stream,
                "token": token,
                "stream_words": [read_be(base, stream + offset) for offset in range(0, 16, 4)] if stream else [],
                "counter_before": read_be(base, worker + 64),
                "field72_before": read_be(base, worker + 72),
                "worker36": read_be(base, worker + 36),
                "worker76": read_be(base, worker + 76),
                "ring_producer": read_be(base, ring_queue + 56),
                "ring_consumer": read_be(base, ring_queue + 60),
                "gpu_dispatch_id": active_dispatch_id,
                "parent_gpu_dispatch_id": parent_dispatch_id,
                "parent_dequeue_id": active_dequeues[-1]["id"] if active_dequeues else None,
                "parent_record": active_dequeues[-1]["slot_value"] if active_dequeues else None,
                "context": context,
                "base": base,
            }
            public = {key: value for key, value in saved.items()
                      if key not in ("context", "base")}
            public["phase"] = "entry"
            saved["event"] = emit("completion", public)
            keep_finisher(CompletionFinish(gdb.newest_frame(), saved))
        except gdb.error as exc:
            print(f"WORKER_RING_COMPLETION_ERROR {exc}")
        return False


class KernelEventCall(gdb.Breakpoint):
    def __init__(self, symbol, address):
        self.symbol = symbol
        super().__init__(f"*{address:#x}", internal=True)

    def stop(self):
        if state["bink_target"] is None:
            return False
        try:
            context, base = context_base()
            event = ppc_reg(context, 3)
            if event not in {queue + 32 for queue in state["worker_queues"]}:
                return False
            thread = thread_id()
            thread_label = thread_name()
            fields = {
                "symbol": self.symbol,
                "thread": thread,
                "thread_name": thread_label,
                "event": event,
                "guest_signal_state": read_be(base, event + 4),
                "gpu_dispatch_id": active_source1_gpu_dispatch_id(),
                "parent_gpu_dispatch_id": (
                    state["active_dequeues"].get(thread, [])[-1].get("parent_gpu_dispatch_id")
                    if state["active_dequeues"].get(thread)
                    else active_source1_gpu_dispatch_id()
                ),
            }
            if self.symbol == "KeWaitForSingleObject":
                state["ke_wait_calls"] += 1
                fields.update({
                    "wait_call": state["ke_wait_calls"],
                    "arguments_r3_r7": [ppc_reg(context, index) for index in range(3, 8)],
                })
            entry = emit("event_call", fields)
            if self.symbol == "KeWaitForSingleObject":
                keep_finisher(KeWaitReturn(
                    gdb.newest_frame(), context, base, entry,
                ))
        except gdb.error as exc:
            print(f"WORKER_RING_EVENT_CALL_ERROR symbol={self.symbol} error={exc}")
        return False


class KeWaitReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, entry):
        super().__init__(frame, internal=True)
        self.context, self.base, self.entry = context, base, entry

    def stop(self):
        try:
            event = self.entry["event"]
            entry_fields = {
                key: value for key, value in self.entry.items()
                if key not in ("kind", "trace_sequence", "wall_clock_epoch_ms", "elapsed_seconds")
            }
            emit("ke_wait_return", {
                **entry_fields,
                "guest_signal_state_at_return": read_be(self.base, event + 4),
                "return_status": ppc_reg(self.context, 3),
                "entry_elapsed_seconds": self.entry["elapsed_seconds"],
                "duration_seconds": round(time.monotonic() - started - self.entry["elapsed_seconds"], 3),
            })
        except gdb.error as exc:
            print(f"WORKER_RING_KE_WAIT_RETURN_ERROR call={self.entry.get('wait_call')} {exc}")
        release_finisher(self)
        return False


class ProducerFinish(gdb.FinishBreakpoint):
    def __init__(self, frame, saved):
        super().__init__(frame, internal=True)
        self.saved = saved

    def stop(self):
        try:
            base = self.saved["base"]
            self.saved["counter_after"] = read_be(base, self.saved["manager"] + 11012)
            self.saved["stream_words_after"] = [
                read_be(base, self.saved["stream"] + offset)
                for offset in (0, 4, 8, 12)
            ] if self.saved["stream"] else []
            event = dict(self.saved)
            event.pop("context", None)
            event.pop("base", None)
            emit("producer_call", event)
            if self.saved["delta"] != 0:
                emit("producer", event)
            stack = state["active_producers"].get(self.saved["thread"], [])
            if stack and stack[-1]["id"] == self.saved["id"]:
                stack.pop()
        except gdb.error as exc:
            print(f"WORKER_RING_PRODUCER_FINISH_ERROR id={self.saved['id']} error={exc}")
        release_finisher(self)
        return False


class CounterWrite(gdb.Breakpoint):
    def __init__(self, base, guest_address):
        self.base = base
        self.guest_address = guest_address
        self.previous = read_be(base, guest_address)
        self.write_count = 0
        host_address = base + guest_address
        super().__init__(
            f"*(unsigned int*){host_address:#x}",
            type=gdb.BP_WATCHPOINT,
            wp_class=gdb.WP_WRITE,
            internal=True,
        )

    def stop(self):
        try:
            value = read_be(self.base, self.guest_address)
            self.write_count += 1
            thread = thread_id()
            active_dequeues = state["active_dequeues"].get(thread, [])
            active_producers = state["active_producers"].get(thread, [])
            stack = gdb.execute("bt 4", to_string=True).splitlines()
            emit("counter_write", {
                "write_index": self.write_count,
                "guest_address": self.guest_address,
                "before": self.previous,
                "after": value,
                "signed_delta": ((value - self.previous + 0x80000000) & 0xFFFFFFFF) - 0x80000000,
                **gpu_dispatch_event_fields(thread),
                "parent_dequeue_id": active_dequeues[-1].get("id") if active_dequeues else None,
                "parent_record": active_dequeues[-1].get("slot_value") if active_dequeues else None,
                "parent_producer_id": active_producers[-1].get("id") if active_producers else None,
                "thread": thread,
                "thread_name": thread_name(),
                "host_stack": stack[:4],
            })
            self.previous = value
        except gdb.error as exc:
            print(f"WORKER_RING_COUNTER_WRITE_ERROR {exc}")
        return False


class Worker72Write(gdb.Breakpoint):
    def __init__(self, base, worker, source):
        self.base = base
        self.worker = worker
        self.guest_address = worker + 72
        self.previous = read_be(base, self.guest_address)
        self.source = source
        super().__init__(
            f"*(unsigned int*){base + self.guest_address:#x}",
            type=gdb.BP_WATCHPOINT,
            wp_class=gdb.WP_WRITE,
            internal=True,
        )

    def stop(self):
        try:
            after = read_be(self.base, self.guest_address)
            thread = thread_id()
            active = state["active_dequeues"].get(thread, [])
            parent = active[-1] if active else state["last_dequeue_by_thread"].get(thread)
            emit("worker72_write", {
                "guest_address": self.guest_address,
                "worker": self.worker,
                "watch_armed_from": self.source,
                "before": self.previous,
                "after": after,
                "counter": read_be(self.base, self.worker + 64),
                "thread": thread,
                "thread_name": thread_name(),
                "dequeue_parent": ({
                    "id": parent.get("id"),
                    "queue": parent.get("queue"),
                    "record": parent.get("slot_value"),
                    "gpu_dispatch_id": parent.get("gpu_dispatch_id"),
                    "parent_gpu_dispatch_id": parent.get("parent_gpu_dispatch_id"),
                    "phase": "active" if active else "previous_return",
                    "consumer_before": parent.get("consumer", parent.get("consumer_before")),
                } if parent else None),
                "gpu_dispatch_id": active_source1_gpu_dispatch_id(),
                "parent_gpu_dispatch_id": parent.get("parent_gpu_dispatch_id") if parent else None,
                "worker_queue": queue_snapshot(self.base, parent["queue"])
                    if parent and parent.get("queue") else None,
                "host_stack": gdb.execute("bt 6", to_string=True).splitlines()[:6],
            })
            self.previous = after
        except gdb.error as exc:
            print(f"WORKER_RING_WORKER72_WRITE_ERROR {exc}")
        return False


def arm_worker72_watch(base, worker, source):
    manager = state.get("manager")
    if not worker:
        return False
    if manager is None:
        print(f"WORKER_RING_WORKER72_CANDIDATE_PENDING source={source} candidate={worker:#x}")
        return False
    if worker + 64 != manager + 11012:
        print("WORKER_RING_WORKER72_CANDIDATE_REJECT "
              f"source={source} candidate={worker:#x} manager={manager:#x} "
              f"candidate_counter={worker + 64:#x} expected_counter={manager + 11012:#x}")
        return False
    current = state.get("worker72_watch")
    if current is not None:
        if current.worker != worker:
            print("WORKER_RING_WORKER72_ADDRESS_MISMATCH "
                  f"old={current.worker:#x} new={worker:#x} source={source}")
            return False
        return True
    state["worker72_watch"] = Worker72Write(base, worker, source)
    print("WORKER_RING_WORKER72_WATCH "
          f"worker={worker:#x} address={worker + 72:#x} source={source} "
          f"initial={read_be(base, worker + 72):#x}")
    return True


class QueueProducer(gdb.Breakpoint):
    def __init__(self):
        super().__init__("sub_823B31A0", internal=True)

    def stop(self):
        if state["bink_target"] is None:
            return False
        try:
            context, base = context_base()
            state["producer_calls"] += 1
            manager = ppc_reg(context, 3)
            record = ppc_reg(context, 4)
            tag = ppc_reg(context, 6)
            delta = ppc_reg(context, 7)
            stream = ppc_reg(context, 8)
            if state.get("counter_watch") is None:
                counter_address = manager + 11012
                state["counter_watch"] = CounterWrite(base, counter_address)
                print("WORKER_RING_COUNTER_WATCH address=%#x initial=%#x"
                      % (counter_address, read_be(base, counter_address)))
            thread = thread_id()
            lr = read_le(context + 256, 8) & 0xFFFFFFFF
            saved = {
                "id": next_id(),
                "thread": thread,
                "thread_name": thread_name(),
                "gpu_dispatch_id": active_source1_gpu_dispatch_id(),
                "parent_gpu_dispatch_id": active_source1_gpu_dispatch_id(),
                "producer_call": state["producer_calls"],
                "caller_lr": lr,
                "manager": manager,
                "record": record,
                "record_words": [read_be(base, record + offset) for offset in range(0, 16, 4)] if record else [],
                "payload": ppc_reg(context, 5),
                "tag": tag,
                "delta": delta,
                "stream": stream,
                "counter_before": read_be(base, manager + 11012),
                "stream_words_before": [read_be(base, stream + offset) for offset in (0, 4, 8, 12)] if stream else [],
                "routes": [],
                "context": context,
                "base": base,
            }
            state["active_producers"].setdefault(thread, []).append(saved)
            keep_finisher(ProducerFinish(gdb.newest_frame(), saved))
        except gdb.error as exc:
            print(f"WORKER_RING_PRODUCER_ERROR {exc}")
        return False


class SubmissionRoute(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)

    def stop(self):
        if state["bink_target"] is None:
            return False
        try:
            thread = thread_id()
            active = state["active_producers"].get(thread, [])
            if not active:
                return False
            context, base = context_base()
            args = [ppc_reg(context, index) for index in range(3, 9)]
            lr = read_le(context + 256, 8) & 0xFFFFFFFF
            event = {
                "producer_id": active[-1]["id"],
                "producer_call": active[-1]["producer_call"],
                "gpu_dispatch_id": active[-1].get("gpu_dispatch_id"),
                "parent_gpu_dispatch_id": active[-1].get("parent_gpu_dispatch_id"),
                "symbol": self.symbol,
                "caller_lr": lr,
                "arguments_r3_to_r8": args,
                "counter_at_route": read_be(base, active[-1]["manager"] + 11012),
                "thread": thread,
                "thread_name": thread_name(),
            }
            active[-1]["routes"].append({
                "symbol": self.symbol,
                "caller_lr": lr,
                "arguments_r3_to_r8": args,
            })
            emit("submission_route", event)
        except gdb.error as exc:
            print(f"WORKER_RING_SUBMISSION_ROUTE_ERROR symbol={self.symbol} error={exc}")
        return False


class Source1CallbackFinish(gdb.FinishBreakpoint):
    def __init__(self, frame, callback_scope):
        super().__init__(frame, internal=True)
        self.callback_scope = callback_scope

    def stop(self):
        thread = self.callback_scope["thread"]
        stack = state["active_source1_callbacks"].get(thread, [])
        for index in range(len(stack) - 1, -1, -1):
            if stack[index]["scope_id"] == self.callback_scope["scope_id"]:
                del stack[index]
                break
        if not stack:
            state["active_source1_callbacks"].pop(thread, None)
        release_finisher(self)
        return False


class Source1Callback(gdb.Breakpoint):
    def __init__(self):
        super().__init__("sub_823B37B8", internal=True)

    def stop(self):
        if state["bink_target"] is None:
            return False
        try:
            context, base = context_base()
            source = ppc_reg(context, 3)
            if source != 1:
                return False
            manager = ppc_reg(context, 4)
            callback_context = ppc_reg(context, 13)
            callback_bit_index = read_be(base, callback_context + 268, 1)
            callback_object = read_be(base, manager + 10900)
            callback = read_be(base, callback_object + 16) if callback_object else 0
            callback_data = read_be(base, callback_object + 20) if callback_object else 0
            manager_flags = read_be(base, manager + 10904)
            queue_head_pointer = read_be(base, manager + 0x2A90)
            state["source1_callback_ordinal"] += 1
            callback_scope = {
                "scope_id": next_id(),
                "thread": thread_id(),
                "gpu_dispatch_id": sample_gpu_dispatch_id(),
            }
            finisher = Source1CallbackFinish(gdb.newest_frame(), callback_scope)
            state["active_source1_callbacks"].setdefault(
                callback_scope["thread"], [],
            ).append(callback_scope)
            keep_finisher(finisher)
            event = {
                "entry_ordinal": state["source1_callback_ordinal"],
                "gpu_dispatch_id": callback_scope["gpu_dispatch_id"],
                "source": source,
                "manager": manager,
                "guest_lr": read_le(context + 256, 8) & 0xFFFFFFFF,
                "arguments_r3_to_r10": [ppc_reg(context, index) for index in range(3, 11)],
                "callback_bit_index": callback_bit_index,
                "callback_bit_mask": 1 << callback_bit_index if callback_bit_index < 32 else 0,
                "callback_object": callback_object,
                "callback_function": callback,
                "callback_data": callback_data,
                "callback_mask": read_be(base, callback_object) if callback_object else 0,
                "manager_flags_before": manager_flags,
                "manager_flag_bit_set_before": bool(
                    callback_bit_index < 32 and manager_flags & (1 << callback_bit_index)
                ),
                "software_queue": {
                    "head_pointer": queue_head_pointer,
                    "head": read_be(base, queue_head_pointer) if queue_head_pointer else None,
                    "tail": read_be(base, manager + 0x2A9C),
                    "predicate_byte": read_be(base, manager + 0x2ABD, 1),
                },
                "manager_counter_before": read_be(base, manager + 11012),
                "manager_words_10904_to_1091c": [
                    read_be(base, manager + offset)
                    for offset in (10904, 10908, 10912, 10916, 10920, 10924, 10928)
                ],
                "thread": thread_id(),
                "thread_name": thread_name(),
            }
            emit("source1_callback", event)
        except Exception as exc:
            print(f"WORKER_RING_SOURCE1_CALLBACK_ERROR {exc}")
        return False


BinkTarget()
if trace_event_write_shd:
    EventWriteShdPacket()
WorkerLoop()
ControllerMethod("sub_8230CD00")
ControllerMethod("sub_82308E60")
SceneFunction("sub_82DDC6F0")
SceneFunction("sub_82DDD1C8")
SceneFunction("sub_82E2C5A8")
SceneFunction("sub_82E2CD10")
SceneFunction("sub_82F38158")
SceneFunction("sub_82FD5658")
SceneFunction("sub_82F33810")
RetailQueueWait()
CallbackEnqueue()
QueueDequeue()
WorkerCompletion()
QueueProducer()
SubmissionRoute("sub_823B2AF0")
SubmissionRoute("sub_823B21D0")
Source1Callback()
end

run

python
pid = gdb.selected_inferior().pid
stop_context = {}

def capture_stop_diagnostics():
    snapshot = {}
    manager = state["manager"]
    base = state["guest_base"]
    if manager and base:
        head_pointer = read_be(base, manager + 0x2A90)
        snapshot["software_gpu_queue"] = {
            "manager": manager,
            "head_pointer": head_pointer,
            "head": read_be(base, head_pointer) if head_pointer else None,
            "tail": read_be(base, manager + 0x2A9C),
            "predicate_byte": read_be(base, manager + 0x2ABD, 1),
            "manager_11008": read_be(base, manager + 11008),
            "manager_11012": read_be(base, manager + 11012),
        }
    worker_queues = []
    for queue in sorted(state["worker_queues"]):
        try:
            item = queue_snapshot(base, queue)
            item["event_signal_state"] = read_be(base, queue + 36)
            worker_queues.append(item)
        except gdb.error as exc:
            worker_queues.append({"queue": queue, "error": str(exc)})
    snapshot["worker_queues"] = worker_queues

    for thread in gdb.selected_inferior().threads():
        name = thread.name or ""
        if not name.startswith("Core 0/0: Main"):
            continue
        try:
            thread.switch()
            context, thread_base = context_base()
            snapshot["guest_main_thread"] = {
                "thread": name,
                "host_context": context,
                "guest_base": thread_base,
                "current_guest_pc_context_slot": read_le(context + 0x100, 8) & 0xFFFFFFFF,
                "guest_registers": {
                    f"r{index}": ppc_reg(context, index)
                    for index in (1, 3, 13, 30, 31)
                },
                "backtrace": gdb.execute("bt 8", to_string=True).strip(),
            }
        except Exception as exc:
            snapshot["guest_main_thread_error"] = str(exc)
        break
    return snapshot

try:
    stop_context["program"] = gdb.execute("info program", to_string=True).strip()
    if "signal" in stop_context["program"].lower():
        thread = gdb.selected_thread()
        stop_context["thread"] = thread.name if thread else None
        for key, command in (
            ("host_pc", "p/x $pc"),
            ("symbol", "info symbol $pc"),
            ("source_line", "info line *$pc"),
            ("registers", "info registers"),
            ("signal_info", "p $_siginfo"),
            ("backtrace", "bt 12"),
        ):
            try:
                value = gdb.execute(command, to_string=True).strip()
                stop_context[key] = value
                if key == "symbol":
                    import re
                    match = re.search(r"sub_([0-9A-Fa-f]{8})", value)
                    stop_context["guest_function_entry"] = (
                        f"0x{match.group(1)}" if match else None
                    )
                elif key == "host_pc":
                    stop_context[key] = int(value.split("=", 1)[-1], 16)
            except Exception as exc:
                stop_context[key + "_error"] = str(exc)
except Exception as exc:
    stop_context["capture_error"] = str(exc)
try:
    stop_context["diagnostics"] = capture_stop_diagnostics()
    print("WORKER_RING_STOP_DIAGNOSTICS " + json.dumps(
        stop_context["diagnostics"], sort_keys=True,
    ))
except Exception as exc:
    stop_context["diagnostics_error"] = str(exc)
for key in ("enqueue_events", "dequeue_events", "completion_events", "producer_events",
            "producer_call_events", "submission_route_events", "source1_callback_events",
            "event_call_events", "counter_write_events", "worker72_write_events",
            "controller_update_events", "controller_return_events", "host_input_events",
            "xam_input_events", "xam_input_return_events", "bink_complete_events", "input_gate_events",
            "scene_function_events", "scene_function_return_events", "scene_state_events",
            "retail_queue_wait_events", "retail_queue_wait_return_events",
            "queue_field_write_events",
            "ke_wait_return_events"):
    print(f"WORKER_RING_TOTAL {key}={len(state[key])}")
print("WORKER_RING_TOTAL bink_target_polls=%d" % state["bink_target_polls"])
print("WORKER_RING_TOTAL event_write_shd_packet_events=%d" % len(state["event_write_shd_packet_events"]))
print("WORKER_RING_GPU_DISPATCH_ID_SUMMARY " + json.dumps({
    "getter_available": state["gpu_dispatch_id_symbol_available"] is True,
    "sample_calls": state["gpu_dispatch_id_sample_calls"],
    "sample_errors": state["gpu_dispatch_id_sample_errors"],
    "queue_record_links": state["queue_dispatch_id_links"],
    "queue_record_evictions": state["queue_dispatch_id_evictions"],
    "source1_callback_records_with_id": sum(
        event.get("gpu_dispatch_id") is not None
        for event in state["source1_callback_events"]
    ),
    "queue_dequeue_records_with_parent_id": sum(
        event.get("parent_gpu_dispatch_id") is not None
        for event in state["dequeue_events"]
    ),
}, sort_keys=True))
final_queues = []
final_scene_state = None
if state["guest_base"]:
    try:
        final_scene_state = scene_manager_snapshot(state["guest_base"])
    except gdb.error as exc:
        final_scene_state = {"error": str(exc)}
    for queue in sorted(state["worker_queues"]):
        try:
            snapshot = queue_snapshot(state["guest_base"], queue)
            snapshot["event_signal_state"] = read_be(state["guest_base"], queue + 36)
            final_queues.append(snapshot)
        except gdb.error as exc:
            final_queues.append({"queue": queue, "error": str(exc)})
payload = {
    "schema": "shift.xbox360.linux-gpu-backend-events.v1",
    "gpu_backend": gpu_plugin_name,
    "run_start_wall_clock_epoch_ms": wall_started_ms,
    "run_end_wall_clock_epoch_ms": int(time.time() * 1000),
    "captured_on": "2026-10-27",
    "bink_target": state["bink_target"],
    "bink_target_diagnostics": {
        "poll_count": state["bink_target_polls"],
        "max_progress": state["bink_target_max_progress"],
        "last_poll": state["bink_target_last"],
        "first_samples": state["bink_target_samples"],
    },
    "event_write_shd_packet_events": state["event_write_shd_packet_events"],
    "gpu_dispatch_id_trace": {
        "getter_available": state["gpu_dispatch_id_symbol_available"] is True,
        "sample_calls": state["gpu_dispatch_id_sample_calls"],
        "sample_errors": state["gpu_dispatch_id_sample_errors"],
        "queue_record_links": state["queue_dispatch_id_links"],
        "queue_record_evictions": state["queue_dispatch_id_evictions"],
        "source1_callback_records_with_id": sum(
            event.get("gpu_dispatch_id") is not None
            for event in state["source1_callback_events"]
        ),
        "queue_dequeue_records_with_parent_id": sum(
            event.get("parent_gpu_dispatch_id") is not None
            for event in state["dequeue_events"]
        ),
    },
    "manager": state["manager"],
    "worker_queues": sorted(state["worker_queues"]),
    "final_queue_snapshots": final_queues,
    "final_scene_state": final_scene_state,
    "producer_calls": state["producer_calls"],
    "xam_input_calls": state["xam_input_calls"],
    "controller_update_call_counts": state["controller_update_call_counts"],
    "input_gate_emitted": state["input_gate_emitted"],
    "stop_context": stop_context,
    "worker72_watch_worker": (
        state["worker72_watch"].worker if state["worker72_watch"] else None
    ),
    "counts": {key: len(state[key]) for key in ("enqueue_events", "dequeue_events", "completion_events",
                "producer_events", "producer_call_events", "submission_route_events",
                "source1_callback_events", "event_call_events", "counter_write_events",
                "worker72_write_events", "controller_update_events", "controller_return_events",
                "host_input_events", "xam_input_events", "xam_input_return_events",
                "bink_complete_events", "input_gate_events",
                "scene_function_events", "scene_function_return_events", "scene_state_events",
                "retail_queue_wait_events", "retail_queue_wait_return_events",
                "queue_field_write_events",
                "ke_wait_return_events", "event_write_shd_packet_events")},
    "mapped_hashes": state["mapped_hashes"],
    "events": {key: state[key] for key in ("enqueue_events", "dequeue_events", "completion_events",
                "producer_events", "producer_call_events", "submission_route_events",
                "source1_callback_events", "event_call_events", "counter_write_events",
                "worker72_write_events", "controller_update_events", "controller_return_events",
                "host_input_events", "xam_input_events", "xam_input_return_events",
                "bink_complete_events", "input_gate_events",
                "scene_function_events", "scene_function_return_events", "scene_state_events",
                "retail_queue_wait_events", "retail_queue_wait_return_events",
                "queue_field_write_events",
                "ke_wait_return_events")},
}
(out / "events.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
if pid:
    try:
        gdb.execute("thread apply all bt 4")
    except Exception as exc:
        print(f"WORKER_RING_STACK_ERROR {exc}")
    try:
        gdb.execute("detach")
        os.kill(pid, signal.SIGINT)
        print(f"WORKER_RING_HOST_SIGINT pid={pid}")
    except ProcessLookupError:
        print(f"WORKER_RING_HOST_ALREADY_EXITED pid={pid}")
end
quit
