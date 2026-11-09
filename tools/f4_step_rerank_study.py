"""Can the chart-step pattern improve OCJP FINAL 4?  For every logged live round
(rrr_records/live.jsonl, ranking logged BEFORE the result), re-rank the top-K OCJP
numbers by how often the chart moved from the EP's digits to theirs (learned only
on the dataset before that round), and score the new top 4."""
import json, collections, os
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
def load(f): return [int(t) for t in open(f).read().split() if t.isdigit()]
cache = {}
def steps(ds):
    if ds not in cache:
        s = load(ds); S = list(zip(s, s[1:]))
        t = collections.Counter((b // 10 - a // 10) % 10 for a, b in S)
        u = collections.Counter((b % 10 - a % 10) % 10 for a, b in S)
        n = len(S); cache[ds] = ({k: t[k] / n for k in range(10)}, {k: u[k] / n for k in range(10)}, s[-1])
    return cache[ds]
res = collections.defaultdict(lambda: [0, 0])
for r in L:
    if not os.path.exists(r['dataset']) or len(r.get('ranked', [])) < 4: continue
    tp, up, e = steps(r['dataset']); R = r['result']; rk = r['ranked']
    sc = lambda v: tp[(v // 10 - e // 10) % 10] * up[(v % 10 - e % 10) % 10]
    ser = r['round'][0]
    def add(name, pick):
        for key in (name, name + ' [' + ser + ']'):
            res[key][0] += R in pick; res[key][1] += 1
    add('A current top4', rk[:4])
    for K in (6, 8, 10, 20):
        add(f'B top{K} re-sorted by steps', sorted(rk[:K], key=lambda v: -sc(v))[:4])
    for K in (8, 10):
        pos = {v: i for i, v in enumerate(rk)}
        add(f'C top{K} rank+steps blend', sorted(rk[:K], key=lambda v: pos[v] / K - 4 * sc(v) / max(sc(x) for x in rk[:K]))[:4])
    tens_ok = [v for v in rk if tp[(v // 10 - e // 10) % 10] >= sorted(tp.values())[-3]]
    add('D top4 among OCJP with top-3 tens step', (tens_ok + [v for v in rk if v not in tens_ok])[:4])
    allsc = sorted(range(100), key=lambda v: -sc(v))
    add('E SHADOW (steps only)', allsc[:4])
for k in sorted(res):
    if '[' in k: continue
    h, n = res[k]; print(f"{k:42} {h:4} of {n}  ({h/n:5.1%})  chance {n*0.04:.1f}")
print()
for ser in 'XY':
    for k in sorted(res):
        if k.endswith(f'[{ser}]'):
            h, n = res[k]; print(f"{k:46} {h:3} of {n}")
