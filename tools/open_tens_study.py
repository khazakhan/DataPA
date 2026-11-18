import collections, sys
files=sys.argv[1:]
def load(f): return [int(t) for t in open(f).read().split() if t.isdigit()]
def preds(s):
    e=s[-1]; et=e//10
    S=list(zip(s,s[1:]))
    out={}
    st=collections.Counter((b//10-a//10)%10 for a,b in S)
    out['step']=[(et+k)%10 for k,_ in st.most_common()]
    tm=collections.Counter(b//10 for a,b in S if a//10==et)
    out['trans']=[d for d,_ in tm.most_common()]
    fr=collections.Counter(x//10 for x in s[-60:])
    out['hot60']=[d for d,_ in fr.most_common()]
    cold=collections.Counter(x//10 for x in s[-30:])
    out['cold30']=sorted(range(10),key=lambda d:cold[d])
    # gap: tens digit absent longest
    last={}
    for i,x in enumerate(s): last[x//10]=i
    out['due']=sorted(range(10),key=lambda d:last.get(d,-1))
    # full combined: product of step & trans
    out['step*trans']=sorted(range(10),key=lambda d:-(st[(d-et)%10]+1)*(tm[d]+1))
    return out
tot=collections.defaultdict(lambda:[0,0,0]); n_all=0
for f in files:
    s=load(f); res=collections.defaultdict(lambda:[0,0,0]); n=0
    for i in range(300,len(s)-1):
        P=preds(s[:i+1]); r=s[i+1]//10; n+=1
        for k,v in P.items():
            v=v+[d for d in range(10) if d not in v]
            res[k][0]+= r==v[0]; res[k][1]+= r in v[:3]
    half=n//2
    print(f, n, {k:(round(100*a/n,1),round(100*b/n,1)) for k,(a,b,_) in res.items()})
    for k,(a,b,_) in res.items(): tot[k][0]+=a; tot[k][1]+=b
    n_all+=n
print('ALL',n_all,{k:(round(100*a/n_all,1),round(100*b/n_all,1)) for k,(a,b,_) in tot.items()})
