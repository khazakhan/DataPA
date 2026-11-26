"""OPEN / CLOSE best-2 study (user 2026-11-27: 'OPEN and CLOSE best of best ... final 2 ... across all
the 24 sets').  Walk-forward on every round of the 24 uploaded sets: each rule sees only the numbers
before the round and names 2 OPEN digits (tens) and 2 CLOSE digits (units).  Chance = 20% each.
Learn on Sets 1-12, prove on Sets 13-24 (both halves).  Vote-based rules need rank_all (Sets 7-24 +
re-run files) and are scored only where it exists.
Usage: python3 tools/openclose_study.py [--top 2]"""
import sys, json, os
from collections import Counter, deque
sys.path.insert(0, 'tools')
from slot4_study import load

TOP = int(sys.argv[sys.argv.index('--top') + 1]) if '--top' in sys.argv else 2


def seq_of(k):
    toks = open(f'holdout_sets/set{k:02d}.txt').read().split()
    return [int(t) if t.isdigit() else None for t in toks]


def rank_all_of(k, R):
    f = f'holdout_sets/set{k:02d}_r40.jsonl'
    extra = {}
    if os.path.exists(f):
        for l in open(f):
            try:
                j = json.loads(l); extra[j['pos']] = j.get('rank_all')
            except ValueError:
                pass
    for r in R:
        r['rank_all'] = r.get('rank_all') or extra.get(r['pos'])


def top(score, n=TOP):
    return sorted(range(10), key=lambda d: (-score[d], d))[:n]


def rules_for(h, dig, r):
    """h = earlier numbers (no gaps), dig = digit function; returns {rule: [digits]}"""
    D = [dig(v) for v in h]
    last = D[-1]
    out = {}
    for W in (10, 20, 50, 100, 200, 10**9):
        c = Counter(D[-W:]); nm = 'all' if W == 10**9 else W
        out[f'hot {nm}'] = top([c[d] for d in range(10)])
        out[f'cold {nm}'] = top([-c[d] for d in range(10)])
    st = Counter((b - a) % 10 for a, b in zip(D, D[1:]))
    out['step all'] = top([st[(d - last) % 10] for d in range(10)])
    st2 = Counter((b - a) % 10 for a, b in zip(D[-201:], D[-200:]))
    out['step 200'] = top([st2[(d - last) % 10] for d in range(10)])
    tr = Counter(b for a, b in zip(D, D[1:]) if a == last)
    out['after last digit'] = top([tr[d] for d in range(10)])
    seen = {d: -1 for d in range(10)}
    for i, d in enumerate(D):
        seen[d] = i
    out['most overdue'] = top([-seen[d] for d in range(10)])
    out['most recent'] = top([seen[d] for d in range(10)])
    c100 = Counter(D[-100:])
    out['step x hot100'] = top([(st[(d - last) % 10] + 1) * (c100[d] + 1) for d in range(10)])
    out['step x cold100'] = top([(st[(d - last) % 10] + 1) / (c100[d] + 1) for d in range(10)])
    out['last digit + cut'] = [last, (last + 5) % 10]
    ra = r.get('rank_all')
    if ra:
        for N in (4, 12, 20, 40):
            c = Counter(dig(v) for v in ra[:N])
            out[f'vote top {N}'] = top([c[d] + 0.001 * (10 - sorted(range(10), key=lambda x: (-c[x], x)).index(d)) for d in range(10)])
        w = [0.0] * 10
        for i, v in enumerate(ra[:40]):
            w[dig(v)] += 40 - i
        out['vote 40 weighted'] = top(w)
        c = Counter(dig(v) for v in ra[-30:])
        out['vote bottom 30 avoided'] = top([-c[d] for d in range(10)])
    return out


def main():
    res = {}          # (side, rule) -> per set [hits1, n1, hits2, n2]
    for k in range(1, 25):
        R = load(f'set{k:02d}'); rank_all_of(k, R); S = seq_of(k)
        h_ = len(R) // 2
        for i, r in enumerate(R):
            h = [v for v in S[:r['pos']] if v is not None]
            if len(h) < 50:
                continue
            for side, dig in (('OPEN', lambda v: v // 10), ('CLOSE', lambda v: v % 10)):
                tgt = dig(r['result'])
                for name, ds in rules_for(h, dig, r).items():
                    a = res.setdefault((side, name), {}).setdefault(k, [0, 0, 0, 0])
                    j = 0 if i < h_ else 2
                    a[j] += tgt in ds; a[j + 1] += 1
    for side in ('OPEN', 'CLOSE'):
        print(f'\n### {side}: top {TOP} digits, chance {10 * TOP}%')
        print('| Rule | Learn 1-12 | Prove 13-24 | Prove halves | Sets above chance (13-24) | All 24 |')
        print('|---|---|---|---|---|---|')
        rows = []
        for (sd, name), per in res.items():
            if sd != side:
                continue
            agg = lambda ks: [sum(per[k][j] for k in ks if k in per) for j in range(4)]
            L = agg(range(1, 13)); P = agg(range(13, 25)); A = agg(range(1, 25))
            pct = lambda h, n: 100 * h / max(n, 1)
            above = sum(1 for k in range(13, 25) if k in per and (per[k][0] + per[k][2]) / max(per[k][1] + per[k][3], 1) > TOP / 10)
            rows.append((pct(L[0] + L[2], L[1] + L[3]), name, L, P, A, above))
        for lp, name, L, P, A, above in sorted(rows, reverse=True):
            pct = lambda h, n: f'{100 * h / max(n, 1):.2f}%'
            print(f'| {name} | {pct(L[0] + L[2], L[1] + L[3])} ({L[1] + L[3]}) | {pct(P[0] + P[2], P[1] + P[3])} '
                  f'| {pct(P[0], P[1])} / {pct(P[2], P[3])} | {above} of 12 | {pct(A[0] + A[2], A[1] + A[3])} |')


if __name__ == '__main__':
    main()
