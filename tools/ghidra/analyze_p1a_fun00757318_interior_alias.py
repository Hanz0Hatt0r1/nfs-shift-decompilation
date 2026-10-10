#!/usr/bin/env python3
"""Hash-locked retail proof for five indexed-wheel interior aliases in FUN_00757318."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = 'SHIFT.P1A.P13AFun00757318InteriorAliasClosure/1'
UPSTREAM = 'SHIFT.P1A.P13AFun007572f0IndexedWheelRootLifetime/1'
RETAIL_SHA = 'eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TEXT_VA, TEXT_RAW = 0x00401000, 0x00000400
RANGES = {
    'indexed_body': (0x00757318, 0x00757beb, '40e942861f5e15b40542c88c11f7b08131c0280d47cf43109889c3363bfbdcee'),
    'interpolating_writer': (0x007a06a0, 0x007a07b7, '06bffad36d14d0a5a9c0e4774acaa1b04f5ea3cf1895f39d65c9d9a381b8cb02'),
    'scalar_writer': (0x007a0420, 0x007a0451, 'c1bb69f90c4bb2db3e12b615ed2b06d8af00ea4a21b2d7b627941000f1075b7f'),
}
# site, derived wheel-relative offset, consuming callsite, target
ALIASES = (
    (0x007573bc, 0x610, 0x007573fd, 0x007a06a0),
    (0x0075740f, 0x638, 0x00757428, 0x007a06a0),
    (0x0075743a, 0x5e8, 0x00757453, 0x007a06a0),
    (0x007577b8, 0x6a0, 0x007577e4, 0x007a0420),
    (0x007577f6, 0x6c0, 0x0075780f, 0x007a0420),
)
INST = re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
REGISTER = re.compile(r'\b(?:eax|ebx|ecx|edx|esi|edi|esp|ebp|ax|al|ah|cx|cl|ch)\b')
FPU_WRITE = re.compile(r'^QWORD PTR \[(esi|ecx)(?:\+0x([0-9a-f]+))?\]$')


def normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', s.strip()).replace(', ', ',')


def disassemble(exe: Path, start: int, end: int):
    cmd = ['objdump', '-d', '-Mintel', f'--start-address=0x{start:x}',
           f'--stop-address=0x{end:x}', str(exe)]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, errors='replace')
    out = []
    for line in result.stdout.splitlines():
        m = INST.match(line)
        if m:
            out.append((int(m.group(1), 16), m.group(2).lower(), normalize(m.group(3))))
    return out


def require(rows, addr: int, mnemonic: str, operands: str = '') -> str:
    actual = {a: (m, o) for a, m, o in rows}.get(addr)
    expected = (mnemonic, normalize(operands))
    if actual != expected:
        raise AssertionError(f'instruction drift {addr:#x}: {actual} != {expected}')
    return f'0x{addr:08x} {mnemonic} {expected[1]}'.rstrip()


def check_alias_to_call(rows, site: int, offset: int, call: int, target: int):
    require(rows, site, 'lea', f'ecx,[edi+0x{offset:x}]')
    require(rows, call, 'call', f'0x{target:x}')
    between = [(a, m, o) for a, m, o in rows if site < a < call]
    # Only FPU and stack-argument construction may intervene. Any ECX write or
    # control-flow transfer would invalidate the exact receiver handoff.
    allowed = {'fld', 'fst', 'fstp', 'fadd', 'fsub', 'fmul', 'fdiv',
               'fxch', 'fchs', 'fldz', 'fld1', 'sub', 'add'}
    for a, m, o in between:
        if m not in allowed:
            raise AssertionError(('unexpected handoff instruction', hex(a), m, o))
        if m in {'sub', 'add'} and not o.startswith('esp,'):
            raise AssertionError(('unexpected arithmetic', hex(a), m, o))
        if REGISTER.search(o) and re.search(r'\becx\b', o):
            raise AssertionError(('receiver clobbered', hex(a), m, o))
    return {'site': f'0x{site:08x}', 'wheel_relative_offset': f'+0x{offset:x}',
            'consumer_call': f'0x{call:08x}', 'consumer': f'FUN_{target:08x}',
            'receiver_register': 'ECX', 'intervening_instruction_count': len(between)}


def classify_interpolating_writer(rows):
    require(rows, 0x007a06b1, 'mov', 'esi,ecx')
    require(rows, 0x007a06cc, 'lea', 'ecx,[ebp+0x10]')
    require(rows, 0x007a06d2, 'call', '0x753620')
    require(rows, 0x007a071f, 'lea', 'ecx,[ebp-0x10]')
    require(rows, 0x007a0777, 'call', '0x7af310')
    require(rows, 0x007a079e, 'ret', '0x18')
    require(rows, 0x007a07b4, 'ret', '0x18')
    expected_calls = [(0x007a06d2, '0x753620'), (0x007a0777, '0x7af310')]
    calls = [(a, o) for a, m, o in rows if m == 'call']
    if calls != expected_calls:
        raise AssertionError(('interpolating writer call surface', calls))
    # ESI is the exact derived receiver after 0x7a06b1. A callee-saved
    # prologue PUSH before capture is not a pointer escape. All subsequent
    # ESI uses are 64-bit FPU scalar stores, or epilogue restoration.
    scalar_stores = []
    for a, m, o in rows:
        if a <= 0x007a06b1 or not re.search(r'\besi\b', o):
            continue
        if m == 'pop' and o == 'esi':
            continue
        hit = FPU_WRITE.fullmatch(o) if m in ('fst', 'fstp') else None
        if not hit or hit.group(1) != 'esi':
            raise AssertionError(('derived receiver escape/unsupported use', hex(a), m, o))
        scalar_stores.append((a, int(hit.group(2), 16) if hit.group(2) else 0))
    if [off for _, off in scalar_stores] != [0x20, 0, 8, 0x10, 0x18, 0, 8, 0x10, 0x18]:
        raise AssertionError(('interpolating scalar write set', scalar_stores))
    return {'entry_receiver_capture': '0x007a06b1 ESI=ECX',
            'complete_function_size': RANGES['interpolating_writer'][1] - RANGES['interpolating_writer'][0],
            'scalar_fpu_write_count': len(scalar_stores),
            'scalar_fpu_write_offsets': [f'+0x{x:x}' for _, x in scalar_stores],
            'only_direct_callees': [{'call': f'0x{a:08x}', 'target': target} for a, target in calls],
            'callee_receivers_are_stack_locals': True,
            'derived_receiver_stored_as_pointer': False,
            'derived_receiver_forwarded': False,
            'derived_receiver_returned': False}


def classify_scalar_writer(rows):
    require(rows, 0x007a044e, 'ret', '0x18')
    writes = []
    for a, m, o in rows:
        if m in ('call', 'jmp', 'push') and m != 'push':
            raise AssertionError(('unexpected transfer', hex(a), m, o))
        if not re.search(r'\becx\b', o):
            continue
        hit = FPU_WRITE.fullmatch(o) if m in ('fst', 'fstp') else None
        if not hit or hit.group(1) != 'ecx':
            raise AssertionError(('scalar writer pointer escape', hex(a), m, o))
        writes.append((a, int(hit.group(2), 16) if hit.group(2) else 0))
    if [off for _, off in writes] != [0, 8, 0x10, 0x18]:
        raise AssertionError(('scalar writer write set', writes))
    if any(m in ('call', 'jmp') for _, m, _ in rows):
        raise AssertionError('scalar writer is not a leaf')
    return {'complete_function_size': RANGES['scalar_writer'][1] - RANGES['scalar_writer'][0],
            'scalar_fpu_write_count': len(writes),
            'scalar_fpu_write_offsets': [f'+0x{x:x}' for _, x in writes],
            'direct_call_count': 0, 'derived_receiver_stored_as_pointer': False,
            'derived_receiver_forwarded': False, 'derived_receiver_returned': False}


def analyze(exe: Path, upstream: Path):
    binary = exe.read_bytes()
    sha = hashlib.sha256(binary).hexdigest()
    if sha != RETAIL_SHA:
        raise ValueError(f'unsupported retail image {sha}')
    source = json.loads(upstream.read_text(encoding='utf-8'))
    if source.get('format') != UPSTREAM or not source.get('ready'):
        raise ValueError('wrong or unready indexed-root upstream contract')
    if source['indexed_root']['formula'] != 'vehicle_root + 0x400 + index*0xA80':
        raise AssertionError('indexed root provenance changed')
    expected_sites = [f'0x{x[0]:08x}' for x in ALIASES]
    if [x['site'] for x in source['exact_root_lifetime']['derived_interior_aliases']] != expected_sites:
        raise AssertionError('derived-alias upstream surface changed')
    auth = {}; rows = {}
    for name, (start, end, expected_sha) in RANGES.items():
        raw = binary[TEXT_RAW + start - TEXT_VA:TEXT_RAW + end - TEXT_VA]
        digest = hashlib.sha256(raw).hexdigest()
        if len(raw) != end-start or digest != expected_sha:
            raise AssertionError(('range drift', name, digest))
        auth[name] = {'start': f'0x{start:08x}', 'end_exclusive': f'0x{end:08x}',
                      'size': end-start, 'sha256': digest}
        rows[name] = disassemble(exe, start, end)
    found = []
    for site, offset, call, target in ALIASES:
        found.append(check_alias_to_call(rows['indexed_body'], site, offset, call, target))
    interpolating = classify_interpolating_writer(rows['interpolating_writer'])
    scalar = classify_scalar_writer(rows['scalar_writer'])
    return {'format': FORMAT, 'version': 1, 'ready': True, 'owner': 'Process 1A / P1.3A',
            'authority': {'platform': 'PC retail 1.02', 'retail_executable_sha256': sha,
                          'upstream_contract': UPSTREAM, 'ranges': auth,
                          'ghidra_receiver_abi': 'FUN_007a06a0 and FUN_007a0420 are __thiscall; ECX=this'},
            'scope': {'indexed_wheel_root': source['indexed_root']['formula'],
                      'derived_alias_count': len(found), 'aliases': found},
            'consumer_adjudication': {'FUN_007a06a0': interpolating,
                                      'FUN_007a0420': scalar,
                                      'all_five_aliases_are_interior_not_root': True,
                                      'any_interior_alias_pointer_persisted': False,
                                      'any_interior_alias_reconstructed_as_root': False},
            'adjudication': {
                'p13a_fun00757318_interior_alias_subset_complete': True,
                'p13a_fun00757318_interior_alias_persistent_escape_found': False,
                'runtime_generated_selected_wheel_pointer_stores_ruled_out': False,
                'reconstructed_wheel_pointers_ruled_out': False,
                'other_derived_aliases_ruled_out': False,
                'stored_or_escaped_aliases_ruled_out': False,
                'callbacks_and_indirect_entry_ruled_out': False,
                'p13a_slot0_complete': False, 'p13a_slot1_complete': False,
                'p1_3_control_producer_complete': False, 'external_provider_count': 7},
            'limits': [
                'Closes only five machine-verified FUN_00757318 interior aliases from the merged indexed-wheel-root path.',
                'The interpolating writer retains the receiver in ESI, passes stack-local ECX receivers to its two direct callees, and writes only QWORD scalar fields to the derived receiver.',
                'The second writer is a 49-byte leaf that writes four QWORD scalar fields and does not copy or forward its ECX receiver.',
                'Other runtime reconstructed roots, callbacks, incoming indirect entry and global selected-wheel pointer persistence remain open.'
            ],
            'next_step': 'Compose the bounded indexed/trampolined wheel-root materializer closures; keep broad alias, runtime-callback, slot0/slot1 and P1.3 gates fail-closed.'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('executable', type=Path)
    p.add_argument('upstream', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    report = json.dumps(analyze(args.executable, args.upstream), sort_keys=True, indent=2) + '\n'
    if args.output:
        args.output.write_text(report, encoding='utf-8')
    else:
        print(report, end='')


if __name__ == '__main__':
    main()