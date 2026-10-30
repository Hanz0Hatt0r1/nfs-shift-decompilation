set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
handle SIGSEGV nostop noprint pass
python
import gdb
import hashlib
import os
import re
import signal
import threading
import time
from pathlib import Path

trace_out = os.environ.get(
    'SHIFT_CONTROLLER_TRACE_OUT',
    '/tmp/nfs-shift-p1-exact-runtime-post-bink-wait-20261027')
gdb.execute('set logging file %s/gdb.log' % trace_out)
gdb.execute('set logging overwrite on')
gdb.execute('set logging enabled on')
gdb.execute('set environment LD_LIBRARY_PATH %s/bin' % trace_out)
gdb.execute('set environment SDL_GAMECONTROLLER_IGNORE_DEVICES 0x045e/0x0b12')

started = time.monotonic()
target_vtable = 0x8212E5B8
controller_object = None
controller_base = None
last_controller_state = None
host_counts = {'xam': 0, 'getstate': 0}
host_buttons = {}
last_host_buttons = None
input_results = {'Start': 0, 'A': 0}
state = {
    'bink': 0,
    'wrapper': 0,
    'target': 0,
    'progress': 0,
    'target_seen': False,
    'target_elapsed': None,
    'bink_cycles': 0,
    'cycle_terminal_seen': False,
    'last_bink_progress': None,
    'scene_calls': 0,
    'scene_samples': 0,
    'last_scene_time': None,
    'last_scene_child': None,
    'last_scene_counter': None,
    'queue_calls': 0,
    'queue_samples': 0,
    'queue_after_bink': False,
    'queue_last': None,
    'wait_word_watchpoint': None,
    'wait_word_initial': None,
    'wait_word_address': None,
    'last_input_buttons': 0,
    'action_samples': {'Start': 0, 'A': 0},
    'action_returns': {'Start': 0, 'A': 0},
}

def le(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'little')

def be(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'big')

def ctx_base():
    return int(gdb.parse_and_eval('$rdi')), int(gdb.parse_and_eval('$rsi'))

class HostInputReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, user, state_ptr):
        super().__init__(frame, internal=True)
        self.user, self.state_ptr = user, state_ptr

    def stop(self):
        global last_host_buttons
        try:
            status = int(gdb.parse_and_eval('$eax'))
            raw = bytes(gdb.selected_inferior().read_memory(self.state_ptr, 16))
            packet = int.from_bytes(raw[:4], 'big')
            buttons = int.from_bytes(raw[4:6], 'big')
            if self.user == 0:
                state['last_input_buttons'] = buttons
            host_buttons[buttons] = host_buttons.get(buttons, 0) + 1
            if buttons != last_host_buttons:
                print('HOST_INPUT_STATE user=%d status=%#x packet=%d buttons=%#06x raw=%s elapsed=%.3f' %
                      (self.user, status, packet, buttons, raw.hex(), time.monotonic() - started))
                last_host_buttons = buttons
        except gdb.error as exc:
            print('HOST_INPUT_STATE_ERROR user=%d error=%s' % (self.user, exc))
        return False

class InputSystemGetState(gdb.Breakpoint):
    def __init__(self, address):
        super().__init__('*%#x' % address, internal=True)

    def stop(self):
        try:
            user = int(gdb.parse_and_eval('$esi')) & 0xffffffff
            state_ptr = int(gdb.parse_and_eval('$rdx'))
            host_counts['getstate'] += 1
            if user == 0 and state_ptr:
                HostInputReturn(gdb.newest_frame(), user, state_ptr)
        except gdb.error as exc:
            print('INPUT_SYSTEM_ENTRY_ERROR %s' % exc)
        return False

class XamInputEntry(gdb.Breakpoint):
    def __init__(self, address):
        super().__init__('*%#x' % address, internal=True)

    def stop(self):
        try:
            user = int(gdb.parse_and_eval('$edi')) & 0xffffffff
            host_counts['xam'] += 1
            if host_counts['xam'] <= 4 or host_counts['xam'] % 250 == 0:
                print('XAM_INPUT_ENTRY hit=%d user=%d flags=%#x elapsed=%.3f' %
                      (host_counts['xam'], user,
                       int(gdb.parse_and_eval('$esi')) & 0xffffffff,
                       time.monotonic() - started))
        except gdb.error as exc:
            print('XAM_INPUT_ENTRY_ERROR %s' % exc)
        return False

