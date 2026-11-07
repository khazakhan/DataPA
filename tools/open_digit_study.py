"""User 2026-11-07: 'can you identify the OPEN digit strongly?' OPEN = tens digit of the result (also units checked).
Pick the most common tens/units digit in the OCJP ranking (top N, weighted by rank) and score on 1,293 rounds.
Chance: 1 digit 10%, 2 digits 20%, 3 digits 30%."""
import io, contextlib, collections
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('tools/final4_full_study.py').read().split('n = len(R)')[0])
n = len(R)
def pick(r, side, N, k, weighted):
    c = collections.Counter()
    for i, v in enumerate(r['rk'][:N]):
        d = v // 10 if side == 't' else v % 10
        c[d] += (N - i) if weighted else 1
    return [d for d, _ in sorted(c.items(), key=lambda t: (-t[1], t[0]))][:k]
print(f"rounds {n}")
for side, lab in (('t', 'OPEN (tens)'), ('u', 'CLOSE (units)')):
    for N in (4, 10, 20, 40):
        for w in (False, True):
            row = []
            for k in (1, 2, 3):
                h = sum(((r['res'] // 10) if side == 't' else (r['res'] % 10)) in pick(r, side, N, k, w) for r in R)
                row.append(f"{k} digit{'s' if k > 1 else ' '} {100*h/n:5.1f}% (ch {10*k}%)")
            print(f"  {lab:13s} from top {N:2d}{' weighted' if w else '         '}: " + '   '.join(row))
