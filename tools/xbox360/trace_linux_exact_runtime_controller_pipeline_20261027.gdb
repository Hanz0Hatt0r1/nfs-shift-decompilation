set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set debuginfod enabled off
set logging file /tmp/nfs-shift-p1-exact-runtime-controller-pipeline-20261027/gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-exact-runtime-controller-pipeline-20261027/bin
set environment SDL_GAMECONTROLLER_IGNORE_DEVICES 0x045e/0x0b12

python
import gdb
import os
import signal
import threading
import time

target_object = 0xBCAEB260
start_time = time.monotonic()
hit_counts = {}
logged_states = set()
host_input_samples = 0
host_button_counts = {}
last_host_buttons = None
input_getstate_breakpoint = None
input_getstate_calls = 0
xam_entry_breakpoint = None
xam_entry_calls = 0
controller_returns = 0
last_guest_state = None

def read_be(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'big')

def read_le(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'little')

def sample_guest_object():
    ctx = int(gdb.parse_and_eval('$rdi'))
    base = int(gdb.parse_and_eval('$rsi'))
    obj = read_le(ctx, 4)  # PPCContext.r3 is host memory; guest fields are big-endian.
    if obj != target_object:
        return None
    current = read_be(base + obj + 128, 4)
    previous = read_be(base + obj + 132, 4)
    return base, obj, current, previous

def install_input_system_breakpoint():
    global input_getstate_breakpoint, xam_entry_breakpoint
    if input_getstate_breakpoint is not None or xam_entry_breakpoint is not None:
        return
    pid = gdb.selected_inferior().pid
    with open('/proc/%d/maps' % pid, encoding='ascii') as maps:
        for line in maps:
            fields = line.rstrip().split(None, 5)
            if len(fields) == 6 and fields[2] == '00000000' and fields[5].endswith('/librexruntime.so'):
                load_bias = int(fields[0].split('-', 1)[0], 16)
                input_address = load_bias + 0x293260  # Exact runtime SHA 6c56ca97….
                xam_address = load_bias + 0x430540
                input_getstate_breakpoint = InputSystemGetState('*%#x' % input_address)
                xam_entry_breakpoint = XamInputEntry('*%#x' % xam_address)
                print('HOST_INPUT_BREAKPOINT input=%#x xam=%#x load_bias=%#x runtime=%s' %
                      (input_address, xam_address, load_bias, fields[5]))
                return
    print('HOST_INPUT_BREAKPOINT_ERROR librexruntime.so mapping not found')

class ControllerMethod(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)

    def stop(self):
        hit_counts[self.symbol] = hit_counts.get(self.symbol, 0) + 1
        count = hit_counts[self.symbol]
        install_input_system_breakpoint()
        sample = sample_guest_object()
        if sample:
            base, obj, current, previous = sample
            state = (self.symbol, current, previous)
            if state not in logged_states:
                logged_states.add(state)
                print('CONTROLLER_STATE elapsed=%.3f func=%s hit=%d object=%#x '
                      'current=%#06x previous=%#06x edge=%#06x' %
                      (time.monotonic() - start_time, self.symbol, count,
                       obj, current, previous, current ^ previous))
        if self.symbol == 'sub_82308E60':
            if count <= 5 or count in (100, 500, 1000):
                print('CONTROLLER_UPDATE elapsed=%.3f hit=%d object=%s' %
                      (time.monotonic() - start_time, count,
                       'target' if sample else 'other'))
            elapsed = time.monotonic() - start_time
            if sample and 50.0 <= elapsed <= 118.0 and count % 4 == 1:
                ControllerReturn(gdb.newest_frame(), sample[1], sample[0])
        return False

class ControllerReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, obj, base):
        super().__init__(frame, internal=True)
        self.obj = obj
        self.base = base

    def stop(self):
        global last_guest_state, controller_returns
        try:
            controller_returns += 1
            current = read_be(self.base + self.obj + 128, 4)
            previous = read_be(self.base + self.obj + 132, 4)
            edges = bytes(gdb.selected_inferior().read_memory(self.base + self.obj + 140, 25))
            state = (current, previous, edges)
            if state != last_guest_state:
                print('CONTROLLER_RETURN elapsed=%.3f object=%#x current=%#06x '
                      'previous=%#06x edge_bytes=%s' %
                      (time.monotonic() - start_time, self.obj, current,
                       previous, edges.hex()))
                last_guest_state = state
        except gdb.error as exc:
            print('CONTROLLER_RETURN_READ_ERROR %s' % exc)
        return False

class HostInputReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, user, state_ptr):
        super().__init__(frame, internal=True)
        self.user = user
        self.state_ptr = state_ptr

    def stop(self):
        global host_input_samples, last_host_buttons
        try:
            status = int(gdb.parse_and_eval('$eax'))
            raw = bytes(gdb.selected_inferior().read_memory(self.state_ptr, 16))
            packet = int.from_bytes(raw[0:4], 'big')
            buttons = int.from_bytes(raw[4:6], 'big')
            host_input_samples += 1
            host_button_counts[buttons] = host_button_counts.get(buttons, 0) + 1
            if buttons != last_host_buttons:
                print('HOST_INPUT_STATE elapsed=%.3f user=%d status=%#x packet=%d '
                      'buttons=%#06x raw=%s' %
                      (time.monotonic() - start_time, self.user, status,
                       packet, buttons, raw.hex()))
                last_host_buttons = buttons
        except gdb.error as exc:
            print('HOST_INPUT_STATE_READ_ERROR %s' % exc)
        return False

class InputSystemGetState(gdb.Breakpoint):
    def __init__(self, spec):
        super().__init__(spec, internal=True)

    def stop(self):
        global input_getstate_calls
        user = int(gdb.parse_and_eval('$esi')) & 0xffffffff
        state_ptr = int(gdb.parse_and_eval('$rdx'))
        input_getstate_calls += 1
        if input_getstate_calls <= 8:
            print('HOST_INPUT_CALL hit=%d user=%d state=%#x' %
                  (input_getstate_calls, user, state_ptr))
        elapsed = time.monotonic() - start_time
        if user == 0 and state_ptr and 5.0 <= elapsed <= 115.0:
            HostInputReturn(gdb.newest_frame(), user, state_ptr)
        return False

InputSystemGetState.samples = 0

class XamInputEntry(gdb.Breakpoint):
    def __init__(self, spec):
        super().__init__(spec, internal=True)

    def stop(self):
        global xam_entry_calls
        xam_entry_calls += 1
        if xam_entry_calls <= 8:
            user = int(gdb.parse_and_eval('$edi')) & 0xffffffff
            flags = int(gdb.parse_and_eval('$esi')) & 0xffffffff
            state = int(gdb.parse_and_eval('$rdx'))
            print('XAM_INPUT_ENTRY hit=%d user=%d flags=%#x state=%#x' %
                  (xam_entry_calls, user, flags, state))
        return False

for symbol in ('sub_82308E60', 'sub_8230CD00', 'sub_8230D398', 'sub_828B22B8'):
    ControllerMethod(symbol)

class InputSummary(gdb.Command):
    def __init__(self):
        super().__init__('retail-input-summary', gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        print('RETAIL_INPUT_COUNTS xam_entries=%d host_getstate_calls=%d '
              'host_completed=%d button_masks=%r controller_returns=%d' %
              (xam_entry_calls, input_getstate_calls, host_input_samples,
               host_button_counts, controller_returns))

InputSummary()

def bounded_interrupt():
    gdb.post_event(lambda: gdb.execute('interrupt'))

def arm_interrupt(seconds):
    timer = threading.Timer(seconds, bounded_interrupt)
    timer.daemon = True
    timer.start()
    return timer

arm_interrupt(225.0)
end

set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-exact-runtime-controller-pipeline-20261027/user --cache_root=/tmp/nfs-shift-p1-exact-runtime-controller-pipeline-20261027/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
retail-input-summary
python
print('CONTROLLER_PIPELINE_SUMMARY ' + repr(hit_counts))
inferior_pid = gdb.selected_inferior().pid
print('CONTROLLER_PIPELINE_STOP pid=%s' % inferior_pid)
end
detach
python
if inferior_pid:
    try:
        os.kill(inferior_pid, signal.SIGINT)
        print('sent SIGINT to bounded inferior pid=%d' % inferior_pid)
    except ProcessLookupError:
        print('inferior already exited pid=%d' % inferior_pid)
end
