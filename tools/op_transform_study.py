"""Operation-transform model (user 2026-11-11): the next operation is learned as a CHANGE of an
earlier operation - same op, sign flipped, step +/-1 or +/-2, cut switched (each = a shift of the
digit step), and xy/yx crossed (take the other side's op).  On each side (x = tens, y = units) a
change is  target = a*source + b (mod 10), a = +1 (same direction) or -1 (sign flipped), b = shift
(0 same, 5 cut switch, +/-1, +/-2 ...), source = own side or the other side (crossed).
The model counts, from the chart's PAST only, how often each change happened, then scores every
next number.  Frames:
  A  EP op       : op into the EP          -> op EP -> next number
  B  ROOT op     : op earlier-EP -> ROOT   -> op ROOT -> next number   (number = ROOT + op)
  C  last result : last round's ROOT->result op -> this round's ROOT->result op
  D  ROOT op on EP: op earlier-EP -> ROOT  -> op EP -> next number
Walk-forward on every distinct chart from number 300; top-1 / top-4 numbers, OPEN/CLOSE digits.
Usage: python3 tools/op_transform_study.py"""
import os, sys, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, 'tools')
from oc_deep_study import charts

T, U = (lambda v: v // 10), (lambda v: v % 10)
step = lambda a, b: ((T(b) - T(a)) % 10, (U(b) - U(a)) % 10)
add = lambda v, s: ((T(v) + s[0]) % 10) * 10 + (U(v) + s[1]) % 10

class Model:
    def __init__(self):
        # w[side][src][a][b]: side 0 tens / 1 units; src 0 own side / 1 other side (crossed)
        self.w = [[[[1.0] * 10 for _ in range(2)] for _ in range(2)] for _ in range(2)]
    def learn(self, src, tgt):
        for side in (0, 1):
            for si, s in enumerate((src[side], src[1 - side])):
                for ai, a in enumerate((1, -1)):
                    self.w[side][si][ai][(tgt[side] - a * s) % 10] += 1
    def side_scores(self, src, side):
        out = [0.0] * 10
        for si, s in enumerate((src[side], src[1 - side])):
            for ai, a in enumerate((1, -1)):
                ww = self.w[side][si][ai]; tot = sum(ww)
                for t in range(10):
                    out[t] += ww[(t - a * s) % 10] / tot
        return out

def main():
    res = collections.defaultdict(lambda: [0, 0, 0, 0, 0])   # n, top1, top4, open1, close1
    for name, fl in charts():
        rep = sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / (len(fl) - 1)
        low = rep < 0.06
        grp = 'low-repeat' if low else 'normal'
        M = {k: Model() for k in 'ABCD'}
        lastpos = {}; prev_rr = None
        for i in range(1, len(fl) - 1):
            ep, nxt = fl[i], fl[i + 1]
            j = lastpos.get(ep)                          # earlier occurrence of EP
            root = fl[j + 1] if j is not None and j + 1 < i else None
            srcA = step(fl[i - 1], ep)
            srcB = step(ep, root) if root is not None else None      # earlier EP -> ROOT (same digits as EP)
            rr = step(root, nxt) if root is not None else None
            if i >= 300:
                av = T(ep) if low else None
                cands = [n for n in range(100) if av is None or T(n) != av]
                S = {}
                for k, base, src in (('A', ep, srcA), ('B', root, srcB), ('C', root, prev_rr), ('D', ep, srcB)):
                    if base is None or src is None:
                        continue
                    st, su = M[k].side_scores(src, 0), M[k].side_scores(src, 1)
                    S[k] = {n: st[(T(n) - T(base)) % 10] * su[(U(n) - U(base)) % 10] for n in cands}
                if len(S) == 4:
                    S['A+B+C+D'] = {n: sum(S[k][n] for k in 'ABCD') for n in cands}
                    S['A+D'] = {n: S['A'][n] + S['D'][n] for n in cands}
                    for k, sc in S.items():
                        top = sorted(cands, key=lambda n: -sc[n])
                        o = [sum(sc[n] for n in cands if T(n) == d) for d in range(10)]
                        c = [sum(sc[n] for n in cands if U(n) == d) for d in range(10)]
                        for g in (grp, 'all'):
                            r = res[(g, k)]; r[0] += 1; r[1] += nxt == top[0]; r[2] += nxt in top[:4]
                            r[3] += T(nxt) == max(range(10), key=lambda d: (d != av, o[d])); r[4] += U(nxt) == max(range(10), key=lambda d: c[d])
            # learn after predicting (walk-forward)
            if i >= 2:
                M['A'].learn(step(fl[i - 2], fl[i - 1]), srcA)
            if root is not None:
                M['B'].learn(srcB, rr); M['D'].learn(srcB, step(ep, nxt))
                if prev_rr is not None:
                    M['C'].learn(prev_rr, rr)
                prev_rr = rr
            lastpos[ep] = i
    for g in ('low-repeat', 'normal', 'all'):
        n = res[(g, 'A')][0]
        print(f"\n{g} charts ({n} predictions)  chance: top1 {'1.1' if g == 'low-repeat' else '1.0'}%  top4 {'4.4' if g == 'low-repeat' else '4.0'}%  OPEN/CLOSE 1 digit {'~11' if g == 'low-repeat' else '10'}% / 10%")
        for k in ('A', 'B', 'C', 'D', 'A+D', 'A+B+C+D'):
            r = res[(g, k)]
            if r[0]:
                print(f"   {k:8s} top1 {100*r[1]/r[0]:4.2f}%  top4 {100*r[2]/r[0]:5.2f}%   OPEN {100*r[3]/r[0]:5.1f}%  CLOSE {100*r[4]/r[0]:5.1f}%")


if __name__ == '__main__':
    main()
