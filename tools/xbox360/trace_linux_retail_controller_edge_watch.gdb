set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set can-use-hw-watchpoints 1
set logging file /tmp/nfs-shift-p1-controller-edge-watch-20261026/gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-p2-scratch-linux-20261026/bin
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
watchpoints = {}
xam_entry_hits = 0
host_getstate_hits = 0
host_getstate_samples = 0
host_masks = {}
last_host_mask = None

def read_be(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'big')

def read_le(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'little')

def target_sample():
    ctx = int(gdb.parse_and_eval('$rdi'))
    base = int(gdb.parse_and_eval('$rsi'))
    obj = read_le(ctx, 4)
    if obj != target_object:
        return None
    current = read_be(base + obj + 128, 4)
    previous = read_be(base + obj + 132, 4)
    return base, obj, current, previous

class EdgeByteWatch(gdb.Breakpoint):
    def __init__(self, base, obj, offset, button):
        self.base = base
        self.obj = obj
        self.offset = offset
        self.button = button
        self.guest_address = obj + offset
        self.host_address = base + self.guest_address
        self.previous = read_be(self.host_address, 1)
        super().__init__('*(unsigned char*)0x%x' % self.host_address,
                         type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE,
                         internal=True)

    def stop(self):
        current_byte = read_be(self.host_address, 1)
        if current_byte != self.previous:
            current_mask = read_be(self.base + self.obj + 128, 4)
            previous_mask = read_be(self.base + self.obj + 132, 4)
            pc = gdb.selected_frame().pc()
            print('EDGE_BYTE_WRITE button=%s guest=%#x host=%#x old=%#04x new=%#04x '
                  'current=%#06x previous=%#06x pc=%#x' %
                  (self.button, self.guest_address, self.host_address,
                   self.previous, current_byte, current_mask, previous_mask, pc))
            try:
                print(gdb.execute('x/i $pc', to_string=True).strip())
                print(gdb.execute('bt 5', to_string=True).strip())
            except gdb.error as exc:
                print('EDGE_BYTE_CONTEXT_ERROR %s' % exc)
            self.previous = current_byte
            self.enabled = False
        return False

def install_edge_watchpoints(sample):
    base, obj, current, previous = sample
    changed = current ^ previous
    for mask, offset, button in ((0x0010, 140, 'Start'), (0x1000, 148, 'A')):
        key = (obj, offset)
        if changed & mask and key not in watchpoints:
            try:
                watchpoints[key] = EdgeByteWatch(base, obj, offset, button)
                print('EDGE_BYTE_WATCH_ARMED button=%s guest=%#x initial=%#04x current=%#06x previous=%#06x' %
                      (button, obj + offset, read_be(base + obj + offset, 1), current, previous))
            except gdb.error as exc:
                print('EDGE_BYTE_WATCH_FAILED button=%s guest=%#x error=%s' %
                      (button, obj + offset, exc))

class XamInputEntry(gdb.Breakpoint):
    def __init__(self, spec):
        super().__init__(spec, internal=True)

    def stop(self):
        global xam_entry_hits
        xam_entry_hits += 1
        return False

class HostInputReturn(gdb.FinishBreakpoint):
    def __init__(self, frame, user, state_ptr):
        super().__init__(frame, internal=True)
        self.user = user
        self.state_ptr = state_ptr

    def stop(self):
        global host_getstate_samples, last_host_mask
        status = int(gdb.parse_and_eval('$eax'))
        raw = bytes(gdb.selected_inferior().read_memory(self.state_ptr, 16))
        packet = int.from_bytes(raw[:4], 'big')
        buttons = int.from_bytes(raw[4:6], 'big')
        host_getstate_samples += 1
        host_masks[buttons] = host_masks.get(buttons, 0) + 1
        if buttons != last_host_mask:
            print('HOST_INPUT_STATE elapsed=%.3f user=%d status=%#x packet=%d buttons=%#06x' %
                  (time.monotonic() - start_time, self.user, status, packet, buttons))
            last_host_mask = buttons
        return False

