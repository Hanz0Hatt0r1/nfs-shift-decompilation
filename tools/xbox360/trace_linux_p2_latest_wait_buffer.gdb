set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
file /tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/bin/nfs_shift
set logging file /tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/capture_wait_ib.gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/bin
set environment SHIFT_NATIVE_VULKAN_TRACE_RING 1
python
import gdb
import hashlib
import os
import signal
from pathlib import Path

TARGET_POLL = 0x1B964006
TARGET_SOURCE = 0x095D0120
CAPTURE = Path('/tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/wait_ib_095d0120.bin')
target_pid = None

class WaitBufferCapture(gdb.Breakpoint):
    def __init__(self):
        super().__init__('shift::xbox::decode_captured_wait_reg_mem')
        self.done = False
    def stop(self):
        global target_pid
        if self.done:
            return False
        inferior = gdb.selected_inferior()
        packet = int(gdb.parse_and_eval('$rdi'))
        raw = bytes(inferior.read_memory(packet, 24))
        poll = int.from_bytes(raw[8:12], 'big')
        if poll != TARGET_POLL:
            return False
        self.done = True
        target_pid = inferior.pid
        data = bytes(inferior.read_memory(0x200000000 + TARGET_SOURCE, 0x2000))
        CAPTURE.write_bytes(data)
        print('target_wait_packet raw=%s' % raw.hex())
        print('source_guest=%08x length=%d sha256=%s path=%s' % (
            TARGET_SOURCE, len(data), hashlib.sha256(data).hexdigest(), CAPTURE))
        return True

WaitBufferCapture()
end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/user --cache_root=/tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
handle SIGINT stop noprint nopass
run
detach
python
if target_pid:
    os.kill(target_pid, signal.SIGINT)
    print('sent SIGINT to bounded retail process pid=%d after guest-buffer capture' % target_pid)
end
