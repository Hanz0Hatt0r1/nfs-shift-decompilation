set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
handle SIGSEGV nostop noprint pass
handle SIGBUS stop print nopass

python
import gdb
import json
import os
import time

out = os.environ['SHIFT_MENU_GATE_TRACE_OUT']
backend = os.environ['SHIFT_MENU_GATE_GPU_BACKEND']
started = time.monotonic()
base_address = None
setup_object = None
scene_object = None
setup_state_last = {}
setup_scene_pointer_watchpoint = None
state2_active = False
state2_index = 0
scene_state_watchpoint = None
host_input_breakpoints = []
host_input_calls = 0
host_input_completions = 0
host_input_masks = {}
last_host_buttons = None
counts = {}
state2_counts = {}
dynamic_targets = {}
dynamic_breakpoints = {}
controller_object = None
controller_base = None
controller_candidates = 0
controller_snapshots = {}
predicate_hits = {'Start': 0, 'A': 0}
true_handler_seen = set()
action_event_watches = {}
target_controller_vtable = 0x8212e5b8
main_menu_queue_interfaces = set()
main_menu_queue_process_calls = 0
main_menu_queue_getter_calls = {}
main_menu_queue_active_getter_calls = {}
main_menu_queue_receiver = None
main_menu_queue_enqueue_calls = 0
main_menu_queue_enqueue_returns = 0
main_menu_queue_direct_append_calls = 0
main_menu_queue_direct_append_returns = 0
main_menu_process_parent_calls = 0
main_menu_process_parent_returns = 0
gui_queue_constructor_calls = 0
gui_queue_open_calls = 0
action_consumer_symbols = ('sub_822EF7B0', 'sub_822F7EC8')
action_consumer_breakpoints = []
action_consumer_calls = {symbol: 0 for symbol in action_consumer_symbols}
action_consumer_returns = {symbol: 0 for symbol in action_consumer_symbols}
action_consumer_hits = {symbol: 0 for symbol in action_consumer_symbols}
action_consumer_seen = {symbol: {'Start': set(), 'A': set()}
                         for symbol in action_consumer_symbols}
worker_gate_symbols = ('sub_822E7F70', 'sub_822E80A8', 'sub_822E1910')
worker_gate_breakpoints = []
worker_gate_calls = {symbol: 0 for symbol in worker_gate_symbols}
worker_gate_returns = {symbol: 0 for symbol in worker_gate_symbols}
worker_gate_hits = {symbol: 0 for symbol in worker_gate_symbols}
worker_gate_seen = {symbol: {'Start': set(), 'A': set()}
                    for symbol in worker_gate_symbols}
worker_gate_sample_limit = 12
dispatch_probe_calls = 0
dispatch_probe_returns = 0
dispatch_probe_seen = {'Start': set(), 'A': set()}
dispatch_probe_sample_limit = 24
context_r3_watchpoints = []
context_r3_watch_installed = False
gdb.execute('set logging file %s/gdb.log' % out)
gdb.execute('set logging overwrite on')
gdb.execute('set logging enabled on')
gdb.execute('set environment LD_LIBRARY_PATH %s/bin' % out)
gdb.execute('set environment SDL_GAMECONTROLLER_IGNORE_DEVICES 0x045e/0x0b12')
gdb.execute('set environment SHIFT_NATIVE_VULKAN_TRACE_RING 0')
gdb.execute('set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data '
            '--user_data_root=%s/user --cache_root=%s/cache '
            '--gpu_plugin=%s --no-async_shader_compilation --fullscreen=false' % (out, out, backend))

def le(address, size=4):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'little')

def be(address, size=4):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'big')

def reg(context, index):
    offset = {0: 8, 1: 16, 2: 24, 3: 0}.get(index, index * 8)
    return le(context + offset, 4)

def guest_lr(context):
    return le(context + 256, 8) & 0xffffffff

def context_base():
    return int(gdb.parse_and_eval('$rdi')), int(gdb.parse_and_eval('$rsi'))

def safe_be(base, address, size=4):
    try:
        return be(base + address, size)
    except (gdb.error, OSError, OverflowError):
        return None

def safe_words(base, address, count=8):
    # Guest stack/output pointers observed in this executable can use the
    # 0x70000000 user range; accept them here and let safe_be reject unmapped
    # addresses through GDB's memory-read error path.
    if not address or address < 0x70000000 or address >= 0xc0000000:
        return None
    return [safe_be(base, address + offset * 4) for offset in range(count)]

def app_event_queue_snapshot(base, queue):
    if not queue:
        return None
    head = safe_be(base, queue + 0x174)
    tail = safe_be(base, queue + 0x178)
    flags = safe_be(base, queue + 0x180)
    vtable = safe_be(base, queue)
    return {
        'queue': hex(queue),
        'vtable': hex(vtable) if vtable else None,
        'head': hex(head) if head else None,
        'tail': hex(tail) if tail else None,
        'head_empty': head == 0,
        'tail_empty': tail == 0,
        'capacity': safe_be(base, queue + 0x17c),
        'flags': hex(flags) if flags is not None else None,
        'opened': bool(flags & 0x80000000) if flags is not None else None,
        'head_node_words': safe_words(base, head, 8) if head else None,
    }

def emit(marker, payload):
    payload['elapsed_seconds'] = round(time.monotonic() - started, 3)
    thread = gdb.selected_thread()
    payload['thread'] = thread.name if thread else None
    print(marker + ' ' + json.dumps(payload, sort_keys=True))

def install_host_input_breakpoints():
    if host_input_breakpoints:
        return
    pid = gdb.selected_inferior().pid
    try:
        for line in open('/proc/%d/maps' % pid, encoding='ascii'):
            fields = line.rstrip().split(None, 5)
            if (len(fields) == 6 and fields[2] == '00000000'
                    and fields[5].endswith('/librexruntime.so')):
                load_bias = int(fields[0].split('-', 1)[0], 16)
                runtime = fields[5]
                get_state_address = load_bias + 0x307340
                xam_entry_address = load_bias + 0x4a4600
                host_input_breakpoints.extend((
                    HostInputSystemGetState('*%#x' % get_state_address),
                    HostXamInputEntry('*%#x' % xam_entry_address),
                ))
                emit('P1_HOST_INPUT_BREAKPOINTS', {
                    'runtime': runtime, 'runtime_sha256': '693abc4814fe04a8025e41be989ac14faa31565b2786e1397f87ad9544d601cd',
                    'input_system_get_state': hex(get_state_address),
                    'xam_input_get_state_entry': hex(xam_entry_address),
                })
                return
    except (OSError, ValueError) as exc:
        emit('P1_HOST_INPUT_BREAKPOINT_ERROR', {'error': str(exc)})
    emit('P1_HOST_INPUT_BREAKPOINT_ERROR', {'error': 'librexruntime.so mapping not found'})

class HostInputReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, user, state_ptr):
        super().__init__(frame, internal=True)
        self.user, self.state_ptr = user, state_ptr
    def stop(self):
        global host_input_completions, last_host_buttons
        try:
            status = int(gdb.parse_and_eval('$eax')) & 0xffffffff
            raw = bytes(gdb.selected_inferior().read_memory(self.state_ptr, 16))
            packet = int.from_bytes(raw[0:4], 'big')
            buttons = int.from_bytes(raw[4:6], 'big')
            host_input_completions += 1
            host_input_masks[buttons] = host_input_masks.get(buttons, 0) + 1
            emit('P1_HOST_INPUT_SAMPLE', {
                'user': self.user, 'status': hex(status), 'packet': packet,
                'buttons': hex(buttons), 'completion_index': host_input_completions,
            })
            if buttons != last_host_buttons or host_input_completions <= 8:
                emit('P1_HOST_INPUT_STATE', {
                    'user': self.user, 'status': hex(status), 'packet': packet,
                    'buttons': hex(buttons), 'raw_16': raw.hex(),
                    'completion_index': host_input_completions,
                })
                last_host_buttons = buttons
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_HOST_INPUT_STATE_ERROR %s' % exc)
        return False

class HostInputSystemGetState(gdb.Breakpoint):
    def __init__(self, spec):
        super().__init__(spec, internal=True)
    def stop(self):
        global host_input_calls
        try:
            # SysV x86-64 member call: rdi=this, esi=user, rdx=state pointer.
            user = int(gdb.parse_and_eval('$esi')) & 0xffffffff
            state_ptr = int(gdb.parse_and_eval('$rdx'))
            host_input_calls += 1
            if host_input_calls <= 8:
                emit('P1_HOST_INPUT_CALL', {
                    'user': user, 'state_pointer': hex(state_ptr),
                    'input_system_object': hex(int(gdb.parse_and_eval('$rdi'))),
                    'call_index': host_input_calls,
                })
            if user == 0 and state_ptr:
                HostInputReturn(gdb.newest_frame(), user, state_ptr)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_HOST_INPUT_CALL_ERROR %s' % exc)
        return False

class HostXamInputEntry(gdb.Breakpoint):
    def __init__(self, spec):
        super().__init__(spec, internal=True)
        self.hits = 0
    def stop(self):
        self.hits += 1
        if self.hits <= 12:
            try:
                emit('P1_XAM_INPUT_ENTRY', {
                    'user': hex(int(gdb.parse_and_eval('$edi')) & 0xffffffff),
                    'flags': hex(int(gdb.parse_and_eval('$esi')) & 0xffffffff),
                    'state_pointer': hex(int(gdb.parse_and_eval('$rdx'))),
                    'call_index': self.hits,
                })
            except (gdb.error, ValueError) as exc:
                print('P1_XAM_INPUT_ENTRY_ERROR %s' % exc)
        return False

