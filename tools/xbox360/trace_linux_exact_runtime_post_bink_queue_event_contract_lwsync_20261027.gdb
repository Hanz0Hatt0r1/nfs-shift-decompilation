set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set debuginfod enabled off
handle SIGSEGV nostop noprint pass
python
import gdb
import hashlib
import os
import re
import signal
import time
from pathlib import Path

out = os.environ.get('SHIFT_QUEUE_EVENT_TRACE_OUT', '/tmp/nfs-shift-p1-queue-event-contract-lwsync-20261027')
gdb.execute('set logging file %s/gdb.log' % out)
gdb.execute('set logging overwrite on')
gdb.execute('set logging enabled on')
gdb.execute('set environment LD_LIBRARY_PATH %s/bin' % out)
gdb.execute('set environment SDL_GAMECONTROLLER_IGNORE_DEVICES 0x045e/0x0b12')
started = time.monotonic()
state = {'target': False, 'manager': None, 'counter_address': None, 'worker_event': None,
         'worker_queue': None, 'worker_entries': 0, 'worker_tokens': {},
         'producer_entries': 0, 'producer_counted_entries': 0,
         'callback_enqueue_entries': 0, 'callback_queue_matches': 0,
         'counter_writes': 0, 'event_counts': {},
         'worker_events': set(), 'event_breakpoints_installed': False,
         'controller_ready': False, 'runtime_hash': None, 'plugin_hash': None}

def le(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'little')

def be(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'big')

def ctx_base():
    return int(gdb.parse_and_eval('$rdi')), int(gdb.parse_and_eval('$rsi'))

def thread_name():
    thread = gdb.selected_thread()
    return thread.name if thread else '?'

def install_kernel_event_breakpoints():
    if state['event_breakpoints_installed']:
        return
    pid = gdb.selected_inferior().pid
    paths = set()
    bias = None
    for line in Path('/proc/%d/maps' % pid).read_text().splitlines():
        fields = line.split(None, 5)
        if len(fields) != 6:
            continue
        if fields[2] == '00000000' and fields[5].endswith('/librexruntime.so'):
            bias = int(fields[0].split('-', 1)[0], 16)
            paths.add(fields[5])
        elif fields[2] == '00000000' and fields[5].endswith('/librexgpu-shift-native.so'):
            paths.add(fields[5])
    if bias is None:
        print('QUEUE_EVENT_RUNTIME_MAP_ERROR librexruntime.so not mapped')
        return
    for path in sorted(paths):
        try:
            digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            if path.endswith('/librexruntime.so'):
                state['runtime_hash'] = digest
            else:
                state['plugin_hash'] = digest
            print('QUEUE_EVENT_MAPPED path=%s sha256=%s' % (path, digest))
        except OSError as exc:
            print('QUEUE_EVENT_HASH_ERROR path=%s error=%s' % (path, exc))
    offsets = {'KeSetEvent': 0x5D2F30, 'KePulseEvent': 0x5D2F60,
               'KeResetEvent': 0x5D2F90, 'KeWaitForSingleObject': 0x5D3260}
    for symbol, offset in offsets.items():
        KernelEventCall(symbol, bias + offset)
    state['event_breakpoints_installed'] = True
    print('QUEUE_EVENT_BREAKPOINTS load_bias=%#x offsets=%r' % (bias, offsets))

