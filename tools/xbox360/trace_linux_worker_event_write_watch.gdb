set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set logging file /tmp/nfs-shift-p1-worker-event-write-watch-20261026/gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-p2-scratch-linux-20261026/bin
set environment SDL_GAMECONTROLLER_IGNORE_DEVICES 0x045e/0x0b12
python
import gdb
from pathlib import Path

watchpoints = []
seen_events = set()
queue_hits = 0

def read_be(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'big')

def read_le(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'little')

class EventStateWatch(gdb.Breakpoint):
    def __init__(self, guest_address, host_address):
        self.guest_address = guest_address
        self.host_address = host_address
        self.previous = read_be(host_address, 4)
        super().__init__('*(unsigned int*)0x%x' % host_address,
                         type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE,
                         internal=True)

    def stop(self):
        current = read_be(self.host_address, 4)
        thread = gdb.selected_thread().global_num
        pc = gdb.selected_frame().pc()
        print('EVENT_STATE_WRITE guest=%#x host=%#x thread=%d old=%#x new=%#x pc=%#x' %
              (self.guest_address, self.host_address, thread, self.previous, current, pc))
        try:
            print(gdb.execute('x/i $pc', to_string=True).strip())
            print(gdb.execute('bt 5', to_string=True).strip())
        except gdb.error as exc:
            print('EVENT_STATE_CONTEXT_ERROR %s' % exc)
        self.previous = current
        return False

class WorkerEntry(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B8AC8', internal=True)

    def stop(self):
        ctx = int(gdb.parse_and_eval('$rdi'))
        base = int(gdb.parse_and_eval('$rsi'))
        guest_object = read_le(ctx, 4)
        event_guest = guest_object + 32
        host_address = base + event_guest + 4
        if event_guest not in seen_events:
            seen_events.add(event_guest)
            print('WORKER_EVENT guest_object=%#x event_guest=%#x event_state_host=%#x thread=%d initial=%#x' %
                  (guest_object, event_guest, host_address,
                   gdb.selected_thread().global_num, read_be(host_address, 4)))
            try:
                watchpoints.append(EventStateWatch(event_guest, host_address))
                print('WATCHPOINT_INSTALLED guest=%#x host=%#x' % (event_guest, host_address))
            except gdb.error as exc:
                print('WATCHPOINT_INSTALL_FAILED guest=%#x host=%#x error=%s' % (event_guest, host_address, exc))
        return False

class QueueWait(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B34A0', internal=True)

    def stop(self):
        global queue_hits
        queue_hits += 1
        if queue_hits <= 30 or queue_hits % 100 == 0:
            ctx = int(gdb.parse_and_eval('$rdi'))
            base = int(gdb.parse_and_eval('$rsi'))
            obj = read_le(ctx, 4)
            head_ptr = read_be(base + obj + 10896, 4)
            head = read_be(base + head_ptr, 4)
            tail = read_be(base + obj + 10908, 4)
            predicate = int.from_bytes(bytes(gdb.selected_inferior().read_memory(base + obj + 10941, 1)), 'big')
            print('RETAIL_QUEUE_WAIT hit=%d thread=%d object=%#x head=%d tail=%d predicate=%#x' %
                  (queue_hits, gdb.selected_thread().global_num, obj, head, tail, predicate))
        return False

WorkerEntry()
QueueWait()
end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-worker-event-write-watch-20261026/user --cache_root=/tmp/nfs-shift-p1-worker-event-write-watch-20261026/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
