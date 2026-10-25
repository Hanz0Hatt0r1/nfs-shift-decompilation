set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set solib-search-path /home/pes/work/xbox360-wsi-check-20261025/bin
set logging file /tmp/xbox360_ntcreatefile_root_probe.log
set logging overwrite on
set logging enabled on
set $hit = 0
break rex::kernel::xboxkrnl::NtCreateFile_entry
commands
  silent
  set $hit = $hit + 1
  python
import gdb
inf = gdb.selected_inferior()
ctx = int(gdb.parse_and_eval('$rbx'))
lr = int.from_bytes(inf.read_memory(ctx + 0x100, 8).tobytes(), 'little')
obj = int(gdb.parse_and_eval('$rcx'))
obj_guest = int.from_bytes(inf.read_memory(ctx + 0x28, 4).tobytes(), 'little')
base = obj - obj_guest
try:
    raw = inf.read_memory(obj, 8).tobytes()
    root = int.from_bytes(raw[0:4], 'big')
    name_ptr = int.from_bytes(raw[4:8], 'big')
    desc = inf.read_memory(base + name_ptr, 8).tobytes()
    length = int.from_bytes(desc[0:2], 'big')
    string_ptr = int.from_bytes(desc[4:8], 'big')
    name = inf.read_memory(base + string_ptr, length).tobytes().decode('ascii', 'replace') if length else ''
except Exception as exc:
    root, name = 0xffffffff, 'decode-error:' + str(exc)
gdb.write('NTCREATE hit=%d lr=0x%08x object_guest=0x%08x root=0x%08x path=%r\n' % (int(gdb.parse_and_eval('$hit')), lr & 0xffffffff, obj_guest, root, name))
end
  if ($hit >= 20)
    kill
    quit
  end
  continue
end
run --game_data_root=/home/pes/work/process2-linux-retail-root-20261024/game --gpu_plugin=shift-native --no-async_shader_compilation
