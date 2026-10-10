#!/usr/bin/env python3
"""Bounded caller-cleaned slot+4 dispatch inventory; NOT global callback closure."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from collections import deque
from pathlib import Path

FORMAT = 'SHIFT.P1A.P13AFun0067b660Slot4DispatchAbiFrontier/1'
UPSTREAM = 'SHIFT.P1A.P13AFun0067b660StaticVtableObject/1'
RETAIL_SHA = 'eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TEXT_VA, TEXT_RAW = 0x00401000, 0x400
RANGES = {
    'registry_dispatch': (0x00614570, 0x006145e1, '66e3758fccaa6e1682c769bb68556f7d75dea76c51aa82bf8fd523e3ce7626bc'),
    'secondary_dispatch': (0x006022d0, 0x006022fe, '6eb7ca96c6e6201003cf2c6ef463680592c019b19f7dcf74528a1a6a251309a6'),
    'registry_registration_1': (0x005ff8bc, 0x005ff8da, '61d2d99bfffc233302cce7d7d317767b8f343ca6a98009a394e36fc30ed5e0a6'),
    'registry_registration_2': (0x005ffc50, 0x005ffc85, 'f98e932cd57e4e720b1853f379cb2ca7b00c08e38f35b30c48318d88c7040d70'),
}
INSN = re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
REG = r'(?:eax|ebx|ecx|edx|esi|edi|ebp)'
MEM_SLOT4 = re.compile(r'^DWORD PTR \[(' + REG + r')\+0x4\]$')
REGS = set(('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp'))
REGISTRY_SITES = [0x005ff8c6, 0x005ff8d5, 0x005ffc7a]


def instructions(lines):
    for line in lines:
        match = INSN.match(line)
        if match:
            yield (int(match.group(1), 16), match.group(2).lower(),
                   re.sub(r'\s+', ' ', match.group(3).strip()).replace(', ', ','))


def last_slot4_load(history, call_addr, target):
    """Return a near same-block slot+4 load, without crossing calls or jumps."""
    for addr, op, operand in reversed(history):
        if call_addr - addr > 100:
            break
        if op in {'call', 'jmp', 'ret', 'retn', 'retf'} or op.startswith('j'):
            break
        if ',' not in operand:
            continue
        dst, src = operand.split(',', 1)
        # Conservatively stop on any recognized destination-register write.
        if dst == target:
            if op == 'mov' and MEM_SLOT4.fullmatch(src):
                return (addr, src)
            break
        if op == 'xchg' and target in (dst, src):
            break
    return None


def scan(rows):
    """Scan streaming instructions. 'Immediate' means next decoded instruction."""
    history = deque(maxlen=16)
    raw_direct = 0
    reg_slot4 = 0
    raw_direct_cleanup = []
    reg_cleanup = []
    pending = None
    total = 0
    for row in rows:
        addr, op, operand = row
        total += 1
        if pending is not None:
            kind, site, load, pushed, base = pending
            if op == 'add' and operand == 'esp,0x4':
                item = {'call': f'0x{site:08x}', 'slot4_load': f'0x{load:08x}',
                        'pushed_argument': pushed, 'vtable_operand': base,
                        'caller_cleanup': f'0x{addr:08x}'}
                (reg_cleanup if kind == 'register' else raw_direct_cleanup).append(item)
            pending = None
        if op == 'call':
            mem = MEM_SLOT4.fullmatch(operand)
            if mem:
                raw_direct += 1
                # Only classify caller-cleaned one-argument shape with a push.
                push = history[-1] if history else None
                if push and push[1] == 'push':
                    pending = ('memory', addr, addr, push[2], operand)
            elif operand in REGS:
                load = last_slot4_load(history, addr, operand)
                if load is not None:
                    reg_slot4 += 1
                    push = history[-1] if history else None
                    if push and push[1] == 'push':
                        pending = ('register', addr, load[0], push[2], load[1])
        history.append(row)
    return {'decoded_instruction_count': total,
            'raw_memory_slot4_call_count': raw_direct,
            'near_register_slot4_call_count': reg_slot4,
            'raw_memory_slot4_immediate_cleanup': raw_direct_cleanup,
            'near_register_slot4_immediate_cleanup': reg_cleanup}


def machine_map(executable, start, stop):
    cmd = ['objdump', '-d', '-Mintel', f'--start-address=0x{start:x}',
           f'--stop-address=0x{stop:x}', str(executable)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return {addr: (op, operand) for addr, op, operand in instructions(out.splitlines())}


def require(table, addr, op, operand):
    actual = table.get(addr)
    if actual != (op, operand):
        raise AssertionError((hex(addr), actual, (op, operand)))
    return f'0x{addr:08x} {op} {operand}'


def analyze(executable: Path, upstream: Path):
    blob = executable.read_bytes()
    if hashlib.sha256(blob).hexdigest() != RETAIL_SHA:
        raise ValueError('retail executable SHA drift')
    parent = json.loads(upstream.read_text(encoding='utf-8'))
    if parent['format'] != UPSTREAM or parent['object_vtable']['address'] != '0x00af7544':
        raise ValueError('wrong upstream static vtable identity')
    if not parent['adjudication']['p13a_fun0067b660_static_vtable_object_identity_complete']:
        raise ValueError('upstream object identity incomplete')
    authority = {}
    maps = {}
    for name, (start, stop, expected_hash) in RANGES.items():
        offset = TEXT_RAW + start - TEXT_VA
        raw = blob[offset:offset + stop - start]
        if len(raw) != stop - start or hashlib.sha256(raw).hexdigest() != expected_hash:
            raise AssertionError(('machine range drift', name))
        authority[name] = {'start': f'0x{start:08x}', 'end_exclusive': f'0x{stop:08x}',
                           'size': stop - start, 'sha256': hashlib.sha256(raw).hexdigest()}
        maps[name] = machine_map(executable, start, stop)
    A = {}
    R = maps['registry_dispatch']
    for name, addr, op, operand in [
        ('registry_init_callback', 0x61457a, 'mov', 'eax,DWORD PTR [edi+0x4]'),
        ('registry_init_indirect_call', 0x614584, 'call', 'edx'),
        ('registry_result_store', 0x61458b, 'mov', 'DWORD PTR [edi+0x8],eax'),
        ('registry_array', 0x6145a9, 'mov', 'esi,0xbe8738'),
        ('registry_receiver_load', 0x6145b0, 'mov', 'eax,DWORD PTR [esi]'),
        ('registry_vptr_load', 0x6145be, 'mov', 'ecx,DWORD PTR [eax]'),
        ('registry_slot4_load', 0x6145c0, 'mov', 'edx,DWORD PTR [ecx+0x4]'),
        ('registry_arg', 0x6145c3, 'push', 'eax'),
        ('registry_call', 0x6145c4, 'call', 'edx'),
        ('registry_cleanup', 0x6145c6, 'add', 'esp,0x4'),
        ('registry_clear', 0x6145c9, 'mov', 'DWORD PTR [esi],0x0'),
    ]:
        A[name] = require(R, addr, op, operand)
    S = maps['secondary_dispatch']
    for name, addr, op, operand in [
        ('secondary_vptr_load', 0x6022e8, 'mov', 'eax,DWORD PTR [esi]'),
        ('secondary_slot4_load', 0x6022ea, 'mov', 'ecx,DWORD PTR [eax+0x4]'),
        ('secondary_arg', 0x6022ed, 'push', 'eax'),
        ('secondary_call', 0x6022ee, 'call', 'ecx'),
        ('secondary_cleanup', 0x6022f0, 'add', 'esp,0x4'),
    ]:
        A[name] = require(S, addr, op, operand)
    for site in REGISTRY_SITES:
        name = 'registry_registration_1' if site < 0x5ff900 else 'registry_registration_2'
        A[f'registry_registration_{site:08x}'] = require(maps[name], site, 'call', '0x6144f0')
    # Exact complete direct-call surface to the registry thunk (including .secu).
    all_rows = []
    proc = subprocess.Popen(['objdump', '-d', '-Mintel', str(executable)],
                            stdout=subprocess.PIPE, text=True, errors='replace')
    try:
        from collections import deque
        # Streaming parser keeps only 16 instruction records for slot4 provenance.
        def trace():
            assert proc.stdout is not None
            for insn in instructions(proc.stdout):
                if insn[1] == 'call' and insn[2] == '0x6144f0':
                    all_rows.append(insn[0])
                yield insn
        inventory = scan(trace())
    finally:
        if proc.stdout: proc.stdout.close()
    if proc.wait() != 0:
        raise RuntimeError('objdump failed')
    if all_rows != REGISTRY_SITES:
        raise AssertionError(('registry producer drift', all_rows))
    expected = [
        {'call': '0x006022ee', 'slot4_load': '0x006022ea', 'pushed_argument': 'eax',
         'vtable_operand': 'DWORD PTR [eax+0x4]', 'caller_cleanup': '0x006022f0'},
        {'call': '0x006145c4', 'slot4_load': '0x006145c0', 'pushed_argument': 'eax',
         'vtable_operand': 'DWORD PTR [ecx+0x4]', 'caller_cleanup': '0x006145c6'},
    ]
    if inventory['near_register_slot4_immediate_cleanup'] != expected:
        raise AssertionError(('register candidate drift', inventory['near_register_slot4_immediate_cleanup']))
    if inventory['raw_memory_slot4_immediate_cleanup']:
        raise AssertionError('raw memory immediate cleanup candidate drift')
    if inventory['raw_memory_slot4_call_count'] != 79:
        raise AssertionError('raw slot4 call inventory drift')
    return {
        'format': FORMAT, 'version': 1, 'owner': 'Process 1A / P1.3A', 'ready': True,
        'authority': {'platform': 'PC retail 1.02', 'retail_executable_sha256': RETAIL_SHA,
                      'upstream_contract': UPSTREAM, 'machine_ranges': authority},
        'slot4_abi_inventory': inventory,
        'registry_path': {'dispatch_call': '0x006145c4', 'array_base': '0x00be8730',
                          'callback_result_field': 'record+0x8',
                          'record_8_populated_by_callback_result': True,
                          'array_record_stride': 12, 'array_capacity': 8,
                          'receiver_loaded_from_registry': True,
                          'registry_receiver_is_initializer_callback_return': True,
                          'pushed_argument_equals_registry_receiver': True,
                          'direct_registration_thunk': '0x006144f0',
                          'direct_registration_calls': [f'0x{x:08x}' for x in all_rows],
                          'dynamic_registration_forwarder': '0x005ffc7a',
                          'registered_fun0067b660_object_proven': False,
                          'registry_dispatch_target_fun0067b660_proven': False},
        'secondary_path': {'dispatch_call': '0x006022ee',
                           'pushed_argument_is_loaded_vtable_pointer': True,
                           'pushed_argument_is_receiver_object_proven': False,
                           'target_fun0067b660_proven': False},
        'machine_anchors': A,
        'adjudication': {
            'p13a_fun0067b660_immediate_slot4_caller_cleanup_subset_complete': True,
            'fun0067b660_immediate_slot4_dispatch_target_proven': False,
            'fun0067b660_callback_argument_provenance_complete': False,
            'fun0067b660_callback_argument_is_selected_wheel_ruled_out': False,
            'callbacks_and_indirect_entry_ruled_out': False,
            'runtime_generated_selected_wheel_pointer_stores_ruled_out': False,
            'stored_or_escaped_aliases_ruled_out': False,
            'p13a_slot0_complete': False, 'p13a_slot1_complete': False,
            'p1_3_control_producer_complete': False, 'external_provider_count': 7},
        'limits': [
            '79 raw call [reg+4] sites are an opcode inventory, not 79 proven virtual dispatches.',
            'Near register-call provenance is bounded to 16 preceding decoded instructions and stops at intervening branches, calls, or writes to the target register.',
            'Caller cleanup requires immediate add esp,4 after the indirect call and an immediately preceding push; alternate cleanup, delayed aliases, and indirect target formation remain unclassified.',
            'Registry record+0x8 is populated from a separate initializer callback return at 0x00614584, not directly from registration input; that return identity is unresolved.',
            'The registry can accept dynamic registrations via 0x005ffc7a, so a connection to the animation object is not ruled out.',
            'The explicit callback argument for FUN_0067b660 remains unresolved; no global negative gate is promoted.'
        ],
        'next_step': 'Trace dynamic registration arguments through 0x005ffc7a or recover alternate indirect invocation forms of 0x00af7544 slot +0x4.'
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('executable', type=Path)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = analyze(args.executable, args.upstream)
    content = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(content, encoding='utf-8')
    else:
        print(content, end='')


if __name__ == '__main__':
    main()