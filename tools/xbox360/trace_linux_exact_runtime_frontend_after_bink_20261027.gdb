set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
handle SIGSEGV nostop noprint pass
python
import gdb
import hashlib
import os
import signal
import threading
import time
from pathlib import Path

trace_out = os.environ.get(
    'SHIFT_CONTROLLER_TRACE_OUT',
    '/tmp/nfs-shift-p1-exact-runtime-frontend-after-bink-20261027')
gdb.execute('set logging file %s/gdb.log' % trace_out)
gdb.execute('set logging overwrite on')
gdb.execute('set logging enabled on')
gdb.execute('set environment LD_LIBRARY_PATH %s/bin' % trace_out)
gdb.execute('set environment SDL_GAMECONTROLLER_IGNORE_DEVICES 0x045e/0x0b12')
gdb.execute('set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data '
            '--user_data_root=%s/user --cache_root=%s/cache '
            '--gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false' %
            (trace_out, trace_out))

started = time.monotonic()
target_vtable = 0x8212E5B8
controller_object = None
controller_base = None
input_results = {'Start': 0, 'A': 0}
controller_edge_states = {}
state = {
    'bink': 0,
    'wrapper': 0,
    'target': 0,
    'progress': 0,
    'target_seen': False,
    'target_elapsed': None,
    'last_bink_progress': None,
    'scene_calls': 0,
    'scene_returns': 0,
    'child_calls': {'sub_82E2C5A8': 0, 'sub_82E2CD10': 0},
    'child_returns': {'sub_82E2C5A8': 0, 'sub_82E2CD10': 0},
}
scene_state = {}
child_state = {}

def le(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'little')

def be(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'big')

def ctx_base():
    return int(gdb.parse_and_eval('$rdi')), int(gdb.parse_and_eval('$rsi'))

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

class ControllerEdge(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)

    def stop(self):
        try:
            context, base = ctx_base()
            obj = le(context, 4)
            if obj != controller_object:
                return False
            current = be(base + obj + 128, 4)
            previous = be(base + obj + 132, 4)
            start = be(base + obj + 140, 1)
            a_button = be(base + obj + 148, 1)
            snapshot = (current, previous, start, a_button)
            if controller_edge_states.get(self.symbol) != snapshot:
                controller_edge_states[self.symbol] = snapshot
                print('FRONTEND_CONTROLLER_STATE func=%s current=%#06x previous=%#06x '
                      'start=%#04x a=%#04x elapsed=%.3f' %
                      (self.symbol, current, previous, start, a_button,
                       time.monotonic() - started))
        except gdb.error as exc:
            print('FRONTEND_CONTROLLER_STATE_ERROR func=%s error=%s' % (self.symbol, exc))
        return False

class DigitalLookupReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, button, value):
        super().__init__(frame, internal=True)
        self.context, self.button, self.value = context, button, value

    def stop(self):
        try:
            result = le(self.context, 4)
            input_results[self.button] += 1
            if input_results[self.button] <= 6:
                print('RETAIL_INPUT_PREDICATE button=%s byte=%#04x result=%u elapsed=%.3f' %
                      (self.button, self.value, result, time.monotonic() - started))
        except gdb.error as exc:
            print('RETAIL_INPUT_PREDICATE_ERROR button=%s error=%s' %
                  (self.button, exc))
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
            if index == 4:
                button = 'Start'
            elif index == 12:
                button = 'A'
            else:
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
            state.update({'bink': movie, 'wrapper': wrapper,
                          'target': target, 'progress': progress})
            if target == 281 and progress != state['last_bink_progress']:
                state['last_bink_progress'] = progress
                if progress in (1, 60, 120, 180, 240, 270, 280, 281):
                    print('FRONTEND_BINK function=%s wrapper=%#x object=%#x progress=%u target=%u elapsed=%.3f' %
                          (self.symbol, wrapper, movie, progress, target,
                           time.monotonic() - started))
                if progress >= target and not state['target_seen']:
                    state['target_seen'] = True
                    state['target_elapsed'] = time.monotonic() - started
                    print('FRONTEND_BINK_TARGET object=%#x progress=%u target=%u elapsed=%.3f' %
                          (movie, progress, target, state['target_elapsed']))
        except gdb.error as exc:
            print('FRONTEND_BINK_ERROR function=%s error=%s' % (self.symbol, exc))
        return False

class SceneReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, obj, before):
        super().__init__(frame, internal=True)
        self.context, self.base, self.obj, self.before = context, base, obj, before

    def stop(self):
        try:
            result = le(self.context, 4)
            child_word = be(self.base + self.obj + 264, 4)
            counter = be(self.base + self.obj + 356, 4)
            snapshot = (result, child_word, counter, state['progress'], state['target'])
            if scene_state.get(self.obj) != snapshot:
                scene_state[self.obj] = snapshot
                state['scene_returns'] += 1
                print('FRONTEND_SCENE_RETURN object=%#x result=%u child_word_264=%#x counter_before=%u counter_after=%u bink=%u/%u elapsed=%.3f' %
                      (self.obj, result, child_word, self.before, counter,
                       state['progress'], state['target'], time.monotonic() - started))
        except gdb.error as exc:
            print('FRONTEND_SCENE_RETURN_ERROR %s' % exc)
        return False

