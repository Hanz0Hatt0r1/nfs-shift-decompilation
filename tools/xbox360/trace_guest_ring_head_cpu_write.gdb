set pagination off
set confirm off
set debuginfod enabled off
set print thread-events off
set breakpoint pending off
break sub_823A0310
continue
set $ctx = (unsigned char*)$rdi
set $base = (unsigned char*)$rsi
set $record = *(unsigned int*)$ctx
set $owner_raw = *(unsigned int*)($base+$record)
set $object = (($owner_raw & 0xff)<<24) | (($owner_raw & 0xff00)<<8) | (($owner_raw & 0xff0000)>>8) | (($owner_raw & 0xff000000)>>24)
set $head_ptr_raw = *(unsigned int*)($base+$object+0x2a90)
set $head_ptr = (($head_ptr_raw & 0xff)<<24) | (($head_ptr_raw & 0xff00)<<8) | (($head_ptr_raw & 0xff0000)>>8) | (($head_ptr_raw & 0xff000000)>>24)
set $head_addr = $base+$head_ptr
set $head_raw = *(unsigned int*)$head_addr
set $head = (($head_raw & 0xff)<<24) | (($head_raw & 0xff00)<<8) | (($head_raw & 0xff0000)>>8) | (($head_raw & 0xff000000)>>24)
set $tail_raw = *(unsigned int*)($base+$object+0x2a9c)
set $tail = (($tail_raw & 0xff)<<24) | (($tail_raw & 0xff00)<<8) | (($tail_raw & 0xff0000)>>8) | (($tail_raw & 0xff000000)>>24)
set $r30 = *(unsigned long long*)($ctx+240)
set $predicate = *(unsigned char*)($base+$object+0x2abd)
printf "watch_setup object=%#x head_ptr=%#x head=%u tail=%u expected_r30=%#llx predicate=%#x host_addr=%p\n", $object, $head_ptr, $head, $tail, $r30, $predicate, $head_addr
watch -location *(unsigned int*)$head_addr
set $head_watch = $bpnum
set $head_hits = 0
commands $head_watch
  silent
  set $write_raw = *(unsigned int*)$head_addr
  set $write_value = (($write_raw & 0xff)<<24) | (($write_raw & 0xff00)<<8) | (($write_raw & 0xff0000)>>8) | (($write_raw & 0xff000000)>>24)
  set $tail_raw = *(unsigned int*)($base+$object+0x2a9c)
  set $tail = (($tail_raw & 0xff)<<24) | (($tail_raw & 0xff00)<<8) | (($tail_raw & 0xff0000)>>8) | (($tail_raw & 0xff000000)>>24)
  set $predicate = *(unsigned char*)($base+$object+0x2abd)
  set $head_hits = $head_hits + 1
  if $head_hits <= 12 || $head_hits % 128 == 0
    printf "head_write hit=%d gdb_thread=%d value=%u tail=%u predicate=%#x pc=%p\n", $head_hits, $_thread, $write_value, $tail, $predicate, $pc
    if $head_hits <= 12
      info symbol $pc
      bt 4
    end
  end
  continue
end
disable 1
handle SIGINT stop noprint nopass
continue
