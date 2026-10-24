# Read-only exact-XEX guest queue trace for the Linux AMD64 ReXGlue executable.
# Run with:
#   gdb -q -nx -x trace_guest_gpu_queue.gdb -ex run --args ./nfs_shift \
#     --game_data_root=... --gpu_plugin=shift-native --no-async_shader_compilation \
#     > /tmp/<unique-trace-name>.log 2>&1
#
# ReXGlue PPCFunc uses void(PPCContext&, uint8_t*). Under the Linux AMD64
# System V ABI, rdi points to PPCContext and rsi is its virtual-memory base.
# PPCContext's 64-bit GPR fields put guest r3/r4/r13/lr at byte offsets
# 0/32/104/256. No guest memory is modified or read by this trace.

set pagination off
set confirm off
set print thread-events off
set breakpoint pending off

set $interrupt_hits = 0
break sub_823B37B8
commands
  silent
  set $interrupt_hits = $interrupt_hits + 1
  if $interrupt_hits == 1 || $interrupt_hits % 64 == 0
    printf "source0_callback hit=%d gdb_thread=%d ctx=%p base=%p r3=%#llx r4=%#llx r13=%#llx lr=%#llx\n", $interrupt_hits, $_thread, (void*)$rdi, (void*)$rsi, *(unsigned long long*)($rdi), *(unsigned long long*)($rdi+32), *(unsigned long long*)($rdi+104), *(unsigned long long*)($rdi+256)
  end
  continue
end

set $consumer_hits = 0
break sub_823A4640
commands
  silent
  set $consumer_hits = $consumer_hits + 1
  if $consumer_hits == 1 || $consumer_hits % 64 == 0
    printf "deferred_consumer hit=%d gdb_thread=%d ctx=%p base=%p object=%#llx r4=%#llx lr=%#llx\n", $consumer_hits, $_thread, (void*)$rdi, (void*)$rsi, *(unsigned long long*)($rdi), *(unsigned long long*)($rdi+32), *(unsigned long long*)($rdi+256)
  end
  continue
end

set $wait_hits = 0
break sub_823B34A0
commands
  silent
  set $wait_hits = $wait_hits + 1
  if $wait_hits == 1 || $wait_hits % 128 == 0
    printf "ring_wait hit=%d gdb_thread=%d ctx=%p base=%p object=%#llx arg4=%#llx arg5=%#llx arg6=%#llx lr=%#llx\n", $wait_hits, $_thread, (void*)$rdi, (void*)$rsi, *(unsigned long long*)($rdi), *(unsigned long long*)($rdi+32), *(unsigned long long*)($rdi+40), *(unsigned long long*)($rdi+48), *(unsigned long long*)($rdi+256)
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
