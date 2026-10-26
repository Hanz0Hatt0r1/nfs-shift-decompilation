set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set can-use-hw-watchpoints 1
file /tmp/nfs-shift-p1-p2-early-rptr-test-20261026/bin/nfs_shift
set logging file /tmp/nfs-shift-p1-early-cpu-watch-20261026-retry/gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-p2-early-rptr-test-20261026/bin
set environment SHIFT_NATIVE_VULKAN_TRACE_RING 1

break 'rex::memory::Memory::Initialize()'
commands
 silent
 printf "memory_initialize_entry\n"
 disable 1
 set $memory_init_return = *(void**)$rsp
 printf "memory_initialize_return_address=%p\n", $memory_init_return
 tbreak *$memory_init_return
 commands
  silent
  printf "memory_initialize_returned_watch_setup\n"
  x/wx 0x21b964004
  watch -l *(unsigned int*)0x21b964004
  commands
   silent
   printf "cpu_write physical value="
   x/wx 0x21b964004
   bt 8
   continue
  end
  watch -l *(unsigned int*)0x1bb964004
  commands
   silent
   printf "cpu_write vA value="
   x/wx 0x1bb964004
   bt 8
   continue
  end
  watch -l *(unsigned int*)0x1db964004
  commands
   silent
   printf "cpu_write vC value="
   x/wx 0x1db964004
   bt 8
   continue
  end
  watch -l *(unsigned int*)0x1fb963004
  commands
   silent
   printf "cpu_write vE value="
   x/wx 0x1fb963004
   bt 8
   continue
  end
  continue
 end
 continue
end

break shift::xbox::decode_captured_wait_reg_mem
commands
 silent
 python
raw = bytes(gdb.selected_inferior().read_memory(int(gdb.parse_and_eval("$rdi")), 24))
if int.from_bytes(raw[8:12], "big") == 0x1B964006:
    print("target_wait_decode raw=%s" % raw.hex())
end
 continue
end

handle SIGINT stop noprint nopass
python
import threading
import gdb
def bounded_interrupt():
    gdb.post_event(lambda: gdb.execute("interrupt"))
timer = threading.Timer(70.0, bounded_interrupt)
timer.daemon = True
timer.start()
end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-early-cpu-watch-20261026-retry/user --cache_root=/tmp/nfs-shift-p1-early-cpu-watch-20261026-retry/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
python
import os
import signal
retail_pid = gdb.selected_inferior().pid
print("bounded_probe_stopped pid=%d" % retail_pid)
end
detach
python
if retail_pid:
    os.kill(retail_pid, signal.SIGINT)
    print("sent SIGINT after detach pid=%d" % retail_pid)
end
