set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set can-use-hw-watchpoints 1
file /tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/bin/nfs_shift
set logging file /tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/watch_wait_word.gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/bin
set environment SHIFT_NATIVE_VULKAN_TRACE_RING 1
python
import gdb
import hashlib
from pathlib import Path

WATCHES = []
TARGET_POLL = 0x1B964006
ADDRESSES = (0x21B964004, 0x1FB963004)

class GuestWordWatch(gdb.Breakpoint):
    def __init__(self, address):
        self.address = address
        super().__init__("*(unsigned int *)%#x" % address,
                         type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE)
        print("armed_guest_word_write_watch host=%#x" % address)

    def stop(self):
        try:
            value = int(gdb.parse_and_eval("*(unsigned int *)%#x" % self.address))
            print("guest_word_write alias_host=%#x value=%08x" % (self.address, value))
            gdb.execute("bt 8")
        except Exception as error:
            print("guest_word_watch_error host=%#x error=%s" % (self.address, error))
        self.enabled = False
        return False

class WaitPacketBreakpoint(gdb.Breakpoint):
    def __init__(self):
        super().__init__("shift::xbox::decode_captured_wait_reg_mem")
        self.seen = False

    def stop(self):
        if self.seen:
            return False
        inferior = gdb.selected_inferior()
        raw = bytes(inferior.read_memory(int(gdb.parse_and_eval("$rdi")), 24))
        poll = int.from_bytes(raw[8:12], "big")
        if poll != TARGET_POLL:
            return False
        self.seen = True
        print("target_wait_packet poll=%08x raw=%s" % (poll, raw.hex()))
        for address in ADDRESSES:
            try:
                value = int(gdb.parse_and_eval("*(unsigned int *)%#x" % address))
                print("wait_word_before_watch host=%#x value=%08x" % (address, value))
                WATCHES.append(GuestWordWatch(address))
            except Exception as error:
                print("wait_word_watch_unavailable host=%#x error=%s" % (address, error))
        pid = inferior.pid
        maps = Path("/proc/%d/maps" % pid).read_text().splitlines()
        for address in ADDRESSES:
            matches = []
            for line in maps:
                bounds = line.split()[0]
                start, end = (int(piece, 16) for piece in bounds.split("-"))
                if start <= address < end:
                    matches.append(line)
            print("wait_word_mapping host=%#x lines=%s" % (address, matches))
        return False

WaitPacketBreakpoint()
end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/user --cache_root=/tmp/nfs-shift-p1-p2latest-plugin-v2-20261026/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
handle SIGINT stop noprint nopass
run
