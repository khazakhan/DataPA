import re,glob,os,itertools,sys
S=os.path.dirname(os.path.abspath(__file__)); D='/home/khazakhan/DataScinceAnal/rrr_datasets/'
SH={'nc':0,'+1':1,'+2':2,'-1':9,'-2':8,'cut':5,'c+1':6,'c+2':7,'c-1':4,'c-2':3}
NM={v:k for k,v in SH.items()}
def flip(s):
    c=5 if s in(5,6,7,4,3) else 0; d=(s-c)%10; return (c-d)%10
def tog(s): return (s+5)%10
TR={'same':lambda s:s,'flip':flip,'cut-switch':tog,'cut-switch+flip':lambda s:flip(tog(s))}
def vals(f):
    v=[]
    for l in open(f):
        for t in l.split():
            if re.fullmatch(r'\d{1,2}',t): v.append(int(t))
    return v
def info(name):
    o=open(f'{S}/outs/{name}.out').read()
    m=re.search(r'\]LAST\s+(\d\d) → (\d\d)\s+(\S+)\s+(\S+)',o)
    v=vals(D+name+'.txt')
    return dict(cep=int(m.group(2)),cx=SH[m.group(3)],cy=SH[m.group(4)],gep=v[-1],gprev=v[-2])
names=[f'ds{i:02d}' for i in range(1,42)]+[f'b{i:02d}' for i in range(1,27)]
R=[]
for i,n in enumerate(names):
    d=info(n); d['name']=n
    nxt=names[i+1] if i+1<len(names) and not(n=='ds41') else None
    d['res']=vals(D+nxt+'.txt')[-1] if nxt and n!='b26' else None
    R.append(d)
def ap(v,sx,sy): return ((v//10+sx)%10)*10+(v%10+sy)%10
rules={}
for src,opsrc,cross,tx,ty in itertools.product(['chainEP','gridEP'],['chain step','grid step'],[0,1],TR,TR):
    def pred(d,src=src,opsrc=opsrc,cross=cross,tx=tx,ty=ty):
        if opsrc=='chain step': a,b=d['cx'],d['cy']
        else: a,b=(d['gep']//10-d['gprev']//10)%10,(d['gep']%10-d['gprev']%10)%10
        if cross: a,b=b,a
        base=d['cep'] if src=='chainEP' else d['gep']
        return ap(base,TR[tx](a),TR[ty](b))
    rules[(src,opsrc,'cross' if cross else 'straight',tx,ty)]=pred
# extra simple rules
rules[('reverse chainEP',)]=lambda d:(d['cep']%10)*10+d['cep']//10
rules[('reverse gridEP',)]=lambda d:(d['gep']%10)*10+d['gep']//10
known=[d for d in R if d['res'] is not None]
sc=sorted(((sum(p(d)==d['res'] for d in known),k) for k,p in rules.items()),reverse=True)
print('rounds',len(known),'rules',len(rules))
for h,k in sc[:8]: print(h,k,[d['name'] for d in known if rules[k](d)==d['res']])
import collections; print('hit distribution',sorted(collections.Counter(h for h,_ in sc).items()))
last=R[-1]; print('NEXT',last, )
for h,k in sc[:8]: print(' pred',k,'%02d'%rules[k](last))
tgt=collections.Counter()
for d in known: tgt[(NM[(d['res']//10-d['cep']//10)%10],NM[(d['res']%10-d['cep']%10)%10])]+=1
print(tgt.most_common(6))
k=('chainEP','chain step','cross','flip','cut-switch'); print('RULE',k,[d['name'] for d in known if rules[k](d)==d['res']],'next %02d'%rules[k](last))
print('--- single-digit rules on chain EP (hits of %d; chance %.1f)'%(len(known),len(known)/10))
for axis in 'xy':
    for frm in ('cx','cy'):
        for t in TR:
            hits=[d['name'] for d in known if ((d['cep']//10 if axis=='x' else d['cep']%10)+TR[t](d[frm]))%10==(d['res']//10 if axis=='x' else d['res']%10)]
            print(' new',axis,'= old',frm[1],t,len(hits),'| series B:',sum(h.startswith('b') for h in hits))
k=('chainEP','chain step','straight','flip','flip'); print('RULE',k,[d['name'] for d in known if rules[k](d)==d['res']],'next %02d'%rules[k](last))
k=('chainEP','chain step','straight','same','cut-switch+flip'); print('HELD next %02d'%rules[k](last))
print('TARGETS',tgt.most_common(8))
tb=collections.Counter((NM[(d['res']//10-d['cep']//10)%10],NM[(d['res']%10-d['cep']%10)%10]) for d in known if d['name'].startswith('b')); print('TARGETS B',tb.most_common(6))
print('repeat-prev-target hits',sum(1 for a,b in zip(known,known[1:]) if b['name']!='b01' and ((a['res']-0)//10-a['cep']//10)%10==(b['res']//10-b['cep']//10)%10 and (a['res']%10-a['cep']%10)%10==(b['res']%10-b['cep']%10)%10),'of',len(known)-2)
k=('gridEP','grid step','straight','same','same'); print('RULE',k,[d['name'] for d in known if rules[k](d)==d['res']],'next %02d'%rules[k](last))
gt=collections.Counter((NM[(d['res']//10-d['gep']//10)%10],NM[(d['res']%10-d['gep']%10)%10]) for d in known); print('GRID TARGETS',gt.most_common(6))
for lab,base in (('grid','gep'),('chain','cep')):
    for ax in 'xy':
        c=collections.Counter(NM[((d['res']//10 if ax=='x' else d['res']%10)-(d[base]//10 if ax=='x' else d[base]%10))%10] for d in known)
        cb=collections.Counter(NM[((d['res']//10 if ax=='x' else d['res']%10)-(d[base]//10 if ax=='x' else d[base]%10))%10] for d in known if d['name'].startswith('b'))
        print('AXIS',lab,ax,c.most_common(4),'| B:',cb.most_common(3))
