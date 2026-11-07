import json, sys, importlib.util
sys.argv = ['x', sys.argv[1]]
src = open(sys.argv[1].replace('dump_all2.json','analyze.py')).read().split("groups = {")[0]
exec(src)
rows = []
for r in R:
    it, tf = items(r)
    g = r['grid_ep']
    if g is not None:
        it['G2'] = ((g//10+6)%10)*10 + (g%10+4)%10
        for name, (dt, du) in {'Gcm1':(5,9),'Gcm2':(5,8),'Gcp2':(5,7),'Gcp1':(5,1),'Gm2c':(8,5),'Gp1m1':(1,9)}.items():
            it[name] = ((g//10+dt)%10)*10 + (g%10+du)%10
    grp = 'J' if r['series']=='j' else 'valid' if r['series'] in ('h','i') else 'train'
    rows.append((grp, r['res'], it))
names = sorted({k for _,_,it in rows for k in it})
def score(sel, grp):
    h = n = 0
    for g, res, it in rows:
        if g != grp: continue
        nums = []
        for k in sel:
            if k in it and it[k] not in nums: nums.append(it[k])
        nums = nums[:16]; n += len(nums); h += res in nums
    return h, n
sel = []
while True:
    best = max((k for k in names if k not in sel), key=lambda k: (score(sel+[k], 'train')[0], -names.index(k)))
    if score(sel+[best], 'train')[0] <= score(sel, 'train')[0] and len(sel) >= 16: break
    sel.append(best)
    if len(sel) >= 22: break
print('greedy order:', sel)
for grp in ('train','valid','J'):
    h, n = score(sel, grp); print(grp, 'hits', h, 'numbers', n, 'by size', round(n/100,1))
cur = ['B0','B1','B2','B3','B4','G2','A0','R1','R2','R3','R4','R5','R6','R7'] + [f'T{i:02d}' for i in range(1,12)]
for grp in ('train','valid','J'):
    h, n = score(cur, grp); print('current-like', grp, h, n, round(n/100,1))
