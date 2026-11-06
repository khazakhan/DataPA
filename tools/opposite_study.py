import json, sys, io, contextlib, collections
sys.path.insert(0, '/home/khazakhan/DataScinceAnal')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
def full(o): return AB.get(o, o)
ap = lambda e, x, y: D.apply_op(e // 10, x) * 10 + D.apply_op(e % 10, y)
def T(o, f):
    if 'C' in f: o = D.KK_CUT_TOGGLE[o]
    if 'F' in f: o = D.SIGN_FLIP[o]
    return o
# forms: which pair (xy/yx of new/old) and transform on x / y
FORMS = {}
for src in ('new xy', 'new yx', 'old xy', 'old yx'):
    for fx in ('', 'F', 'C', 'FC'):
        for fy in ('', 'F', 'C', 'FC'):
            FORMS[(src, fx, fy)] = None
def pairs(ox, oy, nx, ny):
    return {'new xy': (nx, ny), 'new yx': (ny, nx), 'old xy': (ox, oy), 'old yx': (oy, ox)}
def label(fx, fy):
    n = lambda f: {'': 'as is', 'F': 'sign flip', 'C': 'cut sw', 'FC': 'cut sw+flip'}[f]
    return f"x {n(fx)}, y {n(fy)}"
def run(rounds, name):
    hit = collections.Counter(); size = collections.Counter(); n = 0
    grp_hit = collections.Counter(); grp_size = collections.Counter()
    for root, res, rows in rounds:
        n += 1
        per = collections.defaultdict(set)
        for (ox, oy, nx, ny) in rows:
            P = pairs(full(ox), full(oy), full(nx), full(ny))
            for (src, fx, fy) in FORMS:
                p, q = P[src]
                per[(src, fx, fy)].add(ap(root, T(p, fx), T(q, fy)))
        groups = collections.defaultdict(set)
        for k, s in per.items():
            size[k] += len(s); hit[k] += res in s
            src, fx, fy = k
            ch = len(fx) + len(fy)
            opp = 'as is (0 changes)' if ch == 0 else ('both sides fully opposite (cut sw+flip both)' if fx == fy == 'FC' else f'{ch} change(s)')
            groups[opp] |= s
            groups['ANY xy/yx form (all 16 per pair)'] |= s
        for g, s in groups.items():
            grp_size[g] += len(s); grp_hit[g] += res in s
    print(f"\n== {name}: {n} rounds ==")
    print(f"{'group':48s} {'held':>5s} {'chance':>7s} {'x':>5s}  avg size")
    for g in sorted(grp_hit, key=lambda g: g):
        ch = grp_size[g] / 100
        print(f"{g:48s} {grp_hit[g]:5d} {ch:7.1f} {grp_hit[g]/ch:5.2f}  {grp_size[g]/n:5.1f}")
    best = sorted(FORMS, key=lambda k: -(hit[k] / max(size[k] / 100, 1e-9)))
    print("single forms, best and worst by held/chance:")
    for k in best[:6] + best[-3:]:
        ch = size[k] / 100
        print(f"   {k[0]:7s} {label(k[1], k[2]):34s} {hit[k]:4d} vs {ch:6.1f}  x{hit[k]/ch:4.2f}")
    return hit, size
# live S/T
L = [json.loads(l) for l in open('/home/khazakhan/DataScinceAnal/rrr_records/live.jsonl')]
L = [r for r in L if r.get('round', '')[:1] in 'ST' and r.get('result') is not None and r.get('rows')]
live = [(r['ep'], r['result'], [(x['old'][0], x['old'][1], x['new'][0], x['new'][1]) for x in r['rows']]) for r in L]
run(live, 'LIVE S2-T5')
H = json.load(open('/home/khazakhan/DataScinceAnal/rrr_records/history_all.json'))
hist = [(h['ep'], h['res'], [(row[3], row[4], row[5], row[6]) for row in h['rows']]) for h in H if h['rows']]
run(hist, 'HISTORY')
print("\n== out-of-sample: forms picked on HISTORY, scored on LIVE ==")
with contextlib.redirect_stdout(io.StringIO()):
    hh, hs = run(hist, 'h'); lh, ls = run(live, 'l')
rk = sorted(FORMS, key=lambda k: -(hh[k] / max(hs[k], 1)))
for top in (1, 4, 8):
    held = 0; sz = 0
    for root, res, rows in live:
        s = set()
        for (ox, oy, nx, ny) in rows:
            P = pairs(full(ox), full(oy), full(nx), full(ny))
            for (src, fx, fy) in rk[:top]:
                p, q = P[src]; s.add(ap(root, T(p, fx), T(q, fy)))
        held += res in s; sz += len(s)
    print(f"   top {top} history forms: live held {held} of {len(live)} vs chance {sz/100:.1f}")
rk2 = sorted(FORMS, key=lambda k: -(lh[k] / max(ls[k], 1)))
print("   best LIVE forms, on HISTORY:", [(k[0], label(k[1], k[2]), hh[k], round(hs[k]/100, 1)) for k in rk2[:3]])
