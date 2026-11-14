"""Frozen walk-forward test of FINAL 4 feeds (user 2026-11-15, after AB82: 'start step 2 walk-forward test').

Question: would any other 4-number source, fed into FINAL 4, have hit more often than the current FINAL 4?
Data: rrr_records/live.jsonl -- every round logged live BEFORE its result (P..AB), so each source below
uses only what was on the page before the result. Table-4 columns are rebuilt from the logged rows with the
script's own op functions. Each source gives exactly 4 different numbers (topped up from the page ranking
when short), so chance is 4% for every source.

Walk-forward pickers (no hindsight): at round t they choose using rounds < t only.
  WF-BEST : the fixed source with the most hits above chance so far (first 60 rounds: FINAL 4).
  WF-VOTE : every table column votes for its numbers with a weight learned from earlier rounds
            (log lift, smoothed); top 4 by total weight.
Block test: per series, consecutive 7-round blocks, passed if 4+ hits (the user's submission gate)."""
import json, sys, io, re, math, contextlib, collections
sys.path.insert(0, '/home/khazakhan/DataScinceAnal')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
SF, CT = D.SIGN_FLIP, D.KK_CUT_TOGGLE
def ap(e, x, y): return D.apply_op(e // 10, x) * 10 + D.apply_op(e % 10, y)
def cutn(n): return D.cut(n // 10) * 10 + D.cut(n % 10)
def yx(n): return (n % 10) * 10 + n // 10

COLS = ['xy', 'yx', '*xy', '*yx', '~xy', '~yx', 'old xy', 'old yx', 'newold xy', 'oldnew yx', 'oldy-newy', 'oldx-newx']
def cells(root, row):
    ox, oy = AB[row['old'][0]], AB[row['old'][1]]
    nx, ny = AB[row['new'][0]], AB[row['new'][1]]
    sx, sy = oy, SF[CT[ox]]                    # * columns
    tx, ty = SF[CT[oy]], CT[ox]                # ~ columns
    return {'xy': ap(root, nx, ny), 'yx': ap(root, ny, nx), '*xy': ap(root, sx, sy), '*yx': ap(root, sy, sx),
            '~xy': ap(root, tx, ty), '~yx': ap(root, ty, tx), 'old xy': ap(root, ox, oy), 'old yx': ap(root, oy, ox),
            'newold xy': ap(root, nx, oy), 'oldnew yx': ap(root, oy, nx),
            'oldy-newy': ap(root, oy, SF[ny]), 'oldx-newx': ap(root, ox, SF[nx])}

def four(seq, rk):
    out = []
    for v in list(seq) + list(rk):
        if v not in out: out.append(v)
        if len(out) == 4: break
    return out

shadow = {}
for l in open('rrr_records/shadow_f4.jsonl'):
    d = json.loads(l); shadow[d['round']] = d['pick']
L = {}
for l in open('rrr_records/live.jsonl'):
    d = json.loads(l); L[d['round']] = d
R = []
for d in L.values():
    if not d.get('rows') or d.get('result') in (None, ''): continue
    root, res = int(d['ep']), int(d['result'])
    rk = [int(v) for v in d.get('ranked', [])]
    rows = sorted(d['rows'], key=lambda r: r['pos'])
    order = rows[::-1]                                  # LAST row first, then going up
    C = [cells(root, r) for r in order]
    lists = d['lists']; f4 = [int(v) for v in lists['top4']]
    src = {'FINAL 4 (now)': f4,
           'PRIME 4': four((d.get('ladder') or {}).get('prime4') or f4, rk),
           'ranked 5-8 (control)': four(rk[4:8], rk[8:]),
           'FULL CUT of FINAL 4': four([cutn(v) for v in f4], rk),
           'yx of FINAL 4': four([yx(v) for v in f4], rk),
           'LAST row xy/yx/*xy/*yx': four([C[0][k] for k in ('xy', 'yx', '*xy', '*yx')], rk),
           'LAST row old/newold': four([C[0][k] for k in ('old xy', 'old yx', 'newold xy', 'oldnew yx')], rk),
           'LAST-OP 4': four(d.get('lastop') or [], rk),
           'Rule 28': four(d.get('r28') or [], rk)}
    for k in COLS:
        src['col ' + k] = four([c[k] for c in C], rk)
    vote = collections.Counter(v for c in C for v in c.values())
    pos = {v: i for i, v in enumerate(rk)}
    src['table vote (most cells)'] = sorted(vote, key=lambda v: (-vote[v], pos.get(v, 999)))[:4]
    if d['round'] in shadow: src['SHADOW'] = four(shadow[d['round']], rk)
    ser = re.match(r'[A-Z]+', d['round']).group()
    R.append(dict(round=d['round'], ser=ser, res=res, src=src, C=C, rk=rk))

# keep the logged order: series in the order they were played, rounds by number
SER_ORDER = ['P', 'Q', 'R', 'S', 'T', 'U', 'V', 'X', 'Y', 'Z', 'AA', 'AB']
R.sort(key=lambda r: (SER_ORDER.index(r['ser']) if r['ser'] in SER_ORDER else 99, int(re.sub(r'\D', '', r['round']) or 0)))
n = len(R)

# walk-forward pickers
FIXED = [k for k in R[-1]['src'] if k != 'SHADOW']
score = collections.Counter(); seen = collections.Counter()
W = collections.defaultdict(lambda: [0, 0.0])   # column -> [hits, expected]
for r in R:
    # WF-BEST
    if sum(seen.values()) == 0 or seen['FINAL 4 (now)'] < 60:
        pick = 'FINAL 4 (now)'
    else:
        pick = max(FIXED, key=lambda k: (score[k] - 0.04 * seen[k]) if seen[k] else -9)
    r['src']['WF-BEST (walk-forward)'] = r['src'][pick]; r['wf_pick'] = pick
    # WF-VOTE
    sc = collections.defaultdict(float)
    for c in r['C']:
        for k, v in c.items():
            h, e = W[k]; sc[v] += math.log((h + 1) / (e + 1))
    pos = {v: i for i, v in enumerate(r['rk'])}
    r['src']['WF-VOTE (walk-forward)'] = sorted(range(100), key=lambda v: (-sc[v], pos.get(v, 999)))[:4]
    # learn after the round
    for k in FIXED:
        seen[k] += 1; score[k] += r['res'] in r['src'][k]
    for k in COLS:
        s = {c[k] for c in r['C']}
        W[k][0] += r['res'] in s; W[k][1] += len(s) / 100

def z(h, m, p=0.04):
    return (h - m * p) / math.sqrt(m * p * (1 - p)) if m else 0

def blocks(rounds, key):
    passed = tot = best = 0
    by = collections.defaultdict(list)
    for r in rounds:
        if key in r['src']: by[r['ser']].append(r['res'] in r['src'][key])
    for s, hs in by.items():
        for i in range(0, len(hs) - 6, 7):
            b = sum(hs[i:i + 7]); tot += 1; passed += b >= 4; best = max(best, b)
    return passed, tot, best

keys = sorted({k for r in R for k in r['src']}, key=lambda k: -sum(r['res'] in r['src'][k] for r in R if k in r['src']) / max(1, sum(k in r['src'] for r in R)))
print(f"FROZEN WALK-FORWARD TEST of FINAL 4 feeds -- {n} live-logged rounds, series {' '.join(s for s in SER_ORDER if any(r['ser'] == s for r in R))}")
print("Every source = exactly 4 numbers, so chance = 4.0%.  z = standard deviations above chance (2+ = probably real).\n")
print(f"{'source':34s} {'hits':>5s} {'rounds':>6s} {'rate':>6s} {'z':>5s}   7-round blocks passed (4+ of 7) / best block")
for k in keys:
    rs = [r for r in R if k in r['src']]; h = sum(r['res'] in r['src'][k] for r in rs)
    p, t, b = blocks(R, k)
    print(f"{k:34s} {h:5d} {len(rs):6d} {100*h/len(rs):5.1f}% {z(h, len(rs)):5.1f}   {p} of {t}, best {b} of 7")
print("\nWF-BEST picked (rounds):", dict(collections.Counter(r['wf_pick'] for r in R).most_common()))
# by series for the two main candidates
print("\nBy series (hits / rounds):")
for s in SER_ORDER:
    rs = [r for r in R if r['ser'] == s]
    if not rs: continue
    line = '  '.join(f"{k.split(' (')[0]} {sum(r['res'] in r['src'][k] for r in rs if k in r['src'])}"
                     for k in ('FINAL 4 (now)', 'PRIME 4', 'WF-BEST (walk-forward)', 'WF-VOTE (walk-forward)'))
    print(f"  {s:3s} {len(rs):4d} rounds   {line}")
best_fixed = max(FIXED, key=lambda k: sum(r['res'] in r['src'][k] for r in R))
m = len(FIXED)
print(f"\nNote: {m} fixed sources were compared; the best of {m} random 4-number sources would score about "
      f"{n*0.04 + 2.0*math.sqrt(n*0.04*0.96):.0f} hits (z about 2) by luck alone, so only the walk-forward rows are a fair test of 'pick the best'.")
