#!/usr/bin/env python3
"""Single-instance retail run.

Rotation is disabled for measurement: every frame this title presents is emitted
in its first ~45 s, and the 5 MB x 20 rotation discarded enough early content
that a clean baseline reported 616 presents where the same build measured 697.
Counting is only comparable with rotation out of the way.
"""
import os, signal, subprocess, sys, time
from pathlib import Path
from evdev import AbsInfo, UInput, ecodes
OUT=Path(os.environ.get("SHIFT_RUN_OUT", ".")).resolve(); BIN=OUT/"bin"
GOG="/home/pes/work/process2-retail-isolated-irq-20261023/game-data"
axes={ecodes.ABS_X:AbsInfo(0,-32768,32767,0,0,16), ecodes.ABS_Y:AbsInfo(0,-32768,32767,0,0,16),
      ecodes.ABS_RX:AbsInfo(0,-32768,32767,0,0,16), ecodes.ABS_RY:AbsInfo(0,-32768,32767,0,0,16),
      ecodes.ABS_Z:AbsInfo(0,0,255,0,0,0), ecodes.ABS_RZ:AbsInfo(0,0,255,0,0,0),
      ecodes.ABS_HAT0X:AbsInfo(0,-1,1,0,0,0), ecodes.ABS_HAT0Y:AbsInfo(0,-1,1,0,0,0)}
keys=[ecodes.BTN_SOUTH,ecodes.BTN_EAST,ecodes.BTN_NORTH,ecodes.BTN_WEST,ecodes.BTN_TL,
      ecodes.BTN_TR,ecodes.BTN_SELECT,ecodes.BTN_START,ecodes.BTN_THUMBL,ecodes.BTN_THUMBR]
dev=UInput({ecodes.EV_KEY:keys, ecodes.EV_ABS:[(c,i) for c,i in axes.items()]},
           name="Microsoft X-Box 360 pad", bustype=ecodes.BUS_USB,
           vendor=0x045E, product=0x028E, version=0x0114)
env=os.environ.copy(); env["LD_LIBRARY_PATH"]=str(BIN)
env["REX_LOG_MAX_FILE_SIZE_MB"]="100"   # max allowed: keep the whole run in one file
env["REX_LOG_MAX_FILES"]="100"
for extra in sys.argv[1:]:
    k,_,v=extra.partition("="); env[k]=v
p=subprocess.Popen([str(BIN/"nfs_shift"),"--game_data_root",GOG,
                    "--user_data_root",str(OUT/"user"),"--cache_root",str(OUT/"cache"),
                    "--gpu_plugin","shift-native","--no-async_shader_compilation",
                    "--fullscreen=false"],
                   cwd=str(BIN),env=env,stdout=open(OUT/"stdout.log","w"),
                   stderr=subprocess.STDOUT,preexec_fn=os.setsid)
print(f"pid={p.pid} t0={time.strftime('%H:%M:%S')}",flush=True)
def shot(tag):
    subprocess.run(["grim",str(OUT/"shots"/f"{tag}.png")],capture_output=True,timeout=30)
    print(f"shot {tag}",flush=True)
def tap(code,label,hold=0.3,gap=0.6):
    dev.write(ecodes.EV_KEY,code,1);dev.syn();time.sleep(hold)
    dev.write(ecodes.EV_KEY,code,0);dev.syn();time.sleep(gap)
    print(f"tap {label}",flush=True)
try:
    prev=0
    for t in (100,140):
        time.sleep(t-prev); prev=t
        shot(f"t{t}")
    for lbl,c in [("Start",ecodes.BTN_START),("A1",ecodes.BTN_SOUTH),
                  ("A2",ecodes.BTN_SOUTH),("A3",ecodes.BTN_SOUTH)]:
        tap(c,lbl)
    shot("after_input")
    time.sleep(20); shot("t240_after")
finally:
    os.killpg(os.getpgid(p.pid),signal.SIGTERM); time.sleep(2)
    try: os.killpg(os.getpgid(p.pid),signal.SIGKILL)
    except Exception: pass
    dev.close()
print("done",flush=True)
