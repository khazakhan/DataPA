import json,re,os
os.chdir('/home/khazakhan/DataScinceAnal')
b={}
for l in open('rrr_records/builder60_live.jsonl'):
    r=json.loads(l); b[r['round']]=r
def order(page,which):
    t=open(page).read()
    m=re.search(r'\*\*%s \((tens|units)\)\*\* \| \*\*\d\*\* \| [^|]+\| ([\d ]+) \|'%which,t)
    return [int(x) for x in m.group(2).split()] if m else None
res=[]
for rd,r in b.items():
    if r.get('result') is None: continue
    p='rrr_outputs/%s.md'%rd.lower()
    if not os.path.exists(p): continue
    o=order(p,'OPEN'); c=order(p,'CLOSE')
    if not o or not c: continue
    res.append((rd,r,o,c))
print('rounds',len(res))
def bvote(lst,pos,w):
    s=[0.0]*10
    for i,n in enumerate(lst):
        d=n//10 if pos==0 else n%10
        s[d]+=w(i)
    return sorted(range(10),key=lambda d:-s[d])
W={'flat60':lambda i:1,'lin':lambda i:60-i,'top20':lambda i:1 if i<20 else 0,'inv':lambda i:1/(i+1)}
def score(name,fo,fc):
    h=[[0,0,0],[0,0,0]]
    half=len(res)//2; hh=[[0,0],[0,0]]
    for k,(rd,r,o,c) in enumerate(res):
        R=r['result']; oo=fo(r,o); cc=fc(r,c)
        for j,(ordr,d) in enumerate([(oo,R//10),(cc,R%10)]):
            rk=ordr.index(d)
            h[j][0]+=rk==0; h[j][1]+=rk<3; h[j][2]+=rk
            hh[j][k>=half]+=rk<3
    n=len(res)
    print(f"{name:12s} OPEN top1 {h[0][0]:3d} top3 {h[0][1]:3d} ({hh[0][0]}|{hh[0][1]}) avgrank {h[0][2]/n:.2f} | CLOSE top1 {h[1][0]:3d} top3 {h[1][1]:3d} ({hh[1][0]}|{hh[1][1]}) avgrank {h[1][2]/n:.2f}")
score('page',lambda r,o:o,lambda r,c:c)
for k,w in W.items():
    score('b60-'+k,lambda r,o,w=w:bvote(r['builder'],0,w),lambda r,c,w=w:bvote(r['builder'],1,w))
# blend: page rank points + builder
def blend(page,lst,pos,a):
    s=[0.0]*10
    for i,d in enumerate(page): s[d]+=(10-i)
    v=[0.0]*10
    for i,n in enumerate(lst): v[n//10 if pos==0 else n%10]+=(60-i)
    mx=max(v) or 1
    for d in range(10): s[d]+=a*10*v[d]/mx
    return sorted(range(10),key=lambda d:-s[d])
for a in (0.5,1,2):
    score(f'blend{a}',lambda r,o,a=a:blend(o,r['builder'],0,a),lambda r,c,a=a:blend(c,r['builder'],1,a))
print('chance: top1 %.1f top3 %.1f avgrank 4.5'%(len(res)*.1,len(res)*.3))
