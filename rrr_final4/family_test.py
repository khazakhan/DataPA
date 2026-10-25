"""User idea after N265 = 87 (EP 86): FINAL 4 held 23 (c-1/c+2) and 78
(-1/+2), the same steps with only the cuts different ("same family"); one
slot was wasted.  Rule tested: walk the FINAL 4 ranking and keep at most one
number per step family (x step, y step, cut ignored); the next number in the
ranking fills the slot.  Also: one per family when the family ignores the
signs too.  Hits against the shipped FINAL 4 on every replayed round."""
import json, sys, glob, os, re
R = [r for r in json.load(open(sys.argv[1])) if r.get('ocjp_full') and r.get('res') is not None]
S = os.path.dirname(sys.argv[1]); seen = {(r['series'], r['k']) for r in R}
for f in glob.glob(os.path.join(S, 'd2_*.json')):
    m = re.search(r'd2_(\d+)\.json$', f)
    if not m: continue
    k = int(m.group(1)); nxt = f'rrr_datasets/n{k + 1}.txt'
    if ('n', k) in seen or not os.path.exists(nxt): continue
    d = json.load(open(f)); d.update(series='n', k=k, res=int(open(nxt).read().split()[-1])); R.append(d)
def side(s):
    c = s.startswith('c'); t = s[3:] if s.startswith('cut') else s[1:] if c else s
    return c, (0 if t in ('', 'nc') else int(t))
def ranked(r):
    tb = [n for n, _ in r['table']]; st = [x[0] if isinstance(x, list) else x for x in r['strong']]
    L = [r['rec'], tb, r['again'], r['wide'], r['yx'], r['found']]
    v = lambda n: sum(n in set(l) for l in L); t = lambda n: (n in st) + (n in set(r['ncspec']))
    op = {}
    for n, o, p, k in r['ocjp_full']: op.setdefault(n, o)
    return sorted(set(r['ocjp']), key=lambda n: (-v(n), -t(n), n)), op
FAM = {'steps (cut ignored)': lambda o: tuple(side(s)[1] for s in o.split('/')),
       'step sizes (cut and sign ignored)': lambda o: tuple(abs(side(s)[1]) for s in o.split('/'))}
for name, rows in (('all series', R), ('series N', [r for r in R if r['series'] == 'n'])):
    n = len(rows); base = sum(r['res'] in ranked(r)[0][:4] for r in rows)
    print(f'{name}: {n} rounds, shipped FINAL 4 {base} = {base / n:.1%}')
    for fn, fam in FAM.items():
        h = ch = 0
        for r in rows:
            rk, op = ranked(r); pick, used = [], set()
            for m in rk:
                f = fam(op[m])
                if f in used: continue
                used.add(f); pick.append(m)
                if len(pick) == 4: break
            h += r['res'] in pick; ch += pick != rk[:4]
        print(f'   one per family, {fn:<34} {h} = {h / n:.1%}  (changed FINAL 4 in {ch} rounds)')
