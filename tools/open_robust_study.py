"""OPEN robust study (user 2026-11-28: 'make me robust and strong in OPEN').  Same walk-forward frame as
tools/openclose_study.py (every round of the 24 sets, each rule sees only earlier numbers, top 2 tens digits,
chance 20%; learn = Sets 1-12, prove = Sets 13-24).  Adds new rule families: chart column (7 columns),
2-step memory, cross digit (last units -> next tens), step on ROOT, recency-weighted step, and Borda mixes.
Usage: python3 tools/open_robust_study.py [--top 4]"""
import sys, json, os, itertools
from collections import Counter
sys.path.insert(0, 'tools')
from slot4_study import load
from openclose_study import rank_all_of, seq_of

T = lambda v: v // 10


def scores(S, pos, r):
    """{rule: 10 scores} for the round at token position pos (S = all tokens, None = gap)."""
    hp = [(i, v) for i, v in enumerate(S[:pos]) if v is not None]
    h = [v for _, v in hp]; D = [T(v) for v in h]; last = D[-1]; out = {}
    st = Counter((b - a) % 10 for a, b in zip(D, D[1:]))
    out['step all (now)'] = [st[(d - last) % 10] for d in range(10)]
    # recency-weighted steps
    for hl in (100, 300):
        w = [0.0] * 10; n = len(D)
        for j, (a, b) in enumerate(zip(D, D[1:])):
            w[(b - a) % 10] += 0.5 ** ((n - 2 - j) / hl)
        out[f'step decay {hl}'] = [w[(d - last) % 10] for d in range(10)]
    # 2-step memory: step after the previous step
    ps = (D[-1] - D[-2]) % 10
    st2 = Counter((c - b) % 10 for a, b, c in zip(D, D[1:], D[2:]) if (b - a) % 10 == ps)
    out['step after step'] = [st2[(d - last) % 10] + 0.01 * st[(d - last) % 10] for d in range(10)]
    # step from ROOT (number before last)
    sr = Counter((c - a) % 10 for a, c in zip(D, D[2:]))
    out['step from ROOT'] = [sr[(d - D[-2]) % 10] for d in range(10)]
    # cross digit: last units -> next tens
    U = [v % 10 for v in h]
    cx = Counter((D[j + 1] - U[j]) % 10 for j in range(len(D) - 1))
    out['cross units->tens'] = [cx[(d - U[-1]) % 10] for d in range(10)]
    # chart column (7 columns: position in row)
    col = pos % 7
    cc = Counter(T(v) for i, v in hp if i % 7 == col)
    out['column hot'] = [cc[d] for d in range(10)]
    cs = Counter()
    prevc = None
    for i, v in hp:
        if i % 7 == col:
            if prevc is not None: cs[(T(v) - prevc) % 10] += 1
            prevc = T(v)
    lastc = prevc
    out['column step'] = [cs[(d - lastc) % 10] if lastc is not None else 0 for d in range(10)]
    # step conditioned on column
    stc = Counter((T(v) - T(u)) % 10 for (i0, u), (i, v) in zip(hp, hp[1:]) if i % 7 == col)
    out['step in this column'] = [stc[(d - last) % 10] for d in range(10)]
    ra = r.get('rank_all')
    if ra:
        c = Counter(T(v) for v in ra[-30:])
        out['vote bottom 30 avoided'] = [-c[d] for d in range(10)]
        c = Counter(T(v) for v in ra[:12])
        out['vote top 12'] = [c[d] for d in range(10)]
    return out


def borda(sc):
    o = sorted(range(10), key=lambda d: (-sc[d], d)); b = [0] * 10
    for i, d in enumerate(o): b[d] = 10 - i
    return b


TOP = int(sys.argv[sys.argv.index('--top') + 1]) if '--top' in sys.argv else 2


def top2(sc): return sorted(range(10), key=lambda d: (-sc[d], d))[:TOP]


def main():
    res = {}
    for k in range(1, 25):
        R = load(f'set{k:02d}'); rank_all_of(k, R); S = seq_of(k); h_ = len(R) // 2
        for i, r in enumerate(R):
            if sum(v is not None for v in S[:r['pos']]) < 50: continue
            sc = scores(S, r['pos'], r); tgt = r['result'] // 10
            B = {n: borda(s) for n, s in sc.items()}
            picks = {n: top2(s) for n, s in sc.items()}
            names = sorted(B)
            for a, b in itertools.combinations(names, 2):
                picks[f'{a} + {b}'] = top2([B[a][d] + B[b][d] + 0.01 * B['step all (now)'][d] for d in range(10)])
            for a, b, c in itertools.combinations(names, 3):
                if 'step all (now)' in (a, b, c):
                    picks[f'{a} + {b} + {c}'] = top2([B[a][d] + B[b][d] + B[c][d] + 0.01 * B['step all (now)'][d] for d in range(10)])
            for n, ds in picks.items():
                x = res.setdefault(n, {}).setdefault(k, [0, 0, 0, 0]); j = 0 if i < h_ else 2
                x[j] += tgt in ds; x[j + 1] += 1
        print(f'set {k} done', file=sys.stderr)
    rows = []
    for n, per in res.items():
        ag = lambda ks: [sum(per[k][j] for k in ks if k in per) for j in range(4)]
        L, P = ag(range(1, 13)), ag(range(13, 25))
        pc = lambda a, b: 100 * a / max(b, 1)
        above = sum(1 for k in range(13, 25) if k in per and (per[k][0] + per[k][2]) / max(per[k][1] + per[k][3], 1) > TOP / 10)
        rows.append((pc(L[0] + L[2], L[1] + L[3]), n, L[1] + L[3], pc(P[0] + P[2], P[1] + P[3]), pc(P[0], P[1]), pc(P[2], P[3]), above, P[1] + P[3]))
    rows.sort(reverse=True)
    print('| Rule | Learn 1-12 | Prove 13-24 | Prove halves | Proof sets above chance |\n|---|---|---|---|---|')
    for lp, n, ln, pp, p1, p2, ab, pn in rows[:40]:
        print(f'| {n} | {lp:.2f}% ({ln}) | {pp:.2f}% ({pn}) | {p1:.2f}% / {p2:.2f}% | {ab} of 12 |')
    for lp, n, ln, pp, p1, p2, ab, pn in rows:
        if n == 'step all (now)': print(f'CURRENT: {n} learn {lp:.2f}% prove {pp:.2f}% ({p1:.2f}/{p2:.2f}) {ab}/12')


if __name__ == '__main__':
    main()