class SceneFieldWatch(gdb.Breakpoint):
    def __init__(self, base, scene):
        self.base, self.scene = base, scene
        self.previous = safe_be(base, scene + 8)
        self.host_address = base + scene + 8
        super().__init__('*(unsigned int*)%#x' % self.host_address,
                         type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE, internal=True)
    def stop(self):
        try:
            current = safe_be(self.base, self.scene + 8)
            emit('P1_SCENE_GATE_FIELD_WRITE', {
                'scene': hex(self.scene), 'guest_field': hex(self.scene + 8),
                'before': self.previous, 'after': current,
                'host_pc': hex(int(gdb.parse_and_eval('$pc'))),
                'host_symbol': gdb.execute('info symbol $pc', to_string=True).strip(),
                'state2_index': state2_index,
            })
            self.previous = current
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_SCENE_GATE_FIELD_WRITE_ERROR %s' % exc)
        return False

class SetupScenePointerWatch(gdb.Breakpoint):
    def __init__(self, base, setup):
        self.base, self.setup = base, setup
        self.previous = safe_be(base, setup + 8)
        self.host_address = base + setup + 8
        super().__init__('*(unsigned int*)%#x' % self.host_address,
                         type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE, internal=True)
    def stop(self):
        global scene_object, scene_state_watchpoint
        try:
            current = safe_be(self.base, self.setup + 8)
            emit('P1_SETUP_SCENE_POINTER_WRITE', {
                'setup_object': hex(self.setup), 'guest_field': hex(self.setup + 8),
                'before': self.previous, 'after': hex(current) if current else current,
                'setup_state': safe_be(self.base, self.setup + 4),
                'host_pc': hex(int(gdb.parse_and_eval('$pc'))),
                'host_symbol': gdb.execute('info symbol $pc', to_string=True).strip(),
                'host_backtrace': gdb.execute('bt 8', to_string=True).strip().splitlines(),
            })
            self.previous = current
            if current and 0x80000000 <= current < 0xc0000000 and scene_state_watchpoint is None:
                scene_object = current
                scene_state_watchpoint = SceneFieldWatch(self.base, scene_object)
                emit('P1_SCENE_GATE_WATCH_ARMED', {
                    'setup_object': hex(self.setup), 'scene_object': hex(scene_object),
                    'setup_state': safe_be(self.base, self.setup + 4),
                    'scene_gate_value_plus_8': safe_be(self.base, scene_object + 8),
                    'scene_vtable': hex(safe_be(self.base, scene_object)),
                    'armed_from': 'setup_scene_pointer_write',
                })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_SETUP_SCENE_POINTER_WRITE_ERROR %s' % exc)
        return False

def install_dynamic(role, base, object_guest, slot):
    if not object_guest or object_guest < 0x80000000 or object_guest >= 0xc0000000:
        return None
    vtable = safe_be(base, object_guest)
    target = safe_be(base, vtable + slot) if vtable else None
    if not target or target < 0x80000000 or target >= 0xc0000000:
        emit('P1_STATE2_DYNAMIC_TARGET_INVALID', {
            'role': role, 'object': hex(object_guest),
            'vtable': hex(vtable) if vtable else None, 'slot': hex(slot),
            'target': hex(target) if target else None,
        })
        return target
    dynamic_targets.setdefault(target, []).append({'role': role, 'object': object_guest, 'slot': slot})
    if target not in dynamic_breakpoints:
        dynamic_breakpoints[target] = DynamicProbe(target)
    emit('P1_STATE2_DYNAMIC_TARGET', {
        'role': role, 'object': hex(object_guest), 'vtable': hex(vtable),
        'slot': hex(slot), 'target': hex(target),
    })
    return target

