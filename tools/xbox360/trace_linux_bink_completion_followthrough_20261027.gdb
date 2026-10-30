set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
handle SIGSEGV nostop noprint pass
set logging file /tmp/nfs-shift-p1-bink-completion-followthrough-20261027/gdb-final.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-bink-completion-followthrough-20261027/bin:/home/pes/work/process2-depth-resolve-handoff-20261027
python
import gdb, hashlib, os, signal, threading, time
from pathlib import Path

started = time.monotonic()
state = {
    'bink': 0,
    'wrapper': 0,
    'target': 0,
    'target_seen': False,
    'target_elapsed': None,
    'last_scene_progress': None,
    'counts': {'manager': 0, 'post': 0, 'scene': 0, 'c5a8': 0, 'cd10': 0},
    'returns': {'scene': 0, 'c5a8': 0, 'cd10': 0},
}

def le(addr, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(addr, size)), 'little')

def be(addr, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(addr, size)), 'big')

def args():
    return int(gdb.parse_and_eval('$rdi')), int(gdb.parse_and_eval('$rsi'))

def sample_bink(ctx, base):
    wrapper = le(ctx, 4)
    bink = be(base + wrapper + 4, 4) if wrapper else 0
    target = be(base + bink + 8, 4) if bink else 0
    progress = be(base + bink + 12, 4) if bink else 0
    return wrapper, bink, target, progress

class ReturnTrace(gdb.FinishBreakpoint):
    def __init__(self, frame, ctx, base, function, obj, main=0):
        super().__init__(frame, internal=True)
        self.ctx, self.base, self.function, self.obj, self.main = ctx, base, function, obj, main

    def stop(self):
        try:
            result = le(self.ctx, 4)
            bink = state['bink']
            target = be(self.base + bink + 8, 4) if bink else 0
            progress = be(self.base + bink + 12, 4) if bink else 0
            counter = be(self.base + self.main + 356, 4) if self.main else 0
            fields = tuple(be(self.base + bink + off, 4) for off in (236, 248, 276, 820)) if bink else ()
            state['returns'][self.function] += 1
            print('BINK_RETURN elapsed=%.3f function=%s object=%#x result=%u progress=%u target=%u object356=%u fields236_248_276_820=%s' %
                  (time.monotonic() - started, self.function, self.obj, result, progress, target, counter, fields))
        except Exception as exc:
            print('BINK_RETURN_READ_ERROR function=%s object=%#x error=%s' % (self.function, self.obj, exc))
        return False

class BinkEntry(gdb.Breakpoint):
    def __init__(self, symbol, key):
        self.key = key
        super().__init__(symbol, internal=True)

    def stop(self):
        state['counts'][self.key] += 1
        try:
            ctx, base = args()
            wrapper, bink, target, progress = sample_bink(ctx, base)
            if target == 281:
                state['wrapper'], state['bink'], state['target'] = wrapper, bink, target
                if self.key == 'post' and progress >= target and not state['target_seen']:
                    state['target_seen'] = True
                    state['target_elapsed'] = time.monotonic() - started
                    print('BINK_TARGET_REACHED elapsed=%.3f function=%s hit=%d wrapper=%#x object=%#x progress=%u target=%u fields236_248_276_820=%s lr=%#x' %
                          (state['target_elapsed'], self.key, state['counts'][self.key], wrapper, bink, progress, target,
                           tuple(be(base + bink + off, 4) for off in (236, 248, 276, 820)), le(ctx + 256, 8) & 0xffffffff))
                elif state['counts'][self.key] <= 2 or progress >= target - 2:
                    print('BINK_PATH elapsed=%.3f function=%s hit=%d wrapper=%#x object=%#x progress=%u target=%u lr=%#x' %
                          (time.monotonic() - started, self.key, state['counts'][self.key], wrapper, bink, progress, target,
                           le(ctx + 256, 8) & 0xffffffff))
        except Exception as exc:
            print('BINK_PATH_READ_ERROR function=%s error=%s' % (self.key, exc))
        return False

