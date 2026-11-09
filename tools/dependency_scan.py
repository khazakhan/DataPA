"""Broad scan: does the next number depend on ANY earlier cell?
Grid-aware (7 columns, voids kept as gaps).  For lags 1..21 and each digit pairing
(tens/units of the earlier cell -> tens/units of the next), chi-square of the
digit-difference distribution vs 200 shuffles of the same chart."""
import random, sys, glob, re
def grid(f):
    out=[]
    for line in open(f):
        t=line.split()
        out+= [int(x) if x.isdigit() else None for x in t]
    return out
def chi(vals):
    n=len(vals)
    if n<100: return 0
    c=[0]*10
    for v in vals: c[v]+=1
    e=n/10; return sum((x-e)**2/e for x in c)
def scan(seq,lag,a,b):
    D=lambda v,k: v//10 if k=='t' else v%10
    return chi([(D(seq[i],b)-D(seq[i-lag],a))%10 for i in range(lag,len(seq)) if seq[i] is not None and seq[i-lag] is not None])
random.seed(7)
for k in sys.argv[1:]:
    fs=sorted(glob.glob(f'rrr_datasets/{k}[0-9]*.txt'),key=lambda f:int(re.findall(r'(\d+)\.txt',f)[0]))
    s=grid(fs[-1]); vals=[v for v in s if v is not None]
    print(f"chart {k}: {len(vals)} numbers")
    hits=[]
    for lag in range(1,22):
        for a in 'tu':
            for b in 'tu':
                x=scan(s,lag,a,b)
                null=[]
                for _ in range(60):
                    v=vals[:]; random.shuffle(v); it=iter(v)
                    sh=[next(it) if c is not None else None for c in s]
                    null.append(scan(sh,lag,a,b))
                null.sort(); thr=null[-2]   # ~97th pct
                if x>thr: hits.append((lag,a+'->'+b,round(x,1),round(thr,1)))
    for h in hits: print("  lag",h[0],h[1],"chi2",h[2],"shuffle 97%",h[3])
    print("  (pairs tested 84; about 2-3 pass by luck)")
