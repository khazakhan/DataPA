"""OPEN / CLOSE digit from the chart's own digit steps (walk-forward, no peeking):
OPEN = last number's tens + the tens step that has come most often so far,
CLOSE = same for units.  Compared with chance (10% one digit / 30% three)."""
import sys, collections, glob, re
def load(f): return [int(t) for t in open(f).read().split() if t.isdigit()]
for f in sys.argv[1:]:
    s = load(f); h1 = h3 = c1 = c3 = n = 0
    for i in range(300, len(s) - 1):
        S = list(zip(s[:i], s[1:i + 1]))
        t = collections.Counter((b // 10 - a // 10) % 10 for a, b in S)
        u = collections.Counter((b % 10 - a % 10) % 10 for a, b in S)
        e, r = s[i], s[i + 1]
        ot = [(e // 10 + k) % 10 for k, _ in t.most_common()]
        ou = [(e % 10 + k) % 10 for k, _ in u.most_common()]
        n += 1
        h1 += r // 10 == ot[0]; h3 += r // 10 in ot[:3]
        c1 += r % 10 == ou[0]; c3 += r % 10 in ou[:3]
    print(f"{f}: OPEN 1 digit {h1/n:.1%}  3 digits {h3/n:.1%} | CLOSE 1 digit {c1/n:.1%}  3 digits {c3/n:.1%}  ({n} rounds; chance 10% / 30%)")