class SceneUpdate(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82DDC6F0', internal=True)

    def stop(self):
        try:
            context, base = ctx_base()
            obj = le(context, 4)
            state['scene_calls'] += 1
            progress, target = state['progress'], state['target']
            if not state['target_seen'] and not (target == 281 and progress >= 279):
                return False
            child_word = be(base + obj + 264, 4)
            counter = be(base + obj + 356, 4)
            snapshot = (child_word, counter, progress, target)
            if scene_state.get(('entry', obj)) != snapshot:
                scene_state[('entry', obj)] = snapshot
                print('FRONTEND_SCENE_ENTRY object=%#x child_word_264=%#x counter=%u bink=%u/%u elapsed=%.3f' %
                      (obj, child_word, counter, progress, target, time.monotonic() - started))
            SceneReturn(gdb.newest_frame(), context, base, obj, counter)
        except gdb.error as exc:
            print('FRONTEND_SCENE_ENTRY_ERROR %s' % exc)
        return False

class ChildReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, context, base, symbol, obj, before):
        super().__init__(frame, internal=True)
        self.context, self.base, self.symbol, self.obj, self.before = context, base, symbol, obj, before

    def stop(self):
        try:
            result = le(self.context, 4)
            fields = tuple(be(self.base + self.obj + off, 4) for off in (0, 4, 8, 12))
            snapshot = (result, fields, state['progress'], state['target'])
            key = (self.symbol, self.obj)
            if child_state.get(key) != snapshot:
                child_state[key] = snapshot
                state['child_returns'][self.symbol] += 1
                print('FRONTEND_CHILD_RETURN function=%s object=%#x result=%u fields=%r bink=%u/%u elapsed=%.3f' %
                      (self.symbol, self.obj, result, fields, state['progress'], state['target'],
                       time.monotonic() - started))
        except gdb.error as exc:
            print('FRONTEND_CHILD_RETURN_ERROR function=%s error=%s' % (self.symbol, exc))
        return False

class ChildUpdate(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)

    def stop(self):
        try:
            context, base = ctx_base()
            obj = le(context, 4)
            if not state['target_seen'] and not (state['target'] == 281 and state['progress'] >= 279):
                return False
            if state['target_elapsed'] is not None and time.monotonic() - started > state['target_elapsed'] + 15:
                return False
            state['child_calls'][self.symbol] += 1
            before = tuple(be(base + obj + off, 4) for off in (0, 4, 8, 12))
            if state['child_calls'][self.symbol] <= 8:
                print('FRONTEND_CHILD_ENTRY function=%s object=%#x fields=%r bink=%u/%u elapsed=%.3f' %
                      (self.symbol, obj, before, state['progress'], state['target'],
                       time.monotonic() - started))
            ChildReturn(gdb.newest_frame(), context, base, self.symbol, obj, before)
        except gdb.error as exc:
            print('FRONTEND_CHILD_ENTRY_ERROR function=%s error=%s' % (self.symbol, exc))
        return False

ControllerReady()
ControllerEdge('sub_82308E60')
ControllerEdge('sub_8230CD00')
DigitalLookup()
BinkProgress('sub_82679C50')
BinkProgress('sub_82679510')
SceneUpdate()
ChildUpdate('sub_82E2C5A8')
ChildUpdate('sub_82E2CD10')

def bounded_interrupt():
    gdb.post_event(lambda: gdb.execute('interrupt'))

timer = threading.Timer(160.0, bounded_interrupt)
timer.daemon = True
timer.start()
end

run
python
pid = gdb.selected_inferior().pid
try:
    lines = [line for line in Path('/proc/%d/maps' % pid).read_text().splitlines()
             if 'librexruntime.so' in line or 'librexgpu-shift' in line]
    for path in sorted({line.split()[-1] for line in lines}):
        print('FRONTEND_MAPPED_LIBRARY path=%s sha256=%s' %
              (path, hashlib.sha256(Path(path).read_bytes()).hexdigest()))
except Exception as exc:
    print('FRONTEND_MAPPED_LIBRARY_ERROR %s' % exc)
print('FRONTEND_TRACE_SUMMARY controller=%s bink=%#x progress=%u/%u target_seen=%s target_elapsed=%r scene_calls=%d scene_returns=%d child_calls=%r child_returns=%r input_predicate_counts=%r pid=%s' %
      (hex(controller_object) if controller_object else None, state['bink'], state['progress'],
       state['target'], state['target_seen'], state['target_elapsed'], state['scene_calls'],
       state['scene_returns'], state['child_calls'], state['child_returns'], input_results, pid))
print('FRONTEND_THREAD_SNAPSHOT_BEGIN')
gdb.execute('info threads')
gdb.execute('thread apply all bt 8')
print('FRONTEND_THREAD_SNAPSHOT_END')
if pid:
    try:
        gdb.execute('detach')
        os.kill(pid, signal.SIGINT)
        print('FRONTEND_TRACE sent host SIGINT pid=%d' % pid)
    except ProcessLookupError:
        print('FRONTEND_TRACE host already exited pid=%d' % pid)
end
quit
