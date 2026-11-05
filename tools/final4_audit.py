"""FINAL 4 audit (user 2026-11-05: 'find blunder / middle / minor mistakes that
make OCJP FINAL 4 miss').  Input rrr_records/f4_inputs.json (RRR3_F4DUMP of
every history round: OCJP candidates, the 4 voting lists, tie lists, places,
the FINAL 4 picked) and rrr_records/history_all.json.

Checks
 1. consistency: FINAL 4 inside the candidates, no repeats, same as the
    ranked top 4 in the page's final box
 2. coverage: how often the result is an OCJP candidate at all (cap on FINAL 4)
 3. tie-break: how often the 4th seat is decided by 'lower number', and how
    often the result lost only on that rule
 4. parameter-free alternative tie-breaks on the same rounds"""
import json, random, collections
D = json.load(open('/home/khazakhan/DataScinceAnal/rrr_records/f4_inputs.json'))
H = {h['ds']: h for h in json.load(open('/home/khazakhan/DataScinceAnal/rrr_records/history_all.json'))}
n = len(D)
bad_in = bad_rep = bad_box = 0
for d in D:
    f4 = d['final4']
    bad_in += any(v not in d['cands'] for v in f4)
    bad_rep += len(set(f4)) != len(f4)
    rk = H[d['ds']]['src'].get('rk', [])[:4]
    bad_box += rk != f4
print(f"rounds {n}")
print(f"1. FINAL 4 outside candidates: {bad_in}; repeats: {bad_rep}; final box top 4 differs: {bad_box}")
cov = sum(d['res'] in d['cands'] for d in D)
size = sum(len(set(d['cands'])) for d in D) / n
print(f"2. result inside OCJP candidates: {cov} of {n} ({cov/n*100:.1f}%), average candidates {size:.1f} "
      f"(by size alone {size:.1f}%)")


def key_parts(d, v):
    votes = sum(v in l for l in d['lists'].values())
    tie = sum(v in l for l in d['tie'])
    return votes, tie


def pick(d, tb):
    c = sorted(set(d['cands']))
    return sorted(c, key=lambda v: (-key_parts(d, v)[0], -key_parts(d, v)[1], tb(d, v)))[:4]


hits = collections.Counter(); decided = lost_tb = 0
rng = random.Random(0)
for d in D:
    c = sorted(set(d['cands']))
    ks = sorted(((key_parts(d, v)), v) for v in c)
    order = sorted(c, key=lambda v: (-key_parts(d, v)[0], -key_parts(d, v)[1], v))
    if len(order) > 4 and key_parts(d, order[3]) == key_parts(d, order[4]):
        decided += 1
        if d['res'] in c and key_parts(d, d['res']) == key_parts(d, order[3]) and d['res'] not in order[:4]:
            lost_tb += 1
    for name, tb in (('lower number (now)', lambda d, v: v),
                     ('higher number', lambda d, v: -v),
                     ('OCJP place', lambda d, v: d['place'].get(str(v), 99)),
                     ('random', lambda d, v: rng.random())):
        hits[name] += d['res'] in pick(d, tb)
print(f"3. 4th seat decided by the 'lower number' rule in {decided} of {n} rounds; "
      f"result lost only on that rule in {lost_tb} rounds")
print("4. same votes, other tie-breaks (no fitting, same rounds):")
for k, v in hits.items():
    print(f"   {k:20s} {v} hits")
