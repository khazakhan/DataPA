import os,re,glob,collections
os.chdir('/home/khazakhan/DataScinceAnal')
def flat_of(p):
    return [int(t) for line in open(p) for t in line.split() if re.fullmatch(r'\d{1,2}',t)]
last={}
for p in glob.glob('rrr_datasets/*.txt'):
    m=re.match(r'rrr_datasets/([a-z]+)(\d+)\.txt$',p)
    if m and (m.group(1) not in last or int(m.group(2))>last[m.group(1)][0]): last[m.group(1)]=(int(m.group(2)),p)
tot=collections.Counter()
for s,(n,p) in sorted(last.items()):
    fl=flat_of(p)
    if len(fl)<200: continue
    low=sum(a//10==b//10 for a,b in zip(fl,fl[1:]))/(len(fl)-1)<0.06
    if low: continue
    k=0;h1=h3=0
    for i in range(100,len(fl)):
        hist=fl[:i]; ts=[1]*10
        for a,b in zip(hist,hist[1:]): ts[(b//10-a//10)%10]+=1
        e=hist[-1]//10; o=sorted(range(10),key=lambda d:(-ts[(d-e)%10],d))
        d=fl[i]//10; k+=1; h1+=o[0]==d; h3+=d in o[:3]
    tot['n']+=k; tot['t1']+=h1; tot['t3']+=h3
    half='A' if len(tot)%2 else 'B'
    print(f'{s:3s} n={k:4d} top1 {100*h1/k:5.1f}% top3 {100*h3/k:5.1f}%')
print('ALL normal charts n=%d top1 %.1f%% top3 %.1f%% (chance 10/30)'%(tot['n'],100*tot['t1']/tot['n'],100*tot['t3']/tot['n']))
