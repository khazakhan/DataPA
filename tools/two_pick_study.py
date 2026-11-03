"""MegaStar / PowerStar study (user 2026-11-04, S33 screenshot: 'pick only
two numbers beside table 4').  Scores several ways to pick 2 numbers on all
live rounds: FINAL 4 #1-2, most lists holding a number (vote count incl. the
*, ~ columns), and votes weighted by each list's past hit rate (walk-forward,
using only earlier rounds).  python3 tools/two_pick_study.py"""
import json, sys, os, io, contextlib
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
R = [json.loads(l) for l in open('rrr_records/live.jsonl')]
def extra(r):
    ep = r['ep']; st, ti = set(), set()
    for row in r['rows']:
        ox, oy = AB[row['old'][0]], AB[row['old'][1]]
        for fn, out in ((D._star_ops, st), (D._tilde_ops, ti)):
            a, b = fn(ox, oy)
            out |= {D.apply_op(ep // 10, a) * 10 + D.apply_op(ep % 10, b), D.apply_op(ep // 10, b) * 10 + D.apply_op(ep % 10, a)}
    return {'star': st, 'tilde': ti}
SKIP = {'top4', 'top10', 'top20', 'top40'}
def lists(r):
    L = {k: set(v) for k, v in r['lists'].items() if k not in SKIP and v}
    L.update(extra(r)); L['prime10'] = set(r.get('prime10', [])); L['p4fam'] = set(r.get('prime4fam', []))
    return L
rank_of = lambda r, v: r['ranked'].index(v) if v in r['ranked'] else 99
hits = {'FINAL 4 #1-2': 0, 'most lists': 0, 'weighted lists (walk-forward)': 0, 'random 2 (expected)': 0}
rate = {}                 # list -> [hits, size] from earlier rounds only
for r in R:
    L = lists(r); res = r['result']
    hits['FINAL 4 #1-2'] += res in r['ranked'][:2]
    votes = {v: sum(v in s for s in L.values()) for v in range(100)}
    two = sorted(range(100), key=lambda v: (-votes[v], rank_of(r, v)))[:2]; hits['most lists'] += res in two
    w = {k: ((rate[k][0] + 1) / (rate[k][1] / 100 + 1)) if k in rate else 1 for k in L}
    wv = {v: sum(w[k] for k, s in L.items() if v in s) for v in range(100)}
    two = sorted(range(100), key=lambda v: (-wv[v], rank_of(r, v)))[:2]; hits['weighted lists (walk-forward)'] += res in two
    for k, s in L.items():
        a = rate.setdefault(k, [0, 0]); a[0] += res in s; a[1] += len(s)
    hits['random 2 (expected)'] += 0.02
for k, v in hits.items():
    print(f'  {k:32s}: {v:5.1f} of {len(R)}')
