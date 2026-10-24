"""Global check: the current script on every series (all data sets).
Per series: rounds run, crashes, OCJP holding the result, STRONG 20, FINAL 4,
MASTER.  With a second dump (older script) it also lists every round where a
hit was lost, so a change made for one series cannot quietly hurt another."""
import json, sys
VOTE = ('rec', 'table', 'again', 'wide', 'yx', 'found')
def final4(r):
    L = [set(r[k]) for k in VOTE if k != 'table'] + [{x for x, _ in r['table']}]
    oc = sorted(set(r['ocjp']))
    return sorted(oc, key=lambda m: (-sum(m in v for v in L),
                                     -((m in r['strong']) + 1 + (m in r['ncspec'])), m))[:4]
new = json.load(open(sys.argv[1]))
old = {(r['series'], r['k']): r for r in json.load(open(sys.argv[2]))} if len(sys.argv) > 2 else {}
by = {}
lost = []
for r in new:
    s = by.setdefault(r['series'], dict(n=0, crash=0, ocjp=0, strong=0, f4=0, m=0))
    s['n'] += 1
    if 'ep' not in r or not r.get('ocjp'):
        s['crash'] += 1; continue
    f = final4(r); res = r['res']
    s['ocjp'] += res in r['ocjp']; s['strong'] += res in r['strong']
    s['f4'] += res in f; s['m'] += res == f[0]
    o = old.get((r['series'], r['k']))
    if o and o.get('ocjp') and res in o['ocjp'] and res not in r['ocjp']:
        lost.append((r['series'], r['k'], res))
tot = dict(n=0, crash=0, ocjp=0, strong=0, f4=0, m=0)
print(f"{'series':<7}{'rounds':>7}{'errors':>7}{'OCJP':>14}{'STRONG 20':>14}{'FINAL 4':>13}{'MASTER':>10}")
for k in sorted(by, key=lambda x: -by[x]['n']):
    s = by[k]; n = s['n'] - s['crash']
    for a in tot: tot[a] += s[a]
    print(f"{k:<7}{s['n']:>7}{s['crash']:>7}{s['ocjp']:>6}/{n:<3}{s['ocjp']/n:5.0%}{s['strong']:>7}/{n:<3}{s['strong']/n:4.0%}"
          f"{s['f4']:>6}/{n:<3}{s['f4']/n:4.0%}{s['m']:>5}/{n:<3}")
n = tot['n'] - tot['crash']
print(f"{'ALL':<7}{tot['n']:>7}{tot['crash']:>7}{tot['ocjp']:>6}/{n:<3}{tot['ocjp']/n:5.0%}{tot['strong']:>7}/{n:<3}{tot['strong']/n:4.0%}"
      f"{tot['f4']:>6}/{n:<3}{tot['f4']/n:4.0%}{tot['m']:>5}/{n:<3}")
if old: print(f'\nOCJP hits lost against the older script: {len(lost)} {lost[:10]}')
