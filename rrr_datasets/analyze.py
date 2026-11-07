import json, sys
from collections import Counter, defaultdict
R = json.load(open(sys.argv[1]))
AB = {'nc':0,'+1':1,'+2':2,'-1':9,'-2':8,'cut':5,'c+1':6,'c+2':7,'c-1':4,'c-2':3}
INV = {v:k for k,v in AB.items()}
def parts(d):  # (has_cut, signed step) from delta
    cutf = d in (5,6,7,4,3); n = (d-5)%10 if cutf else d
    return cutf, {0:0,1:1,2:2,9:-1,8:-2}[n]
def join(cutf, n): return ((5 if cutf else 0) + n) % 10
def ap(ep, dx, dy): return ((ep//10+dx)%10)*10 + (ep%10+dy)%10
def items(r):
    ep, g = r['ep'], r['grid_ep']; it = {}
    tf = []
    for v, lab in r['table']:
        if v not in tf: tf.append(v)
    for i, v in enumerate(tf): it[f'T{i+1:02d}'] = v
    if g is None: return it, tf
    bt, bu = (g//10+5)%10, (g%10+4)%10
    for rank, st in enumerate((0,-1,1,-2,2)): it[f'B{rank}'] = bt*10 + (bu+st)%10
    dv = bt*10+bu; dx, dy = (dv//10-ep//10)%10, (dv%10-ep%10)%10
    (xc, xn), (yc, yn) = parts(dx), parts(dy)
    sw = {1:2,2:1,-1:-2,-2:-1}
    for v, lab in r['table']:
        sx, sy = lab.split('/')
        if sy in ('-1','-2','+1','+2'):
            n = parts(AB[sy])[1]; it['R1'] = ap(ep, AB[sx], join(True, -n)); break
    if -yn in sw: it['R2'] = ap(ep, join(True, sw[-yn]), join(False, xn))
    if xn in sw:
        it['R3'] = ap(ep, join(False, -sw[xn]), 5)
        it['R4'] = ap(ep, join(xc, sw[xn]), dy)
    if xn: it['R5'] = ap(ep, join(False, -xn), dy)
    if dy != 0: it['R6'] = ap(ep, dx, 0)
    for v, lab in r['table']:
        sx, sy = lab.split('/')
        if v//10 != bt: continue
        a, b = parts(AB[sx])[1], parts(AB[sy])[1]
        if a and b:
            it['R7'] = ap(ep, join(False, -a), join(False, (-1 if a > 0 else 1)*abs(b))); break
    for i, v in enumerate(r['again']):
        if v is not None: it[f'A{i}'] = v
    for i, v in enumerate(r['rec'][:12]): it[f'C{i+1:02d}'] = v
    return it, tf
groups = {'train': ('b','c','d','ds','e','f','g'), 'valid': ('h','i'), 'J': ('j',)}
stat = defaultdict(lambda: defaultdict(lambda: [0,0]))
gfreq = defaultdict(Counter); efreq = defaultdict(Counter); n = Counter()
for r in R:
    grp = next(k for k, v in groups.items() if r['series'] in v)
    it, tf = items(r); n[grp] += 1
    for k, v in it.items():
        stat[k][grp][0] += 1; stat[k][grp][1] += (v == r['res'])
    if r['grid_ep'] is not None:
        g = r['grid_ep']; gfreq[grp][((r['res']//10-g//10)%10, (r['res']%10-g%10)%10)] += 1
    efreq[grp][((r['res']//10-r['ep']//10)%10, (r['res']%10-r['ep']%10)%10)] += 1
print(dict(n))
print('item   train(hit/rounds)  valid   J')
for k in sorted(stat):
    s = stat[k]; print(f"{k:5} {s['train'][1]:3}/{s['train'][0]:3}   {s['valid'][1]:3}/{s['valid'][0]:3}   {s['J'][1]}/{s['J'][0]}")
print('top grid-EP op cells (train count, valid count):')
for (c, k) in sorted(((v, k) for k, v in gfreq['train'].items()), reverse=True)[:22]:
    print(f"  {INV[k[0]]:>4}/{INV[k[1]]:<4} train {c:2}  valid {gfreq['valid'][k]:2}  J {gfreq['J'][k]}")
print('top chain-EP op cells:')
for (c, k) in sorted(((v, k) for k, v in efreq['train'].items()), reverse=True)[:10]:
    print(f"  {INV[k[0]]:>4}/{INV[k[1]]:<4} train {c:2}  valid {efreq['valid'][k]:2}")
json.dump({'g': {f"{k[0]}{k[1]}": v for k, v in gfreq['train'].items()}}, open(sys.argv[1] + '.g', 'w'))