class InputSystemGetState(gdb.Breakpoint):
    def __init__(self, spec):
        super().__init__(spec, internal=True)

    def stop(self):
        global host_getstate_hits
        host_getstate_hits += 1
        user = int(gdb.parse_and_eval('$esi')) & 0xffffffff
        state_ptr = int(gdb.parse_and_eval('$rdx'))
        elapsed = time.monotonic() - start_time
        if user == 0 and state_ptr and 5 <= elapsed <= 55:
            if host_getstate_hits % 4 == 0:
                HostInputReturn(gdb.newest_frame(), user, state_ptr)
        return False

class RetailControllerMethod(gdb.Breakpoint):
    def __init__(self, symbol):
        self.symbol = symbol
        super().__init__(symbol, internal=True)

    def stop(self):
        hit_counts[self.symbol] = hit_counts.get(self.symbol, 0) + 1
        sample = target_sample()
        if sample:
            base, obj, current, previous = sample
            state = (self.symbol, current, previous)
            if state not in seen_states:
                seen_states.add(state)
                print('RETAIL_CONTROLLER_STATE elapsed=%.3f func=%s hit=%d object=%#x current=%#06x previous=%#06x edge=%#06x' %
                      (time.monotonic() - start_time, self.symbol,
                       hit_counts[self.symbol], obj, current, previous, current ^ previous))
            if self.symbol == 'sub_8230CD00':
                install_edge_watchpoints(sample)
        return False

class RetailInputSummary(gdb.Command):
    def __init__(self):
        super().__init__('retail-edge-summary', gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        print('RETAIL_EDGE_SUMMARY xam_entries=%d host_getstate_calls=%d host_samples=%d masks=%r functions=%r watchpoints=%r' %
              (xam_entry_hits, host_getstate_hits, host_getstate_samples,
               host_masks, hit_counts,
               {key: value.enabled for key, value in watchpoints.items()}))

seen_states = set()

def install_runtime_breakpoints():
    global install_runtime_breakpoints_done
    if install_runtime_breakpoints_done:
        return
    pid = gdb.selected_inferior().pid
    with open('/proc/%d/maps' % pid, encoding='ascii') as maps:
        for line in maps:
            fields = line.rstrip().split(None, 5)
            if len(fields) == 6 and fields[2] == '00000000' and fields[5].endswith('/librexruntime.so'):
                bias = int(fields[0].split('-', 1)[0], 16)
                XamInputEntry('*%#x' % (bias + 0x4a3060))
                InputSystemGetState('*%#x' % (bias + 0x305da0))
                install_runtime_breakpoints_done = True
                print('RUNTIME_BREAKPOINTS load_bias=%#x path=%s' % (bias, fields[5]))
                return
    print('RUNTIME_BREAKPOINTS_ERROR librexruntime.so mapping not found')

install_runtime_breakpoints_done = False

for symbol in ('sub_82308E60', 'sub_8230CD00', 'sub_8230D398'):
    RetailControllerMethod(symbol)

class RuntimeLoaded(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82308E60', internal=True)

    def stop(self):
        install_runtime_breakpoints()
        return False

RuntimeLoaded()
RetailInputSummary()

def bounded_interrupt():
    gdb.post_event(lambda: gdb.execute('interrupt'))

timer = threading.Timer(60.0, bounded_interrupt)
timer.daemon = True
timer.start()
end

set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-controller-edge-watch-20261026/user --cache_root=/tmp/nfs-shift-p1-controller-edge-watch-20261026/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
retail-edge-summary
python
import os
import signal
pid = gdb.selected_inferior().pid
print('RETAIL_EDGE_STOP pid=%s' % pid)
end
detach
python
if pid:
    try:
        os.kill(pid, signal.SIGINT)
        print('sent SIGINT to bounded inferior pid=%d' % pid)
    except ProcessLookupError:
        print('inferior already exited pid=%d' % pid)
end
