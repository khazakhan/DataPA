import json, sys
R = [r for r in json.load(open(sys.argv[1])) if r.get('ocjp_full') and 'res' in r]
fl = lambda v: [x[0] if isinstance(x, list) else x for x in v]
NEVER = ['rec', 'table', 'again', 'wide', 'yx', 'found']
def pick(r, tb):
    ops = {}
    for i, (v, op, *_) in enumerate(r['ocjp_full']): ops.setdefault(v, i)
    L = {k: set(fl(r.get(k, []))) for k in NEVER}; st = set(fl(r.get('strong', [])))
    def sc(v):
        t = {'lower': 0, 'place': ops[v]}.get(tb, None)
        if t is None: t = -(v in L[tb])
        return (-sum(v in s for s in L.values()), -(v in st), t, v)
    return sorted(ops, key=sc)[:4]
n = len(R); h = n // 2
print('rounds', n)
for tb in ['lower', 'place'] + NEVER:
    a = [r['res'] in pick(r, tb) for r in R]
    print(f'{tb:6} all {sum(a)}/{n} {sum(a)/n:.1%}  1st half {sum(a[:h])}  2nd half {sum(a[h:])}')
