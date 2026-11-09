"""Does the next number depend on ROOT (follower of the earlier same number)
or on the last number at all?  Chi-square vs uniform, plus shuffle test."""
import random, sys, collections, glob, re
def load(f):
    s=[]
    for t in open(f).read().split():
        if t.isdigit(): s.append(int(t))
    return s
def pairs(seq):
    out=[]; last={}
    for i in range(1,len(seq)):
        ep=seq[i-1]
        # ROOT = number that followed the previous occurrence of ep
        j=last.get(ep)
        if j is not None and j+1<i: out.append((seq[j+1],seq[i],ep))
        last[ep]=i-1
    return out
def chi(c,n,k=10):
    e=n/k; return sum((c.get(i,0)-e)**2/e for i in range(k))
def score(seq):
    P=pairs(seq)
    dt=collections.Counter(((r//10)-(x//10))%10 for x,r,_ in P)   # tens step ROOT->result
    du=collections.Counter(((r%10)-(x%10))%10 for x,r,_ in P)
    lt=collections.Counter(((r//10)-(e//10))%10 for _,r,e in P)   # step from EP
    lu=collections.Counter(((r%10)-(e%10))%10 for _,r,e in P)
    n=len(P); return n,chi(dt,n)+chi(du,n), chi(lt,n)+chi(lu,n)
files={}
for f in glob.glob('rrr_datasets/*.txt'):
    m=re.match(r'rrr_datasets/([a-z]+)(\d+)\.txt',f)
    if m and (m[1] not in files or int(m[2])>files[m[1]][0]): files[m[1]]=(int(m[2]),f)
random.seed(1)
print("chart  pairs  ROOT-link chi2  shuffle-95%  EP-link chi2  shuffle-95%")
for k in sorted(files):
    seq=load(files[k][1])
    if len(seq)<300: continue
    n,a,b=score(seq)
    sa=[];sb=[]
    for _ in range(200):
        s=seq[:]; random.shuffle(s); _,x,y=score(s); sa.append(x); sb.append(y)
    sa.sort(); sb.sort()
    print(f"{k:5} {n:6} {a:14.1f} {sa[190]:12.1f} {b:13.1f} {sb[190]:12.1f}")
