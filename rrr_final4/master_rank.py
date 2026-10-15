import json,os,re,sys
S=sys.argv[1]; R='rrr_datasets'
U=['rec','table','again','wide','yx','found']; T=['strong','fam_seats','ncspec']
def L(d,k):
    if k=='table': return set(t[0] for t in d['table'])
    if k=='again': return set(a for a in d['again'] if a is not None)
    return set(e[0] if isinstance(e,list) else e for e in (d[k] or []))
def nxt(s,n):
    for f in (f"{R}/{s}{n+1:02d}.txt", f"{R}/{s}{n+1}.txt"):
        if os.path.exists(f): return f
def load(s,n):
    for p in (f'{S}/all10/{s}_{n}.json', f'{S}/{s}{n}.json', f'{S}/all/{s}_{n}.json'):
        if os.path.exists(p):
            d=json.load(open(p))
            if 'ocjp' in d and 'ocjp_full' in d: return d
rows=[]
for s in 'bcdfhijk':
    ns=set()
    for dname in ('all','all10'):
        for f in os.listdir(f'{S}/{dname}'):
            if f.startswith(s+'_'): ns.add(int(f.split('_')[1][:-5]))
    if s=='k': ns|=set(range(45,99))
    for n in sorted(ns):
        f=nxt(s,n)
        if not f: continue
        tok=open(f).read().split()[-1]
        if not re.fullmatch(r'\d\d?',tok): continue
        d=load(s,n)
        if not d: continue
        r=int(tok); c=sorted(set(d['ocjp']))
        if not c: continue
        Ls={k:L(d,k) for k in U}; Ts=[L(d,k) for k in T]
        order=sorted(c,key=lambda v:(-sum(v in Ls[k] for k in U),-sum(v in t for t in Ts),v))
        rank=order.index(r)+1 if r in order else None
        rows.append((s,n,r,rank,len(c)))
def rep(sel,name):
    n=len(sel); t1=sum(1 for x in sel if x[3]==1); t4=sum(1 for x in sel if x[3] and x[3]<=4); t2=sum(1 for x in sel if x[3] and x[3]<=2)
    print(f'{name}: rounds {n}  #1 exact {t1} ({t1/n:.1%}, chance 1%)  top2 {t2} ({t2/n:.1%})  top4 {t4} ({t4/n:.1%}, chance 4%)')
rep(rows,'ALL series')
rep([x for x in rows if x[0] in 'jk'],'J/K')
rep([x for x in rows if x[0]=='k' and x[1]>=45],'LIVE K46-K99')
print('live top-8 ranks:',[(x[1]+1,x[2],x[3]) for x in rows if x[0]=='k' and x[1]>=45 and x[3] and x[3]<=8])
