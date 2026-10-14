import json, os, re, sys, math, random, collections
sys.argv = ['x']
os.chdir('/home/khazakhan/DataScinceAnal')
import importlib.util
spec = importlib.util.spec_from_file_location('dp', 'DataProcessing.py'); dp = importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(dp)
except SystemExit: pass
S = '/tmp/claude-1000/-home-khazakhan/2943c45c-cff3-42ca-943c-1c3fe5bcef48/scratchpad/all'
ORDER = ['b','c','d','f','h','i','j','k']
def nextfile(s, n):
    for f in (f"rrr_datasets/{s}{n+1:02d}.txt", f"rrr_datasets/{s}{n+1}.txt"):
        if os.path.exists(f): return f
rounds = []
for s in ORDER:
    ns = sorted(int(f.split('_')[1][:-5]) for f in os.listdir(S) if f.startswith(s+'_'))
    for n in ns:
        d = json.load(open(f"{S}/{s}_{n}.json"))
        tok = open(nextfile(s, n)).read().split()[-1]
        if not re.fullmatch(r'\d\d?', tok): continue
        d['r'] = int(tok); d['id'] = f"{s}{n}"; rounds.append(d)
def oplab(ep, v):
    return dp.OP_ABBREV[dp.find_op(ep//10, v//10)] + '/' + dp.OP_ABBREV[dp.find_op(ep%10, v%10)]
print('rounds', len(rounds))
inO = sum(d['r'] in d['ocjp'] for d in rounds); szO = sum(len(set(d['ocjp'])) for d in rounds)
print(f"result in OCJP: {inO}/{len(rounds)} = {inO/len(rounds):.1%}; avg OCJP size {szO/len(rounds):.1f} -> chance {szO/len(rounds)/100:.1%}")
LISTS = ['strong','rec','yx','wide','found','fam_seats','ncspec']
def feats(d, v, cands):
    f = {}
    ent = [e for e in d['ocjp_full'] if e[0] == v]
    f['minplace'] = min(e[2] for e in ent)
    f['mult'] = len(ent)
    f['base'] = any(e[3]=='base' for e in ent)
    f['votes'] = sum(v in (d[k] or []) for k in LISTS) + (v in [t[0] for t in d['table']]) + (v in [a for a in d['again'] if a is not None])
    f['op'] = oplab(d['ep'], v)
    xo, yo = f['op'].split('/'); f['xo'], f['yo'] = xo, yo
    f['tens'] = v//10; f['units'] = v%10
    return f
# walk-forward
methods = collections.defaultdict(lambda: [0, 0])  # hits, rounds with OCJP
opc = collections.Counter(); xc = collections.Counter(); yc = collections.Counter(); numc = collections.Counter()
plc = collections.Counter(); pln = collections.Counter()   # place-class hits / appearances
vc = collections.Counter(); vn = collections.Counter()
mc = collections.Counter(); mn = collections.Counter()
rnd = random.Random(1); rand_exp = 0.0
WARM = 100
for i, d in enumerate(rounds):
    cands = sorted(set(d['ocjp']))
    if cands and i >= WARM:
        F = {v: feats(d, v, cands) for v in cands}
        def pc(v): return min(F[v]['minplace'], 39)//10
        tot = sum(opc.values()) + 1
        scores = {
          'earliest place': lambda v: -F[v]['minplace'],
          'most lists (votes)': lambda v: F[v]['votes'],
          'repeated in OCJP': lambda v: F[v]['mult'],
          'op pair seen most': lambda v: (opc[F[v]['op']]+1),
          'x op x y op seen most': lambda v: (xc[F[v]['xo']]+1)*(yc[F[v]['yo']]+1),
          'number seen most (HOT)': lambda v: numc[v],
          'place class best rate': lambda v: (plc[pc(v)]+1)/(pln[pc(v)]+10),
          'votes class best rate': lambda v: (vc[F[v]['votes']]+1)/(vn[F[v]['votes']]+10),
          'combined (NB)': lambda v: math.log((plc[pc(v)]+1)/(pln[pc(v)]+10)) + math.log((vc[F[v]['votes']]+1)/(vn[F[v]['votes']]+10)) + math.log((mc[F[v]['mult']]+1)/(mn[F[v]['mult']]+10)) + math.log((xc[F[v]['xo']]+1)/(sum(xc.values())+10)) + math.log((yc[F[v]['yo']]+1)/(sum(yc.values())+10)),
        }
        for name, fn in scores.items():
            top = sorted(cands, key=lambda v: (-fn(v), v))[:4]
            methods[name][0] += d['r'] in top; methods[name][1] += 1
        rand_exp += (4/len(cands)) * (d['r'] in cands)
        methods['random 4 of OCJP (expected)'][1] += 1
    # learn after the round
    if cands:
        for v in cands:
            f = feats(d, v, cands); k = min(f['minplace'], 39)//10
            pln[k] += 1; vn[f['votes']] += 1; mn[f['mult']] += 1
            if v == d['r']: plc[k] += 1; vc[f['votes']] += 1; mc[f['mult']] += 1
    lab = oplab(d['ep'], d['r']); opc[lab] += 1; xc[lab.split('/')[0]] += 1; yc[lab.split('/')[1]] += 1; numc[d['r']] += 1
n = methods['earliest place'][1]
methods['random 4 of OCJP (expected)'][0] = rand_exp
print(f"\nwalk-forward over {n} rounds (first {WARM} used only to learn); any 4 numbers by chance = 4.0%")
for name, (h, m) in sorted(methods.items(), key=lambda x: -x[1][0]):
    print(f"  {name:<30} {h:6.1f} hits / {m} = {h/m:.1%}")
