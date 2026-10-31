"""Log the user's LAST-row move for one round.

python3 tools/last_move.py <round> <dataset before result> <result> <x op> <y op>

Finds which cells of the LAST ROW DIGIT MENU give the user's x op and y op
(source op of the LAST row x change) and appends one line to
rrr_records/last_moves.jsonl.  Re-logging a round replaces its line."""
import sys, io, os, json, contextlib
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.')
import DataProcessing as D
rnd, ds, res, xop, yop = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
with contextlib.redirect_stdout(io.StringIO()):
    D.run(open(ds), None, None)
ep = D._RRR_ASK['ep']
last = [r for r in D._RRR_ASK['rows'] if r[7] == 'LAST'][-1]
pos, a, b, ox, oy, nx, ny, _ = last
srcs = {"new x": nx, "new y": ny, "old x": ox, "old y": oy}
sw = {1: 2, 2: 1, -1: -2, -2: -1, 0: 0}
def menu(target):
    tc, tk = D._op_side(target)
    hits = []
    for nm, op in srcs.items():
        c, k = D._op_side(D.OP_ABBREV[op])
        for ch, (cc, kk) in (("as is", (c, k)), ("sign flipped", (c, -k)), ("cut switched", (not c, k)), ("step switched", (c, sw[k]))):
            if (cc, kk) == (tc, tk):
                hits.append(f"{nm} {ch}")
    return hits
rec = dict(round=rnd, ep=ep, result=res, x_op=xop, y_op=yop,
           last=dict(pos=pos, src=f"{a:02d}->{b:02d}", old=[D.OP_ABBREV[ox], D.OP_ABBREV[oy]], new=[D.OP_ABBREV[nx], D.OP_ABBREV[ny]]),
           x_from=menu(xop), y_from=menu(yop))
chk = D._op_apply(ep // 10, *D._op_side(xop)) * 10 + D._op_apply(ep % 10, *D._op_side(yop))
rec['check'] = chk == res
p = 'rrr_records/last_moves.jsonl'
old = [l for l in (open(p).read().splitlines() if os.path.exists(p) else []) if json.loads(l)['round'] != rnd]
open(p, 'w').write('\n'.join(old + [json.dumps(rec)]) + '\n')
print(json.dumps(rec, indent=1))
