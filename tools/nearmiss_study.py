"""How often is the result one small digit change (+-1, +-2, cut) away from a
PRIME 4 number, and how big is that neighbourhood?  python3 tools/nearmiss_study.py"""
import json
S = 'FNMKO'
src = {s: json.load(open(f'rrr_records/replay/src{s}.json')) for s in S}
cut = lambda d: (d + 5) % 10
def prime(r):
    s = r['src']; rk = s.get('rk', [])
    v = {n: (n in s.get('rule5', [])) + (n in s.get('rule2', [])) + (n in s.get('rule18', [])) for n in range(100)}
    rp = {x: i for i, x in enumerate(rk)}
    return sorted(range(100), key=lambda n: (-v[n], rp.get(n, 999), n))[:10]
steps = {'+-1': (1, 9), '+-2': (2, 8), 'cut': (5,)}
def near(p, kinds):
    out = set()
    for k in kinds:
        for d in steps[k]:
            out.add(((p // 10 + d) % 10) * 10 + p % 10); out.add((p // 10) * 10 + (p % 10 + d) % 10)
    return out
N = sum(len(src[s]) for s in S)
for kinds in (['+-1'], ['+-2'], ['cut'], ['+-1', '+-2', 'cut']):
    h = sz = exact = 0
    for s in S:
        for r in src[s]:
            pr = prime(r)[:4]; nb = set().union(*(near(p, kinds) for p in pr)) - set(pr)
            h += r['res'] in nb; sz += len(nb)
    print(f"one {'/'.join(kinds):11} change from PRIME 4: {h} of {N} rounds; neighbourhood {sz/N:.1f} numbers -> chance {sz/100:.1f}")
