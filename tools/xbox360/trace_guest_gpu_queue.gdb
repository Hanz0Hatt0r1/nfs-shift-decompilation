# Read-only exact-XEX guest queue trace for the Linux AMD64 ReXGlue executable.
# Run with:
#   gdb -q -nx -x trace_guest_gpu_queue.gdb -ex run --args ./nfs_shift \
#     --game_data_root=... --gpu_plugin=shift-native --no-async_shader_compilation \
#     > /tmp/<unique-trace-name>.log 2>&1
#
# ReXGlue PPCFunc uses void(PPCContext&, uint8_t*). Under the Linux AMD64
# System V ABI, rdi points to PPCContext and rsi is its virtual-memory base.
# PPCContext's 64-bit GPR fields put guest r3/r4/r13/lr at byte offsets
# 0/32/104/256. The trace reads guest RAM through rsi and never writes it.

set pagination off
set confirm off
set print thread-events off
set breakpoint pending off

set $interrupt_hits = 0
set $last_source0_state = -1
break sub_823B37B8
commands
  silent
  set $interrupt_hits = $interrupt_hits + 1
  set $ctx = (unsigned char*)$rdi
  set $base = (unsigned char*)$rsi
  set $source = *(unsigned int*)$ctx
  if $interrupt_hits == 1
    # Bind runtime observations to the plugin actually mapped in this inferior,
    # rather than assuming the artifact copied into the run directory was loaded.
    python
import gdb, hashlib
pid = gdb.selected_inferior().pid
mapped = {}
try:
    with open("/proc/%d/maps" % pid, encoding="utf-8") as maps:
        for line in maps:
            if "librexgpu-shift-native.so" not in line:
                continue
            fields = line.rstrip().split(None, 5)
            if len(fields) == 6:
                path = fields[5]
                mapped[path] = mapped.get(path, 0) + 1
    if not mapped:
        print("mapped_gpu_plugin pid=%d status=not-found" % pid)
    for path, segment_count in sorted(mapped.items()):
        hash_path = path.removesuffix(" (deleted)")
        try:
            with open(hash_path, "rb") as plugin_file:
                digest = hashlib.sha256(plugin_file.read()).hexdigest()
        except OSError as error:
            digest = "unavailable:%s" % error
        print("mapped_gpu_plugin pid=%d path=%s sha256=%s segments=%d" % (pid, path, digest, segment_count))
except OSError as error:
    print("mapped_gpu_plugin pid=%d status=maps-unavailable error=%s" % (pid, error))
    end
  end
  if $source == 0
    # r4 is the callback object on the source-0 path. The retail MMIO read at
    # 0x7FC86544 uses REX_MM_LOAD_U32, so base+guest-address is not its value.
    # The consumer's guest LR (0x823B3844) below is the direct taken-path proof.
    # Guest queue words are PPC big-endian in this little-endian host mapping.
    set $object = *(unsigned int*)($ctx+32)
    set $read_raw = *(unsigned int*)($base+$object+0x413c)
    set $read_index = (($read_raw & 0xff)<<24) | (($read_raw & 0xff00)<<8) | (($read_raw & 0xff0000)>>8) | (($read_raw & 0xff000000)>>24)
    set $write_raw = *(unsigned int*)($base+$object+0x4140)
    set $write_index = (($write_raw & 0xff)<<24) | (($write_raw & 0xff00)<<8) | (($write_raw & 0xff0000)>>8) | (($write_raw & 0xff000000)>>24)
    set $predicate = *(unsigned char*)($base+$object+0x2abd)
    set $source0_state = ((unsigned long long)$read_index << 32) | ((unsigned long long)$write_index << 8) | $predicate
    if $interrupt_hits <= 8 || $source0_state != $last_source0_state
      printf "source0_callback hit=%d gdb_thread=%d object=%#x queue_read=%u queue_write=%u predicate=%#x lr=%#llx\n", $interrupt_hits, $_thread, $object, $read_index, $write_index, $predicate, *(unsigned long long*)($ctx+256)
      set $last_source0_state = $source0_state
    end
  else
    if $interrupt_hits == 1 || $interrupt_hits % 64 == 0
      printf "interrupt_callback hit=%d source=%u gdb_thread=%d ctx=%p base=%p r4=%#llx r13=%#llx lr=%#llx\n", $interrupt_hits, $source, $_thread, (void*)$rdi, (void*)$rsi, *(unsigned long long*)($rdi+32), *(unsigned long long*)($rdi+104), *(unsigned long long*)($rdi+256)
    end
  end
  continue
