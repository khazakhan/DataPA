"""ONE-MEN-ARMY (user 2026-11-06): the 20 strongest numbers from all tables.
Each list that has fired above chance on the 1293 history rounds votes with its
weight (log lift, rrr_records/oma_weights.json); a number's score is the sum
of the weights of the lists holding it; ties go by the page ranking.
Held-out test (leave one series out): 344 of 1293 vs chance 259 (x1.33);
STRONG 20 alone 349 -> about the same, display only.

python3 tools/oma.py <dataset>            print ONE-MEN-ARMY for the next round
python3 tools/oma.py <dataset> --score R  also log round R's numbers (for the live count)
python3 tools/oma.py --result R N         score logged round R with result N"""
import sys, os, json, io, contextlib, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.'); sys.path.insert(0, 'tools')
from replay_collect import collect
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
LOG = 'rrr_records/oma_live.jsonl'
if sys.argv[1] == '--result':          # python3 tools/oma.py --result S68 37 : score a declared round
    rnd, res = sys.argv[2], int(sys.argv[3])
    recs = [json.loads(l) for l in open(LOG)]
    for r in recs:
        if r['round'] == rnd: r['result'] = res; print(rnd, res, 'HIT' if res in r['oma'] else 'miss')
    open(LOG, 'w').write(''.join(json.dumps(r) + '\n' for r in recs)); sys.exit()
ds = sys.argv[1]
W = json.load(open('rrr_records/oma_weights.json'))['weights']
src = collect(ds)
with contextlib.redirect_stdout(io.StringIO()):
    os.environ['OMA_OFF'] = '1'; D.run(open(ds), None, None)
ep = D._RRR_ASK['ep']; ex, ey = ep // 10, ep % 10
pos = {v: i for i, v in enumerate(src['rk'])}
sc = collections.Counter(); who = collections.defaultdict(list)
for k, w in W.items():
    for v in set(src.get(k, [])):
        sc[v] += w; who[v].append(k)
oma = sorted(range(100), key=lambda v: (-sc[v], pos.get(v, 999), v))[:20]
op = lambda v: f"{D.OP_ABBREV[D.find_op(ex, v // 10)]}/{D.OP_ABBREV[D.find_op(ey, v % 10)]}"
LOG = 'rrr_records/oma_live.jsonl'
recs = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
done = [r for r in recs if 'result' in r]
hits = sum(r['result'] in r['oma'] for r in done)
if '--score' in sys.argv:
    rnd = sys.argv[sys.argv.index('--score') + 1]
    recs = [r for r in recs if r['round'] != rnd] + [dict(round=rnd, dataset=ds, root=ep, oma=oma)]
    open(LOG, 'w').write(''.join(json.dumps(r) + '\n' for r in recs))
fl = D._RRR3_PREV.get('flat') or []
print(f"ONE-MEN-ARMY (20 strongest from all fired tables, {D._after_tag(fl[-1]) if fl else 'EP'}, ops on ROOT {D._root_op(ep)}):")
for i, v in enumerate(oma):
    print(f"  {i+1:2d}. {v:02d} ({op(v)})  score {sc[v]:.2f}  [{', '.join(sorted(who[v], key=lambda k: -W[k]))}]")
print(f"  ascending: {' '.join(f'{v:02d}' for v in sorted(oma))}")
print(f"  live {hits} of {len(done)}; history held-out 344 of 1293 (26.6%) vs chance 20%; STRONG 20 alone 349. Display only.")
