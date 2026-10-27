set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
handle SIGSEGV nostop noprint pass
set logging file /tmp/nfs-shift-p1-bink-transition-20261027/gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /home/pes/work/process2-depth-resolve-handoff-20261027:/tmp/nfs-shift-p2-depth-resolve-target-frame707-20261027/bin
set environment SDL_GAMECONTROLLER_IGNORE_DEVICES 0x045e/0x0b12
python
import gdb, time, threading, os, signal
started = time.monotonic()
counts = {'manager': 0, 'video': 0, 'post': 0}
last_progress = {'manager': None, 'video': None, 'post': None}

def read_le(addr, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(addr, size)), 'little')

def read_be(addr, size):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(addr, size)), 'big')

def guest_sample():
    ctx = int(gdb.parse_and_eval('$rdi'))
    base = int(gdb.parse_and_eval('$rsi'))
    obj = read_le(ctx, 4)
    lr = read_le(ctx + 256, 8) & 0xffffffff
    bink = read_be(base + obj + 4, 4) if obj else 0
    target = read_be(base + bink + 8, 4) if bink else 0
    progress = read_be(base + bink + 12, 4) if bink else 0
    fields = tuple(read_be(base + bink + off, 4) for off in (236, 248, 276, 820)) if bink else ()
    return base, obj, bink, target, progress, fields, lr

class GuestPath(gdb.Breakpoint):
    def __init__(self, symbol, key):
        self.key = key
        super().__init__(symbol, internal=True)

    def stop(self):
        counts[self.key] += 1
        n = counts[self.key]
        try:
            base, obj, bink, target, progress, fields, lr = guest_sample()
            changed = progress != last_progress[self.key]
            last_progress[self.key] = progress
            if changed or n <= 3 or n % 80 == 0 or progress >= target:
                print('BINK_PATH elapsed=%.3f path=%s hit=%d wrapper=%#x bink=%#x progress=%u target=%u fields236_248_276_820=%s lr=%#x video_hits=%d' %
                      (time.monotonic() - started, self.key, n, obj, bink, progress, target, fields, lr, counts['video']))
        except Exception as exc:
            print('BINK_PATH_READ_ERROR path=%s hit=%d error=%s' % (self.key, n, exc))
        return False

GuestPath('sub_82679C50', 'manager')
GuestPath('sub_82678FD0', 'video')
GuestPath('sub_82679510', 'post')

def interrupt_gdb():
    gdb.post_event(lambda: gdb.execute('interrupt'))

timer = threading.Timer(140.0, interrupt_gdb)
timer.daemon = True
timer.start()
end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-bink-transition-20261027/user --cache_root=/tmp/nfs-shift-p1-bink-transition-20261027/cache --gpu_plugin=shift-native --no-async_shader-compilation --fullscreen=false
run
python
pid = gdb.selected_inferior().pid
print('BINK_TRACE_SUMMARY counts=%r pid=%s' % (counts, pid))
if pid:
    try:
        gdb.execute('detach')
        os.kill(pid, signal.SIGINT)
        print('BINK_TRACE sent host SIGINT pid=%d' % pid)
    except ProcessLookupError:
        print('BINK_TRACE host already exited pid=%d' % pid)
end
quit
