set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
handle SIGSEGV nostop noprint pass
python
import gdb
import os
import re
import signal
import threading
import time

out = os.environ.get('SHIFT_WORKER_TOKEN_TRACE_OUT', '/tmp/nfs-shift-p1-worker-token-trace-20261027')
gdb.execute('set logging file %s/gdb.log' % out)
gdb.execute('set logging overwrite on')
gdb.execute('set logging enabled on')
gdb.execute('set environment LD_LIBRARY_PATH %s/bin' % out)
gdb.execute('set environment SDL_GAMECONTROLLER_IGNORE_DEVICES 0x045e/0x0b12')
started = time.monotonic()
state = {'target': False, 'target_elapsed': None, 'manager': None,
         'counter_address': None, 'watchpoint': None, 'entries': 0,
         'tokens': {}, 'stream_addresses': set(), 'controller_updates': 0,
         'controller_ready_seen': False}

def le(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'little')

def be(address, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, size)), 'big')

def ctx_base():
    return int(gdb.parse_and_eval('$rdi')), int(gdb.parse_and_eval('$rsi'))

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
                state['target_elapsed'] = time.monotonic() - started
                print('WORKER_TOKEN_BINK_TARGET movie=%#x progress=%d target=%d elapsed=%.3f' %
                      (movie, progress, target, state['target_elapsed']))
        except gdb.error as exc:
            print('WORKER_TOKEN_BINK_ERROR %s' % exc)
        return False

class ControllerUpdate(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82308E60', internal=True)
    def stop(self):
        try:
            context, _ = ctx_base()
            state['controller_updates'] += 1
            if not state['controller_ready_seen']:
                state['controller_ready_seen'] = True
                print('CONTROLLER_UPDATE elapsed=%.3f hit=%d object=ready' %
                      (time.monotonic() - started, state['controller_updates']))
        except gdb.error as exc:
            print('WORKER_TOKEN_CONTROLLER_ERROR %s' % exc)
        return False

class QueueCounter(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B31A0', internal=True)
    def stop(self):
        if not state['target'] or state['counter_address'] is not None:
            return False
        try:
            context, base = ctx_base()
            manager = le(context, 4)
            address = base + manager + 11012
            state['manager'] = manager
            state['counter_address'] = address
            print('WORKER_TOKEN_COUNTER_ARM manager=%#x address=%#x value=%#x elapsed=%.3f' %
                  (manager, address, be(address, 4), time.monotonic() - started))
            output = gdb.execute('watch -l *(unsigned int*)%#x' % address, to_string=True)
            match = re.search(r'(?:Hardware )?[Ww]atchpoint (\d+)', output)
            if not match:
                print('WORKER_TOKEN_WATCH_ERROR %s' % output.strip())
                return False
            number = int(match.group(1))
            state['watchpoint'] = number
            gdb.execute('\n'.join([
                f'commands {number}', 'silent', 'python',
                f'address = {address:#x}',
                'value = int.from_bytes(bytes(gdb.selected_inferior().read_memory(address, 4)), "big")',
                'thread = gdb.selected_thread()',
                'print("WORKER_TOKEN_COUNTER_WRITE value=" + hex(value) + " thread=" + (thread.name if thread else "?"))',
                'if value in (0, 1, 0xffffffff): gdb.execute("bt 5")',
                f'if value == 0xffffffff: gdb.execute("disable {number}")',
                'end', 'continue', 'end']))
        except gdb.error as exc:
            print('WORKER_TOKEN_COUNTER_ERROR %s' % exc)
        self.enabled = False
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
            address = base + obj + 64
            if address != state['counter_address']:
                return False
            r4, stream = (le(context + offset, 4) for offset in (32, 40))
            token = be(base + stream, 4)
            state['entries'] += 1
            state['tokens'][token] = state['tokens'].get(token, 0) + 1
            state['stream_addresses'].add(stream)
            if state['entries'] <= 12:
                fields = {str(offset): be(base + obj + offset, 4)
                          for offset in (56, 60, 64, 72)}
                print('WORKER_TOKEN_ENTRY hit=%d object=%#x queue=%#x stream=%#x token=%#x fields=%r elapsed=%.3f' %
                      (state['entries'], obj, r4, stream, token, fields,
                       time.monotonic() - started))
        except gdb.error as exc:
            print('WORKER_TOKEN_ENTRY_ERROR %s' % exc)
        return False

BinkTarget()
ControllerUpdate()
QueueCounter()
WorkerCompletion()

def bounded_interrupt():
    gdb.post_event(lambda: gdb.execute('interrupt'))
timer = threading.Timer(80.0, bounded_interrupt)
timer.daemon = True
timer.start()
end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-bink-completion-followthrough-20261027/user --cache_root=/tmp/nfs-shift-p1-bink-completion-followthrough-20261027/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
python
pid = gdb.selected_inferior().pid
print('WORKER_TOKEN_FINAL_STATE entries=%d tokens=%r streams=%r target_elapsed=%.3f controller_updates=%d controller_ready_seen=%s' %
      (state['entries'], state['tokens'], sorted(state['stream_addresses']),
       state['target_elapsed'] or -1, state['controller_updates'],
       state['controller_ready_seen']))
try:
    gdb.execute('thread apply all bt 5')
except Exception as exc:
    print('WORKER_TOKEN_STACK_ERROR %s' % exc)
if pid:
    try:
        gdb.execute('detach')
        os.kill(pid, signal.SIGINT)
        print('WORKER_TOKEN sent host SIGINT pid=%d' % pid)
    except ProcessLookupError:
        print('WORKER_TOKEN host already exited pid=%d' % pid)
end
quit
