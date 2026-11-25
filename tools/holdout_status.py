"""One-look status of the 24-set all-rounds test (for 'start our project' after a restart).
Per set: rounds done / to do, FINAL 4 hits so far, and whether a test process is running.
Usage: python3 tools/holdout_status.py"""
import json, os, subprocess
START = {'24': 574}
run = subprocess.run(['pgrep', '-af', 'python3 tools/allrounds.py holdout_sets/set'], capture_output=True, text=True).stdout
print('| Set | Done | Total | FINAL 4 hits | Rate | State |\n|---|---|---|---|---|---|')
for n in range(1, 25):
    s = f'{n:02d}'; src = f'holdout_sets/set{s}.txt'
    if not os.path.exists(src):
        continue
    toks = open(src).read().split()
    total = len(toks) - START.get(s, 100)
    out = f'holdout_sets/set{s}_r12.jsonl'
    rows = []
    if os.path.exists(out):
        for l in open(out):
            try: rows.append(json.loads(l))
            except ValueError: pass
    sc = [r for r in rows if r.get('result') is not None and r.get('final4')]
    hits = sum(r['result'] in r['final4'] for r in sc)
    state = 'RUNNING' if f'set{s}.txt' in run else ('done' if len({r['pos'] for r in rows}) >= total else ('waiting' if not rows else 'PART'))
    print(f'| {s} | {len({r["pos"] for r in rows})} | {total} | {hits} | {100*hits/max(len(sc),1):.2f}% | {state} |')
