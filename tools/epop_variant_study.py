"""User 2026-11-15 (AC79=57): 'same operations of EP and ROOT; xy and yx; sign changed; cut + sign changed;
cut + sign changed with inc/dec' -- does it hold the result? Applied on the ROOT, ops taken from the
EP move (prev->EP) and the ROOT move (EP->ROOT). Two readings:
  A: one transform applied to BOTH sides together (5 transforms) -> small set
  B: each side transformed separately (5x5)                      -> big set
Scored on every live-logged round: hits vs the set size (chance = size/100)."""
import json, sys, io, re, contextlib
sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
def parts(o):
    a = D.OP_ABBREV[o]; c = a.startswith('c') and a != 'cut' or a == 'cut'
    n = a[1:] if a.startswith('c') and a != 'cut' else ('0' if a in ('nc', 'cut') else a)
    return c, int(n)
def mk(c, n):
    n = max(-2, min(2, n))
    a = ('cut' if n == 0 else f'c{n:+d}') if c else ('nc' if n == 0 else f'{n:+d}')
    return AB[a]
def T(o, t):
    c, n = parts(o)
    if t == 'same': return o
    if t == 'sign': return mk(c, -n)
    if t == 'cutsign': return mk(not c, -n)
    if t == 'cutsign+1': return mk(not c, -n + 1)
    if t == 'cutsign-1': return mk(not c, -n - 1)
TS = ['same', 'sign', 'cutsign', 'cutsign+1', 'cutsign-1']
ap = lambda e, x, y: D.apply_op(e // 10, x) * 10 + D.apply_op(e % 10, y)
L = {}
for l in open('rrr_records/live.jsonl'):
    d = json.loads(l); L[d['round']] = d
fl = {}
res = {'A': [0, 0], 'B': [0, 0], 'F4': [0, 0]}; n = 0
for d in L.values():
    root, ep, r = int(d['ep']), int(d['after']), int(d['result'])
    # EP move: number before EP -> EP, read from dataset file
    tok = [int(t) for t in re.findall(r'(?<![\d*])\d{1,2}(?![\d*])', open(d['dataset']).read())]
    if len(tok) < 2 or tok[-1] != ep: continue
    prev = tok[-2]
    epop = (D.find_op(prev // 10, ep // 10), D.find_op(prev % 10, ep % 10))
    rtop = (D.find_op(ep // 10, root // 10), D.find_op(ep % 10, root % 10))
    if '?' in epop + rtop: continue
    n += 1
    A, B = set(), set()
    for ox, oy in (epop, rtop):
        for t in TS:
            A.add(ap(root, T(ox, t), T(oy, t))); A.add(ap(root, T(oy, t), T(ox, t)))
            for t2 in TS:
                B.add(ap(root, T(ox, t), T(oy, t2))); B.add(ap(root, T(oy, t), T(ox, t2)))
    for k, s in (('A', A), ('B', B), ('F4', set(int(v) for v in d['lists']['top4']))):
        res[k][0] += r in s; res[k][1] += len(s)
print(f'{n} live rounds')
for k, (h, sz) in res.items():
    print(f'{k:3s} hits {h:4d} = {100*h/n:5.1f}%   avg numbers {sz/n:5.1f}   chance {sz/n:5.1f}%   lift {h/(sz/100):.2f}')
