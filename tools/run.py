#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute bound FIFO assertions and labelled negative controls."""
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
PAIRS = ((5,7), (7,5), (4,11))
MUTANTS = {
    'sync_bypass': ('{wptr_rq1, wgray}', '{wgray, wgray}', 'WRITE_SYNC_PIPELINE_FAILED'),
    'full_pointer': ('wbin + (winc & ~wfull)', 'wbin + winc', 'WRITE_POINTER_FAILED'),
}

def execute(command, cwd, timeout):
    start = time.monotonic()
    try:
        proc = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, start_new_session=True)
    except OSError as exc:
        return {'exit': None, 'timeout': False, 'seconds': round(time.monotonic()-start,6), 'output': str(exc)}
    timed = False
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed = True
        os.killpg(proc.pid, signal.SIGKILL)
        output, _ = proc.communicate()
    return {'exit': proc.returncode, 'timeout': timed, 'seconds': round(time.monotonic()-start,6), 'output': output}

def source_matches(source, provenance):
    return provenance.get("revision") == "72d8122a7c5d458afabff2f858fe76f134010009" and provenance.get("sha256") == hashlib.sha256(source).hexdigest()

def complete_matrix(cases):
    expected={(variant, pair) for variant in ("correct", *MUTANTS) for pair in PAIRS}
    actual=[(case["variant"], tuple(case["half_periods_ns"])) for case in cases]
    return len(actual)==len(expected) and set(actual)==expected

def accepted(result, expected):
    if result['timeout'] or result['exit'] is None:
        return False
    if expected:
        failures = re.findall(r'\b[A-Z_]+_FAILED\b', result['output'])
        return result['exit'] != 0 and failures == [expected] and 'FIFO_ASSERTIONS_PASS' not in result['output']
    return result['exit'] == 0 and not re.search(r'\b[A-Z_]+_FAILED\b', result['output']) and result['output'].count('FIFO_ASSERTIONS_PASS') == 1 and bool(re.search(r'EXERCISE received=16 blocked_writes=[1-9]\d* blocked_reads=[1-9]\d* write_wraps=[4-9]\d* read_wraps=[4-9]\d*',result['output']))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, default=ROOT/'evidence')
    args = parser.parse_args()
    out = args.evidence.resolve() / ('run-'+uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    source = (ROOT/'rtl/async_fifo.sv').read_text()
    provenance = json.loads((ROOT/'UPSTREAM.json').read_text())
    if not source_matches((ROOT/'rtl/async_fifo.sv').read_bytes(), provenance):
        raise RuntimeError('FIFO source does not match pinned upstream provenance')
    sources = [ROOT/'rtl/async_fifo.sv', ROOT/'tb/fifo_properties.sv', ROOT/'tb/tb.sv', Path(__file__).resolve()]
    report = {'schema_version':1, 'scope':'Bound SVA simulation at ASIZE=2, DSIZE=8, common startup reset assertion with staggered idle release, three clock pairs',
              'upstream':provenance, 'source_provenance_verified':True,
              'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
              'verilator':execute(['verilator','--version'],out,10)['output'].strip(), 'cases':[], 'builds':[]}
    for variant in ('correct', *MUTANTS):
        work = out/variant
        work.mkdir()
        design = source
        expected = None
        if variant in MUTANTS:
            old, new, expected = MUTANTS[variant]
            if source.count(old)!=1:
                raise RuntimeError('Mutation target changed')
            design = source.replace(old,new)
        rtl = work/'async_fifo.sv'
        rtl.write_text(design)
        command = ['verilator','--binary','--timing','--assert','-Wno-fatal','--top-module','tb','--Mdir',str(work/'obj'),
                   str(rtl),str(ROOT/'tb/fifo_properties.sv'),str(ROOT/'tb/tb.sv')]
        build = execute(command,work,180)
        (work/'compile.log').write_text(build.pop('output'))
        report['builds'].append({'variant':variant,**build,'command':command,'source_sha256':hashlib.sha256(rtl.read_bytes()).hexdigest()})
        if build['exit'] != 0 or build['timeout']:
            print('Build failed:',variant)
            break
        for w,r in PAIRS:
            command = [str(work/'obj/Vtb'),f'+WHALF={w}',f'+RHALF={r}']
            result = execute(command,work,15)
            ok = accepted(result,expected)
            log = work/f'{w}-{r}.log'
            log.write_text(result.pop('output'))
            report['cases'].append({'variant':variant,'half_periods_ns':[w,r],'expected_diagnostic':expected,
                                    'accepted':ok, 'command':command,'log':str(log.relative_to(out)),**result})
            print(variant,w,r,'EXPECTED' if ok else 'UNEXPECTED',flush=True)
    report['ok'] = complete_matrix(report['cases']) and all(x['accepted'] for x in report['cases'])
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(out/'summary.json')
    return 0 if report['ok'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
