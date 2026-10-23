import json, sys
rows = [r for r in json.load(open(sys.argv[1])) if 'ocjp' in r and r.get('star')]
U = ['rec', 'table', 'again', 'wide', 'yx', 'found']; T = ['strong', 'fam_seats', 'ncspec']
def L(d, k):
    if k == 'table': return set(t[0] for t in d['table'])
    if k == 'again': return set(a for a in d['again'] if a is not None)
    return set(e[0] if isinstance(e, list) else e for e in (d.get(k) or []))
def f4(d):
    c = sorted(set(d['ocjp'])); s = {k: L(d, k) for k in U + T}
    return sorted(c, key=lambda v: (-sum(v in s[k] for k in U), -sum(v in s[k] for k in T), v))
def star(d): return [v for v, _ in d['star']]
def starocjp(d):
    o = set(d['ocjp']); return [v for v in star(d) if v in o]
methods = {'FINAL 4 (shipped)': lambda d: f4(d)[:4], 'MASTER': lambda d: f4(d)[:1],
           'star #1': lambda d: star(d)[:1], 'star top 3': lambda d: star(d)[:3],
           'star top 4': lambda d: star(d)[:4], 'star top 4 inside OCJP': lambda d: starocjp(d)[:4]}
n = len(rows); half = n // 2
print('rounds', n)
for name, f in methods.items():
    h = [d['res'] in f(d) for d in rows]
    sz = sum(len(f(d)) for d in rows) / n
    print(f"{name:24s} {sum(h):4d}/{n} = {sum(h)/n:5.1%}  (size {sz:.1f}, chance {sz:.1f}%)"
          f"   1st half {sum(h[:half])}  2nd half {sum(h[half:])}   N {sum(x for x, d in zip(h, rows) if d['series']=='n')}/{sum(d['series']=='n' for d in rows)}")
a=[d['res'] in star(d)[:1] for d in rows]; b=[d['res'] in f4(d)[:1] for d in rows]
print('star#1 only',sum(x and not y for x,y in zip(a,b)),'MASTER only',sum(y and not x for x,y in zip(a,b)),'both',sum(x and y for x,y in zip(a,b)))
same=sum(star(d)[0]==f4(d)[0] for d in rows); print('same pick rounds',same)
u=[set(f4(d)[:4])|set(star(d)[:4]) for d in rows]; h=sum(d['res'] in x for d,x in zip(rows,u)); sz=sum(map(len,u))/n
print(f'union F4+star4 {h}/{n}={h/n:.1%} size {sz:.1f}')
q=n//4
for i in range(4):
    seg=rows[i*q:(i+1)*q]; print('quarter',i+1,'star#1',sum(d['res'] in star(d)[:1] for d in seg),'MASTER',sum(d['res'] in f4(d)[:1] for d in seg))
