"""User 2026-11-07 (U5 = 69): 'modify the operations of the OCJP FINAL 4 numbers and you get the result,
98% guaranteed'. Example: FINAL 4 #3 10 = c-2/cut on ROOT 85 -> x c-2 to -2 (cut removed), y cut to c-1
(step -1) -> -2/c-1 = 69. Test on all 1,293 history rounds: for each FINAL 4 number take its op on the ROOT
and allow 'one notch' changes per side (cut on/off, step +1/-1, sign flip). Count how many different
numbers each rule covers and how often the result is among them. Chance = covered numbers / 100."""
import sys, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('tools/final4_full_study.py').read().split('n = len(R)')[0])
def parse(o):
    c = o.startswith('c') or o == 'cut'; t = o[1:] if o.startswith('c') else o
    t = t.replace('ut', '') if o == 'cut' else t
    return (int(c), 0 if t in ('', 'nc') else int(t))
def name(c, s):
    return ('cut' if s == 0 else f"c{s:+d}") if c else ('nc' if s == 0 else f"{s:+d}")
def notch(o):
    c, s = parse(o); out = {(c, s), (1 - c, s), (c, -s)}
    for d in (1, -1):
        if -2 <= s + d <= 2: out.add((c, s + d))
    return {name(*p) for p in out}
RULES = {
  'as is (FINAL 4 now)':            lambda x, y: [(x, y)],
  'one notch, x side only':         lambda x, y: [(a, y) for a in notch(x)],
  'one notch, y side only':         lambda x, y: [(x, b) for b in notch(y)],
  'one notch on one side (x or y)': lambda x, y: [(a, y) for a in notch(x)] + [(x, b) for b in notch(y)],
  'one notch on BOTH sides (U5 example)': lambda x, y: [(a, b) for a in notch(x) for b in notch(y)],
}
n = len(R)
print(f"rounds {n}")
for k, f in RULES.items():
    hits = cov = 0
    for r in R:
        s = set()
        for v in r['rk'][:4]:
            x, y = op_of(r['root'], v)
            s |= {ap(r['root'], a, b) for a, b in f(x, y)}
        cov += len(s); hits += r['res'] in s
    print(f"  {k:38s} covers {cov/n:5.1f} numbers   held {hits:4d} = {100*hits/n:5.1f}%   chance {cov/n:5.1f}%")

# user follow-up: 'check with respect to sign change and cut and decut and xy and yx'
def T(o, kinds):
    c, s = parse(o); out = {(c, s)}
    if 'S' in kinds: out |= {(c, -s) for c, s in list(out)}
    if 'C' in kinds: out |= {(1 - c, s) for c, s in list(out)}
    return [name(*p) for p in out]
def rule2(kinds, yx):
    def f(x, y):
        pairs = [(a, b) for a in T(x, kinds) for b in T(y, kinds)]
        return pairs + ([(b, a) for a, b in pairs] if yx else [])
    return f
print("\nsign change (S), cut/decut (C), xy and yx:")
for lab, kinds, yx in (('xy + yx (swap only)', '', True), ('sign change, both sides', 'S', False),
                       ('sign change + yx', 'S', True), ('cut/decut, both sides', 'C', False),
                       ('cut/decut + yx', 'C', True), ('sign + cut/decut', 'SC', False),
                       ('sign + cut/decut + yx (all)', 'SC', True)):
    f = rule2(kinds, yx); hits = cov = 0
    for r in R:
        s = set()
        for v in r['rk'][:4]:
            x, y = op_of(r['root'], v); s |= {ap(r['root'], a, b) for a, b in f(x, y)}
        cov += len(s); hits += r['res'] in s
    print(f"  {lab:38s} covers {cov/n:5.1f} numbers   held {hits:4d} = {100*hits/n:5.1f}%   chance {cov/n:5.1f}%")

# user follow-up 2: 'within the OCJP FINAL 4 operations, xy and yx with the 4 x ops and 4 y ops, to the ROOT'
def grid(root, f4, mode):
    X = [op_of(root, v)[0] for v in f4]; Y = [op_of(root, v)[1] for v in f4]
    s = {ap(root, a, b) for a in X for b in Y}                      # x_i / y_j
    if mode >= 2: s |= {ap(root, b, a) for a in X for b in Y}       # y_j / x_i (yx)
    if mode >= 3: s |= {ap(root, a, b) for a in X + Y for b in X + Y}  # any of the 8 ops on either side
    return s
print("\nFINAL 4 op grid on the ROOT:")
for lab, mode in (('x ops x y ops (xy grid)', 1), ('xy grid + yx grid', 2), ('all 8 ops on both sides', 3)):
    hits = cov = 0
    for r in R:
        s = grid(r['root'], r['rk'][:4], mode); cov += len(s); hits += r['res'] in s
    print(f"  {lab:38s} covers {cov/n:5.1f} numbers   held {hits:4d} = {100*hits/n:5.1f}%   chance {cov/n:5.1f}%   extra {hits - cov/100:+.0f}")