end

set $consumer_hits = 0
set $last_consumer_state = -1
break sub_823A4640
commands
  silent
  set $consumer_hits = $consumer_hits + 1
  set $ctx = (unsigned char*)$rdi
  set $base = (unsigned char*)$rsi
  set $object = *(unsigned int*)$ctx
  set $read_raw = *(unsigned int*)($base+$object+0x413c)
  set $read_index = (($read_raw & 0xff)<<24) | (($read_raw & 0xff00)<<8) | (($read_raw & 0xff0000)>>8) | (($read_raw & 0xff000000)>>24)
  set $write_raw = *(unsigned int*)($base+$object+0x4140)
  set $write_index = (($write_raw & 0xff)<<24) | (($write_raw & 0xff00)<<8) | (($write_raw & 0xff0000)>>8) | (($write_raw & 0xff000000)>>24)
  set $predicate = *(unsigned char*)($base+$object+0x2abd)
  set $consumer_state = ((unsigned long long)$read_index << 32) | ((unsigned long long)$write_index << 8) | $predicate
  if $consumer_hits <= 8 || $consumer_state != $last_consumer_state
    printf "deferred_consumer hit=%d gdb_thread=%d object=%#x queue_read=%u queue_write=%u predicate=%#x lr=%#llx\n", $consumer_hits, $_thread, $object, $read_index, $write_index, $predicate, *(unsigned long long*)($ctx+256)
    set $last_consumer_state = $consumer_state
  end
  continue
end

set $software_queue_hits = 0
set $last_software_head = -1
set $last_software_tail = -1
set $last_software_global = -1
set $last_software_flag = -1
set $last_software_predicate = -1
break sub_823B33A0
commands
  silent
  set $software_queue_hits = $software_queue_hits + 1
  set $ctx = (unsigned char*)$rdi
  set $base = (unsigned char*)$rsi
  set $object = *(unsigned int*)$ctx
  set $head_ptr_raw = *(unsigned int*)($base+$object+0x2a90)
  set $head_ptr = (($head_ptr_raw & 0xff)<<24) | (($head_ptr_raw & 0xff00)<<8) | (($head_ptr_raw & 0xff0000)>>8) | (($head_ptr_raw & 0xff000000)>>24)
  set $head_raw = 0
  set $head = 0
  if $head_ptr != 0
    set $head_raw = *(unsigned int*)($base+$head_ptr)
    set $head = (($head_raw & 0xff)<<24) | (($head_raw & 0xff00)<<8) | (($head_raw & 0xff0000)>>8) | (($head_raw & 0xff000000)>>24)
  end
  set $tail_raw = *(unsigned int*)($base+$object+0x2a9c)
  set $tail = (($tail_raw & 0xff)<<24) | (($tail_raw & 0xff00)<<8) | (($tail_raw & 0xff0000)>>8) | (($tail_raw & 0xff000000)>>24)
  set $global_raw = *(unsigned int*)($base+0x831b3820)
  set $global = (($global_raw & 0xff)<<24) | (($global_raw & 0xff00)<<8) | (($global_raw & 0xff0000)>>8) | (($global_raw & 0xff000000)>>24)
  set $flag = *(unsigned char*)($base+$object+0x2abc)
  set $predicate = *(unsigned char*)($base+$object+0x2abd)
  if $software_queue_hits <= 12 || $head != $last_software_head || $tail != $last_software_tail || $global != $last_software_global || $flag != $last_software_flag || $predicate != $last_software_predicate || $software_queue_hits % 128 == 0
    printf "software_queue_helper hit=%d object=%#x head_ptr=%#x head=%u tail=%u global_831b3820=%u guard_2abc=%#x predicate_2abd=%#x lr=%#llx\n", $software_queue_hits, $object, $head_ptr, $head, $tail, $global, $flag, $predicate, *(unsigned long long*)($ctx+256)
    set $last_software_head = $head
    set $last_software_tail = $tail
    set $last_software_global = $global
    set $last_software_flag = $flag
    set $last_software_predicate = $predicate
  end
  continue
