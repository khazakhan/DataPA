"""All-rounds walk-forward test of OCJP FINAL 4 on one data set (user 2026-11-25).

Every round from --start to the last number: the unchanged script sees only the
numbers BEFORE that round (fresh sandbox copy each time, so live records are
never touched), its OCJP FINAL 4 is read from the RRR3_F4DUMP file
(CHAT_PAGE_OFF skips the second page build: same FINAL 4, ~7 s instead of 34 s),
and compared with the hidden number.  KING = EP repeat = the last visible number.

Each round is appended to holdout_sets/<set>_all.jsonl as soon as it is done,
so a stopped run resumes where it left off.

Usage: python3 tools/allrounds.py holdout_sets/set01.txt [--start 100] [--jobs 4]
       python3 tools/allrounds.py holdout_sets/set01.txt --report
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from holdout7 import sandbox, truncate  # noqa: E402


def f4_for(text):
    box = sandbox()
    try:
        dump = os.path.join(box, 'f4.json')
        env = {k: v for k, v in os.environ.items() if k != 'CHAT_PAGE_ROUND'}
        # OMA_OFF: the ONE-MEN-ARMY box re-runs the script in the real repo (tools/replay_collect.py) and
        # that inner run wrote the dump last; FINAL 4 identical without it (4 of 4 Set 6 rounds), 7 s -> 3 s
        env.update(CHAT_PAGE_OFF='1', OMA_OFF='1', RRR3_F4DUMP=dump)
        subprocess.run([sys.executable, 'DataProcessing.py'], input=text + 'END\n',
                       capture_output=True, text=True, env=env, cwd=box, timeout=600)
        if not os.path.exists(dump):
            return None, None, {}
        j = json.load(open(dump))
        return j['final4'], j.get('rank12'), {k: j[k] for k in ('rank_all', 'strong') if k in j}
    finally:
        shutil.rmtree(box, ignore_errors=True)


def report(out, name):
    rows = [json.loads(l) for l in open(out)] if os.path.exists(out) else []
    rows = sorted((r for r in rows if r['result'] is not None and r['final4']), key=lambda r: r['pos'])
    n = len(rows)
    if not n:
        print(f'{name}: no rounds yet'); return
    h = n // 2
    f4 = lambda rs: sum(r['result'] in r['final4'] for r in rs)
    m = lambda rs: sum(r['result'] == r['final4'][0] for r in rs)
    k = lambda rs: sum(r['result'] == r['king'] for r in rs)
    pct = lambda a, b: f'{100 * a / max(b, 1):.1f}%'
    print(f'**{name}: {n} rounds tested** (halves {h} | {n - h})')
    print('| Pick | Hits | Rate | Chance | 1st half | 2nd half |')
    print('|---|---|---|---|---|---|')
    for lab, fn, ch in (('OCJP FINAL 4', f4, '4%'), ('MASTER', m, '1%'), ('KING (EP repeat)', k, '1%')):
        a, b = fn(rows[:h]), fn(rows[h:])
        print(f'| {lab} | {a + b} | {pct(a + b, n)} | {ch} | {a} | {b} |')
    # best 7-round window and how many 7-round blocks reach 4+
    blocks = [rows[i:i + 7] for i in range(0, n - 6, 7)]
    best = max((f4(b) for b in blocks), default=0)
    pas = sum(f4(b) >= 4 for b in blocks)
    print(f'\n7-round blocks: {len(blocks)}, best block {best} of 7, blocks with 4+ FINAL 4 hits: {pas}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--start', type=int, default=100, help='first round = number index (needs history before it)')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--out', default=None, help='output jsonl (default holdout_sets/<set>_all.jsonl)')
    a = ap.parse_args()
    name = os.path.basename(a.path)[:-4]
    out = a.out or f'holdout_sets/{name}_all.jsonl'
    if a.report:
        report(out, name); return
    lines = open(a.path).readlines()
    toks = [t for l in lines for t in l.split()]
    done = {json.loads(l)['pos'] for l in open(out)} if os.path.exists(out) else set()
    todo = [p for p in range(a.start, len(toks)) if p not in done]
    print(f'{name}: {len(toks)} numbers, rounds {a.start}..{len(toks) - 1}, {len(done)} done, {len(todo)} to go',
          flush=True)
    lock = threading.Lock()
    count = [0]

    def one(pos):
        drop = len(toks) - pos          # hide toks[pos:] -> chart ends at toks[pos-1]
        hidden = toks[pos]
        prev = next((t for t in reversed(toks[:pos]) if t.isdigit()), None)
        f4, rank12, extra = f4_for(truncate(lines, drop))
        rec = {'pos': pos, 'result': int(hidden) if hidden.isdigit() else None,
               'final4': f4, 'king': int(prev) if prev else None, 'rank12': rank12, **extra}
        with lock:
            with open(out, 'a') as fh:
                fh.write(json.dumps(rec) + '\n')
            count[0] += 1
            if count[0] % 50 == 0:
                print(f'  {count[0]} of {len(todo)} done', flush=True)

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(one, todo))
    report(out, name)


if __name__ == '__main__':
    main()
