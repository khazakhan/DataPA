"""Hidden-rule search on the live rounds (2026-11-17, user after AC130: 'if any gotcha or
hidden rules search for missed results').  For every live round with ROOT r, EP e,
result y, FINAL 4 f: tests (1) is any fixed op from ROOT or from EP to the result
over-represented (100 ops each, chance 1%); (2) does the result op on ROOT repeat a
transform of the EP->ROOT op (same, sign flip, x/y swap, swap+flip, +cut on x/y/both,
+-1 steps); (3) is the result one fixed op away from a FINAL 4 number; (4) by half of
the rounds, so a pattern must show in both.  python3 tools/missed_hidden_rules.py"""
import json, collections, math
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None and r.get('ep') is not None and r.get('after') is not None]
op = lambda a, b: ((b // 10 - a // 10) % 10, (b % 10 - a % 10) % 10)
app = lambda n, o: ((n // 10 + o[0]) % 10) * 10 + (n % 10 + o[1]) % 10
n = len(L); h = n // 2
print('live rounds', n)
def show(title, cnt_all, cnt_a, cnt_b, top=5, chance=0.01):
    print(title)
    for k, c in cnt_all.most_common(top):
        z = (c - n * chance) / math.sqrt(n * chance * (1 - chance))
        print(f'   {k}: {c} of {n} (chance {n*chance:.1f}, z {z:+.1f})  halves {cnt_a[k]} / {cnt_b[k]}')
for name, base in (('ROOT', 'ep'), ('EP', 'after')):
    A = collections.Counter(op(r[base], r['result']) for r in L)
    a = collections.Counter(op(r[base], r['result']) for r in L[:h]); b = collections.Counter(op(r[base], r['result']) for r in L[h:])
    chi = sum((A[(i, j)] - n / 100) ** 2 / (n / 100) for i in range(10) for j in range(10))
    show(f'(1) fixed op from {name} to result (chi-square {chi:.0f}, 99 df, random ~99 +- 14):', A, a, b)
T = {'same': lambda o: o, 'flip': lambda o: (-o[0] % 10, -o[1] % 10), 'swap': lambda o: (o[1], o[0]),
     'swap+flip': lambda o: (-o[1] % 10, -o[0] % 10), 'cut x': lambda o: ((o[0] + 5) % 10, o[1]),
     'cut y': lambda o: (o[0], (o[1] + 5) % 10), 'cut both': lambda o: ((o[0] + 5) % 10, (o[1] + 5) % 10),
     'flip+cut both': lambda o: ((5 - o[0]) % 10, (5 - o[1]) % 10)}
C = collections.Counter(); Ca = collections.Counter(); Cb = collections.Counter()
for i, r in enumerate(L):
    prev = op(r['after'], r['ep'])
    for k, f in T.items():
        for base in ('ROOT', 'EP'):
            y = app(r['ep'] if base == 'ROOT' else r['after'], f(prev))
            if y == r['result']:
                C[f'{k} of EP->ROOT op, on {base}'] += 1; (Ca if i < h else Cb)[f'{k} of EP->ROOT op, on {base}'] += 1
show('(2) result = EP->ROOT op transformed, applied again:', C, Ca, Cb, top=6)
F = collections.Counter(); Fa = collections.Counter(); Fb = collections.Counter()
for i, r in enumerate(L):
    f4 = (r.get('final8') or [])[:4] or r['ranked'][:4]
    for o in {op(v, r['result']) for v in f4}:
        F[o] += 1; (Fa if i < h else Fb)[o] += 1
show('(3) result one fixed op from some FINAL 4 number (chance ~4% each):', F, Fa, Fb, chance=0.04)
