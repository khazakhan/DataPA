"""Tens / units digit study of OCJP FINAL 4 on the full replay (all.json).
Question: FINAL 4 often has the result's tens digit; can the units digit be
picked?  Every rate is compared with what its set size gives by chance."""
import json, sys, random
from collections import Counter

R = json.load(open(sys.argv[1]))
R = [r for r in R if r.get('res') is not None and r['ocjp']]
VOTE = ('rec', 'table', 'again', 'wide', 'yx', 'found')

def lists(r):
    out = {k: set(r[k]) for k in VOTE if k != 'table'}
    out['table'] = {x for x, _ in r['table']}
    return out

def final4(r, L=None):
    L = L or lists(r)
    oc = sorted(set(r['ocjp']))
    key = lambda m: (-sum(m in v for v in L.values()),
                     -((m in r['strong']) + 1 + (m in r['ncspec'])), m)
    return sorted(oc, key=key)

cut = lambda d: (d + 5) % 10
N = len(R)
print(f'rounds {N}')

# 1. tens hit vs chance (chance = distinct tens / 10 per round)
th = ch = ex = 0; nt = Counter()
for r in R:
    f = final4(r)[:4]; t = {m // 10 for m in f}
    th += r['res'] // 10 in t; ch += len(t) / 10; ex += r['res'] in f; nt[len(t)] += 1
print(f'\n1. FINAL 4 exact {ex}/{N} = {ex/N:.1%} (chance 4%)')
print(f'   tens digit in FINAL 4 tens: {th}/{N} = {th/N:.1%}, chance {ch/N:.1%}; distinct tens per round {dict(nt)}')
uh = uc = 0
for r in R:
    f = final4(r)[:4]; u = {m % 10 for m in f}
    uh += r['res'] % 10 in u; uc += len(u) / 10
print(f'   units digit in FINAL 4 units: {uh}/{N} = {uh/N:.1%}, chance {uc/N:.1%}')

# 2. tens alone by each rank (#1..#4) and a 1-number tens pick
for k in range(4):
    h = sum(final4(r)[k] // 10 == r['res'] // 10 for r in R)
    print(f'   tens of #{k+1}: {h}/{N} = {h/N:.1%} (chance 10%)')

# 3. units rules, given the tens is right (rounds where tens of #1 matched)
#    and over all rounds: candidate units digits from the round's own data
def units_rules(r):
    f = final4(r); L = lists(r); ep, g = r['ep'], r['grid_ep']
    pool = Counter()
    for k, v in L.items():
        for m in v: pool[m % 10] += 1
    for m in r['strong']: pool[m % 10] += 1
    top = [d for d, _ in pool.most_common()]
    least = top[::-1]
    u1 = f[0] % 10
    return {
        '#1 units': u1, '#1 units +1': (u1 + 1) % 10, '#1 units -1': (u1 - 1) % 10,
        '#1 units cut': cut(u1), 'EP units': ep % 10, 'EP units cut': cut(ep % 10),
        'after units': g % 10, 'after units cut': cut(g % 10),
        'after tens': g // 10, 'EP tens': ep // 10,
        'most common units in lists': top[0], 'least common units in lists': least[0],
        'units of #2': f[1] % 10, 'units of #3': f[2] % 10, 'units of #4': f[3] % 10,
    }
print('\n3. one units digit, every round (chance 10%):')
names = units_rules(R[0]).keys()
tot = Counter(); cond = Counter(); nc = 0
for r in R:
    u = units_rules(r); t_ok = final4(r)[0] // 10 == r['res'] // 10; nc += t_ok
    for n in names:
        tot[n] += u[n] == r['res'] % 10
        cond[n] += t_ok and u[n] == r['res'] % 10
for n in names:
    print(f'   {n:<30} {tot[n]:4d}/{N} = {tot[n]/N:5.1%}   when #1 tens right: {cond[n]:3d}/{nc} = {cond[n]/max(nc,1):5.1%}')

# 4. |units distance| of result to #1 when tens matched
dist = Counter()
for r in R:
    f = final4(r)[0]
    if f // 10 == r['res'] // 10:
        dist[min((r['res'] - f) % 10, (f - r['res']) % 10)] += 1
print(f'\n4. #1 tens right ({nc} rounds): units distance to #1 {sorted(dist.items())}'
      f'  (uniform: 0:10% 1:20% 2:20% 3:20% 4:20% 5:10%)')

# 5. 4-number sets that keep FINAL 4's tens: #1 tens with units u1-1,u1,u1+1 + #2
def setA(r):
    f = final4(r); a = f[0]; t = a // 10
    return {t * 10 + (a % 10 + d) % 10 for d in (-1, 0, 1)} | {f[1]}
def setB(r):
    f = final4(r); return {m // 10 * 10 + (m % 10 + d) % 10 for m in f[:2] for d in (0, 1)}
for nm, fn in (('#1 band ±1 + #2', setA), ('#1,#2 and units+1', setB)):
    h = sum(r['res'] in fn(r) for r in R); s = sum(len(fn(r)) for r in R) / N
    print(f'5. {nm:<22} {h}/{N} = {h/N:.1%}  (size {s:.1f}, chance {s:.1f}%)')

# 6. split-half check: best units rule chosen on first half, scored on second
half = N // 2
best = max(names, key=lambda n: sum(units_rules(r)[n] == r['res'] % 10 for r in R[:half]))
h2 = sum(units_rules(r)[best] == r['res'] % 10 for r in R[half:])
print(f'\n6. best units rule on first half = "{best}"; on second half {h2}/{N-half} = {h2/(N-half):.1%} (chance 10%)')

# 7. shuffle control: tens hit with results shuffled across rounds
random.seed(1); res = [r['res'] for r in R]; sims = []
for _ in range(200):
    random.shuffle(res)
    sims.append(sum(x // 10 in {m // 10 for m in final4(r)[:4]} for r, x in zip(R, res)) / N)
sims.sort()
print(f'7. tens hit with results shuffled: median {sims[100]:.1%}, 95% band {sims[5]:.1%} – {sims[194]:.1%}; real {th/N:.1%}')

# 8. units hits that are not just an exact FINAL 4 #1 hit
ex1 = sum(final4(r)[0] == r['res'] for r in R)
print(f'\n8. #1 exact {ex1}/{N}; #1 units right but number wrong: {tot["#1 units"] - ex1}/{N} = {(tot["#1 units"] - ex1)/N:.1%} (chance about 9%)')
for n in ('EP units', 'most common units in lists'):
    sims = []
    res = [r['res'] for r in R]
    U = [units_rules(r)[n] for r in R]
    for _ in range(300):
        random.shuffle(res); sims.append(sum(u == x % 10 for u, x in zip(U, res)))
    sims.sort()
    print(f'   {n}: real {tot[n]}, shuffled 95% band {sims[7]}–{sims[292]}')

# 9. does the most-common-units digit hold on both halves, and does it help
#    FINAL 4 as a tie-break (votes, then units-pool count, then old tie-break)?
n = 'most common units in lists'
for a, b in ((0, half), (half, N)):
    h = sum(units_rules(r)[n] == r['res'] % 10 for r in R[a:b])
    print(f'9. {n} rounds {a}-{b}: {h}/{b-a} = {h/(b-a):.1%}')
def final4u(r):
    L = lists(r); pool = Counter()
    for v in L.values():
        for m in v: pool[m % 10] += 1
    for m in r['strong']: pool[m % 10] += 1
    oc = sorted(set(r['ocjp']))
    key = lambda m: (-sum(m in v for v in L.values()), -pool[m % 10],
                     -((m in r['strong']) + 1 + (m in r['ncspec'])), m)
    return sorted(oc, key=key)[:4]
for a, b in ((0, half), (half, N), (0, N)):
    old = sum(r['res'] in final4(r)[:4] for r in R[a:b]); new = sum(r['res'] in final4u(r) for r in R[a:b])
    print(f'   FINAL 4 rounds {a}-{b}: shipped {old}  units tie-break {new}  of {b-a}')
