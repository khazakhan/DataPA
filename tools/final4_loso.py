import json, numpy as np, warnings; warnings.filterwarnings('ignore')
d='/home/khazakhan/DataScinceAnal/rrr_records/f4_'
X=np.load(d+'X.npy'); m=json.load(open(d+'meta.json')); Y=np.array(m['Y']); S=np.array(m['S']); names=m['names']
n=len(Y); rng=np.random.default_rng(0)
def top4(score, i): 
    s=score+rng.random(100)*1e-6; return np.argsort(-s)[:4]
def evalf(fn):
    out={}
    for s in sorted(set(S)):
        te=np.where(S==s)[0]; tr=np.where(S!=s)[0]
        f=fn(tr)
        out[s]=(sum(Y[i] in top4(f(X[i]),i) for i in te), len(te))
    tot=sum(h for h,_ in out.values()); return tot, out
rank=names.index('rank')
print('current (rank only)', evalf(lambda tr: (lambda x: x[:,rank])))
from sklearn.linear_model import LogisticRegression
def logit(C):
    def fit(tr):
        Xt=X[tr].reshape(-1,X.shape[2]); yt=np.zeros(len(tr)*100); 
        for k,i in enumerate(tr): yt[k*100+Y[i]]=1
        mdl=LogisticRegression(C=C,max_iter=2000,class_weight=None).fit(Xt,yt)
        return lambda x: mdl.decision_function(x)
    return fit
for C in (0.01,0.1,1.0):
    print('logit C',C, evalf(logit(C)))
# naive lift-weighted sum (weights = log lift on train)
def liftfit(tr):
    w=[]
    for j in range(X.shape[2]):
        on=X[tr][:,:,j]>0; hit=sum(on[k,Y[i]] for k,i in enumerate(tr)); size=on.sum()
        w.append(np.log((hit+1)/(size/100+1)))
    w=np.array(w); return lambda x: (x>0)@w
print('lift-weighted', evalf(liftfit))
for j,nm in enumerate(names):
    if nm in('rule28','p4fam','wide','rule2','mk3'):
        print('rank +',nm, evalf(lambda tr,j=j:(lambda x: x[:,rank]+0.5*(x[:,j]>0))))
# chance distribution: random 4 picks
sims=[(rng.random((n,100)).argsort(1)[:,:4]==Y[:,None]).any(1).sum() for _ in range(2000)]
print('random 4: mean %.1f, 95th pct %d, 99th %d'%(np.mean(sims),np.percentile(sims,95),np.percentile(sims,99)))
