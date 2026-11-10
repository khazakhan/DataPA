"""Deep dive (2026-11-10): which 4-number pick from the logged live lists holds the result best?
STRONG 20 held 35 of 106 on the low tens-repeat charts (X/Y/Z, chance ~21).  Test 4-number
picks built from STRONG 20 (its order, the EP-tens filter, OPEN/CLOSE sets) against FINAL 4
on every logged live round.  Display/study only."""
import sys, os, json, re, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.')
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None]
ser = lambda r: re.match(r'[A-Z]+', r['round']).group(0)
def flat_of(r):
    return [int(x) for x in open(r['dataset']).read().split() if x.isdigit()]
def picks(r):
    fl = flat_of(r); D._RRR3_PREV['flat'] = fl
    av = D._tens_avoid(); ep_after = fl[-1]
    st = list(dict.fromkeys(r['lists']['strong'])); rk = r['ranked']
    o3, c3 = D._open_close(rk)
    ok = lambda v: av is None or v // 10 != av
    st_av = [v for v in st if ok(v)]
    rkpos = {v: i for i, v in enumerate(rk)}
    P = {}
    P['FINAL 4'] = rk[:4]
    P['STRONG first 4'] = st[:4]
    P['STRONG first 4, EP-tens out'] = st_av[:4]
    P['STRONG in OPEN set'] = [v for v in st_av if v // 10 in o3][:4]
    P['STRONG in OPEN+CLOSE'] = list(dict.fromkeys([v for v in st_av if v // 10 in o3 and v % 10 in c3] +
                                 [v for v in st_av if v // 10 in o3]))[:4]
    P['STRONG by FINAL-4 rank'] = sorted(st_av, key=lambda v: rkpos.get(v, 999))[:4]
    P['STRONG 20 (all 20)'] = st
    P['STRONG EP-tens out (all)'] = st_av
    return P, av
agg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))
for r in L:
    P, av = picks(r)
    g = 'low-repeat X/Y/Z' if ser(r) in ('X', 'Y', 'Z') else 'other charts'
    for k, v in P.items():
        for grp in (g, 'all'):
            a = agg[grp][k]; a[0] += 1; a[1] += r['result'] in set(v); a[2] += len(set(v))
for grp in ('low-repeat X/Y/Z', 'other charts', 'all'):
    print(f"\n{grp}")
    for k, (n, h, s) in agg[grp].items():
        print(f"  {k:28s} {h:4d} of {n:4d} = {100*h/n:5.1f}%   chance {s/100:6.1f} (x{h/(s/100):.2f})")

# stability: per series and per half, for FINAL 4 vs STRONG in OPEN+CLOSE
print("\nper series (FINAL 4 / STRONG in OPEN+CLOSE / how many rounds it had 4 'both' numbers)")
by = collections.defaultdict(lambda: [0, 0, 0, 0])
for r in L:
    P, av = picks(r)
    b = by[ser(r)]; b[0] += 1; b[1] += r['result'] in P['FINAL 4']; b[2] += r['result'] in P['STRONG in OPEN+CLOSE']
    D._RRR3_PREV['flat'] = flat_of(r); o3, c3 = D._open_close(r['ranked'])
    b[3] += sum(1 for v in r['lists']['strong'] if v // 10 in o3 and v % 10 in c3 and (av is None or v // 10 != av)) >= 4
for s, (n, a, b_, f) in by.items():
    print(f"  {s}: {n:3d} rounds  FINAL 4 {a:2d}  OC-STRONG {b_:2d}  (4+ both-digit numbers in {f} rounds)")
xyz = [r for r in L if ser(r) in ('X', 'Y', 'Z')]
h = len(xyz) // 2
for nm, part in (('first half', xyz[:h]), ('second half', xyz[h:])):
    print(f"  X/Y/Z {nm}: OC-STRONG {sum(r['result'] in picks(r)[0]['STRONG in OPEN+CLOSE'] for r in part)} of {len(part)}")

print("\nFINAL 8 variants on X/Y/Z (8 numbers each, chance ~8.9 with EP tens out)")
V = collections.Counter(); zl = []
for r in xyz:
    P, av = picks(r); fl = flat_of(r); sh = D._shadow4(fl); oc = P['STRONG in OPEN+CLOSE']; f4 = P['FINAL 4']
    def fill(*ls):
        out = []
        for l in ls:
            for v in l:
                if v not in out: out.append(v)
        return out[:8]
    for k, s in (('FINAL 4 + SHADOW (now)', fill(f4, sh, r['ranked'])), ('FINAL 4 + OC-STRONG', fill(f4, oc, r['ranked'])),
                 ('OC-STRONG + SHADOW', fill(oc, sh, r['ranked'])), ('OC-STRONG + FINAL 4', fill(oc, f4))):
        V[k] += r['result'] in s
    if ser(r) == 'Z': zl.append((r['round'], r['result'], oc))
for k, h in V.items(): print(f"  {k:24s} {h} of {len(xyz)}")
print("\nZ rounds, OC-STRONG pick:", *[f"{a}={b:02d} {'HIT' if b in c else ''} {' '.join(f'{x:02d}' for x in c)}" for a, b, c in zl], sep='\n  ')

print("\nOC-STRONG with a defined order (the logged STRONG 20 is a set, so 'first 4' above was hash order)")
O = collections.defaultdict(lambda: collections.Counter())
for r in L:
    g = 'X/Y/Z' if ser(r) in ('X', 'Y', 'Z') else 'other'
    fl = flat_of(r); D._RRR3_PREV['flat'] = fl; av = D._tens_avoid()
    o3, c3 = D._open_close(r['ranked']); rkp = {v: i for i, v in enumerate(r['ranked'])}
    st = [v for v in set(r['lists']['strong']) if av is None or v // 10 != av]
    both = [v for v in st if v // 10 in o3 and v % 10 in c3]; one = [v for v in st if v // 10 in o3 and v not in both]
    orders = {'ascending': lambda v: v, 'FINAL-4 rank': lambda v: (rkp.get(v, 999), v),
              'digit strength': lambda v: (o3.index(v // 10), c3.index(v % 10) if v % 10 in c3 else 9, v)}
    for nm, key in orders.items():
        pk = (sorted(both, key=key) + sorted(one, key=key))[:4]
        O[g][nm] += r['result'] in pk
    O[g]['all both-digit (variable size)'] += r['result'] in both
    O[g]['size of both-digit'] += len(both)
    O[g]['n'] += 1
for g, c in O.items():
    n = c.pop('n'); sz = c.pop('size of both-digit')
    print(f"  {g} ({n} rounds; both-digit set avg {sz/n:.1f} numbers, chance {sz/100:.1f} hits):")
    for k, v in c.items(): print(f"     {k:32s} {v}")
