"""FINAL 4 picker study (2026-11-18, user after AD82: 'correct the OCJP FINAL 4 picker').
Alternative 4-number pickers from the same live records; halves + series AD.
python3 tools/final4_picker_study.py"""
import json
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None and r.get('ep') is not None and len(r['ranked']) >= 8 and r.get('lists')]
op = lambda a, b: ((b // 10 - a // 10) % 10, (b % 10 - a % 10) % 10)
app = lambda n, o: ((n // 10 + o[0]) % 10) * 10 + (n % 10 + o[1]) % 10
def nodup(seq, R, k=4):
    out = []
    for v in seq:
        y = app(R, op(R, v)[::-1])
        if v in out or (y in out and y != v): continue
        out.append(v)
        if len(out) == k: break
    return out
S = lambda r: r['lists'].get('strong', [])
P = {
 'current (vote, no yx dup)': lambda r: nodup(r['ranked'], r['ep']),
 'vote top 4 plain': lambda r: r['ranked'][:4],
 'STRONG 20 top 4': lambda r: S(r)[:4],
 'vote ∩ STRONG 20 first': lambda r: nodup([v for v in r['ranked'] if v in S(r)] + r['ranked'], r['ep']),
 'vote top 2 + STRONG top 2': lambda r: (lambda a: a + [v for v in S(r) if v not in a][:2])(r['ranked'][:2]),
 'RECOMMENDED ∩ STRONG first': lambda r: nodup([v for v in r['lists'].get('rec', []) if v in S(r)] + r['ranked'], r['ep']),
}
h = len(L) // 2; AD = [r for r in L if r['round'].startswith('AD')]
print(f'live rounds {len(L)} (halves {h}/{len(L)-h}), AD {len(AD)}; chance 4% = {h*.04:.0f} per half')
for k, f in P.items():
    a = sum(r['result'] in f(r) for r in L[:h]); b = sum(r['result'] in f(r) for r in L[h:]); c = sum(r['result'] in f(r) for r in AD)
    print(f'  {k:28s} {a:3d} | {b:3d}   AD {c}')
