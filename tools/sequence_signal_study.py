"""Deep look (user 2026-11-07 'improvement need some more deep'): is there ANY signal in the raw
number sequence that a FINAL 4 could use?  For every uploaded series (raw pastes b..t, '**' and blanks
skipped) every result is predicted from simple features of the past numbers, learned on the OTHER series
only (leave-one-series-out), and scored as: tens digit top-1, units digit top-1 (chance 10%) and the
best 4 numbers (chance 4%)."""
import re, glob, collections, math
SER = {}
for f in sorted(glob.glob('/home/khazakhan/DataScinceAnal/rrr_datasets/*_raw_paste.txt')):
    k = f.split('/')[-1][0]
    txt = open(f).read()
    if 'Mon' in txt and k == 't':
        txt = txt.split('Mon     Tue     Wed     Thu     Fri     Sat     Sun', 1)[1]
    seq = [int(t) for t in re.findall(r'(?<![\d*])\d{1,2}(?![\d*])', txt)]
    SER[k] = seq
print({k: len(v) for k, v in SER.items()})

def root(seq, i):  # number after the latest earlier occurrence of seq[i-1]
    e = seq[i - 1]
    for j in range(i - 2, -1, -1):
        if seq[j] == e:
            return seq[j + 1]
    return None

FEATS = {
    'EP (last number)': lambda s, i: s[i - 1],
    'ROOT (follower of earlier EP)': root,
    'number 2 back': lambda s, i: s[i - 2],
    'same weekday last week (7 back)': lambda s, i: s[i - 7],
    'none (overall frequency)': lambda s, i: 0,
}
START = 60
res = {}
for name, fe in FEATS.items():
    tot = collections.Counter()
    for test in SER:
        T = collections.defaultdict(collections.Counter); U = collections.defaultdict(collections.Counter)
        N = collections.defaultdict(collections.Counter)
        for k, s in SER.items():
            if k == test: continue
            for i in range(START, len(s)):
                v = fe(s, i)
                if v is None: continue
                T[v // 10][s[i] // 10] += 1; U[v % 10][s[i] % 10] += 1; N[v][s[i]] += 1
        s = SER[test]
        for i in range(START, len(s)):
            v = fe(s, i)
            if v is None: continue
            r = s[i]; tot['n'] += 1
            tt = T[v // 10].most_common(1); uu = U[v % 10].most_common(1)
            tot['tens'] += bool(tt) and tt[0][0] == r // 10
            tot['units'] += bool(uu) and uu[0][0] == r % 10
            # best 4 numbers: product of tens and units probabilities
            def p(d, C): c = C[d]; return (c + 1) / (sum(C.values()) + 10)
            sc = sorted(range(100), key=lambda x: -(p(x // 10, T[v // 10]) * p(x % 10, U[v % 10])))[:4]
            tot['top4'] += r in sc
            nn = [x for x, _ in N[v].most_common(4)]
            tot['exact4'] += r in nn
    res[name] = tot
print(f"\n{'feature':34s} {'rounds':>7s} {'tens':>7s} {'units':>7s} {'best4 (digits)':>15s} {'best4 (same number)':>20s}")
for name, t in res.items():
    n = t['n']
    print(f"{name:34s} {n:7d} {100*t['tens']/n:6.1f}% {100*t['units']/n:6.1f}% {100*t['top4']/n:14.1f}% {100*t['exact4']/n:19.1f}%")
print("chance: tens 10%, units 10%, best 4 = 4%")
# chi-square style check of digit dependence EP -> result on all data pooled
for nm, fe in (('EP', FEATS['EP (last number)']), ('ROOT', root), ('7 back', FEATS['same weekday last week (7 back)'])):
    M = collections.defaultdict(collections.Counter); n = 0
    for s in SER.values():
        for i in range(START, len(s)):
            v = fe(s, i)
            if v is None: continue
            M[v // 10][s[i] // 10] += 1; n += 1
    rows = {a: sum(M[a].values()) for a in M}; cols = collections.Counter()
    for a in M:
        for b, c in M[a].items(): cols[b] += c
    chi = sum((M[a][b] - rows[a] * cols[b] / n) ** 2 / (rows[a] * cols[b] / n) for a in rows for b in cols if rows[a] * cols[b])
    print(f"tens-digit dependence {nm:6s}: chi-square {chi:6.1f} on 81 degrees of freedom (random ~81, signal would be >> 113)")
