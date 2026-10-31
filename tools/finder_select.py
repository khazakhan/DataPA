"""Greedy choice of (row type, change) pairs on train series, tested on others."""
import json, sys
from math import comb
def load(names, d):
    out = []
    for n in names: out += json.load(open(f"{d}/fs{n}.json"))
    return out
def rtype(rel):
    base = rel.split('|')[0]
    t = base if base in ('EP', 'full', 'units', 'tens', 'none') else base[:-2] + '±1'
    return [t] + (['LAST'] if '|LAST' in rel else [])
def preds(rnd, pairs):
    s = set()
    for row in rnd['rows']:
        for rt in rtype(row['rel']):
            for ch in pairs.get(rt, ()):
                s.add(row['ch'][ch])
    return s
def score(data, sel):
    pairs = {}
    for rt, ch in sel: pairs.setdefault(rt, set()).add(ch)
    hits = size = 0
    for r in data:
        p = preds(r, pairs); size += len(p); hits += r['res'] in p
    return hits, size / 100, size / max(1, len(data))
def p_at_least(k, n, p):
    return sum(comb(n, i) * p**i * (1-p)**(n-i) for i in range(k, n+1))
def greedy(train, max_avg):
    cands = {(rt, ch) for r in train for row in r['rows'] for rt in rtype(row['rel']) for ch in row['ch']}
    sel = []
    while True:
        best = None
        h0, e0, a0 = score(train, sel)
        for c in cands - set(sel):
            h, e, a = score(train, sel + [c])
            if a > max_avg: continue
            gain = (h - h0) - (e - e0)
            if best is None or gain > best[0]: best = (gain, c)
        if not best or best[0] <= 0.3: break
        sel.append(best[1])
    return sel
if __name__ == '__main__':
    d = sys.argv[1]; train_names = sys.argv[2].split(','); test_names = sys.argv[3].split(','); max_avg = float(sys.argv[4])
    train, test = load(train_names, d), load(test_names, d)
    sel = greedy(train, max_avg)
    print('chosen:', sel)
    for nm, data in (('train', train), ('test', test)):
        h, e, a = score(data, sel); n = len(data)
        print(f"{nm}: {h}/{n} hits, expected {e:.1f}, avg {a:.1f} numbers, p={p_at_least(h, n, a/100):.4f}")
