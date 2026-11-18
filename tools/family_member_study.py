"""Family member picker (user AD121: 'we reach the same family, but picking the one strong
member fails').  Rounds where the result is in the family of a FINAL 4 number; which rule picks
the exact member?  Chance = 1 / family size (1/8, 1/4 or 1/10 for doubles).
python3 tools/family_member_study.py"""
import json
from collections import Counter
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None and len(r['ranked']) >= 20 and r.get('ep') is not None]
op = lambda a, b: ((b // 10 - a // 10) % 10, (b % 10 - a % 10) % 10)
ap = lambda n, o: ((n // 10 + o[0]) % 10) * 10 + (n % 10 + o[1]) % 10
T = lambda n: (n % 10) * 10 + n // 10
c = lambda d: (d + 5) % 10
def fam(n):
    a, b = n // 10, n % 10; s = set()
    for x in (a, c(a)):
        for y in (b, c(b)): s |= {x * 10 + y, y * 10 + x}
    return s
f4 = lambda r: (r.get('final8') or [])[:4] or r['ranked'][:4]
RULES = {
 'the FINAL 4 number itself': lambda v, F, r: v,
 'its full cut': lambda v, F, r: c(v // 10) * 10 + c(v % 10),
 'its turned': lambda v, F, r: T(v),
 'its tens cut': lambda v, F, r: c(v // 10) * 10 + v % 10,
 'its units cut': lambda v, F, r: (v // 10) * 10 + c(v % 10),
 'its yx': lambda v, F, r: ap(r['ep'], op(r['ep'], v)[::-1]),
 'best vote rank in family (not v)': lambda v, F, r: next((u for u in r['ranked'] if u in F and u != v), v),
 'member with tens = OPEN-like EP tens': lambda v, F, r: next((u for u in sorted(F) if u // 10 == r['ep'] // 10), v),
}
n = 0; hits = Counter(); ch = 0
for r in L:
    x = r['result']
    srcs = [v for v in f4(r) if x in fam(v)]
    if not srcs or x in f4(r): continue
    v = srcs[0]; F = fam(v); n += 1; ch += 1 / (len(F) - 1)
    for k, g in RULES.items(): hits[k] += g(v, F, r) == x
print(f'{len(L)} live rounds; result in the family of a FINAL 4 number (not FINAL 4 itself): {n}')
print(f'chance of picking the exact other member: {ch:.1f}')
for k in RULES: print(f'  {k:38s} {hits[k]}')