class DynamicFinish(gdb.FinishBreakpoint):
    def __init__(self, frame, context, target, roles, args):
        super().__init__(frame, internal=True)
        self.context, self.target, self.roles, self.args = context, target, roles, args

    def stop(self):
        try:
            emit('P1_STATE2_DYNAMIC_RETURN', {
                'guest_target': hex(self.target), 'roles': self.roles,
                'return_r3': hex(reg(self.context, 3)),
                'caller_lr': hex(guest_lr(self.context)), 'args': self.args,
                'state2_index': state2_index,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_STATE2_DYNAMIC_RETURN_ERROR target=%#x error=%s' % (self.target, exc))
        return False

class DynamicProbe(gdb.Breakpoint):
    def __init__(self, target):
        self.target = target
        self.hits = 0
        # Guest code is translated into host functions rather than mapped at
        # base_address + guest_pc. ReXGlue exports those translated functions
        # as sub_82XXXXXX symbols, so resolve the virtual target by that name.
        super().__init__('sub_%08X' % target, internal=True)

    def stop(self):
        if not state2_active:
            return False
        try:
            context, base = context_base()
            lr = guest_lr(context)
            roles = dynamic_targets.get(self.target, [])
            callsite_roles = {
                'scene_gate_1c': {0x82fd58d0},
                'scene_gate_08': {0x82fd590c},
                'global_manager_gate_1c': {0x82fd58a4},
                'service_nested_gate_04': {0x82e2c6c8},
                'service_reject_gate_24c': {0x82e2c6c8},
            }
            matched_roles = [entry for entry in roles
                             if lr in callsite_roles.get(entry['role'], set())]
            if not matched_roles:
                return False
            self.hits += 1
            sample = self.hits <= 8 or state2_index % 8 == 0
            if sample:
                args = [hex(reg(context, index)) for index in (3, 4, 5, 6)]
                emit('P1_STATE2_DYNAMIC_CALL', {
                    'guest_target': hex(self.target), 'roles': matched_roles,
                    'args_r3_r6': args, 'caller_lr': hex(lr),
                    'state2_index': state2_index,
                    'r3_words': safe_words(base, reg(context, 3), 8),
                })
                DynamicFinish(gdb.newest_frame(), context, self.target, matched_roles, args)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_STATE2_DYNAMIC_CALL_ERROR target=%#x error=%s' % (self.target, exc))
        return False

class ActionEventFieldWatch(gdb.Breakpoint):
    def __init__(self, base, event, button, event_code):
        self.base, self.event = base, event
        self.button, self.event_code = button, event_code
        self.write_index = 0
        self.previous = safe_be(base, event + 0x20)
        self.host_address = base + event + 0x20
        super().__init__('*(unsigned int*)%#x' % self.host_address,
                         type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE, internal=True)

    def stop(self):
        try:
            self.write_index += 1
            current = safe_be(self.base, self.event + 0x20)
            payload = {
                'button': self.button, 'event_code': hex(self.event_code),
                'event_object': hex(self.event), 'guest_field': hex(self.event + 0x20),
                'before': self.previous, 'after': current,
                'host_pc': hex(int(gdb.parse_and_eval('$pc'))),
                'host_symbol': gdb.execute('info symbol $pc', to_string=True).strip(),
                'button_field_write_index': self.write_index,
                'state2_active': state2_active, 'state2_index': state2_index,
                'guest_memory_base_at_watch_arm': hex(self.base),
                'guest_memory_modified_by_probe': False,
            }
            try:
                # rdi is the generated guest function's saved PPC context at
                # this watchpoint; rsi is volatile inside the translated body.
                context = int(gdb.parse_and_eval('$rdi'))
                payload['guest_context_candidate'] = hex(context)
                payload['guest_lr'] = hex(guest_lr(context))
                payload['guest_r26_candidate'] = hex(reg(context, 26))
                payload['guest_r31_candidate'] = hex(reg(context, 31))
                payload['guest_r31_matches_event_object'] = reg(context, 31) == self.event
            except (gdb.error, OSError, OverflowError, ValueError):
                payload['guest_context_candidate'] = None
            try:
                payload['host_backtrace'] = gdb.execute('bt 8', to_string=True).strip().splitlines()
            except gdb.error:
                payload['host_backtrace'] = []
            emit('P1_ACTION_EVENT_FIELD_WRITE', payload)
            self.previous = current
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_ACTION_EVENT_FIELD_WRITE_ERROR button=%s error=%s' % (self.button, exc))
        return False

class ControllerPredicateReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, button, edge, caller):
        super().__init__(frame, internal=True)
        self.context, self.button, self.edge, self.caller = context, button, edge, caller

    def stop(self):
        try:
            result = le(self.context, 4)
            emit('P1_RETAIL_INPUT_PREDICATE', {
                'button': self.button, 'edge_byte': hex(self.edge),
                'predicate': result, 'caller_lr': hex(self.caller),
            })
            if (result and self.caller == 0x8230a9d0
                    and self.button not in true_handler_seen):
                true_handler_seen.add(self.button)
                predicate = reg(self.context, 30)
                event = reg(self.context, 31)
                predicate_vtable = safe_be(controller_base, predicate) if controller_base else None
                predicate_offsets = (0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40)
                event_offsets = (0, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 60, 64, 68, 72)
                predicate_fields = [safe_be(controller_base, predicate + off)
                                    for off in predicate_offsets] if controller_base else []
                event_fields = [safe_be(controller_base, event + off)
                                for off in event_offsets] if controller_base else []
                event_code = event_fields[2] if len(event_fields) > 2 else None
                predicate_slots = [safe_be(controller_base, predicate_vtable + off)
                                   for off in (0, 4, 8, 12, 16, 20)] \
                    if controller_base and predicate_vtable else []
                event_vtable = event_fields[0] if event_fields else None
                event_slots = [safe_be(controller_base, event_vtable + off)
                               for off in (0, 4, 8, 12, 16, 20, 24, 28)] \
                    if controller_base and event_vtable else []
                emit('P1_RETAIL_INPUT_TRUE_HANDLER', {
                    'button': self.button, 'caller_lr': hex(self.caller),
                    'predicate_object': hex(predicate),
                    'predicate_offsets': predicate_offsets,
                    'predicate_fields': predicate_fields,
                    'predicate_vtable': hex(predicate_vtable) if predicate_vtable else None,
                    'predicate_vtable_slots': predicate_slots,
                    'event_object': hex(event), 'event_offsets': event_offsets,
                    'event_fields': event_fields,
                    'event_vtable': hex(event_vtable) if event_vtable else None,
                    'event_vtable_slots': event_slots,
                    'guest_context_r30_r31': [hex(predicate), hex(event)],
                })
                expected_code = 0x30010400 if self.button == 'Start' else 0x30010c00
                if event_code == expected_code and (self.button, event) not in action_event_watches:
                    action_event_watches[(self.button, event)] = ActionEventFieldWatch(
                        controller_base, event, self.button, event_code)
                    emit('P1_ACTION_EVENT_FIELD_WATCH_ARMED', {
                        'button': self.button, 'event_code': hex(event_code),
                        'event_object': hex(event), 'guest_field': hex(event + 0x20),
                        'field_before': safe_be(controller_base, event + 0x20),
                        'watch_offset': '0x20',
                        'guest_memory_modified_by_probe': False,
                    })
                try:
                    stack = gdb.execute('bt 16', to_string=True).splitlines()
                    emit('P1_RETAIL_INPUT_TRUE_HANDLER_STACK', {
                        'button': self.button, 'frames': stack,
                    })
                except gdb.error as exc:
                    emit('P1_RETAIL_INPUT_TRUE_HANDLER_STACK_ERROR', {
                        'button': self.button, 'error': str(exc),
                    })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_RETAIL_INPUT_PREDICATE_ERROR button=%s error=%s' % (self.button, exc))
        return False

class ControllerPredicate(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82311290', internal=True)

    def stop(self):
        if controller_object is None or controller_base is None:
            return False
        try:
            context = int(gdb.parse_and_eval('$rdi'))
            table = le(context, 4)
            index = le(context + 32, 4)
            button = 'Start' if index == 4 else 'A' if index == 12 else None
            if button is None:
                return False
            address = (table + index + 20) & 0xffffffff
            expected = controller_object + (140 if button == 'Start' else 148)
            if address != expected:
                return False
            edge = be(controller_base + address, 1)
            if edge & 0x80:
                predicate_hits[button] += 1
                if predicate_hits[button] <= 24:
                    caller = le(context + 256, 8) & 0xffffffff
                    ControllerPredicateReturn(gdb.newest_frame(), context, button, edge, caller)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_RETAIL_INPUT_PREDICATE_ENTRY_ERROR %s' % exc)
        return False

class ControllerEdge(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)

    def stop(self):
        if controller_object is None or controller_base is None:
            return False
        try:
            context, base = context_base()
            obj = le(context, 4)
            if obj != controller_object:
                return False
            snapshot = (be(base + obj + 128, 4), be(base + obj + 132, 4),
                        be(base + obj + 140, 1), be(base + obj + 148, 1))
            if controller_snapshots.get(self.symbol) != snapshot:
                controller_snapshots[self.symbol] = snapshot
                emit('P1_RETAIL_CONTROLLER_EDGE_STATE', {
                    'function': self.symbol, 'object': hex(obj),
                    'buttons': hex(snapshot[0]), 'previous': hex(snapshot[1]),
                    'start_edge': hex(snapshot[2]), 'a_edge': hex(snapshot[3]),
                })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_RETAIL_CONTROLLER_EDGE_ERROR function=%s error=%s' % (self.symbol, exc))
        return False

class ControllerReady(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82308E60', internal=True)

    def stop(self):
        global controller_object, controller_base, controller_candidates
        try:
            context, base = context_base()
            obj = le(context, 4)
            if not obj or obj < 0x80000000 or obj >= 0xc0000000:
                return False
            vtable = safe_be(base, obj)
            if vtable == target_controller_vtable and controller_object is None:
                controller_object, controller_base = obj, base
                fields = (safe_be(base, obj + 128), safe_be(base, obj + 132),
                          safe_be(base, obj + 140, 1), safe_be(base, obj + 148, 1))
                emit('P1_RETAIL_CONTROLLER_FOUND', {
                    'object': hex(obj), 'vtable': hex(vtable), 'fields': fields,
                })
            elif controller_object is None and controller_candidates < 8:
                controller_candidates += 1
                emit('P1_RETAIL_CONTROLLER_CANDIDATE', {
                    'object': hex(obj), 'vtable': hex(vtable) if vtable else None,
                })
            return False
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_RETAIL_CONTROLLER_DISCOVERY_ERROR %s' % exc)
        return False

class Finish(gdb.FinishBreakpoint):
    def __init__(self, frame, context, symbol, args, limit=8, outer=False):
        super().__init__(frame, internal=True)
        self.context, self.symbol, self.args = context, symbol, args
        self.limit, self.outer = limit, outer

    def stop(self):
        global state2_active
        try:
            n = state2_counts.get(self.symbol, 0)
            if n <= self.limit:
                emit('P1_STATE2_RETURN', {
                    'function': self.symbol, 'return_r3': hex(reg(self.context, 3)),
                    'caller_lr': hex(guest_lr(self.context)), 'args': self.args,
                    'state2_index': state2_index,
                })
            if self.outer:
                if state2_index <= 8 or state2_index % 8 == 0:
                    emit('P1_STATE2_UPDATE_RETURN', {
                        'object': hex(setup_object) if setup_object else None,
                        'return_r3': hex(reg(self.context, 3)),
                        'state_after': safe_be(base_address, setup_object + 4) if setup_object else None,
                        'scene_object': hex(scene_object) if scene_object else None,
                        'state2_index': state2_index,
                    })
                state2_active = False
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_STATE2_RETURN_ERROR function=%s error=%s' % (self.symbol, exc))
            if self.outer:
                state2_active = False
        return False

class Probe(gdb.Breakpoint):
    def __init__(self, symbol, limit=8, finish=True):
        self.symbol = symbol[:4] + symbol[4:].upper()
        self.limit, self.want_finish = limit, finish
        super().__init__(self.symbol, internal=True)

    def stop(self):
        global base_address, setup_object, scene_object, scene_state_watchpoint, setup_scene_pointer_watchpoint, state2_active, state2_index
        try:
            context, base = context_base()
            r3, r4 = reg(context, 3), reg(context, 4)
            lr = guest_lr(context)
            count = counts.get(self.symbol, 0) + 1
            counts[self.symbol] = count
            state2_count = None
            if state2_active:
                state2_count = state2_counts.get(self.symbol, 0) + 1
                state2_counts[self.symbol] = state2_count
            if self.symbol == 'sub_82FD5988':
                setup_object, base_address = r3, base
                if count == 1:
                    scene_candidate = safe_be(base, r3 + 8)
                    emit('P1_MENU_SETUP_INIT_ENTRY', {
                        'setup_object': hex(r3), 'setup_state': safe_be(base, r3 + 4),
                        'scene_object': hex(scene_candidate) if scene_candidate else None,
                        'scene_gate_value_plus_8': safe_be(base, scene_candidate + 8) if scene_candidate else None,
                        'scene_vtable': hex(safe_be(base, scene_candidate)) if scene_candidate else None,
                        'caller_lr': hex(lr),
                    })
                    if scene_candidate and 0x80000000 <= scene_candidate < 0xc0000000 and scene_state_watchpoint is None:
                        scene_object = scene_candidate
                        scene_state_watchpoint = SceneFieldWatch(base, scene_object)
                        emit('P1_SCENE_GATE_WATCH_ARMED', {
                            'setup_object': hex(r3), 'scene_object': hex(scene_object),
                            'setup_state': safe_be(base, r3 + 4),
                            'scene_gate_value_plus_8': safe_be(base, scene_object + 8),
                            'scene_vtable': hex(safe_be(base, scene_object)),
                            'armed_from': 'first_sub_82FD5988_entry',
                        })
                    if scene_state_watchpoint is None:
                        setup_scene_pointer_watchpoint = SetupScenePointerWatch(base, r3)
                        emit('P1_SETUP_SCENE_POINTER_WATCH_ARMED', {
                            'setup_object': hex(r3), 'guest_field': hex(r3 + 8),
                            'initial_scene_object': hex(scene_candidate) if scene_candidate else None,
                            'setup_state': safe_be(base, r3 + 4),
                        })
            if self.symbol == 'sub_82FD5658' and setup_object is not None and r3 == setup_object:
                state = safe_be(base, r3 + 4)
                if state in (0, 1, 2, 3) and setup_state_last.get(r3) != state:
                    setup_state_last[r3] = state
                    candidate_scene = safe_be(base, r3 + 8)
                    emit('P1_MENU_SETUP_STATE_OBSERVED', {
                        'setup_object': hex(r3), 'setup_state': state,
                        'scene_object': hex(candidate_scene) if candidate_scene else None,
                        'scene_gate_value_plus_8': safe_be(base, candidate_scene + 8) if candidate_scene else None,
                        'caller_lr': hex(lr),
                    })
                if state in (0, 1, 2, 3) and scene_state_watchpoint is None:
                    candidate_scene = safe_be(base, r3 + 8)
                    if candidate_scene and 0x80000000 <= candidate_scene < 0xc0000000:
                        scene_object = candidate_scene
                        scene_state_watchpoint = SceneFieldWatch(base, scene_object)
                        emit('P1_SCENE_GATE_WATCH_ARMED', {
                            'setup_object': hex(r3), 'scene_object': hex(scene_object),
                            'setup_state': state,
                            'scene_gate_value_plus_8': safe_be(base, scene_object + 8),
                            'scene_vtable': hex(safe_be(base, scene_object)),
                            'armed_from': 'first_state_update_with_scene_object',
                        })
                if state == 2:
                    state2_index += 1
                    state2_active = True
                    scene_object = safe_be(base, r3 + 8)
                    if state2_index in (5, 21, 37):
                        for breakpoint in action_consumer_breakpoints:
                            breakpoint.enabled = True
                        for breakpoint in worker_gate_breakpoints:
                            breakpoint.enabled = True
                        emit('P1_ACTION_CONSUMER_WINDOW', {
                            'enabled': True,
                            'phase': {5: 'Start', 21: 'A', 37: 'Start'}[state2_index],
                            'state2_index': state2_index,
                            'guest_memory_modified_by_probe': False,
                        })
                    elif state2_index in (17, 33, 49):
                        for breakpoint in action_consumer_breakpoints:
                            breakpoint.enabled = False
                        for breakpoint in worker_gate_breakpoints:
                            breakpoint.enabled = False
                        emit('P1_ACTION_CONSUMER_WINDOW', {
                            'enabled': False,
                            'phase_end_index': state2_index,
                            'guest_memory_modified_by_probe': False,
                        })
                    if state2_index == 1:
                        scene_targets = {}
                        for slot, role in ((0x1c, 'scene_gate_1c'), (8, 'scene_gate_08')):
                            target = install_dynamic(role, base, scene_object, slot)
                            scene_targets[role] = hex(target) if target else None
                        if scene_state_watchpoint is None:
                            scene_state_watchpoint = SceneFieldWatch(base, scene_object)
                        install_host_input_breakpoints()
                        emit('P1_STATE2_FIRST_ENTRY', {
                            'object': hex(r3), 'scene_object': hex(scene_object) if scene_object else None,
                            'state': state, 'child_state': safe_be(base, r3 + 0x1c + 0x28),
                            'child_ready': safe_be(base, r3 + 0x1c + 0x2c),
                            'child_fallback': safe_be(base, r3 + 0x1c + 0x30),
                            'scene_gate_targets': scene_targets,
                            'scene_gate_value_plus_8': safe_be(base, scene_object + 8),
                            'scene_words': safe_words(base, scene_object, 16),
                            'caller_lr': hex(lr),
                        })
                    emit('P1_STATE2_UPDATE', {
                        'object': hex(r3), 'state': state,
                        'scene_object': hex(scene_object) if scene_object else None,
                        'scene_words': safe_words(base, scene_object, 12),
                        'caller_lr': hex(lr), 'state2_index': state2_index,
                    })
                    Finish(gdb.newest_frame(), context, self.symbol, [hex(r3)], outer=True)
                return False
            if state2_active and state2_count <= self.limit:
                args = [hex(r3), hex(r4), hex(reg(context, 5)), hex(reg(context, 6))]
                payload = {'function': self.symbol, 'args_r3_r6': args,
                           'caller_lr': hex(lr), 'state2_index': state2_index,
                           'state2_function_count': state2_count}
                if self.symbol in ('sub_82DDD1C8', 'sub_82E2C650', 'sub_821B9988', 'sub_82E2CD10'):
                    payload['arg_words'] = safe_words(base, r3, 24)
                if self.symbol == 'sub_82FF6998':
                    payload['manager_singleton_before'] = safe_be(base, 0x831b2b40)
                emit('P1_STATE2_CALL', payload)
                if self.want_finish and self.symbol != 'sub_82FF6998':
                    Finish(gdb.newest_frame(), context, self.symbol, args, self.limit)
            if self.symbol == 'sub_82E2CD10' and state2_active and state2_count == 1:
                nested = safe_be(base, r3 + 4)
                install_dynamic('service_nested_gate_04', base, nested, 4)
            if self.symbol == 'sub_82E2C650' and state2_active and state2_count == 1:
                nested = safe_be(base, r3 + 0x48)
                install_dynamic('service_reject_gate_24c', base, nested, 0x24c)
            if self.symbol == 'sub_82FF6998' and state2_active and state2_count == 1:
                # The singleton value is observed on return; its vtable slot +0x1c
                # is installed there by the dedicated return probe below.
                GetterFinish(gdb.newest_frame(), context, base)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_STATE2_PROBE_ERROR function=%s error=%s' % (self.symbol, exc))
        return False

class GetterFinish(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base):
        super().__init__(frame, internal=True)
        self.context, self.base = context, base
    def stop(self):
        try:
            obj = reg(self.context, 3)
            emit('P1_STATE2_MANAGER', {
                'object': hex(obj), 'words': safe_words(self.base, obj, 12),
                'vtable': hex(safe_be(self.base, obj)) if obj else None,
                'caller_lr': hex(guest_lr(self.context)), 'state2_index': state2_index,
            })
            install_dynamic('global_manager_gate_1c', self.base, obj, 0x1c)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_STATE2_MANAGER_ERROR %s' % exc)
        return False

ControllerReady()
ControllerEdge('sub_8230CD00')
ControllerPredicate()

for symbol, limit, finish in (
    ('sub_82FD5988', 1, False), ('sub_82FD5658', 8, False),
    ('sub_82ddd1c8', 8, True), ('sub_82e2c650', 8, True),
    ('sub_821b9988', 8, True), ('sub_82e2cd10', 8, True),
    ('sub_82ddd108', 8, True), ('sub_82e8f470', 4, False),
    ('sub_82e86d90', 4, False), ('sub_82ff6998', 8, True),
    ('sub_82fbcb88', 8, True), ('sub_82fd4418', 4, True),
    ('sub_826c1c20', 4, True), ('sub_822bcee8', 4, True),
    ('sub_822bd0c0', 4, False), ('sub_82ddd030', 4, True),
):
    Probe(symbol, limit, finish)
end


python
import gdb

scene_gate_method_counts = {'sub_82DD8FF8': 0, 'sub_82DD9020': 0}
scene_gate_method_target_counts = {'sub_82DD8FF8': 0, 'sub_82DD9020': 0}

class SceneGateMethodFinish(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, symbol, receiver, caller, call_index,
                 receiver_matches_scene, entry_value):
        super().__init__(frame, internal=True)
        self.context, self.base, self.symbol = context, base, symbol
        self.receiver, self.caller, self.call_index = receiver, caller, call_index
        self.receiver_matches_scene, self.entry_value = receiver_matches_scene, entry_value

    def stop(self):
        try:
            emit('P1_MAINMENU_SCENE_GATE_METHOD_RETURN', {
                'function': self.symbol,
                'call_index': self.call_index,
                'receiver': hex(self.receiver),
                'receiver_matches_attached_scene': self.receiver_matches_scene,
                'field_entry': self.entry_value,
                'field_after': safe_be(self.base, self.receiver + 8),
                'return_r3': hex(reg(self.context, 3)),
                'caller_lr': hex(self.caller),
                'state2_index': state2_index,
                'guest_memory_modified_by_probe': False,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAINMENU_SCENE_GATE_METHOD_RETURN_ERROR function=%s error=%s' %
                  (self.symbol, exc))
        return False

class SceneGateMethod(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)

    def stop(self):
        try:
            context, base = context_base()
            receiver = reg(context, 3)
            caller = guest_lr(context)
            scene_match = receiver == scene_object if scene_object is not None else None
            scene_gate_method_counts[self.symbol] += 1
            if scene_match:
                scene_gate_method_target_counts[self.symbol] += 1
            call_index = scene_gate_method_counts[self.symbol]
            target_index = scene_gate_method_target_counts[self.symbol]
            if call_index <= 64 or scene_match:
                emit('P1_MAINMENU_SCENE_GATE_METHOD_CALL', {
                    'function': self.symbol,
                    'guest_function_address': '0x82dd8ff8' if self.symbol == 'sub_82DD8FF8' else '0x82dd9020',
                    'call_index': call_index,
                    'target_call_index': target_index if scene_match else None,
                    'receiver': hex(receiver),
                    'receiver_matches_attached_scene': scene_match,
                    'attached_scene': hex(scene_object) if scene_object is not None else None,
                    'receiver_vtable': hex(safe_be(base, receiver)) if safe_be(base, receiver) else None,
                    'field_before': safe_be(base, receiver + 8),
                    'setup_state': safe_be(base, setup_object + 4) if setup_object else None,
                    'caller_lr': hex(caller),
                    'state2_index': state2_index,
                    'guest_memory_modified_by_probe': False,
                })
                SceneGateMethodFinish(gdb.newest_frame(), context, base, self.symbol,
                                      receiver, caller, call_index, scene_match,
                                      safe_be(base, receiver + 8))
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAINMENU_SCENE_GATE_METHOD_CALL_ERROR function=%s error=%s' %
                  (self.symbol, exc))
        return False

class StartupMemoryFill(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_826D9E70', internal=True)
        self.hits = 0

    def stop(self):
        thread = gdb.selected_thread()
        if thread and thread.name and 'Core 0/0: Main' not in thread.name:
            return False
        self.hits += 1
        try:
            context, base = context_base()
            emit('P1_STARTUP_MEMORY_FILL_ENTRY', {
                'call_index': self.hits,
                'destination_guest': hex(reg(context, 3)),
                'fill_value': hex(reg(context, 4)),
                'length': hex(reg(context, 5)),
                'caller_lr': hex(guest_lr(context)),
                'host_thread': thread.name if thread else None,
                'guest_memory_base': hex(base),
                'guest_memory_modified_by_probe': False,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_STARTUP_MEMORY_FILL_ENTRY_ERROR %s' % exc)
        if self.hits >= 32:
            self.enabled = False
        return False

class GuiQueueConstructorReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, receiver, caller, before, state_before):
        super().__init__(frame, internal=True)
        self.context, self.base, self.receiver = context, base, receiver
        self.caller, self.before = caller, before
        self.state_before = state_before

    def stop(self):
        try:
            emit('P1_GUI_QUEUE_CTOR_RETURN', {
                'queue_receiver': hex(self.receiver),
                'caller_lr': hex(self.caller),
                'return_r3': hex(reg(self.context, 3)),
                'flags_before': hex(self.before) if self.before is not None else None,
                'queue_state_before': self.state_before,
                'queue_state_after': app_event_queue_snapshot(self.base, self.receiver),
                'guest_memory_modified_by_probe': False,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_GUI_QUEUE_CTOR_RETURN_ERROR %s' % exc)
        return False

class GuiQueueConstructor(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_822E1470', internal=True)

    def stop(self):
        global gui_queue_constructor_calls
        try:
            context, base = context_base()
            receiver = reg(context, 3)
            if not (0x80000000 <= receiver < 0xc0000000):
                return False
            gui_queue_constructor_calls += 1
            if gui_queue_constructor_calls <= 128:
                caller = guest_lr(context)
                before = safe_be(base, receiver + 0x180)
                state_before = app_event_queue_snapshot(base, receiver)
                emit('P1_GUI_QUEUE_CTOR_CALL', {
                    'call_index': gui_queue_constructor_calls,
                    'queue_receiver': hex(receiver),
                    'queue_vtable': hex(safe_be(base, receiver)) if safe_be(base, receiver) else None,
                    'caller_lr': hex(caller),
                    'flags_before': hex(before) if before is not None else None,
                    'queue_state_before': state_before,
                    'guest_memory_modified_by_probe': False,
                })
                GuiQueueConstructorReturn(gdb.newest_frame(), context, base,
                                          receiver, caller, before, state_before)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_GUI_QUEUE_CTOR_CALL_ERROR %s' % exc)
        return False

class GuiQueueOpenReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, receiver, caller, args, flags_before,
                 queue_state_before):
        super().__init__(frame, internal=True)
        self.context, self.base, self.receiver = context, base, receiver
        self.caller, self.args, self.flags_before = caller, args, flags_before
        self.queue_state_before = queue_state_before

    def stop(self):
        try:
            emit('P1_GUI_QUEUE_OPEN_RETURN', {
                'queue_receiver': hex(self.receiver),
                'caller_lr': hex(self.caller),
                'args_r3_r6': self.args,
                'return_r3': hex(reg(self.context, 3)),
                'flags_before': hex(self.flags_before) if self.flags_before is not None else None,
                'queue_state_before': self.queue_state_before,
                'queue_state_after': app_event_queue_snapshot(self.base, self.receiver),
                'guest_memory_modified_by_probe': False,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_GUI_QUEUE_OPEN_RETURN_ERROR %s' % exc)
        return False

class GuiQueueOpen(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_822E15B0', internal=True)

    def stop(self):
        global gui_queue_open_calls
        try:
            context, base = context_base()
            receiver = reg(context, 3)
            if safe_be(base, receiver) != 0x82128f1c:
                return False
            gui_queue_open_calls += 1
            if gui_queue_open_calls <= 64:
                args = [hex(reg(context, index)) for index in (3, 4, 5, 6)]
                caller = guest_lr(context)
                flags_before = safe_be(base, receiver + 0x180)
                queue_state_before = app_event_queue_snapshot(base, receiver)
                emit('P1_GUI_QUEUE_OPEN_CALL', {
                    'call_index': gui_queue_open_calls,
                    'queue_receiver': hex(receiver),
                    'queue_vtable': '0x82128f1c',
                    'caller_lr': hex(caller),
                    'args_r3_r6': args,
                    'flags_before': hex(flags_before) if flags_before is not None else None,
                    'queue_state_before': queue_state_before,
                    'guest_memory_modified_by_probe': False,
                })
                GuiQueueOpenReturn(gdb.newest_frame(), context, base, receiver,
                                   caller, args, flags_before, queue_state_before)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_GUI_QUEUE_OPEN_CALL_ERROR %s' % exc)
        return False

class MainMenuQueueMethodReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, gui_object, queue_receiver, target, call_index):
        super().__init__(frame, internal=True)
        self.context, self.base = context, base
        self.gui_object, self.queue_receiver = gui_object, queue_receiver
        self.target, self.call_index = target, call_index

    def stop(self):
        try:
            event = reg(self.context, 3)
            header = safe_be(self.base, event + 4) if event else None
            emit('P1_MAIN_MENU_EVENT_QUEUE_RETURN', {
                'gui_object': hex(self.gui_object),
                'queue_receiver': hex(self.queue_receiver),
                'getter_target': hex(self.target),
                'call_index': self.call_index,
                'return_event': hex(event) if event else None,
                'event_words': safe_words(self.base, event, 12) if event else None,
                'event_type': (header >> 16) & 0xff if header is not None else None,
                'event_subtype': header >> 24 if header is not None else None,
                'queue_words_after': safe_words(self.base, self.queue_receiver, 12),
                'queue_flags_after': safe_be(self.base, self.queue_receiver + 0x180),
                'state2_index': state2_index,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAIN_MENU_EVENT_QUEUE_RETURN_ERROR %s' % exc)
        return False

class MainMenuQueueGetter(gdb.Breakpoint):
    def __init__(self, target, gui_object, queue_receiver):
        self.target, self.gui_object, self.queue_receiver = target, gui_object, queue_receiver
        self.symbol = 'sub_%08X' % target
        super().__init__(self.symbol, internal=True)

    def stop(self):
        if state2_index == 0:
            return False
        try:
            context, base = context_base()
            if reg(context, 3) != self.queue_receiver:
                return False
            raw = safe_be(base, controller_object + 128) if controller_object else 0
            previous = safe_be(base, controller_object + 132) if controller_object else 0
            start_edge = safe_be(base, controller_object + 140, 1) if controller_object else 0
            a_edge = safe_be(base, controller_object + 148, 1) if controller_object else 0
            raw = raw or 0
            previous = previous or 0
            start_edge = start_edge or 0
            a_edge = a_edge or 0
            host = last_host_buttons or 0
            active = bool(((raw | previous | host) & 0x1010)
                          or (start_edge & 0x80) or (a_edge & 0x80))
            index = main_menu_queue_getter_calls.get(self.queue_receiver, 0) + 1
            main_menu_queue_getter_calls[self.queue_receiver] = index
            if active:
                main_menu_queue_active_getter_calls[self.queue_receiver] = (
                    main_menu_queue_active_getter_calls.get(self.queue_receiver, 0) + 1)
            if index <= 96:
                emit('P1_MAIN_MENU_EVENT_QUEUE_CALL', {
                    'gui_object': hex(self.gui_object),
                    'queue_receiver': hex(self.queue_receiver),
                    'getter_target': hex(self.target),
                    'call_index': index,
                    'caller_lr': hex(guest_lr(context)),
                    'input': {'active': active, 'host_buttons': hex(host),
                              'buttons': hex(raw), 'previous': hex(previous),
                              'start_edge': hex(start_edge), 'a_edge': hex(a_edge)},
                    'queue_words_before': safe_words(base, self.queue_receiver, 12),
                    'queue_flags_before': safe_be(base, self.queue_receiver + 0x180),
                    'state2_index': state2_index,
                    'guest_memory_modified_by_probe': False,
                })
                MainMenuQueueMethodReturn(gdb.newest_frame(), context, base,
                                          self.gui_object, self.queue_receiver,
                                          self.target, index)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAIN_MENU_EVENT_QUEUE_CALL_ERROR error=%s' % exc)
        return False

class MainMenuEventQueue(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82DDAC20', internal=True)

    def stop(self):
        global main_menu_queue_process_calls, main_menu_queue_receiver
        if state2_index == 0:
            return False
        try:
            context, base = context_base()
            gui_object = reg(context, 3)
            queue_receiver = gui_object + 0x80
            vtable = safe_be(base, queue_receiver)
            target = safe_be(base, vtable + 4) if vtable else None
            main_menu_queue_process_calls += 1
            if main_menu_queue_process_calls <= 96:
                emit('P1_MAIN_MENU_GUI_EVENT_QUEUE_PROCESS', {
                    'gui_object': hex(gui_object),
                    'queue_receiver': hex(queue_receiver),
                    'caller_lr': hex(guest_lr(context)),
                    'queue_vtable': hex(vtable) if vtable else None,
                    'getter_target': hex(target) if target else None,
                    'state2_index': state2_index,
                    'guest_memory_modified_by_probe': False,
                })
            if (target and 0x80000000 <= target < 0xc0000000
                    and queue_receiver not in main_menu_queue_interfaces):
                main_menu_queue_interfaces.add(queue_receiver)
                main_menu_queue_receiver = queue_receiver
                MainMenuQueueGetter(target, gui_object, queue_receiver)
                emit('P1_MAIN_MENU_EVENT_QUEUE_INTERFACE', {
                    'gui_object': hex(gui_object),
                    'queue_receiver': hex(queue_receiver),
                    'queue_vtable': hex(vtable), 'getter_target': hex(target),
                    'queue_words': safe_words(base, queue_receiver, 12),
                    'queue_flags': safe_be(base, queue_receiver + 0x180),
                    'guest_memory_modified_by_probe': False,
                })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAIN_MENU_EVENT_QUEUE_PROCESS_ERROR %s' % exc)
        return False

class MainMenuQueueEnqueueReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, queue, message_type, message_data,
                 caller, call_index, queue_state_before):
        super().__init__(frame, internal=True)
        self.context, self.base, self.queue = context, base, queue
        self.message_type, self.message_data = message_type, message_data
        self.caller, self.call_index = caller, call_index
        self.queue_state_before = queue_state_before

    def stop(self):
        global main_menu_queue_enqueue_returns
        try:
            main_menu_queue_enqueue_returns += 1
            emit('P1_MAIN_MENU_EVENT_QUEUE_ENQUEUE_RETURN', {
                'call_index': self.call_index,
                'queue_receiver': hex(self.queue),
                'message_type': hex(self.message_type),
                'message_data': hex(self.message_data) if self.message_data else None,
                'caller_lr': hex(self.caller),
                'queue_state_before': self.queue_state_before,
                'queue_state_after': app_event_queue_snapshot(self.base, self.queue),
                'state2_index': state2_index,
                'guest_memory_modified_by_probe': False,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAIN_MENU_EVENT_QUEUE_ENQUEUE_RETURN_ERROR %s' % exc)
        return False

class MainMenuQueueEnqueue(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_822E1880', internal=True)

    def stop(self):
        global main_menu_queue_enqueue_calls
        if main_menu_queue_receiver is None:
            return False
        try:
            context, base = context_base()
            queue = reg(context, 3)
            if queue != main_menu_queue_receiver:
                return False
            main_menu_queue_enqueue_calls += 1
            if main_menu_queue_enqueue_calls <= 64:
                caller = guest_lr(context)
                message_type, message_data = reg(context, 4), reg(context, 5)
                snapshot = app_event_queue_snapshot(base, queue)
                emit('P1_MAIN_MENU_EVENT_QUEUE_ENQUEUE_CALL', {
                    'call_index': main_menu_queue_enqueue_calls,
                    'queue_receiver': hex(queue),
                    'message_type': hex(message_type),
                    'message_data': hex(message_data) if message_data else None,
                    'args_r3_r6': [hex(reg(context, r)) for r in (3, 4, 5, 6)],
                    'caller_lr': hex(caller),
                    'queue_state_before': snapshot,
                    'state2_index': state2_index,
                    'guest_memory_modified_by_probe': False,
                })
                MainMenuQueueEnqueueReturn(gdb.newest_frame(), context, base, queue,
                                           message_type, message_data, caller,
                                           main_menu_queue_enqueue_calls, snapshot)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAIN_MENU_EVENT_QUEUE_ENQUEUE_CALL_ERROR %s' % exc)
        return False

class GuiQueueDirectAppendReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, queue, descriptor, caller, call_index,
                 queue_state_before):
        super().__init__(frame, internal=True)
        self.context, self.base, self.queue = context, base, queue
        self.descriptor, self.caller = descriptor, caller
        self.call_index, self.queue_state_before = call_index, queue_state_before

    def stop(self):
        global main_menu_queue_direct_append_returns
        try:
            main_menu_queue_direct_append_returns += 1
            emit('P1_MAIN_MENU_EVENT_QUEUE_DIRECT_APPEND_RETURN', {
                'call_index': self.call_index,
                'queue_receiver': hex(self.queue),
                'append_descriptor': hex(self.descriptor),
                'caller_lr': hex(self.caller),
                'queue_state_before': self.queue_state_before,
                'queue_state_after': app_event_queue_snapshot(self.base, self.queue),
                'return_r3': hex(reg(self.context, 3)),
                'state2_index': state2_index,
                'guest_memory_modified_by_probe': False,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAIN_MENU_EVENT_QUEUE_DIRECT_APPEND_RETURN_ERROR %s' % exc)
        return False

class GuiQueueDirectAppend(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_822E1B18', internal=True)

    def stop(self):
        global main_menu_queue_direct_append_calls
        if main_menu_queue_receiver is None:
            return False
        try:
            context, base = context_base()
            queue, descriptor = reg(context, 3), reg(context, 4)
            if queue != main_menu_queue_receiver:
                return False
            main_menu_queue_direct_append_calls += 1
            caller = guest_lr(context)
            state_before = app_event_queue_snapshot(base, queue)
            emit('P1_MAIN_MENU_EVENT_QUEUE_DIRECT_APPEND_CALL', {
                'call_index': main_menu_queue_direct_append_calls,
                'queue_receiver': hex(queue),
                'append_descriptor': hex(descriptor),
                'descriptor_words': safe_words(base, descriptor, 8),
                'args_r3_r6': [hex(reg(context, index)) for index in (3, 4, 5, 6)],
                'caller_lr': hex(caller),
                'queue_state_before': state_before,
                'state2_index': state2_index,
                'guest_memory_modified_by_probe': False,
            })
            GuiQueueDirectAppendReturn(gdb.newest_frame(), context, base, queue,
                                       descriptor, caller,
                                       main_menu_queue_direct_append_calls,
                                       state_before)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAIN_MENU_EVENT_QUEUE_DIRECT_APPEND_CALL_ERROR %s' % exc)
        return False

class GuiQueueProcessParentReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, receiver, caller, call_index,
                 setup_state_before, scene_field_before):
        super().__init__(frame, internal=True)
        self.context, self.base, self.receiver = context, base, receiver
        self.caller, self.call_index = caller, call_index
        self.setup_state_before = setup_state_before
        self.scene_field_before = scene_field_before

    def stop(self):
        global main_menu_process_parent_returns
        try:
            main_menu_process_parent_returns += 1
            emit('P1_MAIN_MENU_EVENT_QUEUE_PROCESS_PARENT_RETURN', {
                'call_index': self.call_index,
                'receiver': hex(self.receiver),
                'caller_lr': hex(self.caller),
                'return_r3': hex(reg(self.context, 3)),
                'setup_state_before': self.setup_state_before,
                'setup_state_after': safe_be(self.base, self.receiver + 4),
                'attached_scene_field_before': self.scene_field_before,
                'attached_scene_field_after': safe_be(self.base, scene_object + 8)
                    if scene_object else None,
                'state2_index': state2_index,
                'guest_memory_modified_by_probe': False,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAIN_MENU_EVENT_QUEUE_PROCESS_PARENT_RETURN_ERROR %s' % exc)
        return False

class GuiQueueProcessParent(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82DDB330', internal=True)

    def stop(self):
        global main_menu_process_parent_calls
        if state2_index == 0:
            return False
        try:
            context, base = context_base()
            receiver = reg(context, 3)
            main_menu_process_parent_calls += 1
            caller = guest_lr(context)
            setup_state = safe_be(base, receiver + 4)
            attached_field = safe_be(base, scene_object + 8) if scene_object else None
            emit('P1_MAIN_MENU_EVENT_QUEUE_PROCESS_PARENT_CALL', {
                'call_index': main_menu_process_parent_calls,
                'receiver': hex(receiver),
                'caller_lr': hex(caller),
                'args_r3_r6': [hex(reg(context, index)) for index in (3, 4, 5, 6)],
                'setup_state': setup_state,
                'attached_scene_field': attached_field,
                'state2_index': state2_index,
                'guest_memory_modified_by_probe': False,
            })
            GuiQueueProcessParentReturn(gdb.newest_frame(), context, base, receiver,
                                        caller, main_menu_process_parent_calls,
                                        setup_state, attached_field)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_MAIN_MENU_EVENT_QUEUE_PROCESS_PARENT_CALL_ERROR %s' % exc)
        return False

def action_input_snapshot(base):
    if controller_object is None:
        return None
    raw = safe_be(base, controller_object + 128) or 0
    previous = safe_be(base, controller_object + 132) or 0
    start_edge = safe_be(base, controller_object + 140, 1) or 0
    a_edge = safe_be(base, controller_object + 148, 1) or 0
    host = last_host_buttons or 0
    return {
        'host_buttons': hex(host), 'buttons': hex(raw),
        'previous': hex(previous), 'start_edge': hex(start_edge),
        'a_edge': hex(a_edge),
        'active': bool(((raw | previous | host) & 0x1010)
                       or (start_edge & 0x80) or (a_edge & 0x80)),
    }

class ActionConsumerReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, symbol, call_index, input_snapshot,
                 args, caller):
        super().__init__(frame, internal=True)
        self.context, self.base, self.symbol = context, base, symbol
        self.call_index, self.input_snapshot = call_index, input_snapshot
        self.args, self.caller = args, caller

    def stop(self):
        try:
            action_consumer_returns[self.symbol] += 1
            emit('P1_ACTION_CONSUMER_RETURN', {
                'function': self.symbol,
                'call_index': self.call_index,
                'caller_lr': hex(self.caller),
                'return_r3': hex(reg(self.context, 3)),
                'return_r3_r10': [hex(reg(self.context, index))
                                  for index in range(3, 11)],
                'r30_r31_after': [hex(reg(self.context, index))
                                  for index in (30, 31)],
                'args_r3_r10_at_entry': [hex(value) for value in self.args],
                'input': self.input_snapshot,
                'last_state2_index_seen': state2_index,
                'guest_memory_modified_by_probe': False,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_ACTION_CONSUMER_RETURN_ERROR function=%s error=%s' %
                  (self.symbol, exc))
        return False

class ActionConsumer(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)
        self.enabled = False
        action_consumer_breakpoints.append(self)

    def stop(self):
        if state2_index == 0 or controller_object is None or controller_base is None:
            return False
        try:
            context, base = context_base()
            snapshot = action_input_snapshot(base)
            if snapshot is None or not snapshot['active']:
                return False
            action_consumer_hits[self.symbol] += 1
            args = [reg(context, index) for index in range(3, 11)]
            mask = ((int(snapshot['buttons'], 16)
                     | int(snapshot['previous'], 16)
                     | int(snapshot['host_buttons'], 16)) & 0x1010)
            button = 'Start' if mask & 0x10 else 'A' if mask & 0x1000 else None
            if button is None:
                return False
            receiver = args[0]
            if receiver in action_consumer_seen[self.symbol][button]:
                return False
            if len(action_consumer_seen[self.symbol][button]) >= 2:
                return False
            action_consumer_seen[self.symbol][button].add(receiver)
            action_consumer_calls[self.symbol] += 1
            call_index = action_consumer_calls[self.symbol]
            pointer_words = {}
            for name, value in (("r3", receiver), ("r5", args[2]), ("r6", args[3]),
                                ("r30", reg(context, 30)), ("r31", reg(context, 31))):
                if 0x80000000 <= value < 0xc0000000:
                    pointer_words[name] = safe_words(base, value, 8)
            caller = guest_lr(context)
            payload = {
                'function': self.symbol,
                'call_index': call_index,
                'button': button,
                'receiver': hex(receiver),
                'caller_lr': hex(caller),
                'args_r3_r10': [hex(value) for value in args],
                'pointer_words': pointer_words,
                'r30_r31': [hex(reg(context, index)) for index in (30, 31)],
                'input': snapshot,
                'last_state2_index_seen': state2_index,
                'guest_memory_modified_by_probe': False,
            }
            if call_index <= 2:
                payload['host_backtrace'] = gdb.execute('bt 14', to_string=True).splitlines()
            emit('P1_ACTION_CONSUMER_CALL', payload)
            ActionConsumerReturn(gdb.newest_frame(), context, base, self.symbol,
                                 call_index, snapshot, args, caller)
            if len(action_consumer_seen[self.symbol][button]) >= 2:
                self.enabled = False
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_ACTION_CONSUMER_CALL_ERROR function=%s error=%s' %
                  (self.symbol, exc))
        return False

class ContextR3WriteWatch(gdb.Breakpoint):
    def __init__(self, context, memory_base, call_index, caller, before):
        super().__init__('*(unsigned int*)%#x' % context,
                         type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE,
                         internal=True)
        self.context, self.memory_base = context, memory_base
        self.call_index, self.caller, self.before = call_index, caller, before
        thread = gdb.selected_thread()
        self.origin_thread_global_num = thread.global_num if thread else None
        context_r3_watchpoints.append(self)

    def stop(self):
        thread = gdb.selected_thread()
        if (self.origin_thread_global_num is not None and thread is not None
                and thread.global_num != self.origin_thread_global_num):
            return False
        self.enabled = False
        try:
            pc = int(gdb.parse_and_eval('$pc'))
            payload = {
                'source_function': 'sub_822E1910',
                'source_call_index': self.call_index,
                'source_caller_lr': hex(self.caller),
                'context_pointer': hex(self.context),
                'context_r3_before': hex(self.before),
                'context_r3_after': hex(reg(self.context, 3)),
                'context_guest_lr': hex(guest_lr(self.context)),
                'host_pc': hex(pc),
                'host_symbol': gdb.execute('info symbol $pc', to_string=True).strip(),
                'host_context_r14': hex(int(gdb.parse_and_eval('$r14'))),
                'host_memory_rbx': hex(int(gdb.parse_and_eval('$rbx'))),
                'thread_global_num': thread.global_num if thread else None,
                'host_backtrace': gdb.execute('bt 12', to_string=True).splitlines(),
                'next_host_instructions': gdb.execute('x/8i $pc', to_string=True).splitlines(),
                'guest_memory_modified_by_probe': False,
            }
            emit('P1_CONTEXT_R3_WRITE_WATCH', payload)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_CONTEXT_R3_WRITE_WATCH_ERROR %s' % exc)
        return False

class WorkerGateReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, symbol, call_index, args, snapshot,
                 caller, memory_base, receiver_words_before,
                 receiver_queue_before, second_argument_words_before,
                 stack_r1, capture_call_stack):
        super().__init__(frame, internal=True)
        self.context, self.symbol = context, symbol
        self.call_index, self.args = call_index, args
        self.snapshot, self.caller = snapshot, caller
        self.memory_base = memory_base
        self.receiver_words_before = receiver_words_before
        self.receiver_queue_before = receiver_queue_before
        self.second_argument_words_before = second_argument_words_before
        self.stack_r1, self.capture_call_stack = stack_r1, capture_call_stack

    def stop(self):
        global context_r3_watch_installed
        try:
            worker_gate_returns[self.symbol] += 1
            payload = {
                'function': self.symbol, 'call_index': self.call_index,
                'caller_lr': hex(self.caller),
                'args_r3_r10_at_entry': [hex(value) for value in self.args],
                'return_r3': hex(reg(self.context, 3)),
                'return_r3_r10': [hex(reg(self.context, index))
                                  for index in range(3, 11)],
                'receiver_words_before': self.receiver_words_before,
                'receiver_words_after': safe_words(
                    self.memory_base, self.args[0],
                    len(self.receiver_words_before or []))
                    if self.receiver_words_before is not None else None,
                'receiver_queue_before': self.receiver_queue_before,
                'receiver_queue_after': app_event_queue_snapshot(
                    self.memory_base, self.args[0]),
                'second_argument_words_before': self.second_argument_words_before,
                'second_argument_words_after': safe_words(
                    self.memory_base, self.args[1],
                    len(self.second_argument_words_before or []))
                    if self.second_argument_words_before is not None else None,
                'input': self.snapshot,
                'last_state2_index_seen': state2_index,
                'guest_memory_modified_by_probe': False,
            }
            if self.stack_r1:
                payload['guest_stack_r1'] = hex(self.stack_r1)
                payload['guest_stack_words_after'] = safe_words(
                    self.memory_base, self.stack_r1, 8)
            if self.capture_call_stack:
                payload['host_backtrace_after'] = gdb.execute(
                    'bt 12', to_string=True).splitlines()
                try:
                    host_context = int(gdb.parse_and_eval('$r14'))
                    payload['live_host_context_r14'] = hex(host_context)
                    payload['live_context_matches_saved'] = host_context == self.context
                    payload['live_host_memory_rbx'] = hex(int(gdb.parse_and_eval('$rbx')))
                    payload['live_context_gpr3'] = hex(reg(host_context, 3))
                    host_pc = int(gdb.parse_and_eval('$pc'))
                    payload['host_pc_after_return'] = hex(host_pc)
                    payload['host_symbol_after_return'] = gdb.execute(
                        'info symbol $pc', to_string=True).strip()
                    payload['host_instructions_after_return'] = gdb.execute(
                        'x/10i $pc', to_string=True).splitlines()
                    if not context_r3_watch_installed and reg(self.context, 3) != 0:
                        ContextR3WriteWatch(
                            self.context, self.memory_base, self.call_index,
                            self.caller, reg(self.context, 3))
                        context_r3_watch_installed = True
                        emit('P1_CONTEXT_R3_WATCH_ARMED', {
                            'source_call_index': self.call_index,
                            'caller_lr': hex(self.caller),
                            'context_pointer': hex(self.context),
                            'r3_before_watch': hex(reg(self.context, 3)),
                            'thread_global_num': (gdb.selected_thread().global_num
                                                  if gdb.selected_thread() else None),
                            'guest_memory_modified_by_probe': False,
                        })
                except (gdb.error, OSError, OverflowError, ValueError) as exc:
                    payload['live_context_probe_error'] = str(exc)
            emit('P1_WORKER_GATE_RETURN', payload)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_WORKER_GATE_RETURN_ERROR function=%s error=%s' %
                  (self.symbol, exc))
        return False

class WorkerGateProbe(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)
        self.enabled = False
        worker_gate_breakpoints.append(self)

    def stop(self):
        if state2_index == 0 or controller_base is None:
            return False
        try:
            context, base = context_base()
            snapshot = action_input_snapshot(base)
            if snapshot is None or not snapshot['active']:
                return False
            mask = ((int(snapshot['buttons'], 16)
                     | int(snapshot['previous'], 16)
                     | int(snapshot['host_buttons'], 16)) & 0x1010)
            button = 'Start' if mask & 0x10 else 'A' if mask & 0x1000 else None
            if button is None:
                return False
            fingerprint = tuple(snapshot[field] for field in
                                ('buttons', 'host_buttons', 'previous',
                                 'start_edge', 'a_edge'))
            worker_gate_hits[self.symbol] += 1
            args = [reg(context, index) for index in range(3, 11)]
            caller = guest_lr(context)
            receiver_words_before = safe_words(base, args[0], 8)
            receiver_queue_before = app_event_queue_snapshot(base, args[0])
            second_argument_words_before = safe_words(base, args[1], 8)
            stack_r1 = reg(context, 1)
            capture_call_stack = (self.symbol == 'sub_822E1910'
                                  and caller == 0x822fdf88)
            sample_key = (fingerprint, caller, args[0])
            if sample_key in worker_gate_seen[self.symbol][button]:
                return False
            caller_samples = sum(
                1 for _, sampled_caller, _ in worker_gate_seen[self.symbol][button]
                if sampled_caller == caller)
            if caller_samples >= worker_gate_sample_limit:
                return False
            worker_gate_seen[self.symbol][button].add(sample_key)
            worker_gate_calls[self.symbol] += 1
            call_index = worker_gate_calls[self.symbol]
            payload = {
                'function': self.symbol, 'call_index': call_index,
                'button': button, 'caller_lr': hex(caller),
                'args_r3_r10': [hex(value) for value in args],
                'receiver_words_before': receiver_words_before,
                'receiver_queue_before': receiver_queue_before,
                'second_argument_words_before': second_argument_words_before,
                'input_fingerprint': list(fingerprint),
                'input': snapshot,
                'last_state2_index_seen': state2_index,
                'guest_memory_modified_by_probe': False,
            }
            if stack_r1:
                payload['guest_stack_r1'] = hex(stack_r1)
                payload['guest_stack_words_before'] = safe_words(base, stack_r1, 8)
            if capture_call_stack:
                payload['host_backtrace_before'] = gdb.execute(
                    'bt 12', to_string=True).splitlines()
            emit('P1_WORKER_GATE_CALL', payload)
            WorkerGateReturn(gdb.newest_frame(), context, self.symbol,
                             call_index, args, snapshot, caller, base,
                             receiver_words_before, receiver_queue_before,
                             second_argument_words_before, stack_r1,
                             capture_call_stack)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_WORKER_GATE_CALL_ERROR function=%s error=%s' %
                  (self.symbol, exc))
        return False

class FrontendDispatchReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, call_index, button, caller, args,
                 snapshot, setup_state_before, scene_field_before):
        super().__init__(frame, internal=True)
        self.context, self.base = context, base
        self.call_index, self.button, self.caller = call_index, button, caller
        self.args, self.snapshot = args, snapshot
        self.setup_state_before = setup_state_before
        self.scene_field_before = scene_field_before

    def stop(self):
        global dispatch_probe_returns
        try:
            dispatch_probe_returns += 1
            scene = safe_be(self.base, setup_object + 8) if setup_object else None
            scene_field_after = safe_be(self.base, scene + 8) if scene else None
            emit('P1_FRONTEND_DISPATCH_RETURN', {
                'function': 'sub_822FDCE0', 'call_index': self.call_index,
                'button': self.button, 'caller_lr': hex(self.caller),
                'args_r3_r10_at_entry': [hex(value) for value in self.args],
                'return_r3_r10': [hex(reg(self.context, index))
                                  for index in range(3, 11)],
                'input_at_entry': self.snapshot,
                'setup_state_before': self.setup_state_before,
                'setup_state_after': safe_be(self.base, setup_object + 4)
                    if setup_object else None,
                'scene_object_after': hex(scene) if scene else None,
                'scene_gate_before': self.scene_field_before,
                'scene_gate_after': scene_field_after,
                'guest_stack_r1': hex(reg(self.context, 1)),
                'guest_stack_words_after': safe_words(
                    self.base, reg(self.context, 1), 8),
                'guest_memory_modified_by_probe': False,
            })
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_FRONTEND_DISPATCH_RETURN_ERROR call_index=%d error=%s' %
                  (self.call_index, exc))
        return False

class FrontendDispatchProbe(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_822FDCE0', internal=True)

    def stop(self):
        global dispatch_probe_calls
        if controller_object is None or controller_base is None:
            return False
        try:
            context, base = context_base()
            snapshot = action_input_snapshot(base)
            if snapshot is None or not snapshot['active']:
                return False
            mask = ((int(snapshot['buttons'], 16)
                     | int(snapshot['previous'], 16)
                     | int(snapshot['host_buttons'], 16)) & 0x1010)
            button = ('Start' if mask & 0x10 or int(snapshot['start_edge'], 16) & 0x80
                      else 'A' if mask & 0x1000 or int(snapshot['a_edge'], 16) & 0x80
                      else None)
            if button is None:
                return False
            caller = guest_lr(context)
            fingerprint = tuple(snapshot[field] for field in
                                ('buttons', 'host_buttons', 'previous',
                                 'start_edge', 'a_edge'))
            sample_key = (caller, fingerprint)
            if sample_key in dispatch_probe_seen[button]:
                return False
            if len(dispatch_probe_seen[button]) >= dispatch_probe_sample_limit:
                return False
            dispatch_probe_seen[button].add(sample_key)
            dispatch_probe_calls += 1
            call_index = dispatch_probe_calls
            args = [reg(context, index) for index in range(3, 11)]
            stack_r1 = reg(context, 1)
            scene = safe_be(base, setup_object + 8) if setup_object else None
            setup_state = safe_be(base, setup_object + 4) if setup_object else None
            scene_field = safe_be(base, scene + 8) if scene else None
            emit('P1_FRONTEND_DISPATCH_CALL', {
                'function': 'sub_822FDCE0', 'call_index': call_index,
                'button': button, 'caller_lr': hex(caller),
                'args_r3_r10': [hex(value) for value in args],
                'input_fingerprint': list(fingerprint), 'input': snapshot,
                'state2_index': state2_index, 'state2_active': state2_active,
                'setup_state': setup_state,
                'setup_object': hex(setup_object) if setup_object else None,
                'scene_object': hex(scene) if scene else None,
                'scene_gate_value_plus_8': scene_field,
                'guest_stack_r1': hex(stack_r1),
                'guest_stack_words_before': safe_words(base, stack_r1, 8),
                'guest_memory_modified_by_probe': False,
            })
            FrontendDispatchReturn(gdb.newest_frame(), context, base, call_index,
                                  button, caller, args, snapshot, setup_state,
                                  scene_field)
        except (gdb.error, OSError, OverflowError, ValueError) as exc:
            print('P1_FRONTEND_DISPATCH_CALL_ERROR %s' % exc)
        return False

for symbol in action_consumer_symbols:
    ActionConsumer(symbol)
for symbol in worker_gate_symbols:
    WorkerGateProbe(symbol)
FrontendDispatchProbe()

SceneGateMethod('sub_82DD8FF8')
SceneGateMethod('sub_82DD9020')
StartupMemoryFill()
GuiQueueConstructor()
GuiQueueOpen()
MainMenuEventQueue()
MainMenuQueueEnqueue()
GuiQueueDirectAppend()
GuiQueueProcessParent()
emit('P1_MAINMENU_SCENE_GATE_METHOD_BREAKPOINTS_ARMED', {
    'methods': {'0x82dd8ff8': 'clear scene+8 to zero',
                '0x82dd9020': 'set scene+8 to one'},
    'scene_vtable': '0x8211e280',
    'scene_vtable_slots': {'+0x0c': '0x82dd9020', '+0x14': '0x82dd8ff8'},
    'guest_memory_modified_by_probe': False,
})
end

run

python
try:
    context, base = context_base()
    guest = {'context': hex(context), 'memory_base': hex(base),
             'lr': hex(guest_lr(context)),
             'gpr_r3_r10': [hex(reg(context, index)) for index in range(3, 11)]}
except (gdb.error, OSError, OverflowError, ValueError) as exc:
    guest = {'read_error': str(exc)}
try:
    siginfo = gdb.execute('p $_siginfo', to_string=True).strip()
except gdb.error as exc:
    siginfo = str(exc)
emit('P1_STOP_CONTEXT', {
    'host_pc': hex(int(gdb.parse_and_eval('$pc'))),
    'host_symbol': gdb.execute('info symbol $pc', to_string=True).strip(),
    'siginfo': siginfo, 'guest_registers': guest,
    'host_backtrace': gdb.execute('bt 16', to_string=True).strip().splitlines(),
    'guest_memory_modified_by_probe': False,
})
end

python
emit('P1_MAIN_MENU_EVENT_QUEUE_SUMMARY', {
    'process_event_queue_calls': main_menu_queue_process_calls,
    'interfaces': [hex(address) for address in sorted(main_menu_queue_interfaces)],
    'getter_calls': {hex(address): count
                     for address, count in main_menu_queue_getter_calls.items()},
    'active_getter_calls': {hex(address): count
                            for address, count in main_menu_queue_active_getter_calls.items()},
    'enqueue_calls': main_menu_queue_enqueue_calls,
    'enqueue_returns': main_menu_queue_enqueue_returns,
    'direct_append_calls': main_menu_queue_direct_append_calls,
    'direct_append_returns': main_menu_queue_direct_append_returns,
    'process_parent_calls': main_menu_process_parent_calls,
    'process_parent_returns': main_menu_process_parent_returns,
    'constructor_calls': gui_queue_constructor_calls,
    'open_calls': gui_queue_open_calls,
    'guest_memory_modified_by_probe': False,
})
emit('P1_ACTION_CONSUMER_SUMMARY', {
    'calls': action_consumer_calls,
    'returns': action_consumer_returns,
    'active_hits': action_consumer_hits,
    'sampled_receivers_by_button': {
        symbol: {button: [hex(value) for value in sorted(receivers)]
                 for button, receivers in by_button.items()}
        for symbol, by_button in action_consumer_seen.items()
    },
    'symbols': list(action_consumer_symbols),
    'input_filter': 'Start/A mask or corresponding retail edge byte active',
    'guest_memory_modified_by_probe': False,
})
emit('P1_WORKER_GATE_SUMMARY', {
    'calls': worker_gate_calls,
    'returns': worker_gate_returns,
    'active_hits': worker_gate_hits,
    'sampled_input_caller_receiver_by_button': {
        symbol: {button: [
            {'input_fingerprint': list(fingerprint),
             'caller_lr': hex(caller), 'first_argument': hex(first_argument)}
            for fingerprint, caller, first_argument in sorted(samples)]
            for button, samples in by_button.items()}
        for symbol, by_button in worker_gate_seen.items()
    },
    'symbols': list(worker_gate_symbols),
    'per_button_per_caller_unique_fingerprint_receiver_limit': worker_gate_sample_limit,
    'guest_memory_modified_by_probe': False,
})
emit('P1_CONTEXT_R3_WATCH_SUMMARY', {
    'source_function': 'sub_822E1910',
    'armed': context_r3_watch_installed,
    'watchpoints': len(context_r3_watchpoints),
    'guest_memory_modified_by_probe': False,
})
emit('P1_FRONTEND_DISPATCH_SUMMARY', {
    'function': 'sub_822FDCE0',
    'calls': dispatch_probe_calls, 'returns': dispatch_probe_returns,
    'samples_by_button': {button: len(samples)
                          for button, samples in dispatch_probe_seen.items()},
    'sample_limit_per_button': dispatch_probe_sample_limit,
    'guest_memory_modified_by_probe': False,
})
print('P1_V46_SUMMARY counts=%r state2_iterations=%d input_calls=%d '
      'input_completions=%d input_masks=%r elapsed_seconds=%.3f' %
      (counts, state2_index, host_input_calls, host_input_completions,
       host_input_masks, time.monotonic() - started))
try:
    gdb.execute('info threads')
    gdb.execute('thread apply all bt 10')
except gdb.error as exc:
    print('P1_V46_TIMEOUT_BACKTRACE_ERROR %s' % exc)
end