class ControllerReady(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82308E60', internal=True)

    def stop(self):
        global controller_object, controller_base
        try:
            context, base = ctx_base()
            obj = le(context, 4)
            vtable = be(base + obj, 4) if obj else 0
            if obj and vtable == target_vtable and controller_object is None:
                controller_object, controller_base = obj, base
                print('CONTROLLER_UPDATE elapsed=%.3f object=target guest_object=%#x vtable=%#x' %
                      (time.monotonic() - started, obj, vtable))
        except gdb.error as exc:
            print('CONTROLLER_UPDATE_ERROR %s' % exc)
        return False

class ControllerEdges(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_8230CD00', internal=True)

    def stop(self):
        global last_controller_state
        try:
            if controller_object is None or controller_base is None:
                return False
            context, base = ctx_base()
            obj = le(context, 4)
            if obj != controller_object:
                return False
            current = be(base + obj + 128, 4)
            previous = be(base + obj + 132, 4)
            edge = current ^ previous
            sample = (current, previous, edge)
            if sample != last_controller_state:
                last_controller_state = sample
                print('RETAIL_CONTROLLER_STATE object=%#x current=%#06x previous=%#06x edge=%#06x elapsed=%.3f' %
                      (obj, current, previous, edge, time.monotonic() - started))
        except gdb.error as exc:
            print('RETAIL_CONTROLLER_STATE_ERROR %s' % exc)
        return False

class DigitalLookupReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, button, value):
        super().__init__(frame, internal=True)
        self.context, self.button, self.value = context, button, value

    def stop(self):
        try:
            result = le(self.context, 4)
            input_results[self.button] += 1
            if input_results[self.button] <= 8:
                caller_lr = le(self.context + 256, 8) & 0xffffffff
                print('RETAIL_INPUT_PREDICATE button=%s byte=%#04x result=%u caller_lr=%#x elapsed=%.3f' %
                      (self.button, self.value, result, caller_lr, time.monotonic() - started))
        except gdb.error as exc:
            print('RETAIL_INPUT_PREDICATE_ERROR button=%s error=%s' % (self.button, exc))
        return False

class DigitalLookup(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82311290', internal=True)

    def stop(self):
        try:
            if controller_object is None or controller_base is None:
                return False
            context = int(gdb.parse_and_eval('$rdi'))
            table = le(context, 4)
            index = le(context + 32, 4)
            button = 'Start' if index == 4 else 'A' if index == 12 else None
            if button is None:
                return False
            address = (table + index + 20) & 0xffffffff
            if address not in (controller_object + 140, controller_object + 148):
                return False
            value = be(controller_base + address, 1)
            if value & 0x80:
                DigitalLookupReturn(gdb.newest_frame(), context, button, value)
        except gdb.error as exc:
            print('RETAIL_INPUT_PREDICATE_ENTRY_ERROR %s' % exc)
        return False

class InputActionReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, obj, button, before):
        super().__init__(frame, internal=True)
        self.context, self.base, self.obj = context, base, obj
        self.button, self.before = button, before

    def stop(self):
        try:
            result = le(self.context, 4)
            after = tuple(be(self.base + self.obj + offset, 4)
                          for offset in (8, 28, 32, 56, 60, 64, 68))
            state['action_returns'][self.button] += 1
            print('RETAIL_INPUT_ACTION_RETURN button=%s object=%#x result=%u before=%s after=%s elapsed=%.3f' %
                  (self.button, self.obj, result, self.before, after,
                   time.monotonic() - started))
        except gdb.error as exc:
            print('RETAIL_INPUT_ACTION_RETURN_ERROR button=%s error=%s' %
                  (self.button, exc))
        return False

class InputActionManager(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_8230A8E0', internal=True)

    def stop(self):
        if not state['target_seen'] and state['bink_cycles'] < 2:
            return False
        buttons = state['last_input_buttons']
        button = 'Start' if buttons & 0x0010 else 'A' if buttons & 0x1000 else None
        if button is None or state['action_samples'][button] >= 3:
            return False
        try:
            context, base = ctx_base()
            obj = le(context, 4)
            before = tuple(be(base + obj + offset, 4)
                           for offset in (8, 28, 32, 56, 60, 64, 68))
            state['action_samples'][button] += 1
            print('RETAIL_INPUT_ACTION_ENTRY button=%s object=%#x fields=%s elapsed=%.3f' %
                  (button, obj, before, time.monotonic() - started))
            InputActionReturn(gdb.newest_frame(), context, base, obj, button, before)
        except gdb.error as exc:
            print('RETAIL_INPUT_ACTION_ENTRY_ERROR button=%s error=%s' %
                  (button, exc))
        return False

class BinkProgress(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)

    def stop(self):
        try:
            context, base = ctx_base()
            wrapper = le(context, 4)
            movie = be(base + wrapper + 4, 4) if wrapper else 0
            if not movie:
                return False
            target = be(base + movie + 8, 4)
            progress = be(base + movie + 12, 4)
            previous_progress = state['last_bink_progress']
            if (previous_progress is not None and previous_progress >= target - 1 and
                    progress < 5):
                state['bink_cycles'] += 1
                state['target_seen'] = False
                state['target_elapsed'] = None
                state['cycle_terminal_seen'] = False
                state['queue_after_bink'] = False
                state['queue_last'] = None
                state['scene_samples'] = 0
                print('FRONTEND_BINK_CYCLE_RESTART cycle=%d previous=%u next=%u elapsed=%.3f' %
                      (state['bink_cycles'], previous_progress, progress,
                       time.monotonic() - started))
            state.update({'bink': movie, 'wrapper': wrapper, 'target': target, 'progress': progress})
            if target == 281 and progress != state['last_bink_progress']:
                state['last_bink_progress'] = progress
                if progress in (1, 60, 120, 180, 240, 270, 280, 281):
                    print('FRONTEND_BINK function=%s object=%#x progress=%u target=%u elapsed=%.3f' %
                          (self.symbol, movie, progress, target, time.monotonic() - started))
                if progress >= target - 1 and not state['cycle_terminal_seen']:
                    state['cycle_terminal_seen'] = True
                    state['target_seen'] = True
                    state['target_elapsed'] = time.monotonic() - started
                    print('FRONTEND_BINK_TERMINAL_EDGE object=%#x progress=%u target=%u elapsed=%.3f' %
                          (movie, progress, target, state['target_elapsed']))
                    if 'queue_counter_bp' in globals():
                        queue_counter_bp.enabled = True
        except gdb.error as exc:
            print('FRONTEND_BINK_ERROR function=%s error=%s' % (self.symbol, exc))
        return False

class SceneUpdate(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82DDC6F0', internal=True)

    def stop(self):
        try:
            context, base = ctx_base()
            obj = le(context, 4)
            state['scene_calls'] += 1
            if not state['target_seen']:
                return False
            child = be(base + obj + 264, 4)
            counter = be(base + obj + 356, 4)
            state['last_scene_time'] = time.monotonic() - started
            state['last_scene_child'] = child
            state['last_scene_counter'] = counter
            if (state['scene_samples'] < 12 or child != state.get('scene_first_child') or
                    counter % 60 == 0):
                state['scene_samples'] += 1
                state['scene_first_child'] = child
                print('FRONTEND_SCENE_AFTER_BINK object=%#x child_word_264=%#x counter=%u bink=%u/%u elapsed=%.3f' %
                      (obj, child, counter, state['progress'], state['target'],
                       time.monotonic() - started))
        except gdb.error as exc:
            print('FRONTEND_SCENE_ERROR %s' % exc)
        return False

class RetailQueueWait(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B34A0', internal=True)

    def stop(self):
        try:
            context, base = ctx_base()
            obj = le(context, 4)
            state['queue_calls'] += 1
            if not state['target_seen'] and state['queue_calls'] > 4:
                return False
            now = time.monotonic() - started
            if state['target_seen'] and state['queue_after_bink']:
                return False
            head_pointer = be(base + obj + 10896, 4)
            head = be(base + head_pointer, 4) if head_pointer else 0
            tail = be(base + obj + 10908, 4)
            predicate = be(base + obj + 10941, 1)
            target = le(context + 32, 4)
            item = (obj, head_pointer, head, tail, predicate, target)
            if state['queue_calls'] <= 4 or state['target_seen']:
                state['queue_samples'] += 1
                wait_word = be(base + obj + 11012, 4)
                print('RETAIL_QUEUE_WAIT hit=%d after_bink=%s object=%#x head_pointer=%#x head=%u tail=%u predicate=%#04x target=%u wait_word=%#x elapsed=%.3f' %
                      (state['queue_calls'], state['target_seen'], obj, head_pointer,
                       head, tail, predicate, target, wait_word, now))
                if state['target_seen']:
                    state['queue_after_bink'] = True
                    state['queue_last'] = item
        except gdb.error as exc:
            print('RETAIL_QUEUE_WAIT_ERROR %s' % exc)
        return False

class RetailQueueCounter(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B31A0', internal=True)

    def stop(self):
        if not state['target_seen'] or state['wait_word_watchpoint'] is not None:
            return False
        try:
            context, base = ctx_base()
            obj = le(context, 4)
            args = [le(context + index * 32, 4) for index in range(1, 6)]
            value = be(base + obj + 11012, 4)
            address = base + obj + 11012
            state['wait_word_address'] = address
            state['wait_word_initial'] = value
            print('RETAIL_QUEUE_COUNTER object=%#x vtable=%#x args=%r word=%#x address=%#x elapsed=%.3f' %
                  (obj, be(base + obj, 4), args, value, address, time.monotonic() - started))
            watch_output = gdb.execute(
                'watch -l *(unsigned int*)%#x' % address,
                to_string=True)
            match = re.search(r'(?:Hardware )?[Ww]atchpoint (\d+)', watch_output)
            if not match:
                print('RETAIL_WAIT_WORD_WATCH_ERROR output=%s' % watch_output.strip())
            else:
                number = int(match.group(1))
                state['wait_word_watchpoint'] = number
                print('RETAIL_WAIT_WORD_WATCH address=%#x initial=%#x watchpoint=%d elapsed=%.3f' %
                      (address, value, number, time.monotonic() - started))
                commands = (
                    'commands %d\n'
                    'silent\n'
                    'python\n'
                    'import gdb\n'
                    'address = %#x\n'
                    'raw = bytes(gdb.selected_inferior().read_memory(address, 4))\n'
                    'value = int.from_bytes(raw, "big")\n'
                    'thread = gdb.selected_thread()\n'
                    'print("RETAIL_WAIT_WORD_WRITE address=%%#x value=%%#x thread=%%s" %% (address, value, thread.name if thread else "?"))\n'
                    'if value in (0, 1, 0xffffffff, 0xfffffffe):\n'
                    '    print("RETAIL_WAIT_WORD_WRITER_BACKTRACE value=" + hex(value))\n'
                    '    gdb.execute("bt 8")\n'
                    'end\n'
                    'continue\n'
                    'end' % (number, address))
                gdb.execute(commands)
        except gdb.error as exc:
            print('RETAIL_QUEUE_COUNTER_ERROR %s' % exc)
        self.enabled = False
        return False

class QueuePredicate(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)

    def stop(self):
        try:
            if not state['target_seen']:
                return False
            context, base = ctx_base()
            local = le(context, 4)
            obj = be(base + local, 4)
            byte = be(base + obj + 10941, 1)
            if byte & 0x02 or state.get('last_predicate') != byte:
                state['last_predicate'] = byte
                print('RETAIL_QUEUE_PREDICATE function=%s object=%#x byte=%#04x elapsed=%.3f' %
                      (self.symbol, obj, byte, time.monotonic() - started))
        except gdb.error as exc:
            print('RETAIL_QUEUE_PREDICATE_ERROR function=%s error=%s' % (self.symbol, exc))
        return False

def install_host_input_breakpoints():
    pid = gdb.selected_inferior().pid
    with open('/proc/%d/maps' % pid, encoding='ascii') as maps:
        for line in maps:
            fields = line.rstrip().split(None, 5)
            if len(fields) == 6 and fields[2] == '00000000' and fields[5].endswith('/librexruntime.so'):
                load_bias = int(fields[0].split('-', 1)[0], 16)
                InputSystemGetState(load_bias + 0x293260)
                XamInputEntry(load_bias + 0x430540)
                print('HOST_INPUT_BREAKPOINTS runtime=%s load_bias=%#x getstate=%#x xam=%#x' %
                      (fields[5], load_bias, load_bias + 0x293260, load_bias + 0x430540))
                return
    print('HOST_INPUT_BREAKPOINT_ERROR librexruntime.so mapping not found')

class InstallHostInput(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82308E60', internal=True)
        self.installed = False

    def stop(self):
        if not self.installed:
            self.installed = True
            install_host_input_breakpoints()
        return False

ControllerReady()
InstallHostInput()
ControllerEdges()
DigitalLookup()
BinkProgress('sub_82679C50')
BinkProgress('sub_82679510')
SceneUpdate()
RetailQueueWait()
QueuePredicate('sub_823A0310')
queue_counter_bp = RetailQueueCounter()
queue_counter_bp.enabled = False
InputActionManager()

def bounded_interrupt():
    gdb.post_event(lambda: gdb.execute('interrupt'))

timer = threading.Timer(280.0, bounded_interrupt)
timer.daemon = True
timer.start()
end

set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-exact-runtime-post-bink-wait-20261027/user --cache_root=/tmp/nfs-shift-p1-exact-runtime-post-bink-wait-20261027/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
python
pid = gdb.selected_inferior().pid
try:
    print('POST_BINK_THREAD_SAMPLE_BEGIN')
    gdb.execute('info threads')
    gdb.execute('thread apply all bt 8')
    print('POST_BINK_THREAD_SAMPLE_END')
except Exception as exc:
    print('POST_BINK_THREAD_SAMPLE_ERROR %s' % exc)
try:
    lines = [line for line in Path('/proc/%d/maps' % pid).read_text().splitlines()
             if 'librexruntime.so' in line or 'librexgpu-shift' in line]
    for path in sorted({line.split()[-1] for line in lines}):
        print('POST_BINK_MAPPED_LIBRARY path=%s sha256=%s' %
              (path, hashlib.sha256(Path(path).read_bytes()).hexdigest()))
except Exception as exc:
    print('POST_BINK_MAPPED_LIBRARY_ERROR %s' % exc)
print('POST_BINK_TRACE_SUMMARY controller=%s target_seen=%s target_elapsed=%r bink_cycles=%d bink=%#x progress=%u/%u host_counts=%r host_buttons=%r input_predicates=%r action_samples=%r action_returns=%r scene_calls=%d scene_samples=%d last_scene=%r queue_calls=%d queue_samples=%d queue_after_bink=%s queue_last=%r wait_word_address=%s wait_word_initial=%s wait_word_watchpoint=%s pid=%s' %
      (hex(controller_object) if controller_object else None, state['target_seen'],
       state['target_elapsed'], state['bink_cycles'], state['bink'], state['progress'], state['target'],
       host_counts, host_buttons, input_results, state['action_samples'], state['action_returns'], state['scene_calls'],
       state['scene_samples'], (state['last_scene_time'], state['last_scene_child'],
                                state['last_scene_counter']), state['queue_calls'],
       state['queue_samples'], state['queue_after_bink'], state['queue_last'],
       hex(state['wait_word_address']) if state['wait_word_address'] else None,
       hex(state['wait_word_initial']) if state['wait_word_initial'] is not None else None,
       state['wait_word_watchpoint'], pid))
if pid:
    try:
        gdb.execute('detach')
        os.kill(pid, signal.SIGINT)
        print('POST_BINK_TRACE sent host SIGINT pid=%d' % pid)
    except ProcessLookupError:
        print('POST_BINK_TRACE host already exited pid=%d' % pid)
end
quit