class BinkTarget(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82679510', internal=True)
    def stop(self):
        try:
            context, base = ctx_base()
            wrapper = le(context, 4)
            movie = be(base + wrapper + 4, 4) if wrapper else 0
            target = be(base + movie + 8, 4) if movie else 0
            progress = be(base + movie + 12, 4) if movie else 0
            if target == 281 and progress >= 281 and not state['target']:
                state['target'] = True
                print('QUEUE_EVENT_BINK target=%d/%d movie=%#x elapsed=%.3f' %
                      (progress, target, movie, time.monotonic() - started))
                install_kernel_event_breakpoints()
        except gdb.error as exc:
            print('QUEUE_EVENT_BINK_ERROR %s' % exc)
        return False

class ControllerUpdate(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82308E60', internal=True)
    def stop(self):
        if not state['controller_ready']:
            state['controller_ready'] = True
            print('CONTROLLER_UPDATE elapsed=%.3f object=target' %
                  (time.monotonic() - started))
        return False

class WorkerLoop(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B8AC8', internal=True)
    def stop(self):
        try:
            context, _ = ctx_base()
            queue = le(context, 4)
            event = queue + 32
            state['worker_events'].add(event)
            if len(state['worker_events']) <= 4:
                print('QUEUE_EVENT_WORKER_LOOP queue=%#x event=%#x thread=%s' %
                      (queue, event, thread_name()))
        except gdb.error as exc:
            print('QUEUE_EVENT_WORKER_LOOP_ERROR %s' % exc)
        return False

class CallbackEnqueue(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B8C60', internal=True)
    def stop(self):
        if not state['target']:
            return False
        try:
            context, base = ctx_base()
            record = le(context, 4)
            manager = le(context + 32, 4)
            state['callback_enqueue_entries'] += 1
            if state['callback_enqueue_entries'] <= 24:
                words = [be(base + record + offset, 4) for offset in (0, 4, 8, 12)] if record else []
                entry_regs = [le(context + offset, 4) for offset in (32, 40, 48)]
                queue_samples = []
                for event in sorted(state['worker_events']):
                    queue = event - 32
                    delta = queue - manager - 11328
                    if delta < 0 or delta % 80:
                        continue
                    index = be(base + queue + 56, 4)
                    consumer = be(base + queue + 60, 4)
                    slot = queue + 16 + ((index & 3) * 4)
                    previous = be(base + slot, 4)
                    slots = [be(base + queue + 16 + i * 4, 4) for i in range(4)]
                    queue_samples.append((queue, delta // 80, index, consumer, slot, previous, slots))
                if queue_samples:
                    state['callback_queue_matches'] += 1
                print('QUEUE_EVENT_CALLBACK_ENQUEUE hit=%d record=%#x record_words=%r entry_r4_r6=%r manager=%#x queue_samples=%r thread=%s elapsed=%.3f' %
                      (state['callback_enqueue_entries'], record, words, entry_regs,
                       manager, queue_samples,
                       thread_name(), time.monotonic() - started))
        except gdb.error as exc:
            print('QUEUE_EVENT_CALLBACK_ENQUEUE_ERROR %s' % exc)
        return False

class QueueProducer(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B31A0', internal=True)
    def stop(self):
        if not state['target']:
            return False
        try:
            context, base = ctx_base()
            manager = le(context, 4)
            address = base + manager + 11012
            if state['counter_address'] is None:
                state['manager'] = manager
                state['counter_address'] = address
                print('QUEUE_EVENT_COUNTER manager=%#x address=%#x initial=%#x' %
                      (manager, address, be(address, 4)))
                output = gdb.execute('watch -l *(unsigned int*)%#x' % address, to_string=True)
                match = re.search(r'(?:Hardware )?[Ww]atchpoint (\d+)', output)
                if match:
                    number = int(match.group(1))
                    gdb.execute('\n'.join([
                        f'commands {number}', 'silent', 'python',
                        f'address = {address:#x}',
                        'value = int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, 4)), "big")',
                        'state["counter_writes"] += 1',
                        'if state["counter_writes"] <= 20:',
                        '    print("QUEUE_EVENT_COUNTER_WRITE n=%d value=%s thread=%s" % (state["counter_writes"], hex(value), thread_name()))',
                        'end', 'continue', 'end']))
                else:
                    print('QUEUE_EVENT_COUNTER_WATCH_ERROR %s' % output.strip())
            state['producer_entries'] += 1
            args = [le(context + offset, 4) for offset in (32, 40, 48, 56, 64)]
            counted = args[3] != 0
            if counted:
                state['producer_counted_entries'] += 1
            if state['producer_entries'] <= 24 or (counted and state['producer_counted_entries'] <= 24):
                stream = args[4]
                stream_head = be(base + stream + 4, 4) if stream else 0
                stream_tail = be(base + stream + 8, 4) if stream else 0
                print('QUEUE_EVENT_PRODUCER hit=%d counted_hit=%d counted=%s manager=%#x record=%#x payload=%#x token=%#x delta=%#x stream=%#x stream_head=%#x stream_tail=%#x counter=%#x elapsed=%.3f' %
                      (state['producer_entries'], state['producer_counted_entries'], counted,
                       manager, args[0], args[1], args[2], args[3], stream,
                       stream_head, stream_tail, be(address, 4),
                       time.monotonic() - started))
        except gdb.error as exc:
            print('QUEUE_EVENT_PRODUCER_ERROR %s' % exc)
        return False

class WorkerCompletion(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B85D0', internal=True)
    def stop(self):
        if not state['target'] or state['counter_address'] is None:
            return False
        try:
            context, base = ctx_base()
            obj = le(context, 4)
            if base + obj + 64 != state['counter_address']:
                return False
            queue, stream = le(context + 32, 4), le(context + 40, 4)
            if state['worker_queue'] is None:
                state['worker_queue'] = queue
                state['worker_event'] = queue + 32
                state['worker_events'].add(queue + 32)
                print('QUEUE_EVENT_WORKER_QUEUE object=%#x event=%#x' %
                      (queue, queue + 32))
            token = be(base + stream, 4)
            state['worker_entries'] += 1
            state['worker_tokens'][token] = state['worker_tokens'].get(token, 0) + 1
            if state['worker_entries'] <= 12:
                head = be(base + queue + 56, 4)
                tail = be(base + queue + 60, 4)
                ring_slots = [be(base + queue + 16 + index * 4, 4) for index in range(4)]
                parser = [be(base + obj + offset, 4) for offset in (24, 28, 32, 36)]
                stream_words = [be(base + stream + offset, 4) for offset in (0, 4, 8, 12)]
                print('QUEUE_EVENT_WORKER hit=%d object=%#x queue=%#x head=%#x tail=%#x ring_slots=%r parser24_28_32_36=%r stream=%#x token=%#x stream_words=%r count=%#x field72=%#x elapsed=%.3f' %
                      (state['worker_entries'], obj, queue, head, tail, ring_slots,
                       parser, stream, token, stream_words,
                       be(base + obj + 64, 4), be(base + obj + 72, 4),
                       time.monotonic() - started))
        except gdb.error as exc:
            print('QUEUE_EVENT_WORKER_ERROR %s' % exc)
        return False

class KernelEventCall(gdb.Breakpoint):
    def __init__(self, symbol, address):
        self.symbol = symbol
        super().__init__('*%#x' % address, internal=True)
    def stop(self):
        if state['worker_event'] is None:
            return False
        try:
            context, base = ctx_base()
            event = le(context, 4)
            if event not in state['worker_events']:
                return False
            count = state['event_counts'].get(self.symbol, 0) + 1
            state['event_counts'][self.symbol] = count
            if count <= 24:
                signal_state = be(base + event + 4, 4)
                print('QUEUE_EVENT_CALL function=%s n=%d event=%#x guest_signal_state=%#x thread=%s elapsed=%.3f' %
                      (self.symbol, count, event, signal_state, thread_name(),
                       time.monotonic() - started))
        except gdb.error as exc:
            print('QUEUE_EVENT_CALL_ERROR function=%s error=%s' % (self.symbol, exc))
        return False

BinkTarget()
ControllerUpdate()
CallbackEnqueue()
QueueProducer()
WorkerLoop()
WorkerCompletion()

end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-bink-completion-followthrough-20261027/user --cache_root=/tmp/nfs-shift-p1-bink-completion-followthrough-20261027/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
python
pid = gdb.selected_inferior().pid
print('QUEUE_EVENT_FINAL_STATE target=%s manager=%s counter_address=%s producer_entries=%d producer_counted_entries=%d callback_enqueue_entries=%d callback_queue_matches=%d worker_queue=%s worker_event=%s worker_events=%r worker_entries=%d worker_tokens=%r counter_writes=%d event_counts=%r runtime_hash=%s plugin_hash=%s' %
      (state['target'], hex(state['manager']) if state['manager'] else None,
       hex(state['counter_address']) if state['counter_address'] else None,
       state['producer_entries'], state['producer_counted_entries'], state['callback_enqueue_entries'],
       state['callback_queue_matches'],
       hex(state['worker_queue']) if state['worker_queue'] else None,
       hex(state['worker_event']) if state['worker_event'] else None,
       sorted(hex(event) for event in state['worker_events']),
       state['worker_entries'], state['worker_tokens'], state['counter_writes'],
       state['event_counts'], state['runtime_hash'], state['plugin_hash']))
try:
    gdb.execute('thread apply all bt 4')
except Exception as exc:
    print('QUEUE_EVENT_STACK_ERROR %s' % exc)
if pid:
    try:
        gdb.execute('detach')
        os.kill(pid, signal.SIGINT)
        print('QUEUE_EVENT sent host SIGINT pid=%d' % pid)
    except ProcessLookupError:
        print('QUEUE_EVENT host already exited pid=%d' % pid)
end
quit