class ParentEntry(gdb.Breakpoint):
    def __init__(self, symbol, key):
        self.key = key
        super().__init__(symbol, internal=True)

    def stop(self):
        state['counts'][self.key] += 1
        try:
            ctx, base = args()
            obj = le(ctx, 4)
            progress = be(base + state['bink'] + 12, 4) if state['bink'] else 0
            target = be(base + state['bink'] + 8, 4) if state['bink'] else 0
            if target != 281 or progress < target - 3:
                return False
            main = obj - 264 if self.key == 'c5a8' and obj >= 264 else 0
            counter = be(base + main + 356, 4) if main else 0
            f4 = be(base + obj + 4, 4)
            f12 = be(base + obj + 12, 4)
            print('BINK_PARENT_ENTRY elapsed=%.3f function=%s hit=%d object=%#x progress=%u target=%u object356=%u field4=%#x field12=%#x' %
                  (time.monotonic() - started, self.key, state['counts'][self.key], obj, progress, target, counter, f4, f12))
            ReturnTrace(gdb.newest_frame(), ctx, base, self.key, obj, main)
        except Exception as exc:
            print('BINK_PARENT_READ_ERROR function=%s error=%s' % (self.key, exc))
        return False

class SceneUpdate(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_82DDC6F0', internal=True)

    def stop(self):
        state['counts']['scene'] += 1
        try:
            ctx, base = args()
            main = le(ctx, 4)
            progress = be(base + state['bink'] + 12, 4) if state['bink'] else 0
            target = be(base + state['bink'] + 8, 4) if state['bink'] else 0
            if target != 281 or progress < target - 3:
                return False
            counter = be(base + main + 356, 4)
            child = be(base + main + 264, 4)
            if progress != state['last_scene_progress']:
                print('BINK_SCENE_ENTRY elapsed=%.3f hit=%d object=%#x child=%#x progress=%u target=%u object356=%u' %
                      (time.monotonic() - started, state['counts']['scene'], main, child, progress, target, counter))
                state['last_scene_progress'] = progress
            ReturnTrace(gdb.newest_frame(), ctx, base, 'scene', main, main)
        except Exception as exc:
            print('BINK_SCENE_READ_ERROR error=%s' % exc)
        return False

BinkEntry('sub_82679C50', 'manager')
BinkEntry('sub_82679510', 'post')
ParentEntry('sub_82E2C5A8', 'c5a8')
ParentEntry('sub_82E2CD10', 'cd10')
SceneUpdate()

def interrupt_run():
    gdb.post_event(lambda: gdb.execute('interrupt'))

timer = threading.Timer(60.0, interrupt_run)
timer.daemon = True
timer.start()
end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-bink-completion-followthrough-20261027/user-final --cache_root=/tmp/nfs-shift-p1-bink-completion-followthrough-20261027/cache-final --gpu_plugin=shift-native --no-async_shader-compilation --fullscreen=false
run
python
pid = gdb.selected_inferior().pid
lines = [line for line in Path(f'/proc/{pid}/maps').read_text().splitlines() if 'librexruntime.so' in line or 'librexgpu-shift' in line]
capture = Path('/tmp/nfs-shift-p1-bink-completion-followthrough-20261027/mapped-libraries-final.txt')
capture.write_text('\n'.join(lines) + '\n')
for path in sorted({line.split()[-1] for line in lines}):
    print('BINK_MAPPED_LIBRARY path=%s sha256=%s' % (path, hashlib.sha256(Path(path).read_bytes()).hexdigest()))
print('BINK_MAPPED_CAPTURE sha256=%s' % hashlib.sha256(capture.read_bytes()).hexdigest())
print('BINK_COMPLETION_SUMMARY counts=%r returns=%r bink=%#x target_frame=%u target_elapsed=%r pid=%s' %
      (state['counts'], state['returns'], state['bink'], state['target'], state['target_elapsed'], pid))
if pid:
    try:
        gdb.execute('detach')
        os.kill(pid, signal.SIGINT)
        print('BINK_COMPLETION sent host SIGINT pid=%d' % pid)
    except ProcessLookupError:
        print('BINK_COMPLETION host already exited pid=%d' % pid)
end
quit
