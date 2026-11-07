"""User 2026-11-07 (U14 = 57): EPROOTGEN. EP op (number before EP -> EP) = x1/y1, ROOT op (EP -> ROOT) = x2/y2.
Ops set S = {x1, y1, x2, y2}; 16 combinations a/b (a, b in S) applied to the ROOT. Then widen each op with
cut/decut, sign change, step +1/-1 and pick the 20 strongest (base 16 first, then widened numbers by how many
ways they are made). Test on all 1,293 history rounds; chance = numbers / 100."""
import sys, io, contextlib, re, collections
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('tools/final4_full_study.py').read().split('n = len(R)')[0])
TOK = {}
for h in H:
    try: TOK[h['ds']] = [int(t) for t in re.findall(r'(?<![\d*])\d{1,2}(?![\d*])', open('/home/khazakhan/DataScinceAnal/' + h['ds']).read())]
    except FileNotFoundError: pass
R2 = []
for h, r in zip([h for h in H if h['rows'] and len(h['src'].get('rk', [])) >= 4 and h['ds'] in TOK], R):
    r['prev'] = TOK[h['ds']][-2]; R2.append(r)
def parse(o):
    c = o.startswith('c'); t = o[1:] if c else o
    return (int(c), 0 if t in ('ut', '', 'nc') else int(t))
def name(c, s): return ('cut' if s == 0 else f"c{s:+d}") if c else ('nc' if s == 0 else f"{s:+d}")
def widen(o):
    c, s = parse(o); out = [(1 - c, s), (c, -s)] + [(c, s + d) for d in (1, -1) if -2 <= s + d <= 2]
    return [name(*p) for p in out if name(*p) != o]
def gen(r):
    x1, y1 = op_of(r['prev'], r['ep']); x2, y2 = op_of(r['ep'], r['root'])
    S = list(dict.fromkeys([x1, y1, x2, y2]))
    base = list(dict.fromkeys(ap(r['root'], a, b) for a in S for b in S))
    W = list(dict.fromkeys(S + [w for o in S for w in widen(o)]))
    cnt = collections.Counter(ap(r['root'], a, b) for a in W for b in W)
    top = base + [v for v, _ in sorted(cnt.items(), key=lambda t: (-t[1], t[0])) if v not in base]
    return base, top[:20], set(cnt)
n = len(R2); res = collections.Counter()
for r in R2:
    b, t20, allw = gen(r)
    res['b'] += r['res'] in b; res['bn'] += len(b)
    res['t'] += r['res'] in t20; res['tn'] += len(t20)
    res['w'] += r['res'] in allw; res['wn'] += len(allw)
print(f"rounds {n}")
for k, lab in (('b', 'EPROOTGEN 16 (base grid)'), ('t', 'EPROOTGEN 20 strongest'), ('w', 'all widened combos')):
    m = res[k + 'n'] / n
    print(f"  {lab:26s} numbers {m:5.1f}   held {res[k]:4d} = {100*res[k]/n:5.1f}%   chance {m:5.1f}%   extra {res[k] - res[k+'n']/100:+.0f}")
