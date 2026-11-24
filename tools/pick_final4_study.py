import json,os,collections
os.chdir('/home/khazakhan/DataScinceAnal')
s1={}
for l in open('rrr_records/strong1_live.jsonl'):
    r=json.loads(l); s1[r['round']]=r['pick'][0]
R=[]
for l in open('rrr_records/live.jsonl'):
    r=json.loads(l)
    try: res=int(r['result']); ep=int(r['after'])
    except: continue
    if not os.path.exists(r['dataset']) or not r.get('final8') or len(r['final8'])<4: continue
    fl=[int(x) for x in open(r['dataset']).read().split() if x.isdigit()]
    R.append((r,res,ep,fl))
n=len(R);H=n//2
print('rounds',n)
def votes(r):
    c=collections.Counter()
    for k,v in r['lists'].items():
        if isinstance(v,list):
            for x in set(v): c[int(x)]+=1
    for k in ('prime10','lastop','final8','r28','prime4fam'):
        for x in set(r.get(k) or []): c[int(x)]+=1
    return c
def follow(fl,ep):
    c=collections.Counter(b for a,b in zip(fl,fl[1:]) if a==ep); return c
def rankpos(r):
    return {int(v):i for i,v in enumerate(r['ranked'])}
singles={
 'MASTER ranked#1':lambda r,ep,fl: int(r['ranked'][0]),
 'KING = EP repeat':lambda r,ep,fl: ep,
 'most votes':lambda r,ep,fl: max(votes(r).items(),key=lambda t:(t[1],-rankpos(r).get(t[0],99)))[0],
 'EP chart follower':lambda r,ep,fl: (follow(fl,ep).most_common(1) or [(ep,0)])[0][0],
 'recent50 hottest':lambda r,ep,fl: collections.Counter(fl[-50:]).most_common(1)[0][0],
 'EP yx (reverse)':lambda r,ep,fl: (ep%10)*10+ep//10,
 'votes+rank blend':lambda r,ep,fl: max(range(100),key=lambda v:(votes(r)[v]-0.2*rankpos(r).get(v,60),-v)),
}
print('\nSINGLE PICK (chance 1%% = %.1f per half)'%(H*.01))
for k,f in singles.items():
    h=[0,0]
    for i,(r,res,ep,fl) in enumerate(R): h[i>=H]+=f(r,ep,fl)==res
    print(f'  {k:20s} {h[0]:3d} | {h[1]:3d}   = {100*sum(h)/n:.2f}%  x{sum(h)/(n*.01):.2f}')
h=[0,0];m=0
for i,(r,res,ep,fl) in enumerate(R):
    if r['round'] in s1: m+=1; h[i>=H]+=s1[r['round']]==res
print(f'  STRONG 20 #1 (logged {m}) {h[0]} | {h[1]}  = {100*sum(h)/max(m,1):.2f}%')
def uniq(seq,k=4):
    out=[]
    for v in seq:
        if v not in out: out.append(v)
        if len(out)==k: break
    return out
sets={
 'FINAL 4 now':lambda r,ep,fl: [int(x) for x in r['final8'][:4]],
 'ranked top4':lambda r,ep,fl: [int(x) for x in r['ranked'][:4]],
 'ranked top3 + EP':lambda r,ep,fl: uniq([int(x) for x in r['ranked'][:3]]+[ep]+[int(x) for x in r['ranked'][3:]]),
 'top4 votes':lambda r,ep,fl: [v for v,_ in sorted(votes(r).items(),key=lambda t:(-t[1],rankpos(r).get(t[0],99)))[:4]],
 'blend votes+rank':lambda r,ep,fl: sorted(range(100),key=lambda v:(-(votes(r)[v]-0.2*rankpos(r).get(v,60)),v))[:4],
 'EP + 3 followers':lambda r,ep,fl: uniq([ep]+[v for v,_ in follow(fl,ep).most_common()]+[int(x) for x in r['ranked']]),
 'MASTER+EP+2 followers':lambda r,ep,fl: uniq([int(r['ranked'][0]),ep]+[v for v,_ in follow(fl,ep).most_common()]+[int(x) for x in r['ranked']]),
}
print('\nSET OF 4 (chance 4%% = %.1f per half)'%(H*.04))
for k,f in sets.items():
    h=[0,0]
    for i,(r,res,ep,fl) in enumerate(R): h[i>=H]+=res in f(r,ep,fl)
    print(f'  {k:22s} {h[0]:3d} | {h[1]:3d}   = {100*sum(h)/n:.2f}%  x{sum(h)/(n*.04):.2f}')
print('\nextra FINAL 4 forms vs current rule (ranked top3 + EP)')
ex={
 'top3+EP (current rule)':sets['ranked top3 + EP'],
 'top2+EP+STRONG#1':lambda r,ep,fl: uniq([int(x) for x in r['ranked'][:2]]+[ep]+([s1[r['round']]] if r['round'] in s1 else [])+[int(x) for x in r['ranked'][2:]]),
 'top2+EP+follower':lambda r,ep,fl: uniq([int(x) for x in r['ranked'][:2]]+[ep]+[v for v,_ in follow(fl,ep).most_common(1)]+[int(x) for x in r['ranked'][2:]]),
 'top3+EP, EP first':lambda r,ep,fl: uniq([ep]+[int(x) for x in r['ranked'][:3]]+[int(x) for x in r['ranked'][3:]]),
}
for k,f in ex.items():
    h=[0,0]
    for i,(r,res,ep,fl) in enumerate(R): h[i>=H]+=res in f(r,ep,fl)
    print(f'  {k:24s} {h[0]:3d} | {h[1]:3d}   = {100*sum(h)/n:.2f}%')
same=sum([int(x) for x in r['final8'][:4]]==sets['ranked top3 + EP'](r,ep,fl) for r,res,ep,fl in R[-200:])
print('last 200 rounds: page FINAL 4 == top3+EP in',same)
