"""Gap study on the live log: where does the result sit when FINAL 4 misses,
and does counting how many lists hold a number (votes) beat chance?
Everything here was logged BEFORE each result, so it is a true forward test."""
import json, collections
L=[json.loads(l) for l in open('rrr_records/live.jsonl')]
O={}
for l in open('rrr_records/oma_live.jsonl'):
    o=json.loads(l)
    if o.get('oma'): O[o['round']]=set(o['oma'])
LISTS=['strong','rec','yx','wide','table','charrow','hot','top4','top10','top20','top40','rule1','rule2','rule3','rule5']
def votes(r):
    v=collections.Counter()
    for nm in LISTS:
        for n in set(r['lists'].get(nm) or []): v[n]+=1
    for n in O.get(r['round'],()): v[n]+=1
    return v
# 1. where is the result on a FINAL 4 miss
miss=[r for r in L if r['result'] not in r['lists']['top4']]
inany=sum(any(r['result'] in (r['lists'].get(nm) or []) for nm in LISTS) or r['result'] in O.get(r['round'],()) for r in miss)
print(f"FINAL 4 misses {len(miss)} of {len(L)}; result in at least one list: {inany} ({inany/len(miss):.0%})")
cov=[len(set().union(*[set(r['lists'].get(nm) or []) for nm in LISTS])|O.get(r['round'],set())) for r in L]
print(f"union of all lists covers on average {sum(cov)/len(cov):.0f} of 100 numbers")
# step distance from FINAL 4 on misses
def dist(a,b): return abs(a//10-b//10)+abs(a%10-b%10)
d=collections.Counter(min(dist(r['result'],f) for f in r['lists']['top4']) for r in miss)
print("digit distance to nearest FINAL 4 on misses:",dict(sorted(d.items())))
# chance of distance (uniform result)
import itertools
cd=collections.Counter()
for r in miss[:1]: pass
tot=collections.Counter()
for r in miss:
    for n in range(100):
        if n in r['lists']['top4']: continue
        tot[min(dist(n,f) for f in r['lists']['top4'])]+=1
print("expected by chance:",{k:round(v/96,1) for k,v in sorted(tot.items())})
# 2. vote level vs hit rate
lvl_n=collections.Counter(); lvl_h=collections.Counter()
for r in L:
    v=votes(r)
    for n in range(100):
        k=v.get(n,0); lvl_n[k]+=1; lvl_h[k]+= (n==r['result'])
print("\nvotes  numbers/round  hit%  x chance")
for k in sorted(lvl_n):
    if lvl_n[k]<50: continue
    p=lvl_h[k]/lvl_n[k]; print(f"{k:5} {lvl_n[k]/len(L):13.1f} {p*100:5.1f} {p/0.01:8.2f}")
# 3. fused top-4 by votes (ties by FINAL 4 order) : split halves
def fused(r,k=4):
    v=votes(r); order={n:i for i,n in enumerate(r['lists']['top4'])}
    return sorted(range(100),key=lambda n:(-v.get(n,0),order.get(n,9),n))[:k]
for k in (4,10,20):
    h=[r['result'] in fused(r,k) for r in L]; m=len(h)//2
    print(f"fused top{k}: {sum(h)} of {len(h)} (chance {len(h)*k/100:.1f})  1st half {sum(h[:m])}/{m}  2nd half {sum(h[m:])}/{len(h)-m}")
