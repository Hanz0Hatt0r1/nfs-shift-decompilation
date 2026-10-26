set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set logging file /tmp/nfs-shift-p1-worker-event-20261026/gdb-event-set.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-worker-event-20261026/bin
set environment SHIFT_NATIVE_VULKAN_TRACE_RING 1
set $worker_hits = 0
set $event_set_hits = 0
set $event_pulse_hits = 0
set $event0_guest = 0
set $event1_guest = 0
set $base = 0
break sub_823B8AC8
commands
  silent
  set $worker_hits = $worker_hits + 1
  set $ctx = (unsigned char*)$rdi
  set $base = (unsigned char*)$rsi
  set $object = *(unsigned int*)$ctx
  set $event_guest = $object + 32
  if $worker_hits == 1
    set $event0_guest = $event_guest
  end
  if $worker_hits == 2
    set $event1_guest = $event_guest
  end
  printf "worker_entry hit=%d gdb_thread=%d object=%#x event_guest=%#x event_header=%08x event_state=%08x\n", $worker_hits, $_thread, $object, $event_guest, *(unsigned int*)($base+$event_guest), *(unsigned int*)($base+$event_guest+4)
  continue
end
break rex::system::XEvent::Set(unsigned int, bool)
commands
  silent
  if $event0_guest != 0 && (this->guest_object_ptr_ == $event0_guest || this->guest_object_ptr_ == $event1_guest)
    set $event_set_hits = $event_set_hits + 1
    printf "worker_event_set hit=%d gdb_thread=%d event_guest=%#x increment=%u wait=%d\n", $event_set_hits, $_thread, this->guest_object_ptr_, priority_increment, wait
  end
  continue
end
break rex::system::XEvent::Pulse(unsigned int, bool)
commands
  silent
  if $event0_guest != 0 && (this->guest_object_ptr_ == $event0_guest || this->guest_object_ptr_ == $event1_guest)
    set $event_pulse_hits = $event_pulse_hits + 1
    printf "worker_event_pulse hit=%d gdb_thread=%d event_guest=%#x increment=%u wait=%d\n", $event_pulse_hits, $_thread, this->guest_object_ptr_, priority_increment, wait
  end
  continue
end
break rex::kernel::xboxkrnl::xeKeWaitForSingleObject
commands
  silent
  if $event0_guest != 0 && ((unsigned long)$rdi == (unsigned long)$base + $event0_guest || (unsigned long)$rdi == (unsigned long)$base + $event1_guest)
    printf "worker_event_wait gdb_thread=%d event_host=%#lx reason=%u mode=%u alertable=%u timeout=%#lx\n", $_thread, $rdi, $rsi, $rdx, $rcx, $r8
  end
  continue
end
break sub_823A4758
commands
  silent
  printf "producer_enter gdb_thread=%d\n", $_thread
  continue
end
break sub_82649B68
commands
  silent
  printf "registered_callback_enter gdb_thread=%d\n", $_thread
  continue
end
break sub_823B34A0
commands
  silent
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
  printf "first_retail_queue_wait gdb_thread=%d object=%#x head=%u tail=%u predicate=%#x workers=%d event_sets=%d event_pulses=%d\n", $_thread, $object, $head, $tail, $predicate, $worker_hits, $event_set_hits, $event_pulse_hits
  info breakpoints
  python
import hashlib
from pathlib import Path
import gdb
pid = gdb.selected_inferior().pid
lines = [line for line in Path(f"/proc/{pid}/maps").read_text().splitlines()
         if "librexruntime.so" in line or "librexgpu-shift" in line]
capture = Path("/tmp/nfs-shift-p1-worker-event-20261026/mapped-libraries.txt")
capture.write_text("\n".join(lines) + "\n")
for path in sorted({line.split()[-1] for line in lines}):
    print("mapped_library path=%s sha256=%s" % (path, hashlib.sha256(Path(path).read_bytes()).hexdigest()))
print("mapped_libraries_capture path=%s sha256=%s" % (capture, hashlib.sha256(capture.read_bytes()).hexdigest()))
  end
  quit
end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-worker-event-20261026/user --cache_root=/tmp/nfs-shift-p1-worker-event-20261026/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
run
