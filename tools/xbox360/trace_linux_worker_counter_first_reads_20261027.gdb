set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set debuginfod enabled off
handle SIGSEGV nostop noprint pass
set logging file /tmp/nfs-shift-p1-worker-counter-first-reads-20261027/gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-worker-counter-first-reads-20261027/bin
set environment SHIFT_NATIVE_VULKAN_TRACE_RING 1

python
import gdb, os, signal, threading, time

started = time.monotonic()
state = {'manager': 0, 'base': 0, 'writer': None, 'reader': None,
         'writes': 0, 'reads': 0, 'first_negative_at': None}

def le(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'little')

def be(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'big')

def guest_reg(ctx, offset):
    return le(ctx + offset, 4)

def elapsed():
    return time.monotonic() - started

class FirstReads(gdb.Breakpoint):
    def __init__(self, address):
        self.address = address
        super().__init__('*(unsigned int*)%#x' % address,
                         type=gdb.BP_WATCHPOINT,
                         wp_class=gdb.WP_READ,
                         internal=True)

    def stop(self):
        state['reads'] += 1
        if state['reads'] <= 12:
            pc = int(gdb.parse_and_eval('$pc'))
            thread = gdb.selected_thread().global_num
            print('COUNTER_READ n=%d elapsed=%.6f value=%#x pc=%#x thread=%d' %
                  (state['reads'], elapsed(), be(self.address, 4), pc, thread))
            try:
                print('COUNTER_READ_SYMBOL %s' % gdb.execute('info symbol $pc', to_string=True).strip())
                print('COUNTER_READ_STACK\n%s' % gdb.execute('bt 8', to_string=True).strip())
            except gdb.error as exc:
                print('COUNTER_READ_CONTEXT_ERROR %s' % exc)
        if state['reads'] >= 12:
            self.enabled = False
            print('COUNTER_READ_WATCH_DISABLED n=%d' % state['reads'])
        return False

class CounterWrites(gdb.Breakpoint):
    def __init__(self, address):
        self.address = address
        self.previous = be(address, 4)
        super().__init__('*(unsigned int*)%#x' % address,
                         type=gdb.BP_WATCHPOINT,
                         wp_class=gdb.WP_WRITE,
                         internal=True)

    def stop(self):
        current = be(self.address, 4)
        state['writes'] += 1
        if state['writes'] <= 12:
            print('COUNTER_WRITE n=%d elapsed=%.6f old=%#x new=%#x pc=%#x thread=%d' %
                  (state['writes'], elapsed(), self.previous, current,
                   int(gdb.parse_and_eval('$pc')), gdb.selected_thread().global_num))
        self.previous = current
        if current == 0xffffffff and state['reader'] is None:
            state['first_negative_at'] = elapsed()
            try:
                state['reader'] = FirstReads(self.address)
                print('COUNTER_READ_WATCH_ARMED elapsed=%.6f address=%#x' %
                      (elapsed(), self.address))
            except gdb.error as exc:
                print('COUNTER_READ_WATCH_FAILED address=%#x error=%s' % (self.address, exc))
        return False

class ArmCounter(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B34A0', internal=True)

    def stop(self):
        try:
            ctx = int(gdb.parse_and_eval('$rdi'))
            base = int(gdb.parse_and_eval('$rsi'))
            manager = guest_reg(ctx, 0)
            lr = le(ctx + 256, 8) & 0xffffffff
            if not state['manager'] and lr == 0x823A557C:
                state['manager'], state['base'] = manager, base
                address = base + manager + 11012
                state['writer'] = CounterWrites(address)
                print('COUNTER_WATCH_ARMED elapsed=%.6f manager=%#x address=%#x initial=%#x' %
                      (elapsed(), manager, address, be(address, 4)))
        except Exception as exc:
            print('COUNTER_ARM_ERROR %s' % exc)
        return False

ArmCounter()

def bounded_interrupt():
    gdb.post_event(lambda: gdb.execute('interrupt'))

timer = threading.Timer(105.0, bounded_interrupt)
timer.daemon = True
timer.start()
end

set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-worker-counter-first-reads-20261027/user --cache_root=/tmp/nfs-shift-p1-worker-counter-first-reads-20261027/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
python
pid = gdb.selected_inferior().pid
print('COUNTER_READ_TRACE_END elapsed=%.6f state=%r pid=%s' %
      (elapsed(), {k:v for k,v in state.items() if k not in ('writer','reader')}, pid))
if pid:
    try:
        gdb.execute('detach')
        os.kill(pid, signal.SIGINT)
        print('COUNTER_READ_TRACE_DETACHED pid=%d' % pid)
    except ProcessLookupError:
        print('COUNTER_READ_TRACE_TITLE_EXITED pid=%d' % pid)
end
quit
