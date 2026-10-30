set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set logging file /tmp/xbox360_ntcreatefile_entry_trace.log
set logging overwrite on
set logging enabled on
set $hit = 0
break rex::kernel::xboxkrnl::NtCreateFile_entry
commands
  silent
  set $hit = $hit + 1
  set $ctxptr = $rbx
  set $guestlr = *(unsigned long*)($ctxptr + 0x100)
  python
import datetime, gdb
gdb.write("TIME=" + datetime.datetime.now().strftime("%H:%M:%S.%f") + " ")
end
  printf "NTCREATE_ENTRY hit=%u guest_lr=%08x\n", $hit, (unsigned int)$guestlr
  if ($hit >= 400)
    printf "TRACE_STOP hit_limit=%u\n", $hit
    kill
    quit
  end
  continue
end
run --game_data_root=/home/pes/work/process2-linux-retail-root-20261024/game --gpu_plugin=shift-native --no-async_shader_compilation
