#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run a reproducible FIFO verification matrix and labelled negative control."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ((2, 5), (2, 8), (3, 13))  # (address bits, data bits)
CASES = (
    {'id':'happy-d4-w8', 'config':(2,8), 'scenario':0, 'seed':101, 'clocks':(5,7), 'phases':(0,2)},
    {'id':'boundary-d4-w5', 'config':(2,5), 'scenario':1, 'seed':211, 'clocks':(5,7), 'phases':(1,3)},
    {'id':'boundary-d8-w13','config':(3,13),'scenario':1, 'seed':307, 'clocks':(4,11),'phases':(2,5)},
    {'id':'concurrent-d4-w5-a','config':(2,5), 'scenario':2, 'seed':401, 'clocks':(7,5), 'phases':(0,3)},
    {'id':'concurrent-d4-w5-b','config':(2,5), 'scenario':2, 'seed':409, 'clocks':(3,10),'phases':(2,1)},
    {'id':'concurrent-d4-w8',  'config':(2,8), 'scenario':2, 'seed':503, 'clocks':(5,7), 'phases':(4,0)},
    {'id':'concurrent-d8-w13', 'config':(3,13),'scenario':2, 'seed':601, 'clocks':(11,4),'phases':(1,6)},
)
MUTANTS = {
    # A deliberately narrow defect: an all-ones request advances the pointer while full.
    # Concurrent and happy cases reserve that data value, so only boundary cases trigger it.
    'full_maxdata_pointer': (
        'wbin + (winc & ~wfull)',
        'wbin + (winc & (~wfull | (&wdata)))',
        'WRITE_POINTER_FAILED',
    ),
}
VARIANTS = ('correct', *MUTANTS)

def execute(command, cwd, timeout):
    start = time.monotonic()
    try:
        proc = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)
    except OSError as exc:
        return {'exit':None, 'timeout':False,
                'seconds':round(time.monotonic()-start,6), 'output':str(exc)}
    timed = False
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed = True
        os.killpg(proc.pid, signal.SIGKILL)
        output, _ = proc.communicate()
    return {'exit':proc.returncode, 'timeout':timed,
            'seconds':round(time.monotonic()-start,6), 'output':output}

def source_matches(source, provenance):
    return (provenance.get('revision') == '72d8122a7c5d458afabff2f858fe76f134010009'
            and provenance.get('sha256') == hashlib.sha256(source).hexdigest())

def expected_diagnostic(variant, case):
    return MUTANTS[variant][2] if variant in MUTANTS and case['scenario'] == 1 else None

def complete_matrix(cases):
    expected = {(variant, case['id']) for variant in VARIANTS for case in CASES}
    actual = [(case['variant'], case['case_id']) for case in cases]
    return len(actual) == len(expected) and set(actual) == expected

def accepted(result, expected, case=None):
    if result['timeout'] or result['exit'] is None:
        return False
    failures = re.findall(r'\b[A-Z_]+_FAILED\b', result['output'])
    if expected:
        return result['exit'] != 0 and failures == [expected] and 'FIFO_ASSERTIONS_PASS' not in result['output']
    if result['exit'] != 0 or failures or result['output'].count('FIFO_ASSERTIONS_PASS') != 1:
        return False
    match = re.search(r'EXERCISE scenario=(\d+) seed=(\d+) depth=(\d+) width=(\d+) writes=(\d+) reads=(\d+)', result['output'])
    if not match:
        return False
    scenario, seed, depth, width, writes, reads = map(int, match.groups())
    if writes <= 0 or writes != reads:
        return False
    if case is None:
        return True
    asize, dsize = case['config']
    return (scenario, seed, depth, width) == (case['scenario'], case['seed'], 1 << asize, dsize)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, default=ROOT/'evidence')
    args = parser.parse_args()
    out = args.evidence.resolve()/('run-'+uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    source_path = ROOT/'rtl/async_fifo.sv'
    source = source_path.read_text()
    provenance = json.loads((ROOT/'UPSTREAM.json').read_text())
    if not source_matches(source_path.read_bytes(), provenance):
        raise RuntimeError('FIFO source does not match pinned upstream provenance')
    sources = [source_path, ROOT/'tb/fifo_properties.sv', ROOT/'tb/tb.sv', Path(__file__).resolve()]
    report = {
        'schema_version':2,
        'scope':'Bound SVA and data-scoreboard simulation at depths 4/8, widths 5/8/13, directed boundary and concurrent dual-clock traffic',
        'upstream':provenance,
        'source_provenance_verified':True,
        'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        'verilator':execute(['verilator','--version'],out,10)['output'].strip(),
        'cases':[], 'builds':[],
    }
    for variant in VARIANTS:
        design = source
        if variant in MUTANTS:
            old, new, _ = MUTANTS[variant]
            if source.count(old) != 1:
                raise RuntimeError('Mutation target changed')
            design = source.replace(old,new)
        for asize,dsize in CONFIGS:
            work = out/variant/f'd{1 << asize}-w{dsize}'
            work.mkdir(parents=True)
            rtl = work/'async_fifo.sv'
            rtl.write_text(design)
            command = ['verilator','--binary','--timing','--assert','-Wno-fatal',
                       '--top-module','tb',f'-GASIZE={asize}',f'-GDSIZE={dsize}',
                       '--Mdir',str(work/'obj'),str(rtl),
                       str(ROOT/'tb/fifo_properties.sv'),str(ROOT/'tb/tb.sv')]
            build = execute(command,work,180)
            (work/'compile.log').write_text(build.pop('output'))
            report['builds'].append({'variant':variant,'depth':1 << asize,'width':dsize,
                **build,'command':command,'source_sha256':hashlib.sha256(rtl.read_bytes()).hexdigest()})
            if build['exit'] != 0 or build['timeout']:
                print('Build failed:',variant,asize,dsize)
                continue
            for case in (item for item in CASES if item['config'] == (asize,dsize)):
                w,r = case['clocks']; wp,rp = case['phases']
                command = [str(work/'obj/Vtb'),f'+WHALF={w}',f'+RHALF={r}',
                           f'+WPHASE={wp}',f'+RPHASE={rp}',f'+SEED={case["seed"]}',
                           f'+SCENARIO={case["scenario"]}']
                result = execute(command,work,20)
                expected = expected_diagnostic(variant,case)
                ok = accepted(result,expected,case)
                log = work/f'{case["id"]}.log'
                log.write_text(result.pop('output'))
                report['cases'].append({'variant':variant,'case_id':case['id'],
                    'scenario':case['scenario'],'depth':1 << asize,'width':dsize,
                    'half_periods_ns':[w,r],'phases_ns':[wp,rp],'seed':case['seed'],
                    'expected_diagnostic':expected,'accepted':ok,'command':command,
                    'log':str(log.relative_to(out)),**result})
                print(variant,case['id'],'EXPECTED' if ok else 'UNEXPECTED',flush=True)
    report['ok'] = (complete_matrix(report['cases'])
                    and len(report['builds']) == len(VARIANTS)*len(CONFIGS)
                    and all(x['exit'] == 0 and not x['timeout'] for x in report['builds'])
                    and all(x['accepted'] for x in report['cases']))
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(out/'summary.json')
    return 0 if report['ok'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