end

set $wait_hits = 0
set $last_wait_head = -1
set $last_wait_tail = -1
set $last_wait_predicate = -1
break sub_823B34A0
commands
  silent
  set $wait_hits = $wait_hits + 1
  set $ctx = (unsigned char*)$rdi
  set $base = (unsigned char*)$rsi
  set $object = *(unsigned int*)$ctx
  set $head_ptr_raw = *(unsigned int*)($base+$object+0x2a90)
  set $head_ptr = (($head_ptr_raw & 0xff)<<24) | (($head_ptr_raw & 0xff00)<<8) | (($head_ptr_raw & 0xff0000)>>8) | (($head_ptr_raw & 0xff000000)>>24)
  set $head_raw = 0
  set $head = 0
  if $head_ptr != 0
    set $head_raw = *(unsigned int*)($base+$head_ptr)
    set $head = (($head_raw & 0xff)<<24) | (($head_raw & 0xff00)<<8) | (($head_raw & 0xff0000)>>8) | (($head_raw & 0xff000000)>>24)
  end
  set $tail_raw = *(unsigned int*)($base+$object+0x2a9c)
  set $tail = (($tail_raw & 0xff)<<24) | (($tail_raw & 0xff00)<<8) | (($tail_raw & 0xff0000)>>8) | (($tail_raw & 0xff000000)>>24)
  set $predicate = *(unsigned char*)($base+$object+0x2abd)
  if $wait_hits == 1 || $head != $last_wait_head || $tail != $last_wait_tail || $predicate != $last_wait_predicate || $wait_hits % 128 == 0
    printf "ring_wait hit=%d gdb_thread=%d object=%#x head_ptr=%#x head=%u tail=%u predicate=%#x arg4=%#llx arg5=%#llx arg6=%#llx lr=%#llx\n", $wait_hits, $_thread, $object, $head_ptr, $head, $tail, $predicate, *(unsigned long long*)($rdi+32), *(unsigned long long*)($rdi+40), *(unsigned long long*)($rdi+48), *(unsigned long long*)($rdi+256)
    set $last_wait_head = $head
    set $last_wait_tail = $tail
    set $last_wait_predicate = $predicate
  end
  continue
end

set $predicate_hits = 0
break sub_823A0310
commands
  silent
  set $predicate_hits = $predicate_hits + 1
  if $predicate_hits == 1 || $predicate_hits % 256 == 0
    printf "wait_predicate hit=%d gdb_thread=%d ctx=%p base=%p record=%#llx arg4=%#llx lr=%#llx\n", $predicate_hits, $_thread, (void*)$rdi, (void*)$rsi, *(unsigned long long*)($rdi), *(unsigned long long*)($rdi+32), *(unsigned long long*)($rdi+256)
  end
  continue
end

set $producer_hits = 0
break sub_823A4758
commands
  silent
  set $producer_hits = $producer_hits + 1
  printf "deferred_producer hit=%d gdb_thread=%d ctx=%p base=%p input_r3=%#llx r13=%#llx lr=%#llx\n", $producer_hits, $_thread, (void*)$rdi, (void*)$rsi, *(unsigned long long*)($rdi), *(unsigned long long*)($rdi+104), *(unsigned long long*)($rdi+256)
  continue
end

set $callback_hits = 0
break sub_82649B68
commands
  silent
  set $callback_hits = $callback_hits + 1
  printf "registered_callback hit=%d gdb_thread=%d ctx=%p base=%p r3=%#llx r4=%#llx r13=%#llx lr=%#llx\n", $callback_hits, $_thread, (void*)$rdi, (void*)$rsi, *(unsigned long long*)($rdi), *(unsigned long long*)($rdi+32), *(unsigned long long*)($rdi+104), *(unsigned long long*)($rdi+256)
  continue
end
