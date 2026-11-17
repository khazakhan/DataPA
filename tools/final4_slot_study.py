"""FINAL 4 slot study (2026-11-17, user: 'improve FINAL 4 as sharpest pick'): current FINAL 4 =
vote top 4 with EP repeat at #3.  Try putting one MASTER-changed-op form (or other single forms) into
slot #4 (or #2), on every live round.  Pick on the FIRST half, test on the SECOND half and on series AD.
python3 tools/final4_slot_study.py"""
import json
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None and r.get('ep') is not None and r.get('after') is not None and len(r['ranked']) >= 4]
op = lambda a, b: ((b // 10 - a // 10) % 10, (b % 10 - a % 10) % 10)
app = lambda n, o: ((n // 10 + o[0]) % 10) * 10 + (n % 10 + o[1]) % 10
C = lambda d: (d + 5) % 10; F = lambda d: (-d) % 10
def base(r):
    f = list(r['ranked'][:4])
    if r['after'] not in f: f[2] = r['after']
    return f
FORMS = {
 'MASTER x-1': lambda x, y: ((x - 1) % 10, y), 'MASTER x cut': lambda x, y: (5, y),
 'MASTER swap+cut': lambda x, y: (C(y), C(x)), 'MASTER swap (yx)': lambda x, y: (y, x),
 'MASTER x+1': lambda x, y: ((x + 1) % 10, y), 'MASTER y-1': lambda x, y: (x, (y - 1) % 10),
 'MASTER y+1': lambda x, y: (x, (y + 1) % 10), 'MASTER both cut sw': lambda x, y: (C(x), C(y)),
}
def build(r, form, slot):
    f = base(r)
    if form is None: return f
    R = r['ep']; x, y = op(R, f[0]); v = app(R, FORMS[form](x, y))
    if v not in f: f[slot] = v
    return f
h = len(L) // 2; AD = [r for r in L if r['round'].startswith('AD')]
def score(part, form, slot): return sum(r['result'] in build(r, form, slot) for r in part)
print(f'live rounds {len(L)} (halves {h}/{len(L)-h}), AD {len(AD)}')
print(f'  {"current FINAL 4":28s} {score(L[:h],None,3):3d} | {score(L[h:],None,3):3d} | AD {score(AD,None,3)}')
res = []
for slot in (3, 1):
    for k in FORMS:
        a, b, c = score(L[:h], k, slot), score(L[h:], k, slot), score(AD, k, slot)
        res.append((a, k, slot, b, c))
        print(f'  {k + " in #" + str(slot + 1):28s} {a:3d} | {b:3d} | AD {c}')
best = max(res)
print('picked on first half:', best[1], 'in #', best[2] + 1, '-> second half', best[3], 'vs current', score(L[h:], None, 3))
