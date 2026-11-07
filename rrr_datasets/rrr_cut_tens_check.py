import re,glob,collections
def rows(f,n=None):
    R=[]
    for l in open(f):
        t=l.split()
        if len(t)>=4: R.append([int(x) if re.fullmatch(r'\d{1,2}',x) else None for x in t])
    return R
def stat(seq,lab):
    p=[(a,b) for a,b in zip(seq,seq[1:]) if a is not None and b is not None]
    c=collections.Counter((b//10-a//10)%10 for a,b in p); n=len(p)
    print(f'{lab:38s} pairs {n:6d}  tens+5: {c[5]/n*100:5.1f}%   max other: {max(v for k,v in c.items() if k!=5)/n*100:5.1f}%')
tot=collections.Counter(); N=0
for f in ['rrr_datasets/ds01.txt','rrr_datasets/b01.txt']+sorted(glob.glob('temp_data*.txt')):
    R=rows(f)
    if not R: continue
    flat=[v for r in R for v in r]; stat(flat,f.split('/')[-1]+' row-order')
    if f.startswith('rrr'):
        w=max(len(r) for r in R)
        for cidx in range(w):
            col=[r[cidx] if cidx<len(r) else None for r in R]; stat(col,f.split('/')[-1]+f' column {cidx+1}')
# live results
A=[int(l) for l in open('rrr_datasets/ds41.txt').read().split()[-41:]] if False else None
def tail(f,base):
    a=[x for x in open(f).read().split()]; b=[x for x in open(base).read().split()]
    return [int(x) for x in a[len(b)-1:]]
for f,base,lab in (('rrr_datasets/ds41.txt','rrr_datasets/ds01.txt','LIVE series A'),('rrr_datasets/b24.txt','rrr_datasets/b01.txt','LIVE series B')):
    s=tail(f,base); stat(s,lab+f' ({len(s)-1} results)')
