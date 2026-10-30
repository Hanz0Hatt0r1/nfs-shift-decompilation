set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set logging file /tmp/nfs-shift-p1-p2latest-plugin-20261026/continued.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-p2latest-plugin-20261026/bin
set environment SHIFT_NATIVE_VULKAN_TRACE_RING 1
set $queue_wait_hits = 0
break sub_823B34A0
commands
  silent
  set $queue_wait_hits = $queue_wait_hits + 1
  if $queue_wait_hits == 1
    set $ctx = (unsigned char*)$rdi
    set $base = (unsigned char*)$rsi
    set $object = *(unsigned int*)$ctx
    set $head_ptr_raw = *(unsigned int*)($base+$object+0x2a90)
    set $head_ptr = (($head_ptr_raw & 0xff)<<24) | (($head_ptr_raw & 0xff00)<<8) | (($head_ptr_raw & 0xff0000)>>8) | (($head_ptr_raw & 0xff000000)>>24)
    set $head_raw = *(unsigned int*)($base+$head_ptr)
    set $head = (($head_raw & 0xff)<<24) | (($head_raw & 0xff00)<<8) | (($head_raw & 0xff0000)>>8) | (($head_raw & 0xff000000)>>24)
    set $tail_raw = *(unsigned int*)($base+$object+0x2a9c)
    set $tail = (($tail_raw & 0xff)<<24) | (($tail_raw & 0xff00)<<8) | (($tail_raw & 0xff0000)>>8) | (($tail_raw & 0xff000000)>>24)
    set $predicate = *(unsigned char*)($base+$object+0x2abd)
    printf "first_retail_queue_wait gdb_thread=%d object=%#x head=%u tail=%u predicate=%#x\\n", $_thread, $object, $head, $tail, $predicate
    python
import hashlib
from pathlib import Path
import gdb
pid = gdb.selected_inferior().pid
lines = [line for line in Path(f"/proc/{pid}/maps").read_text().splitlines() if "librexruntime.so" in line or "librexgpu-shift" in line]
for path in sorted({line.split()[-1] for line in lines}):
    print("mapped_library path=%s sha256=%s" % (path, hashlib.sha256(Path(path).read_bytes()).hexdigest()))
    end
    disable 1
  end
  continue
end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-p2latest-plugin-20261026/user --cache_root=/tmp/nfs-shift-p1-p2latest-plugin-20261026/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
