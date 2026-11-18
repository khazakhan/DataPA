"""User request AE52 (2026-11-19): FINAL 4 = strongest OPEN digit x 4 strongest CLOSE digits.
Tested on every logged live round (rrr_records/live.jsonl 'ranked' = the vote order the OPEN/CLOSE
digits come from; same weighting as DataProcessing._open_close, rank-weighted top 10).
Compares with the plain vote top 4 and SHADOW 4 on the same rounds, in two halves."""
import json, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
L = [r for r in map(json.loads, open('rrr_records/live.jsonl')) if r.get('result') is not None and r.get('ranked')]
S = {r['round']: r for r in map(json.loads, open('rrr_records/shadow_f4.jsonl')) if r.get('result') is not None}
def oc(rk, N=10):
    vs = [v[0] if isinstance(v, (list, tuple)) else v for v in rk][:N]
    out = []
    for f in (lambda v: v // 10, lambda v: v % 10):
        c = {}
        for i, v in enumerate(vs): c[f(v)] = c.get(f(v), 0) + (N - i)
        o = [d for d, _ in sorted(c.items(), key=lambda t: (-t[1], t[0]))]
        out.append(o + [d for d in range(10) if d not in o])
    return out
pick = {
 'plain vote top 4': lambda r, o, c: [v[0] if isinstance(v, (list, tuple)) else v for v in r['ranked']][:4],
 'OPEN 1 x CLOSE 4 (user idea)': lambda r, o, c: [o[0] * 10 + u for u in c[:4]],
 'OPEN 2 x CLOSE 2': lambda r, o, c: [t * 10 + u for t in o[:2] for u in c[:2]],
 'OPEN 4 x CLOSE 1': lambda r, o, c: [t * 10 + c[0] for t in o[:4]],
}
for half, R in (('first half', L[:len(L)//2]), ('second half', L[len(L)//2:]), ('series AE', [r for r in L if r['round'].startswith('AE')])):
    line = []
    for k, f in pick.items():
        h = 0
        for r in R:
            o, c = oc(r['ranked']); h += r['result'] in f(r, o, c)
        line.append(f'{k} {h}')
    sh = [r for r in R if r['round'] in S]
    line.append(f"SHADOW {sum(S[r['round']]['result'] in S[r['round']]['pick'] for r in sh)} of {len(sh)}")
    print(f'{half} ({len(R)} rounds, chance 4% = {0.04*len(R):.1f}): ' + ' | '.join(line))
