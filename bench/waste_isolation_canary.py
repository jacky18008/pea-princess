#!/usr/bin/env python3
"""Two optional post-stop canaries within the original eight-call/3M allowance.

This is a new version, not a replacement arm or continuation of the cancelled
v1 matrix. prepare/status are offline. run-one dispatches once with no retries.
"""
import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys

import waste_probe as base
from call_control import CallControl, _digest

IDS = ['q01', 'q02']


def controller(root, ids):
    return CallControl(root/'controller', ids, allow_tools=True)


def combined_gate(prior, current):
    prior_snap = prior.snapshot(); current_snap = current.snapshot()
    if set(prior_snap['calls']) != {'p%02d' % n for n in range(1,7)} or set(prior_snap['skipped']) != {'p07','p08'}:
        raise ValueError('requires the stopped six-call v1 plan with two cancellations')
    tokens = 0
    for snapshot in (prior_snap, current_snap):
        for row in snapshot['calls'].values():
            result = row['record']
            if not result or row['failure_kind']:
                raise ValueError('unresolved/failed/unknown usage blocks canary')
            usage = result.get('direct_terminal_usage')
            if not isinstance(usage,dict) or any(type(usage.get(k)) is not int for k in ('input_tokens','output_tokens')):
                raise ValueError('unknown usage blocks canary')
            tokens += usage['input_tokens'] + usage['output_tokens']
    if len(prior_snap['calls']) + len(current_snap['calls']) >= 8 or tokens >= base.LIMIT:
        raise ValueError('combined eight-call/3M stop reached')
    return tokens


def prepare(output, prior):
    output=Path(output).resolve(); prior=Path(prior).resolve()
    if output.exists(): raise ValueError('refuse existing canary directory')
    output.mkdir(parents=True,mode=0o700)
    old=controller(prior,[r['id'] for r in base.layout()]); new=controller(output,IDS)
    known=combined_gate(old,new)
    files=base.seed_files()
    current_skill_sources=subprocess.check_output(['git','ls-files','skills/vet-flat'],cwd=base.ROOT,text=True).splitlines()
    sources=sorted(set(base.read(prior/'plan.json')['source_sha256']) |
                   {rel for rel in current_skill_sources if (base.ROOT/rel).is_file()} |
                   {'bench/waste_isolation_canary.py'})
    plan={'version':2,'purpose':'post-stop isolated guided sanity checks; not a matched causal cost comparison',
          'model':'gpt-5.6-luna','effort':'low','calls':IDS,'prior_run':str(prior),
          'prior_checkpoint_sha256':base.sha(prior/'controller/checkpoint.json'),
          'prior_known_processed':known,'combined_call_limit':8,'combined_processed_stop':base.LIMIT,
          'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=base.ROOT,text=True).strip(),
          'source_sha256':{rel:base.sha(base.ROOT/rel) for rel in sources},
          'timeout_seconds':300,'prompt':base.COMMON + base.TREATMENT,
          'quality_gate':'Same critical criteria as v1. Stop if first canary has a critical failure; root review required before second. No claim of statistical equivalence or isolated causal effect of bundled changes.'}
    base.write(output/'plan.json',plan); base.write(output/'frozen.json',{'plan_sha256':_digest(plan)})
    for sid in IDS:
        home=output/sid;home.mkdir(mode=0o700)
        base.native.prepare_workdir(home/'work',files)
    return {'prepared':str(output),'max_additional_calls':2,'prior_known_processed':known,'model_calls':0}


def verify(output):
    plan=base.read(output/'plan.json')
    if _digest(plan)!=base.read(output/'frozen.json')['plan_sha256'] or plan['calls']!=IDS:
        raise ValueError('frozen canary plan differs')
    if base.sha(Path(plan['prior_run'])/'controller/checkpoint.json')!=plan['prior_checkpoint_sha256']:
        raise ValueError('original stopped ledger changed')
    for rel,digest in plan['source_sha256'].items():
        if base.sha(base.ROOT/rel)!=digest: raise ValueError('canary source changed: '+rel)
    return plan


def run_one(output):
    output=Path(output).resolve()
    with (output/'canary.lock').open('a+b') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        plan=verify(output); current=controller(output,IDS)
        known=combined_gate(controller(Path(plan['prior_run']),[r['id'] for r in base.layout()]),current)
        done=current.snapshot()['calls']; sid=next(s for s in IDS if s not in done)
        if done and (not (output/'first-review.json').is_file() or base.read(output/'first-review.json').get('continue') is not True):
            raise ValueError('first isolated canary needs passing critical review')
        home=output/sid; work=home/'work'
        if base.native._snapshot(work)!=base.read(base.native._marker(work))['value']['initial']:
            raise ValueError('unused canary fixture changed')
        request={'model':plan['model'],'effort':plan['effort'],'timeout_seconds':plan['timeout_seconds'],
                 'prompt':plan['prompt'],'skip_host_skill_discovery':True,'isolate_workspace_reads':True}
        folder=home/'record';folder.mkdir(mode=0o700);base.write(folder/'request.json',request)
        result=current.run(sid,sid,'answer','isolated-canary',lambda:base.native.invoke(request,folder,work))
        base.write(folder/'result.json',result)
        return {'id':sid,'status':result['status'],'known_combined_before':known,
                'direct_usage':result['direct_terminal_usage'],'answer':result['answer']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run-one','status'))
    parser.add_argument('--output',required=True);parser.add_argument('--prior')
    args=parser.parse_args();output=Path(args.output).resolve()
    if args.action=='prepare':
        if not args.prior: parser.error('prepare requires --prior')
        result=prepare(output,args.prior)
    elif args.action=='run-one':result=run_one(output)
    else: verify(output);result=controller(output,IDS).report()
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
