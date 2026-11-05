"""Origin-op study (user 2026-11-05): for every history round find the
ORIGIN op of the result (after -> result, and EP -> result, xy and yx), then
check which table-4 Ops (row new/old ops and the derived columns) held that op
and which missed.  Also tests whether the origin op repeats from the previous
round (same / sign flip / cut toggle / swap / rrr_next_op).  Chance per op
pair = 1 in 100 (10 x-ops x 10 y-ops; ops <-> numbers are one to one)."""
import json, sys, io, contextlib, collections
sys.path.insert(0, '/home/khazakhan/DataScinceAnal')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
NM = D.OP_ABBREV
H = sorted(json.load(open('/home/khazakhan/DataScinceAnal/rrr_records/history_all.json')), key=lambda h: (h['series'], h['k']))
fo = D.find_op
SF, CT = D.SIGN_FLIP, D.KK_CUT_TOGGLE


def after_of(ds):
    t = open('/home/khazakhan/DataScinceAnal/' + ds).read().split()
    t = [x for x in t if x.isdigit()]
    return int(t[-1])


def origin(src, res):
    xy = (fo(src // 10, res // 10), fo(src % 10, res % 10))
    yx = (fo(src // 10, res % 10), fo(src % 10, res // 10))
    return xy, yx


cols = collections.Counter(); size = collections.Counter(); n = 0
rep = collections.Counter(); prev = {}
x_af = collections.Counter(); y_af = collections.Counter()
same_af_ep = 0
for h in H:
    if not h['rows']:
        continue
    n += 1
    e, r = h['ep'], h['res']
    af = after_of(h['ds'])
    oxy, oyx = origin(e, r)
    axy, ayx = origin(af, r)
    x_af[NM[axy[0]]] += 1; y_af[NM[axy[1]]] += 1
    same_af_ep += axy == oxy
    # Ops list from table 4 rows
    lists = collections.defaultdict(set)
    for pos, a, b, ox, oy, nx, ny, tag in h['rows']:
        ox, oy, nx, ny = AB[ox], AB[oy], AB[nx], AB[ny]
        sx, sy = D._star_ops(ox, oy); tx, ty = D._tilde_ops(ox, oy)
        L = 'LAST ' if tag == 'LAST' else ''
        for nm, p in (('new ops', (nx, ny)), ('old ops', (ox, oy)), ('sign flip new', (SF[nx], SF[ny])),
                      ('cut toggle new', (CT[nx], CT[ny])), ('* ops', (sx, sy)), ('~ ops', (tx, ty)),
                      ('newold (nx,oy)', (nx, oy)), ('oldy,newy+-', (oy, SF[ny])), ('oldx,newx+-', (ox, SF[nx])),
                      ('rrr_next_op', D.rrr_next_op(nx, ny))):
            lists[nm].add(p); lists[L + nm].add(p) if L else None
    for nm, s in lists.items():
        cols[nm + ' | EP xy'] += oxy in s; cols[nm + ' | EP yx'] += oyx in s
        cols[nm + ' | after xy'] += axy in s
        size[nm + ' | EP xy'] += len(s); size[nm + ' | EP yx'] += len(s); size[nm + ' | after xy'] += len(s)
    # does the origin op repeat from the previous round?
    key = h['series']
    if key in prev and prev[key][0] == h['k'] - 1:
        p = prev[key][1]
        for nm, t in (('same op', p), ('sign flip', (SF[p[0]], SF[p[1]])), ('cut toggle', (CT[p[0]], CT[p[1]])),
                      ('x/y swapped', (p[1], p[0])), ('rrr_next_op', D.rrr_next_op(*p))):
            rep[nm] += axy == t; rep['_n'] += nm == 'same op'
    prev[key] = (h['k'], axy)
print(f"rounds {n}")
print("Ops list held the ORIGIN op (hits / expected by chance):")
for k in sorted(cols, key=lambda k: -(cols[k] / max(size[k] / 100, 1e-9))):
    print(f"   {k:34s} {cols[k]:4d} / {size[k]/100:6.1f}   x{cols[k]/(size[k]/100):.2f}")
print(f"origin op after->result same as EP->result: {same_af_ep}")
m = rep.pop('_n')
print(f"after->result origin op vs previous round's origin op ({m} pairs, chance {m/100:.1f} each):")
for k, v in rep.items():
    print(f"   {k:12s} {v}")
print("x op after->result:", dict(x_af.most_common()))
print("y op after->result:", dict(y_af.most_common()))
