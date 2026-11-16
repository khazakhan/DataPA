"""Strict op-history walk-forward (2026-11-17, user: 'go strictly by reading the data and
its history operations').  Each chart = its numbers in order.  An operation is the digit
move (tens step, units step) mod 10 (cut = 5).  At each step, ONLY past steps are used:
  M0 most common op overall           M1 op most often following the last op
  M2 op most often following the last two ops   M3 tens / units digit moves learned per current digit
  M4 next number most often following the current number
Top K numbers are scored against the real next number.  Chance = K%.
python3 tools/op_history_walkforward.py"""
import glob, re, collections, os
def seq(path):
    return [int(t) for l in open(path) for t in l.split() if t.isdigit() and len(t) <= 2]
files = {}
for p in glob.glob('rrr_datasets/*.txt'):
    m = re.match(r'([a-z]+)(\d+)\.txt$', os.path.basename(p))
    if m and (m.group(1) not in files or int(m.group(2)) > files[m.group(1)][0]):
        files[m.group(1)] = (int(m.group(2)), p)
op = lambda a, b: ((b // 10 - a // 10) % 10, (b % 10 - a % 10) % 10)
app = lambda n, o: ((n // 10 + o[0]) % 10) * 10 + (n % 10 + o[1]) % 10
def top(cnt, k, fill):
    out = [v for v, _ in cnt.most_common()]
    for v in fill:
        if v not in out: out.append(v)
    return out[:k]
K = (4, 10)
tot = collections.defaultdict(lambda: [0, 0]); n_all = 0
for s, (_, p) in sorted(files.items()):
    x = seq(p)
    if len(x) < 150: continue
    ops = [op(x[i], x[i + 1]) for i in range(len(x) - 1)]
    for t in range(100, len(x) - 1):
        cur = x[t]; past = ops[:t]; res = x[t + 1]
        allop = collections.Counter(past)
        base = [app(cur, o) for o, _ in allop.most_common()]
        m1 = collections.Counter(past[i + 1] for i in range(len(past) - 1) if past[i] == past[-1])
        m2 = collections.Counter(past[i + 2] for i in range(len(past) - 2) if past[i:i + 2] == past[-2:])
        ten = collections.Counter(x[i + 1] // 10 for i in range(t) if x[i] // 10 == cur // 10)
        uni = collections.Counter(x[i + 1] % 10 for i in range(t) if x[i] % 10 == cur % 10)
        m3 = collections.Counter({a * 10 + b: ten[a] * uni[b] for a in ten for b in uni})
        m4 = collections.Counter(x[i + 1] for i in range(t) if x[i] == cur)
        preds = {'M0 common op': collections.Counter({app(cur, o): c for o, c in allop.items()}),
                 'M1 op after last op': collections.Counter({app(cur, o): c for o, c in m1.items()}),
                 'M2 op after last 2 ops': collections.Counter({app(cur, o): c for o, c in m2.items()}),
                 'M3 digit moves per digit': m3, 'M4 number after number': m4}
        n_all += 1
        for name, c in preds.items():
            for k in K:
                tot[(name, k)][0] += res in top(c, k, base); tot[(name, k)][1] += 1
print('charts', len([1 for s in files]), 'scored steps', n_all)
for (name, k), (h, n) in sorted(tot.items()):
    print(f'{name:26s} top {k:2d}: {h:5d} of {n}  = {100 * h / n:5.2f}%  (chance {k}%)')
