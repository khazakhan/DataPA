"""EP -> next number digit-step pattern: what it is, and does it predict on held-out data?"""
import collections, glob, re, sys
def load(f): return [int(t) for t in open(f).read().split() if t.isdigit()]
def steps(seq): return [((b//10-a//10)%10,(b%10-a%10)%10) for a,b in zip(seq,seq[1:])]
def show(name,seq):
    S=steps(seq); n=len(S)
    t=collections.Counter(s[0] for s in S); u=collections.Counter(s[1] for s in S)
    j=collections.Counter(S)
    print(name,'tens step %:',' '.join(f"{k}:{t[k]*100/n:.0f}" for k in range(10)))
    print(' '*len(name),'units step %:',' '.join(f"{k}:{u[k]*100/n:.0f}" for k in range(10)))
    same=sum(a==b for a,b in zip(seq,seq[1:])); print(' '*len(name),f'exact repeat {same} (chance {n/100:.0f}); tens same {t[0]} (chance {n/10:.0f}); units same {u[0]}')
def heldout(seq,k=4,train_frac=0.5):
    m=int(len(seq)*train_frac); S=steps(seq[:m+1])
    t=collections.Counter(s[0] for s in S); u=collections.Counter(s[1] for s in S)
    hits=0; tests=0
    for a,b in zip(seq[m:],seq[m+1:]):
        score={n:t[(n//10-a//10)%10]*u[(n%10-a%10)%10] for n in range(100)}
        pick=sorted(score,key=lambda n:-score[n])[:k]
        hits+= b in pick; tests+=1
    return hits,tests
files={}
for f in glob.glob('rrr_datasets/*.txt'):
    m=re.match(r'rrr_datasets/([a-z]+)(\d+)\.txt',f)
    if m and (m[1] not in files or int(m[2])>files[m[1]][0]): files[m[1]]=(int(m[2]),f)
for k in ('x','y'): show(k.upper(),load(files[k][1]))
print("\nheld-out test (learn steps on 1st half of chart, predict 2nd half)")
print("chart  top4 held / tests (chance)   top10 held (chance)   top20 held (chance)")
T=[0,0,0,0]
for k in sorted(files):
    s=load(files[k][1])
    if len(s)<300: continue
    h4,n=heldout(s,4); h10,_=heldout(s,10); h20,_=heldout(s,20)
    T[0]+=h4;T[1]+=h10;T[2]+=h20;T[3]+=n
    print(f"{k:5} {h4:4} / {n:4} ({n*.04:5.1f})   {h10:4} ({n*.1:6.1f})   {h20:4} ({n*.2:6.1f})")
n=T[3]; print(f"ALL   {T[0]:4} / {n} ({n*.04:.1f}) x{T[0]/(n*.04):.2f}   {T[1]} ({n*.1:.1f}) x{T[1]/(n*.1):.2f}   {T[2]} ({n*.2:.1f}) x{T[2]/(n*.2):.2f}")
