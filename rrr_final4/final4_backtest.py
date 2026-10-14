exec(open('pick4.py').read().split('# walk-forward')[0])
import collections
U = ['rec','table','again','wide','yx','found']; T = ['strong','fam_seats','ncspec']
def mem(d, v, k):
    if k=='table': return v in [t[0] for t in d['table']]
    if k=='again': return v in [a for a in d['again'] if a is not None]
    return v in (d[k] or [])
h=collections.Counter(); n=collections.Counter(); slots=collections.Counter(); hits_rank=collections.Counter()
for i,d in enumerate(rounds):
    if i < 100: continue
    c = sorted(set(d['ocjp'])); g = 'JK' if d['id'][0] in 'jk' else 'old'
    n[g]+=1
    if not c: continue
    place = {}
    for e in d['ocjp_full']: place[e[0]] = min(place.get(e[0], 99), e[2])
    top = sorted(c, key=lambda v: (-sum(mem(d,v,k) for k in U), -sum(mem(d,v,k) for k in T), v))[:4]
    if d['r'] in top: h[g]+=1; hits_rank[top.index(d['r'])+1]+=1
tot=sum(h.values()); N=sum(n.values())
print(f"exact rule: all {tot}/{N} = {tot/N:.1%}; old {h['old']}/{n['old']} = {h['old']/n['old']:.1%}; J/K {h['JK']}/{n['JK']} = {h['JK']/n['JK']:.1%}; hits by rank {dict(hits_rank)}")
