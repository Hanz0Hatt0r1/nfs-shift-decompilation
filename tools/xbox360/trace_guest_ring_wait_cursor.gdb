set pagination off
set confirm off
set debuginfod enabled off
set $wait_hits = 0
break sub_823A0310
commands
  silent
  set $wait_hits = $wait_hits + 1
  set $ctx = (unsigned char*)$rdi
  set $base = (unsigned char*)$rsi
  set $record = *(unsigned int*)$ctx
  set $owner_raw = *(unsigned int*)($base+$record)
  set $object = (($owner_raw & 0xff)<<24) | (($owner_raw & 0xff00)<<8) | (($owner_raw & 0xff0000)>>8) | (($owner_raw & 0xff000000)>>24)
  set $count_raw = *(unsigned int*)($base+$record+4)
  set $count = (($count_raw & 0xff)<<24) | (($count_raw & 0xff00)<<8) | (($count_raw & 0xff0000)>>8) | (($count_raw & 0xff000000)>>24)
  set $snapshot_raw = *(unsigned int*)($base+$record+8)
  set $snapshot = (($snapshot_raw & 0xff)<<24) | (($snapshot_raw & 0xff00)<<8) | (($snapshot_raw & 0xff0000)>>8) | (($snapshot_raw & 0xff000000)>>24)
  set $prev_raw = *(unsigned int*)($base+$record+12)
  set $prev = (($prev_raw & 0xff)<<24) | (($prev_raw & 0xff00)<<8) | (($prev_raw & 0xff0000)>>8) | (($prev_raw & 0xff000000)>>24)
  set $r29 = *(unsigned long long*)($ctx+232)
  set $r30 = *(unsigned long long*)($ctx+240)
  set $r4 = *(unsigned long long*)($ctx+32)
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
  if $wait_hits <= 4 || $wait_hits % 256 == 0
    printf "wait_cursor hit=%d thread=%d object=%#x count=%u snapshot=%u previous=%u r30=%#llx r4=%#llx head=%u tail=%u predicate=%#x lr=%#llx\n", $wait_hits, $_thread, $object, $count, $snapshot, $prev, $r30, $r4, $head, $tail, $predicate, *(unsigned long long*)($ctx+256)
  end
  continue
end
handle SIGINT stop noprint nopass
continue
