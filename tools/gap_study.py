"""Gap study (user 2026-11-05, S58 '32 missed, fill the gap'): every 1-change
form of the LAST row (old / new ops, xy / yx, one side sign flipped / cut
switched / step switched) tested on all history rounds, with the newest
series P-S apart (honest check).  Chance per form = 1 in 100."""
import json, sys, io, os, contextlib, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
H = json.load(open('rrr_records/history_all.json'))
SW = lambda o: AB[D._op_label(*(lambda c, k: (c, {1: 2, 2: 1, -1: -2, -2: -1}.get(k, k)))(*D._op_side(D.OP_ABBREV[o])))]
CH = {'as is': lambda o: o, 'sign flipped': lambda o: D.SIGN_FLIP[o], 'cut switched': lambda o: D.KK_CUT_TOGGLE[o], 'step switched': SW}
old_ = collections.Counter(); new_ = collections.Counter(); n_old = n_new = 0
for h in H:
    last = [r for r in h['rows'] if r[7] == 'LAST']
    if not last:
        continue
    newer = h['series'] in ('p', 'q', 'r', 's')
    n_new += newer; n_old += not newer
    pos, a, b, ox, oy, nx, ny, _ = last[-1]
    e, res = h['ep'], h['res']
    for which, (p, q) in (('old', (AB[ox], AB[oy])), ('new', (AB[nx], AB[ny]))):
        for rd, (u, w) in (('xy', (p, q)), ('yx', (q, p))):
            for side in ('x', 'y'):
                for cn, f in CH.items():
                    if cn == 'as is' and side == 'y':
                        continue
                    uu, ww = (f(u), w) if side == 'x' else (u, f(w))
                    v = D.apply_op(e // 10, uu) * 10 + D.apply_op(e % 10, ww)
                    key = f"LAST {which} {rd}, " + ('as is' if cn == 'as is' else f"{side} {cn}")
                    (new_ if newer else old_)[key] += v == res
print(f"rounds: older series {n_old}, newest P-S {n_new} (chance per form {n_old/100:.1f} / {n_new/100:.1f})")
for k in sorted(old_, key=lambda k: -(old_[k] + new_[k])):
    print(f"   {k:34s} older {old_[k]:3d}   P-S {new_[k]:2d}   all x{(old_[k] + new_[k]) / ((n_old + n_new) / 100):.2f}")
