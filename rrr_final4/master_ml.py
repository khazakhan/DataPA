import json,os,re,sys,numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
S=sys.argv[1]; R='rrr_datasets'
U=['rec','table','again','wide','yx','found']; T=['strong','fam_seats','ncspec']
def L(d,k):
    if k=='table': return set(t[0] for t in d['table'])
    if k=='again': return set(a for a in d['again'] if a is not None)
    return set(e[0] if isinstance(e,list) else e for e in (d.get(k) or []))
def nxt(s,n):
    for f in (f"{R}/{s}{n+1:02d}.txt", f"{R}/{s}{n+1}.txt"):
        if os.path.exists(f): return f
def load(s,n):
    for p in (f'{S}/all10/{s}_{n}.json', f'{S}/{s}{n}.json', f'{S}/all/{s}_{n}.json'):
        if os.path.exists(p):
            d=json.load(open(p))
            if 'ocjp' in d and 'ocjp_full' in d: return d
DIFF={0:0,1:1,2:2,9:3,8:4,5:5,6:6,7:7,4:8,3:9}  # nc,+1,+2,-1,-2,cut,c+1,c+2,c-1,c-2
def feats(d,v):
    ep=d['ep']; dx=DIFF[(v//10-ep//10)%10]; dy=DIFF[(v%10-ep%10)%10]
    f=[0]*10; f[dx]=1; g=[0]*10; g[dy]=1
    Ls=[v in L(d,k) for k in U+T]
    ag=[a for a in d['again']]; agf=[int(len(ag)>i and ag[i]==v) for i in range(4)]
    st=d['strong']; srank=(st.index(v)+1) if v in st else 0
    ent=[e for e in d['ocjp_full'] if e[0]==v]
    forms=[int(any(e[3]==t for e in ent)) for t in ('base','plus','star','ycut','xcut')]
    minp=min([e[2] for e in ent] or [0])
    epn=ep; adj_y=int(any((s//10)*10+((s%10+5)%10)==v for s in st))
    vote=sum(Ls[:6])
    return f+g+[int(x) for x in Ls]+agf+[int(srank>0),int(0<srank<=10),srank/20]+forms+[int(bool(ent)),minp/40,int(v in d['ocjp']),adj_y,vote,int(v==d.get('grid_ep',-1))]
rows=[]
for s in 'bcdfhijk':
    ns=set()
    for dn in ('all','all10'):
        for f in os.listdir(f'{S}/{dn}'):
            if f.startswith(s+'_'): ns.add(int(f.split('_')[1][:-5]))
    if s=='k': ns|=set(range(45,102))
    for n in sorted(ns):
        f=nxt(s,n)
        if not f: continue
        tok=open(f).read().split()[-1]
        if not re.fullmatch(r'\d\d?',tok): continue
        d=load(s,n)
        if not d or not d['ocjp']: continue
        rows.append((s,n,int(tok),d))
print('rounds',len(rows))
X=[np.array([feats(d,v) for v in range(100)],float) for _,_,_,d in rows]
Y=[np.array([int(v==r) for v in range(100)]) for _,_,r,_ in rows]
def cur_order(d):
    c=sorted(set(d['ocjp'])); Ls={k:L(d,k) for k in U}; Ts=[L(d,k) for k in T]
    return sorted(c,key=lambda v:(-sum(v in Ls[k] for k in U),-sum(v in t for t in Ts),v))
START=150; res={'current':[0,0],'logreg':[0,0],'gbm':[0,0]}; n=0; live={'current':[0,0],'logreg':[0,0],'gbm':[0,0]}
m1=m2=None
for i in range(START,len(rows)):
    if (i-START)%25==0:
        Xt=np.vstack(X[:i]); Yt=np.concatenate(Y[:i])
        m1=LogisticRegression(max_iter=2000,C=0.3).fit(Xt,Yt)
        m2=HistGradientBoostingClassifier(max_iter=150,learning_rate=0.05,max_leaf_nodes=15,min_samples_leaf=40).fit(Xt,Yt)
    s,nn,r,d=rows[i]; n+=1
    co=cur_order(d); p1=m1.predict_proba(X[i])[:,1]; p2=m2.predict_proba(X[i])[:,1]
    o1=list(np.argsort(-p1)); o2=list(np.argsort(-p2))
    isl = s=='k' and nn>=45
    for k,o in (('current',co),('logreg',o1),('gbm',o2)):
        res[k][0]+= o[:1]==[r]; res[k][1]+= r in o[:4]
        if isl: live[k][0]+= o[:1]==[r]; live[k][1]+= r in o[:4]
nl=sum(1 for s,nn,_,_ in rows[START:] if s=='k' and nn>=45)
print(f'walk-forward rounds {n} (live K {nl})')
for k,(a,b) in res.items(): print(f'{k:8s} #1 {a} ({a/n:.1%})  top4 {b} ({b/n:.1%})   live #1 {live[k][0]}/{nl} top4 {live[k][1]}/{nl}')
