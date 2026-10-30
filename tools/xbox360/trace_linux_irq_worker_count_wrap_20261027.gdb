set pagination off
set confirm off
set print thread-events off
set breakpoint pending on
set debuginfod enabled off
handle SIGSEGV nostop noprint pass
set logging file /tmp/nfs-shift-p1-worker-count-underflow-followup-20261027/gdb.log
set logging overwrite on
set logging enabled on
set environment LD_LIBRARY_PATH /tmp/nfs-shift-p1-ring-irq-crosswalk-20261027/bin
set environment SHIFT_NATIVE_VULKAN_TRACE_RING 1
python
import gdb, os, signal, threading, time
start=time.monotonic(); wall0=time.time()
state={'manager':0,'base':0,'watch':None,'irq':0,'callback_fn':0,'enqueue':0,'worker':0,'last_worker':None,'writes':0,'stopped':False}
def le(a,n): return int.from_bytes(bytes(gdb.selected_inferior().read_memory(a,n)),'little')
def be(a,n): return int.from_bytes(bytes(gdb.selected_inferior().read_memory(a,n)),'big')
def gr(c,o): return le(c+o,4)
def now(): return time.monotonic()-start
def wall(): return wall0+now()
class CountWatch(gdb.Breakpoint):
 def __init__(self,a): self.addr=a; self.old=be(a,4); super().__init__('*(unsigned int*)%#x'%a,type=gdb.BP_WATCHPOINT,wp_class=gdb.WP_WRITE,internal=True)
 def stop(self):
  v=be(self.addr,4); state['writes']+=1
  if state['writes']<=20 or (v&0xffffffff)==0xffffffff:
   print('COUNT_FIELD_WRITE n=%d wall=%.6f elapsed=%.3f old=%#x new=%#x pc=%#x thread=%s irq=%d enqueue=%d worker=%d last_worker=%r'%(state['writes'],wall(),now(),self.old,v,int(gdb.parse_and_eval('$pc')),gdb.selected_thread().global_num,state['irq'],state['enqueue'],state['worker'],state['last_worker']))
  self.old=v
  if v==0xffffffff:
   state['stopped']=True; print('FIRST_NEGATIVE_COUNT_STACK'); print(gdb.execute('bt 10',to_string=True)); return True
  return False
class Arm(gdb.Breakpoint):
 def __init__(self): super().__init__('sub_823B34A0',internal=True)
 def stop(self):
  try:
   c=int(gdb.parse_and_eval('$rdi')); b=int(gdb.parse_and_eval('$rsi')); obj=gr(c,0); lr=le(c+256,8)&0xffffffff
   if not state['manager'] and lr==0x823A557C:
    state['manager']=obj; state['base']=b; state['watch']=CountWatch(b+obj+11012)
    print('COUNT_FIELD_ARM wall=%.6f elapsed=%.3f manager=%#x address=%#x initial=%#x'%(wall(),now(),obj,b+obj+11012,be(b+obj+11012,4)))
  except Exception as e: print('ARM_ERROR',e)
  return False
class Callback(gdb.Breakpoint):
 def __init__(self): super().__init__('sub_823B37B8',internal=True)
 def stop(self):
  try:
   c=int(gdb.parse_and_eval('$rdi')); b=int(gdb.parse_and_eval('$rsi')); source=gr(c,0)
   if source==1:
    state['irq']+=1; a=gr(c,32); rec=be(b+a+10900,4); fn=be(b+rec+16,4) if rec else 0; arg=be(b+rec+20,4) if rec else 0; prev=state['callback_fn']; state['callback_fn']=fn
    if fn!=prev: print('CALLBACK_TARGET_CHANGE irq=%d wall=%.6f elapsed=%.3f old=%#x new=%#x arg=%#x'%(state['irq'],wall(),now(),prev,fn,arg))
    if fn==0x823B8C60 and (state['irq']<=10 or state['irq']%100==0): print('IRQ_QUEUE_CALLBACK irq=%d wall=%.6f elapsed=%.3f fn=%#x arg=%#x current_count=%#x'%(state['irq'],wall(),now(),fn,arg,be(state['base']+state['manager']+11012,4) if state['manager'] else 0))
  except Exception as e: print('CALLBACK_ERROR',e)
  return False
class Enqueue(gdb.Breakpoint):
 def __init__(self): super().__init__('sub_823B8C60',internal=True)
 def stop(self):
  state['enqueue']+=1
  if state['enqueue']<=10 or state['enqueue']%100==0:
   try:
    c=int(gdb.parse_and_eval('$rdi')); t=gr(c,0); print('IRQ_QUEUE_ENQUEUE n=%d wall=%.6f elapsed=%.3f task=%#x lr=%#x'%(state['enqueue'],wall(),now(),t,le(c+256,8)&0xffffffff))
   except Exception as e: print('ENQUEUE_ERROR',e)
  return False
class Worker(gdb.Breakpoint):
 def __init__(self): super().__init__('sub_823B85D0',internal=True)
 def stop(self):
  state['worker']+=1
  try:
   c=int(gdb.parse_and_eval('$rdi')); b=int(gdb.parse_and_eval('$rsi')); obj=gr(c,0); q=gr(c,32); entry=gr(c,40); task=be(b+entry,4)
   fields=tuple('%08x'%be(b+obj+o,4) for o in (36,56,60,64,72,76,104))
   state['last_worker']=(obj,q,entry,task,fields)
   if state['worker']<=10 or state['worker']%100==0: print('IRQ_WORK_ENTER n=%d wall=%.6f elapsed=%.3f worker=%#x queue=%#x entry=%#x task=%#x fields=%s'%(state['worker'],wall(),now(),obj,q,entry,task,fields))
  except Exception as e: print('WORK_ERROR',e)
  return False
Arm(); Callback(); Enqueue(); Worker()
def stop(): gdb.post_event(lambda:gdb.execute('interrupt'))
timer=threading.Timer(100.0,stop); timer.daemon=True; timer.start()
end
set args --game_data_root=/home/pes/work/process2-retail-isolated-irq-20261023/game-data --user_data_root=/tmp/nfs-shift-p1-worker-count-underflow-followup-20261027/user --cache_root=/tmp/nfs-shift-p1-worker-count-underflow-followup-20261027/cache --gpu_plugin=shift-native --no-async_shader-compilation --fullscreen=false
run
python
pid=gdb.selected_inferior().pid
print('COUNT_TRACE_END wall=%.6f elapsed=%.3f state=%r pid=%s'%(wall(),now(),{k:v for k,v in state.items() if k!='watch'},pid))
if pid:
 try: gdb.execute('detach'); os.kill(pid,signal.SIGINT); print('COUNT_TRACE_DETACHED pid=%d'%pid)
 except ProcessLookupError: print('COUNT_TRACE_TITLE_EXITED pid=%d'%pid)
end
quit
