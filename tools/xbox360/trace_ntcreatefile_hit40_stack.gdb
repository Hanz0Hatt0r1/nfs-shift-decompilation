set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set logging file /tmp/xbox360_ntcreatefile_hit40_confirm.log
set logging overwrite on
set logging enabled on
set $hit = 0
break rex::kernel::xboxkrnl::NtCreateFile_entry
commands
  silent
  set $hit = $hit + 1
  if ($hit == 40)
    python
import datetime, gdb
gdb.write("TIME=" + datetime.datetime.now().strftime("%H:%M:%S.%f") + " ")
end
    printf "NTCREATE_ENTRY hit=%u guest_lr=%08x\n", $hit, (unsigned int)*(unsigned long*)($rbx + 0x100)
    bt 18
  end
  if ($hit == 41)
    printf "TRACE_STOP hit=%u\n", $hit
    kill
    quit
  end
  continue
end
run --game_data_root=/home/pes/work/process2-linux-retail-root-20261024/game --gpu_plugin=shift-native --no-async_shader_compilation
