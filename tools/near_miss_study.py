"""Near-miss study (user after AD103: 'missed by a variant of 1 only, pick the exact one').
1) How often is the result ONE STEP (one digit ±1) from a FINAL 4 number, vs chance?
2) Cluster picker: vote rank weight + weight of ±1 neighbours in the vote list, top 4.
python3 tools/near_miss_study.py
2026-11-18, 860 live: one step away 120 (14%) vs chance 14%; cluster pickers 21-24 | 16-21 vs vote 25 | 20 -> none better."""
import json
L=[json.loads(l) for l in open('rrr_records/live.jsonl')]
L=[r for r in L if r.get('result') is not None and len(r['ranked'])>=10]
f4=lambda r:(r.get('final8') or [])[:4] or r['ranked'][:4]
def nb(n):
    a,b=n//10,n%10
    return {((a+d)%10)*10+b for d in (1,-1)}|{a*10+(b+d)%10 for d in (1,-1)}
near=[set().union(*[nb(v) for v in f4(r)])-set(f4(r)) for r in L]
print('one step away', sum(r['result'] in s for r,s in zip(L,near)), 'of', len(L), 'chance', round(sum(len(s) for s in near)/100))
def pick(r,K,w):
    rk=r['ranked'][:K]; W={v:1/(i+1) for i,v in enumerate(rk)}
    sc={v:W.get(v,0)+w*sum(W.get(u,0) for u in nb(v)) for v in set(rk)|set().union(*[nb(v) for v in rk])}
    return sorted(sc,key=lambda v:-sc[v])[:4]
h=len(L)//2
print('vote top4', sum(r['result'] in r['ranked'][:4] for r in L[:h]), sum(r['result'] in r['ranked'][:4] for r in L[h:]))
for K in (10,20,40):
    for w in (0.3,0.6,1.0):
        print(f'cluster K{K} w{w}', sum(r['result'] in pick(r,K,w) for r in L[:h]), sum(r['result'] in pick(r,K,w) for r in L[h:]))
