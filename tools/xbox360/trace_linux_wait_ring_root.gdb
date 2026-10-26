set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set can-use-hw-watchpoints 1
file /tmp/nfs-shift-p1-p2-write-trace-20261026/bin/nfs_shift
set logging file /tmp/nfs-shift-p1-p2-write-trace-20261026/gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-p2-write-trace-20261026/bin
set environment SHIFT_NATIVE_VULKAN_TRACE_RING 1

python
import hashlib
import os
import signal
import struct
from pathlib import Path
import gdb

capture_dir = Path("/tmp/nfs-shift-p1-p2-write-trace-20261026")
capture_dir.mkdir(parents=True, exist_ok=True)
target_pid = None

class WaitPacketCapture(gdb.Breakpoint):
    def __init__(self):
        super().__init__("shift::xbox::decode_captured_wait_reg_mem")
        self.done = False

    def stop(self):
        global target_pid
        if self.done:
            return False
        inferior = gdb.selected_inferior()
        target_pid = inferior.pid
        packet = int(gdb.parse_and_eval("$rdi"))
        byte_length = int(gdb.parse_and_eval("$rsi"))
        if byte_length < 24:
            return False
        raw_packet = bytes(inferior.read_memory(packet, 24))
        poll = int.from_bytes(raw_packet[8:12], "big")
        if poll != 0x1B964006:
            return False

        self.done = True
        print("target_wait_packet poll=%08x raw=%s" % (poll, raw_packet.hex()))
        maps_path = Path("/proc/%d/maps" % target_pid)
        mapped_lines = [line for line in maps_path.read_text().splitlines()
                        if "librexruntime.so" in line or "librexgpu-shift" in line]
        maps_capture = capture_dir / "mapped-libraries.txt"
        maps_capture.write_text("\n".join(mapped_lines) + "\n")
        mapped_paths = sorted({line.split()[-1] for line in mapped_lines})
        for path in mapped_paths:
            print("mapped_library path=%s sha256=%s" % (
                path, hashlib.sha256(Path(path).read_bytes()).hexdigest()))
        print("mapped_libraries_capture path=%s sha256=%s" % (
            maps_capture, hashlib.sha256(maps_capture.read_bytes()).hexdigest()))
        # Read only the bytes around the packet; do not modify guest memory.
        root_address = 0x095D0120
        root_length = 0x800
        root_physical = 0x200000000 + root_address
        root_bytes = None
        for name, address in (
            ("physical", root_physical),
            ("vA", 0x100000000 + 0xA0000000 + root_address),
        ):
            try:
                data = bytes(inferior.read_memory(address, root_length))
            except gdb.MemoryError as error:
                print("ring_root_unavailable alias=%s error=%s" % (name, error))
                continue
            path = capture_dir / ("ring_root_" + name + ".bin")
            path.write_bytes(data)
            print("ring_root_capture alias=%s host=%#x bytes=%d sha256=%s path=%s" % (
                name, address, len(data), hashlib.sha256(data).hexdigest(), path))
            if name == "physical":
                root_bytes = data
            elif root_bytes is not None:
                print("ring_root_aliases_equal=%s" % (data == root_bytes))

        # Decode the type-3 INDIRECT_BUFFER packets preceding the wait and
        # preserve each nested IB used by the same command stream.
        if root_bytes is not None:
            offset = 0
            while offset + 4 <= 0x49C:
                header = struct.unpack_from(">I", root_bytes, offset)[0]
                packet_type = header >> 30
                if packet_type in (0, 3):
                    count = (header >> 16) & 0x3FFF
                    byte_length = (count + 2) * 4
                    if offset + byte_length > 0x49C:
                        break
                    opcode = (header >> 8) & 0xFF
                    if packet_type == 3 and opcode == 0x3F and count >= 1:
                        guest_address, dword_count = struct.unpack_from(">II", root_bytes, offset + 4)
                        child_length = dword_count * 4
                        try:
                            child = bytes(inferior.read_memory(
                                0x200000000 + guest_address, child_length))
                        except gdb.MemoryError as error:
                            print("nested_ib_unavailable source_offset=%#x guest=%08x error=%s" % (
                                offset, guest_address, error))
                        else:
                            child_path = capture_dir / ("nested_ib_%08x.bin" % guest_address)
                            child_path.write_bytes(child)
                            print("nested_ib_capture source_offset=%#x guest=%08x dwords=%d bytes=%d sha256=%s path=%s" % (
                                offset, guest_address, dword_count, child_length,
                                hashlib.sha256(child).hexdigest(), child_path))
                    offset += byte_length
                elif packet_type == 2:
                    offset += 4
                else:
                    break
        for name, address in (
            ("physical_wait_word", 0x200000000 + 0x1B964004),
            ("context_vE_alias", 0x100000000 + 0xFB963004),
        ):
            try:
                value = bytes(inferior.read_memory(address, 4)).hex()
                print("wait_word_sample alias=%s host=%#x bytes=%s" % (name, address, value))
            except gdb.MemoryError as error:
                print("wait_word_unavailable alias=%s error=%s" % (name, error))
        return True

WaitPacketCapture()
end

handle SIGINT stop noprint nopass
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-p2-write-trace-20261026/user --cache_root=/tmp/nfs-shift-p1-p2-write-trace-20261026/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
detach
python
if target_pid:
    os.kill(target_pid, signal.SIGINT)
    print("sent SIGINT to bounded retail process pid=%d after detaching" % target_pid)
end
