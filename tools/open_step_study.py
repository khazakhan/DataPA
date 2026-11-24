import json,os,re
os.chdir('/home/khazakhan/DataScinceAnal')
def flat_of(p):
    out=[]
    for line in open(p):
        for t in line.split():
            if re.fullmatch(r'\d{1,2}',t): out.append(int(t))
    return out
recs=[]
for l in open('rrr_records/live.jsonl'):
    r=json.loads(l)
    try:
        res=int(r['result']); rk=[int(x[0] if isinstance(x,list) else x) for x in r['ranked']]
        st=[int(x) for x in r['lists'].get('strong',[])]
    except Exception: continue
    if not os.path.exists(r['dataset']) or len(rk)<40: continue
    fl=flat_of(r['dataset'])
    if len(fl)<60: continue
    recs.append((r['round'],res,rk,st,fl))
print('rounds',len(recs))
def rankw(rk,N,pos):
    c=[0.0]*10
    for i,v in enumerate(rk[:N]): c[v//10 if pos==0 else v%10]+=(N-i)/N
    return c
def norm(c):
    s=sum(c) or 1; return [x/s for x in c]
def order(c): return sorted(range(10),key=lambda d:(-c[d],d))
def chart_trans(fl,pos):
    e=fl[-1]//10 if pos==0 else fl[-1]%10
    c=[1.0]*10
    for a,b in zip(fl,fl[1:]):
        if (a//10 if pos==0 else a%10)==e: c[b//10 if pos==0 else b%10]+=1
    return c
def chart_step(fl,pos):
    g=(lambda v:v//10) if pos==0 else (lambda v:v%10)
    ts=[1.0]*10
    for a,b in zip(fl,fl[1:]): ts[(g(b)-g(a))%10]+=1
    e=g(fl[-1]); return [ts[(d-e)%10] for d in range(10)]
def recent(fl,pos,n=70):
    c=[1.0]*10
    for v in fl[-n:]: c[v//10 if pos==0 else v%10]+=1
    return c
def strongv(st,pos):
    c=[0.0]*10
    for v in st: c[v//10 if pos==0 else v%10]+=1
    return c
M={
 'base top10':lambda rk,st,fl,p: rankw(rk,10,p),
 'top20':lambda rk,st,fl,p: rankw(rk,20,p),
 'top30':lambda rk,st,fl,p: rankw(rk,30,p),
 'top40':lambda rk,st,fl,p: rankw(rk,40,p),
 'strong20':lambda rk,st,fl,p: strongv(st,p),
 'base+strong':lambda rk,st,fl,p: [a+b for a,b in zip(norm(rankw(rk,10,p)),norm(strongv(st,p)))],
 'chart trans':lambda rk,st,fl,p: chart_trans(fl,p),
 'chart step':lambda rk,st,fl,p: chart_step(fl,p),
 'recent70':lambda rk,st,fl,p: recent(fl,p),
 'base+step':lambda rk,st,fl,p: [a+b for a,b in zip(norm(rankw(rk,10,p)),norm(chart_step(fl,p)))],
 'base+trans':lambda rk,st,fl,p: [a+b for a,b in zip(norm(rankw(rk,10,p)),norm(chart_trans(fl,p)))],
 'base+strong+step':lambda rk,st,fl,p: [a+b+c for a,b,c in zip(norm(rankw(rk,10,p)),norm(strongv(st,p)),norm(chart_step(fl,p)))],
}
n=len(recs); H=n//2
for pos,name in ((0,'OPEN'),(1,'CLOSE')):
    print(f'\n{name}  (n={n}, halves {H}/{n-H}; chance top1 10%, top3 30%)')
    for k,f in M.items():
        t1=[0,0];t3=[0,0]
        for i,(rd,res,rk,st,fl) in enumerate(recs):
            o=order(f(rk,st,fl,pos)); d=res//10 if pos==0 else res%10
            h=i>=H; t1[h]+=o[0]==d; t3[h]+=d in o[:3]
        print(f'  {k:18s} top1 {100*t1[0]/H:5.1f}% | {100*t1[1]/(n-H):5.1f}%   top3 {100*t3[0]/H:5.1f}% | {100*t3[1]/(n-H):5.1f}%')

print('\n=== split by chart type, OPEN ===')
def low(fl):
    if len(fl)<301: return False
    return sum(a//10==b//10 for a,b in zip(fl,fl[1:]))/(len(fl)-1)<0.06
def page_open(rk,st,fl):
    c=rankw(rk,10,0); o=order(c)
    if not low(fl): return o
    e=fl[-1]//10; av=e
    ts={}
    for a,b in zip(fl,fl[1:]):
        s=(b//10-a//10)%10; ts[s]=ts.get(s,0)+1
    if st:
        tf=[0]*10
        for v in fl: tf[v//10]+=1
        S=norm([sum(v//10==d for v in st) for d in range(10)])
        X=norm([(ts.get((d-e)%10,0)+1)*(tf[d]+1) for d in range(10)])
        return sorted(range(10),key=lambda d:(d==av,-(S[d]+X[d]),d))
    return sorted(range(10),key=lambda d:(d==av,-ts.get((d-e)%10,0),d))
def step_open(rk,st,fl): return order(chart_step(fl,0))
def mix(rk,st,fl,w):
    a=norm(rankw(rk,10,0)); b=norm(chart_step(fl,0)); return order([x+w*y for x,y in zip(a,b)])
groups={'low-repeat':[r for r in recs if low(r[4])],'normal':[r for r in recs if not low(r[4])],'AF only':[r for r in recs if r[0].startswith('AF')]}
for g,R in groups.items():
    n=len(R);H=n//2
    print(f' {g} n={n}')
    for k,f in (('page now',page_open),('chart step',step_open),('mix w=2',lambda a,b,c:mix(a,b,c,2)),('mix w=4',lambda a,b,c:mix(a,b,c,4))):
        t1=[0,0];t3=[0,0]
        for i,(rd,res,rk,st,fl) in enumerate(R):
            o=f(rk,st,fl);d=res//10;h=i>=H;t1[h]+=o[0]==d;t3[h]+=d in o[:3]
        print(f'   {k:11s} top1 {t1[0]:3d}|{t1[1]:3d} ({100*sum(t1)/n:4.1f}%)  top3 {t3[0]:3d}|{t3[1]:3d} ({100*sum(t3)/n:4.1f}%)   chance per half top1 {H*.1:.0f} top3 {H*.3:.0f}')
