set pagination off
set confirm off
set print thread-events off
set breakpoint pending off
set disable-randomization off
handle SIGSEGV stop print nopass
handle SIGBUS stop print nopass
set environment LD_LIBRARY_PATH /tmp/nfs-p1-private-bin-20261025
set $sink=0
set $post=0
set $lastbase=0
set $lastsrc=0
set $lastdst=0
set $lastsize=0
break sub_82BA8DA8 if *(unsigned int*)($rdi+256)==0x82ba92b8
commands
 silent
 set $sink=$sink+1
 set $lastbase=$rsi
 set $obj=*(unsigned int*)$rdi
 set $lastsrc=*(unsigned int*)($rdi+48)
 set $raww=*(unsigned int*)($rsi+$obj+4)
 set $rawwh=*(unsigned int*)($rsi+$obj+8)
 set $width=(($raww&0xff)<<24)|(($raww&0xff00)<<8)|(($raww>>8)&0xff00)|(($raww>>24)&0xff)
 set $height=(($rawwh&0xff)<<24)|(($rawwh&0xff00)<<8)|(($rawwh>>8)&0xff00)|(($rawwh>>24)&0xff)
 set $rawdst=*(unsigned int*)($rsi+$obj+20)
 set $lastdst=(($rawdst&0xff)<<24)|(($rawdst&0xff00)<<8)|(($rawdst>>8)&0xff00)|(($rawdst>>24)&0xff)
 set $lastsize=$width*$height*4
 if $sink<=4
  printf "bink_buffer_compare hit=%d obj=%#x selector=%#x count=%#x src=%#x width=%u height=%u dst=%#x bytes=%u lr=%#x thread=%d\n",$sink,$obj,*(unsigned int*)($rdi+32),*(unsigned int*)($rdi+40),$lastsrc,$width,$height,$lastdst,$lastsize,*(unsigned int*)($rdi+256),$_thread
  if $lastsrc!=0
   printf "source_first24:\n"
   x/24bx $lastbase+$lastsrc
  end
  if $lastdst!=0
   printf "dest_first24_before:\n"
   x/24bx $lastbase+$lastdst
  end
 end
 continue
end
break sub_82B9C770 if *(unsigned int*)($rdi+256)==0x82ba8e28
commands
 silent
 set $post=$post+1
 if $post<=4
  printf "bink_buffer_after_copy hit=%d src=%#x dst=%#x bytes=%u thread=%d\n",$post,$lastsrc,$lastdst,$lastsize,$_thread
  if $lastsrc!=0
   printf "source_first24_after:\n"
   x/24bx $lastbase+$lastsrc
  end
  if $lastdst!=0
   printf "dest_first24_after:\n"
   x/24bx $lastbase+$lastdst
  end
 end
 continue
end
catch signal SIGSEGV
commands
 silent
 printf "caught_SIGSEGV pc=%p\n",(void*)$pc
 bt 12
 quit
end
catch signal SIGBUS
commands
 silent
 printf "caught_SIGBUS pc=%p\n",(void*)$pc
 bt 12
 quit
end
run --game_data_root=/home/pes/work/process2-linux-retail-root-20261024/game --user_data_root=/tmp/nfs-p1-bink-buffer-registerfix-20261025/user --cache_root=/tmp/nfs-p1-bink-buffer-registerfix-20261025/cache --gpu_plugin=shift-native --no-async_shader_compilation --fullscreen=false
printf "probe_returned sink=%d post_copy=%d stop_pc=%p thread=%d\n",$sink,$post,(void*)$pc,$_thread
