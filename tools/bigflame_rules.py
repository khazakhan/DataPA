import pickle, sys, itertools
recs = pickle.load(open(sys.argv[1], 'rb')); n = len(recs); h = n // 2
def ev(rule):
    out = []
    for part in (recs[:h], recs[h:]):
        hit = size = 0
        for p, r, F in part:
            s = [v for v, f in F.items() if not f['star'] and f['rows'] > 0 and rule(f)]
            size += len(s); hit += r in s
        out.append((hit, size / 100))
    return out
rules = {}
for R in (1, 2, 3):
    rules[f'rows>={R}'] = (lambda R: lambda f: f['rows'] >= R)(R)
for Fm in (2, 3, 4):
    rules[f'fam>={Fm}'] = (lambda Fm: lambda f: f['fam'] >= Fm)(Fm)
for R, N in itertools.product((1, 2, 3), (2, 3, 4, 5)):
    rules[f'rows>={R} & lists>={N}'] = (lambda R, N: lambda f: f['rows'] >= R and f['nl'] >= N)(R, N)
for R, K in itertools.product((1, 2, 3), (20, 40, 60)):
    rules[f'rows>={R} & rank<{K}'] = (lambda R, K: lambda f: f['rows'] >= R and f['rk'] < K)(R, K)
    rules[f'rows>={R} & rank>={K}'] = (lambda R, K: lambda f: f['rows'] >= R and f['rk'] >= K)(R, K)
rules['inp>=2 & inb==0'] = lambda f: f['inp'] >= 2 and f['inb'] == 0
rules['inb>=2'] = lambda f: f['inb'] >= 2
rules['inb>=1 & inp>=1'] = lambda f: f['inb'] >= 1 and f['inp'] >= 1
rules['rows>=2 & inp>=2'] = lambda f: f['rows'] >= 2 and f['inp'] >= 2
print(f'pages {n}: half A {h}, half B {n-h}')
print(f"{'rule':28} {'A hit/chance':>16} {'B hit/chance':>16} {'per page':>8} lift")
for k, rl in rules.items():
    (a, ea), (b, eb) = ev(rl)
    print(f"{k:28} {a:5d} / {ea:7.1f} {b:7d} / {eb:7.1f} {(ea+eb)*100/n:8.1f} {(a+b)/(ea+eb):.2f}")
