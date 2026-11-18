"""MASTER CHANGED OPERATIONS study (2026-11-17, user after AD9 = 02 = MASTER 52 with x op
-1 -> c-1).  For every live round: MASTER m (FINAL 4 #1), ROOT r, MASTER op (dx, dy) on ROOT
(mod 10, cut = 5).  Each form changes the op and re-applies it to ROOT.  Score each form on
all live rounds (chance 1% each), pick the best 4 on the FIRST half, test on the SECOND half.
python3 tools/master_changed_ops.py"""
import json, collections
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None and r.get('ep') is not None]
app = lambda n, o: ((n // 10 + o[0]) % 10) * 10 + (n % 10 + o[1]) % 10
op = lambda a, b: ((b // 10 - a // 10) % 10, (b % 10 - a % 10) % 10)
C = lambda d: (d + 5) % 10; F = lambda d: (-d) % 10
FORMS = {
 'x cut sw': lambda x, y: (C(x), y), 'y cut sw': lambda x, y: (x, C(y)), 'both cut sw': lambda x, y: (C(x), C(y)),
 'x flip': lambda x, y: (F(x), y), 'y flip': lambda x, y: (x, F(y)), 'both flip': lambda x, y: (F(x), F(y)),
 'swap (yx)': lambda x, y: (y, x), 'swap+flip': lambda x, y: (F(y), F(x)), 'swap+cut': lambda x, y: (C(y), C(x)),
 'x+1': lambda x, y: ((x+1) % 10, y), 'x-1': lambda x, y: ((x-1) % 10, y), 'y+1': lambda x, y: (x, (y+1) % 10), 'y-1': lambda x, y: (x, (y-1) % 10),
 'x cut sw+flip': lambda x, y: (C(F(x)), y), 'y cut sw+flip': lambda x, y: (x, C(F(y))),
 'x nc': lambda x, y: (0, y), 'y nc': lambda x, y: (x, 0), 'x cut': lambda x, y: (5, y), 'y cut': lambda x, y: (x, 5),
}
h = len(L) // 2; H = [collections.Counter(), collections.Counter()]
def variants(r):
    m = ((r.get('final8') or []) or r['ranked'])[0]; R = r['ep']; x, y = op(R, m)
    return {k: app(R, f(x, y)) for k, f in FORMS.items()}, m
for i, r in enumerate(L):
    v, m = variants(r)
    for k, n in v.items():
        if n != m and n == r['result']: H[0 if i < h else 1][k] += 1
print('live rounds', len(L), 'halves', h, len(L) - h, '(chance per form ~', round(h / 100, 1), 'per half)')
for k in sorted(FORMS, key=lambda k: -(H[0][k] + H[1][k])):
    print(f'  {k:15s} {H[0][k]:3d} + {H[1][k]:3d} = {H[0][k]+H[1][k]:3d}')
best = sorted(FORMS, key=lambda k: -H[0][k])[:4]
def test(forms, part):
    hit = n = 0
    for r in part:
        v, m = variants(r); s = {v[k] for k in forms}
        hit += r['result'] in s; n += 1
    return hit, n
a = test(best, L[h:]); print('best 4 on first half:', best, '-> second half', a[0], 'of', a[1], f'({100*a[0]/a[1]:.1f}%, chance ~4%)')

# Watch line (user request after AD9): MASTER CHANGED OPS 4 = the 4 forms with the most live
# hits overall: swap (yx), x-1, swap+cut, x cut.  Study above shows them at chance; display only.
#   python3 tools/master_changed_ops.py predict AD10 <ROOT> <MASTER>
#   python3 tools/master_changed_ops.py score AD10 <RESULT>
import sys
WATCH = ['swap (yx)', 'x-1', 'swap+cut', 'x cut']
LOG = 'rrr_records/master_ops4_live.jsonl'
# widened to 10 after AD137 (user: 'widen MASTER CHANGED OPS upto 10'): the 10 forms with the
# most live hits overall (894 rounds).  Walk-forward best 10: 37 vs 40.2 and 33 vs 37.8 -> chance.
WATCH = ['x-1', 'swap (yx)', 'swap+cut', 'x cut', 'y+1', 'y cut', 'both cut sw', 'both flip', 'y-1', 'x cut sw+flip']
LOG = 'rrr_records/master_ops10_live.jsonl'
if len(sys.argv) > 1 and sys.argv[1] == 'predict':
    rnd, R, m = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]); x, y = op(R, m)
    pick = [app(R, FORMS[k](x, y)) for k in WATCH]
    open(LOG, 'a').write(json.dumps({'round': rnd, 'root': R, 'master': m, 'pick': pick, 'result': None}) + '\n')
    print('MASTER CHANGED OPS 10', rnd, ' · '.join(f'{v:02d} ({k})' for v, k in zip(pick, WATCH)))
if len(sys.argv) > 1 and sys.argv[1] == 'score':
    rows = [json.loads(l) for l in open(LOG)]
    for r in rows:
        if r['round'] == sys.argv[2]: r['result'] = int(sys.argv[3])
    open(LOG, 'w').writelines(json.dumps(r) + '\n' for r in rows)
    done = [r for r in rows if r['result'] is not None]
    print('MASTER CHANGED OPS 10 live', sum(r['result'] in r['pick'] for r in done), 'of', len(done))
