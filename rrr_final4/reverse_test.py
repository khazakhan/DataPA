"""User idea after N279 = 41: MASTER 14 with its digits reversed = 41.
Test on every replayed round: the reversed MASTER (1 number) and the reversed
FINAL 4 (up to 4 numbers, doubles like 33 dropped), hits against chance."""
import json, sys, glob, os, re
R = [r for r in json.load(open(sys.argv[1])) if r.get('ocjp_full') and r.get('res') is not None]
S = os.path.dirname(sys.argv[1]); seen = {(r['series'], r['k']) for r in R}
for f in glob.glob(os.path.join(S, 'd2_*.json')):
    m = re.search(r'd2_(\d+)\.json$', f)
    if not m: continue
    k = int(m.group(1)); nxt = f'rrr_datasets/n{k + 1}.txt'
    if ('n', k) in seen or not os.path.exists(nxt): continue
    d = json.load(open(f)); d.update(series='n', k=k, res=int(open(nxt).read().split()[-1])); R.append(d)
def ranked(r):
    tb = [n for n, _ in r['table']]; st = [x[0] if isinstance(x, list) else x for x in r['strong']]
    L = [r['rec'], tb, r['again'], r['wide'], r['yx'], r['found']]
    v = lambda n: sum(n in set(l) for l in L); t = lambda n: (n in st) + (n in set(r['ncspec']))
    return sorted(set(r['ocjp']), key=lambda n: (-v(n), -t(n), n))
rev = lambda n: (n % 10) * 10 + n // 10
for name, rows in (('all series', R), ('series N', [r for r in R if r['series'] == 'n'])):
    n = len(rows); hm = hf = sz = 0
    for r in rows:
        rk = ranked(r); m = rev(rk[0]); s = {rev(x) for x in rk[:4]} - set(rk[:4])
        hm += r['res'] == m and m != rk[0]; hf += r['res'] in s; sz += len(s)
    print(f'{name}: {n} rounds | reversed MASTER {hm} = {hm / n:.1%} (chance 1%) | reversed FINAL 4 {hf} = {hf / n:.1%} ({sz / n:.1f} numbers a round, chance {sz / n:.1f}%)')
