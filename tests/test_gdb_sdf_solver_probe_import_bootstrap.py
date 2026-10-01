import subprocess
import sys
from pathlib import Path


def test_gdb_sdf_probe_imports_provider_modules_without_sitecustomize(tmp_path: Path):
    repo = Path(__file__).resolve().parents[1]
    script = repo / "tools" / "gdb_sdf_solver_probe.py"

    code = r'''
import runpy
import sys
import types

class _Breakpoint:
    def __init__(self, *args, **kwargs):
        pass
    def delete(self):
        pass

class _FinishBreakpoint(_Breakpoint):
    pass

class _Command:
    def __init__(self, *args, **kwargs):
        pass

gdb = types.ModuleType("gdb")
gdb.Breakpoint = _Breakpoint
gdb.FinishBreakpoint = _FinishBreakpoint
gdb.Command = _Command
gdb.BP_BREAKPOINT = 0
gdb.COMMAND_USER = 0
sys.modules["gdb"] = gdb

runpy.run_path(sys.argv[1], run_name="__main__")
print("ok")
'''

    result = subprocess.run(
        [sys.executable, "-S", "-c", code, str(script)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("ok")
