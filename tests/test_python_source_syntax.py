import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _python_sources():
    return sorted(
        path
        for path in ROOT.rglob("*.py")
        if ".git" not in path.parts
        and "__pycache__" not in path.parts
    )


def test_all_python_sources_parse_as_valid_python():
    failures = []

    for path in _python_sources():
        try:
            ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
            )
        except SyntaxError as exc:
            failures.append(
                f"{path.relative_to(ROOT)}:"
                f"{exc.lineno}:{exc.offset}:"
                f" {exc.msg}"
            )

    assert not failures, "Python syntax failures:\n" + "\n".join(
        failures
    )


def test_gdb_probe_is_included_in_syntax_audit():
    target = ROOT / "tools" / "gdb_sdf_solver_probe.py"

    assert target in _python_sources()
