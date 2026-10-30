set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set debuginfod enabled off
set logging file /tmp/nfs-shift-p1-dump-retail-wait-code-20261027/gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-dump-retail-wait-code-20261027/bin
set environment SDL_GAMECONTROLLER_IGNORE_DEVICES 0x045e/0x0b12
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-dump-retail-wait-code-20261027/user --cache_root=/tmp/nfs-shift-p1-dump-retail-wait-code-20261027/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false

python
import gdb
import hashlib
from pathlib import Path

output_path = Path('/home/pes/ghidra_projects/NeedForSpeedShift_Xbox360_Retail_20261027/sub_823B3850.bin')
expected = bytes.fromhex('7d8802a69181fff8fbe1fff09421ffa0')

class DumpRetailWaitCode(gdb.Breakpoint):
    def __init__(self):
        super().__init__('sub_823B3850', internal=True)

    def stop(self):
        try:
            context = int(gdb.parse_and_eval('$rdi'))
            guest_base = int(gdb.parse_and_eval('$rsi'))
            manager = int.from_bytes(bytes(gdb.selected_inferior().read_memory(context, 4)), 'little')
            code = bytes(gdb.selected_inferior().read_memory(guest_base + 0x823B3850, 0x100))
            output_path.write_bytes(code)
            print('RETAIL_WAIT_CODE_DUMP path=%s sha256=%s manager=%#x guest_base=%#x '
                  'guest_address=0x823B3850 prefix=%s expected_prefix_match=%s' %
                  (output_path, hashlib.sha256(code).hexdigest(), manager, guest_base,
                   code[:16].hex(), code.startswith(expected)))
            return True
        except gdb.error as exc:
            print('RETAIL_WAIT_CODE_DUMP_ERROR %s' % exc)
            return False
        except OSError as exc:
            print('RETAIL_WAIT_CODE_DUMP_FILE_ERROR %s' % exc)
            return False

DumpRetailWaitCode()

def bounded_interrupt():
    gdb.post_event(lambda: gdb.execute('interrupt'))

import threading
timer = threading.Timer(120.0, bounded_interrupt)
timer.daemon = True
timer.start()
end

run
python
import os
import signal

pid = gdb.selected_inferior().pid
if pid:
    try:
        gdb.execute('detach')
        os.kill(pid, signal.SIGINT)
        print('RETAIL_WAIT_CODE_DUMP_SENT_SIGINT pid=%d' % pid)
    except ProcessLookupError:
        print('RETAIL_WAIT_CODE_DUMP_PROCESS_EXITED pid=%d' % pid)
end
quit
