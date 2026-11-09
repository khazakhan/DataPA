import json, math, collections
L=[json.loads(l) for l in open('rrr_records/live.jsonl')]
O=[json.loads(l) for l in open('rrr_records/oma_live.jsonl') if '"result"' in l]
O=[o for o in O if o.get('result') is not None]
def pbin_tail(hits, ps):
    # P(X>=hits) for Poisson-binomial via DP
    d=[1.0]
    for p in ps:
        n=[0.0]*(len(d)+1)
        for k,v in enumerate(d):
            n[k]+=v*(1-p); n[k+1]+=v*p
        d=n
    return sum(d[hits:])
def stat(rows):
    hits=sum(h for h,_ in rows); ps=[s/100 for _,s in rows]; exp=sum(ps)
    return len(rows),hits,exp,(hits/exp if exp else 0),pbin_tail(hits,ps),sum(ps)/len(ps)*100 if ps else 0
names=sorted(L[-1]['lists'])
out=[]
for nm in names:
    rows=[(int(r['result'] in r['lists'][nm]),len(set(r['lists'][nm]))) for r in L if r['lists'].get(nm)]
    if not rows: continue
    h=len(rows)//2
    a=stat(rows); f=stat(rows[:h]); s=stat(rows[h:])
    out.append((nm,)+a+(f[3],s[3]))
orow=[(int(o['result'] in o['oma']),len(set(o['oma']))) for o in O]
h=len(orow)//2; a=stat(orow); out.append(('OMA',)+a+(stat(orow[:h])[3],stat(orow[h:])[3]))
print(f"{'list':8} {'rounds':>6} {'size':>5} {'held':>5} {'chance':>7} {'x':>5} {'p(>=)':>7} {'1st half x':>10} {'2nd half x':>10}")
for nm,n,hh,e,x,p,sz,fx,sx in sorted(out,key=lambda t:-t[4]):
    print(f"{nm:8} {n:6} {sz:5.1f} {hh:5} {e:7.1f} {x:5.2f} {p:7.3f} {fx:10.2f} {sx:10.2f}")
# per series for top4 / strong / OMA
print()
ser=collections.defaultdict(list)
for r in L: ser[r['round'].rstrip('0123456789')].append(r)
for k,v in ser.items():
    t4=sum(r['result'] in r['lists']['top4'] for r in v)
    st=sum(r['result'] in r['lists']['strong'] for r in v if r['lists'].get('strong'))
    print(k,len(v),'FINAL4',t4,'exp',round(len(v)*0.04,1),'STRONG20',st,'exp',round(len(v)*0.2,1))
# streak / which list is best per round count: how many of 100 numbers covered vs hits union
