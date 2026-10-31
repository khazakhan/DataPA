"""LAST-OP 4: rank all 100 numbers from the LAST row with the user's crossed
logic (x from new y, y from new x), weighting each change by how often the
user's logged moves used it (rrr_records/last_moves.jsonl).

python3 tools/lastop4.py          leave-one-out test on the logged moves"""
import json
from collections import Counter
SW = {1: 2, 2: 1}
def side(s):
    c = s.startswith('c')
    t = s[3:] if s.startswith('cut') else (s[1:] if c else s)
    return c, (0 if t in ('', 'nc') else int(t))
def change(src, dst):
    (c1, k1), (c2, k2) = side(src) if isinstance(src, str) else src, side(dst) if isinstance(dst, str) else dst
    cut = c1 != c2
    flip = bool(k1 and k2 and (k1 > 0) != (k2 > 0))
    if k1 == 0 and k2 != 0: st = 'add'
    elif k1 != 0 and k2 == 0: st = 'drop'
    elif abs(k1) != abs(k2): st = 'sw'
    else: st = 'same'
    return (cut, flip, st)
OPS = [(c, k) for c in (False, True) for k in (-2, -1, 0, 1, 2)]
def apply(d, c, k): return (((d + 5) % 10 if c else d) + k) % 10
def train(moves):
    fx, fy = Counter(), Counter()
    for m in moves:
        nx, ny = m['last']['new']
        fx[change(ny, m['x_op'])] += 1
        fy[change(nx, m['y_op'])] += 1
    return fx, fy, len(moves)
def rank(ep, nx, ny, model, a=0.5):
    fx, fy, n = model
    L = 16
    px = lambda ch: (fx[ch] + a) / (n + a * L)
    py = lambda ch: (fy[ch] + a) / (n + a * L)
    sx = {apply(ep // 10, *o): px(change(ny, o)) for o in OPS}
    sy = {apply(ep % 10, *o): py(change(nx, o)) for o in OPS}
    sc = {x * 10 + y: sx[x] * sy[y] for x in sx for y in sy}
    return sorted(sc, key=lambda v: -sc[v])
if __name__ == '__main__':
    M = [json.loads(l) for l in open('rrr_records/last_moves.jsonl')]
    hits = {4: 0, 8: 0, 10: 0}
    for i, m in enumerate(M):
        model = train(M[:i] + M[i + 1:])
        nx, ny = m['last']['new']
        r = rank(m['ep'], nx, ny, model)
        pos = r.index(m['result']) + 1
        for k in hits: hits[k] += pos <= k
        print(m['round'], m['result'], 'rank', pos, 'top4', r[:4])
    n = len(M)
    print(f"leave-one-out over {n} logged rounds: top4 {hits[4]} (chance {n*.04:.1f}), top8 {hits[8]} ({n*.08:.1f}), top10 {hits[10]} ({n*.1:.1f})")
