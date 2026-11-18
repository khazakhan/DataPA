"""Strongest family study (user AD100: 'from same family pull exact one').
Family = cut+swap family (8, doubles 10). Pick the family holding most of FINAL 4 + yx.
python3 tools/strong_family_study.py   (839 live: 39|43 per half vs 32.5; exact member at chance)"""
import json
from collections import Counter
L=[json.loads(l) for l in open('rrr_records/live.jsonl')]
L=[r for r in L if r.get('result') is not None and len(r['ranked'])>=10 and r.get('ep') is not None]
op=lambda a,b:((b//10-a//10)%10,(b%10-a%10)%10); ap=lambda n,o:((n//10+o[0])%10)*10+(n%10+o[1])%10
f4=lambda r:(r.get('final8') or [])[:4] or r['ranked'][:4]
def fam(n):
    a,b=n//10,n%10; s=set()
    for x in (a,(a+5)%10):
        for y in (b,(b+5)%10): s|={x*10+y,y*10+x}
    return frozenset(s)
def pick(r):
    R=r['ep']; vs=f4(r)+[ap(R,op(R,v)[::-1]) for v in f4(r)]
    c=Counter(fam(v) for v in vs); best=max(c.values())
    return next(fam(v) for v in vs if c[fam(v)]==best)
h=len(L)//2
a=sum(r['result'] in pick(r) for r in L[:h]); b=sum(r['result'] in pick(r) for r in L[h:])
print(f'{len(L)} live: {a} | {b} per half, chance {sum(len(pick(r)) for r in L)/200:.1f}')
