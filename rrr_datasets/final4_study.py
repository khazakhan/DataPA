import json, itertools, sys, numpy as np
R=[r for r in json.load(open(sys.argv[1])) if 'ep' in r and r.get('ocjp')]
def fl(v): return [x[0] if isinstance(x,list) else x for x in v]
keys=['rec','table','again','wide','yx','found','strong','fam_seats','ncspec']
n=len(R); F=np.zeros((n,100,len(keys)+2)); OK=np.zeros((n,100),bool); RES=np.array([r['res'] for r in R])
for i,r in enumerate(R):
    for v in fl(r['ocjp']): OK[i,v]=True
    for j,k in enumerate(keys):
        for v in set(fl(r.get(k,[]))): F[i,v,j]=1
    rec=fl(r.get('rec',[]))
    for p,v in reversed(list(enumerate(rec))): F[i,v,-2]=1/(1+p)
    oc=fl(r['ocjp'])
    for p,v in reversed(list(enumerate(oc))): F[i,v,-1]=1/(1+p)
TIE=-np.arange(100)*1e-6
def hits(score, rows):
    s=np.where(OK[rows],score[rows]+TIE,-1e9); top=np.argsort(-s,axis=1)[:,:4]
    return int((top==RES[rows,None]).any(1).sum())
half=n//2; A=np.arange(half); B=np.arange(half,n); ALL=np.arange(n)
cur=F[:,:,:6].sum(2)*100+F[:,:,6:9].sum(2)
print('rounds',n,'chance per half ~',round(half*.04,1))
print('current rule  train',hits(cur,A),'test',hits(cur,B),'all',hits(cur,ALL))
best=[]
for ws in itertools.product([0,1],repeat=len(keys)):
    for rw in (0,1,3):
      for ow in (0,1):
        w=np.array(list(ws)+[rw,ow],float)
        sc=F@w; best.append((hits(sc,A),ws,rw,ow))
best.sort(key=lambda t:-t[0])
print('train-best -> test:')
for h,ws,rw,ow in best[:10]:
    w=np.array(list(ws)+[rw,ow],float); print(' train',h,dict(zip(keys,ws)),'rec',rw,'ocjpplace',ow,'test',hits(F@w,B))
# reverse: train on B, test on A
best2=[]
for ws in itertools.product([0,1],repeat=len(keys)):
    for rw in (0,1,3):
      for ow in (0,1):
        w=np.array(list(ws)+[rw,ow],float); best2.append((hits(F@w,B),ws,rw,ow))
best2.sort(key=lambda t:-t[0])
for h,ws,rw,ow in best2[:5]:
    w=np.array(list(ws)+[rw,ow],float); print(' trainB',h,ws,rw,ow,'testA',hits(F@w,A))
