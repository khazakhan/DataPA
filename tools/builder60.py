"""BHARAT BUILDER (user AF146: 'best builder and picker ... for 1000 rounds at least 600 times fired ... test on background,
Indian colours, closed circle to the 5 star pickers').
Every list on the page (Other lists table, watch lines, FINAL 4/8/10, grid, OPEN/CLOSE lines, ONE-MEN-ARMY, BOOSTER,
Count 2+, 80-number list) votes for its numbers.  A list's vote weight = log of its lift, learned ONLY from earlier
pages (walk-forward, nothing from the round being scored).  Numbers are ranked by total weight:
  BUILDER = top K numbers (K chosen so the walk-forward hit rate is >= 60%),  STAR 5 = top 5.
  python3 tools/builder60.py backtest            (walk-forward over every page with the Other lists table)
  python3 tools/builder60.py predict <ROUND> <page.md>   (appends the BHARAT BUILDER section to the page, logs it)
  python3 tools/builder60.py score <ROUND> <result>"""
import re, sys, json, os, glob, math
K = 60           # builder size, set from the backtest (see backtest output)
A = 20.0         # shrink toward chance
DECAY = 0.99     # recent pages count more (user AF199 'make stronger'): walk-forward top 4 43->52, STAR 5 55->61, top 60 607->619 of 971; 0.985-0.992 all gain
LOG = 'rrr_records/builder60_live.jsonl'
SKIP = {'Number', 'List', 'Line', 'Pick', 'Where', 'Model', '#'}

def two(s): return [int(x) for x in re.findall(r'(?<![\d.])\d\d(?![\d.])', s)]
def uniq(l):
    o = []
    for x in l:
        if 0 <= x <= 99 and x not in o: o.append(x)
    return o

def lists(t):
    """{list name: [numbers]} from one page (the lists shown for the NEXT round)."""
    L = {}
    def sec(head):
        i = t.find(head)
        if i < 0: return ''
        j = t.find('\n## ', i + 3)
        return t[i:j if j > 0 else len(t)]
    # Other lists table: | List | Numbers (op) | Live |
    for row in sec('## Other lists with operations').splitlines():
        c = [x.strip() for x in row.split('|')]
        if len(c) < 4 or c[1] in SKIP or c[1].startswith('---'): continue
        ns = uniq(two(re.sub(r'\([^)]*\)', '', c[2])))
        if ns: L['O:' + re.sub(r'\s*\(.*', '', c[1])[:40]] = ns
    # watch lines: | Line | Numbers | Live |
    for row in sec('### Watch lines').splitlines():
        c = [x.strip() for x in row.split('|')]
        if len(c) < 4 or c[1] in SKIP or c[1].startswith('---'): continue
        ns = uniq(two(re.sub(r'\([^)]*\)', '', c[2])))
        if ns: L['W:' + re.sub(r'\d\d ', '', re.sub(r'\s*\(.*', '', c[1]))[:40]] = ns
    m = re.search(r'### OCJP FINAL 4: .*?\n\|.*\n\|.*\n((?:\|.*\n){4})', t)
    if m:
        f4 = [int(re.findall(r'\*\*(\d\d)\*\*', r)[-1]) for r in m.group(1).splitlines()]
        L['FINAL 4'] = f4; L['MASTER'] = f4[:1]
        L['FINAL 4 yx'] = uniq([int(re.findall(r'\| (\d\d) \(', r)[0]) for r in m.group(1).splitlines() if re.findall(r'\| (\d\d) \(', r)])
    for key, pat in (('Grid', r'\*\*OPEN × CLOSE grid \(9\):\*\* (.*?)\('), ('OPEN 1 × CLOSE 4', r'\*\*OPEN 1 × CLOSE 4\*\* .*?: \*\*(.*?)\*\*'),
                     ('OPEN CUT × CLOSE 4', r'\*\*OPEN CUT × CLOSE 4\*\* .*?: \*\*(.*?)\*\*'), ('FINAL 10', r'\*\*OCJP FINAL 10:\*\* (.*?)\('),
                     ('FINAL 8', r'\*\*FINAL 8 ascending:\*\* (.*?)\('), ('BOOSTER', r'\*\*BOOSTER, full list[^:]*:\*\* (.*)'),
                     ('Count 2+', r'\*\*Count 2\+ \(\d+\):\*\* (.*)'), ('ONE-MEN-ARMY', r'## ONE-MEN-ARMY: .*\n\*\*Ascending:\*\* (.*)')):
        m = re.search(pat, t)
        if m:
            ns = uniq(two(re.sub(r'\([^)]*\)', '', m.group(1))))
            if ns: L[key] = ns
    m = re.search(r'\*\*80-number list, left out \(20\):\*\* (.*)', t)
    if m:
        out = set(two(m.group(1)))
        if len(out) == 20: L['80-number list'] = [x for x in range(100) if x not in out]
    for d, key in ((r'\*\*OPEN \(tens\)\*\* \| \*\*(\d)\*\* \| (\d) · (\d) · (\d)', 'OPEN'), (r'\*\*CLOSE \(units\)\*\* \| \*\*(\d)\*\* \| (\d) · (\d) · (\d)', 'CLOSE')):
        m = re.search(d, t)
        if m:
            g = [int(x) for x in m.groups()]
            f = (lambda a, b: a * 10 + b) if key == 'OPEN' else (lambda a, b: b * 10 + a)
            L[key + ' digit'] = [f(g[0], j) for j in range(10)]
            L[key + ' set 3'] = [f(i, j) for i in g[1:] for j in range(10)]
    m = re.search(r'\*\*CLOSE weak 3\*\* [^:]*: (\d) · (\d) · (\d)', t)
    if m: L['CLOSE weak 3'] = [i * 10 + int(d) for d in m.groups() for i in range(10)]
    return L

def pages():
    """(page path, its lists, the result that came for that page's round) in time order, every series."""
    out = []
    for p in glob.glob('rrr_outputs/*.md'):
        m = re.match(r'rrr_outputs/([a-z]+)(\d+)\.md$', p)
        if m: out.append((m.group(1), int(m.group(2)), p))
    by = {}
    for s, n, p in out: by.setdefault(s, {})[n] = p
    res = []
    for s, d in by.items():
        for n in sorted(d):
            if n + 1 not in d: continue
            t = open(d[n]).read()
            if '## Other lists with operations' not in t: continue
            m = re.match(r'# Round [A-Z]+\d+ result: (\d\d)', open(d[n + 1]).read())
            if m: res.append((os.path.getmtime(d[n]), d[n], lists(t), int(m.group(1))))
    res.sort()
    return [(p, L, r) for _, p, L, r in res]

def rank(L, ST):
    """ST = {list: [hits, size_sum]} learned from earlier pages.  Weight = log((h+A)/(e+A))."""
    w = {}
    for k in L:
        h, e = ST.get(k, (0, 0.0))
        w[k] = math.log((h + A) / (e / 100.0 + A))
    sc = [0.0] * 100; cnt = [0] * 100
    for k, ns in L.items():
        for x in ns: sc[x] += w[k]; cnt[x] += 1
    return sorted(range(100), key=lambda x: (-sc[x], -cnt[x], x)), sc, w

def learn(ST, L, r):
    for k in list(ST): ST[k] = (ST[k][0] * DECAY, ST[k][1] * DECAY)
    for k, ns in L.items():
        h, e = ST.get(k, (0, 0.0)); ST[k] = (h + (r in ns), e + len(ns))

def backtest():
    P = pages(); ST = {}; rows = []
    for p, L, r in P:
        if len(ST) >= 5:
            rk = rank(L, ST)[0]; rows.append(rk.index(r))
        learn(ST, L, r)
    n = len(rows); h = n // 2
    print(f'walk-forward test pages: {n} (first {len(P) - n} pages only learn)')
    print('| Size | Hit 1st half | Hit 2nd half | Total | Rate | Chance |\n|---|---|---|---|---|---|')
    for k in (1, 4, 5, 10, 20, 30, 40, 50, 55, 58, 60, 62, 65, 70, 80):
        a = sum(x < k for x in rows[:h]); b = sum(x < k for x in rows[h:])
        print(f'| top {k} | {a} of {h} | {b} of {n - h} | {a + b} | {100 * (a + b) / n:.1f}% | {k}% |')
    last = rows[-1000:]
    print(f'last {len(last)} pages: top {K} held {sum(x < K for x in last)} (chance {K * len(last) / 100:.0f}); STAR 5 held {sum(x < 5 for x in last)} (chance {5 * len(last) / 100:.0f})')

def state():
    ST = {}
    for p, L, r in pages(): learn(ST, L, r)
    return ST

def _family_map():
    """same families as tools/chat_page.py: 10 cut-pair families (15 = 1/6 x 5/0), half-cut (d, cut d), double (dd)."""
    fam, cut = {}, lambda d: (d + 5) % 10
    for i in range(1, 6):
        for j in range(i + 1, 6):
            for a in (i, cut(i)):
                for b in (j, cut(j)):
                    fam[a * 10 + b] = fam[b * 10 + a] = f"{i}{j}"
    for d in range(10):
        fam.setdefault(d * 10 + cut(d), 'half-cut')
        fam[d * 10 + d] = 'double'
    return fam
FAMILY = _family_map()

def star_row(st, band, sup=(), col=''):
    """●**65** [15] (🟧10 🟧60) ... (user AF154/AF160):
    [ ] = other members of the number's family standing in the same band (Saffron / White / Green);
    ( ) = family members found in the Other lists table and the Watch lines (supports), in the row's colour."""
    def mates(x, pool):
        return sorted(v for v in set(pool) if v != x and FAMILY[v] == FAMILY[x])
    out = []
    for x in st:
        b = mates(x, band); s_ = mates(x, sup)
        t = f'●**{x:02d}** [' + (' '.join(f'{v:02d}' for v in b) if b else '—') + ']'
        t += ' (' + (' '.join(f'{col}{v:02d}' for v in s_) if s_ else '—') + ')'
        out.append(t)
    return ' · '.join(out)

OPN = {0: 'nc', 1: '+1', 2: '+2', 9: '-1', 8: '-2', 5: 'cut', 6: 'c+1', 7: 'c+2', 4: 'c-1', 3: 'c-2'}
def op_on(r, x):
    """digit op from ROOT r to x, tens/units, e.g. 65 -> 63 = nc/-2"""
    return f"{OPN[(x // 10 - r // 10) % 10]}/{OPN[(x % 10 - r % 10) % 10]}"

def ep_root(t):
    """('EP 15 (56→15 c+1/-1), ROOT 65 (15→65 cut/nc)', 65) from the page's OCJP FINAL 4 heading"""
    m = None
    for m in re.finditer(r'EP (\d\d) \(([^)]*)\), ROOT (\d\d) \(([^)]*)\)', t):
        pass
    if not m: return '', None
    return m.group(0), int(m.group(3))

def count_table(stars, bands, sup, head, root, f4=(), test=()):
    """STAR 5 family count table (user AF160): op on ROOT, family, [ ] band mates, ( ) supports, counts."""
    lab = ('🟧 Saffron', '⬜ White', '🟩 Green')
    out = [f'\n### 🟧⬜🟩 STAR 5 family count' + (f': {head}' if head else ''),
           f'| Band | Link | STAR | Op on ROOT{f" {root:02d}" if root is not None else ""} | Family | [ ] same band | ( ) Other lists + Watch lines | [ ] | ( ) | Total |',
           '|---|---|---|---|---|---|---|---|---|---|']
    grand = [0, 0]
    # user AF246 screenshot: mark the OCJP FINAL 4 numbers ⭕ and the FINAL 4 TEST-only numbers 🔥 inside [ ] and ( )
    mk = lambda v: (f'⭕**{v:02d}**' if v in f4 else f'🔥**{v:02d}**' if v in test else f'{v:02d}')
    # user AF176: a STAR whose family is shared by another of the 15 STARs gets a green dot 🟢 instead of ●
    fams = [FAMILY[x] for st in stars for x in st]
    dot = lambda x: '🟢' if fams.count(FAMILY[x]) > 1 else '●'
    # user AF207 screenshot: a Link column joins the STARs of the same family with a line (one lane per repeated family)
    order = [FAMILY[x] for st in stars for x in st]
    rows = []                                   # row sequence incl. the 3 band total rows (None)
    for st in stars: rows += [FAMILY[x] for x in st] + [None]
    lanes = [f for f in dict.fromkeys(order) if order.count(f) > 1]
    B = '\u2800'                                # blank of one cell width (markdown keeps it)
    def link(r):
        cell = ''; hit = False                  # after the STAR's own lane the line runs on to the STAR (crossing others)
        for f in lanes:
            idx = [j for j, g in enumerate(rows) if g == f]
            mid = idx[0] < r < idx[-1]
            if rows[r] == f: cell += ('┌─' if r == idx[0] else '└─' if r == idx[-1] else '├─'); hit = True
            elif hit: cell += '┼─' if mid else '──'
            elif mid: cell += '│' + B
            else: cell += B + B
        return cell.rstrip(B) or '—'
    ri = [0]
    def nxt():
        r = ri[0]; ri[0] += 1; return link(r)
    for i, (st, bd) in enumerate(zip(stars, bands)):
        sub = [0, 0]
        for x in st:
            b = sorted(v for v in set(bd) if v != x and FAMILY[v] == FAMILY[x])
            u = sorted(v for v in set(sup) if v != x and FAMILY[v] == FAMILY[x])
            sub[0] += len(b); sub[1] += len(u)
            fam = FAMILY[x] + ('-family' if FAMILY[x][0].isdigit() else '')
            out.append(f"| {lab[i]} | {nxt()} | {dot(x)}**{x:02d}** | {op_on(root, x) if root is not None else '—'} | {fam} | "
                       f"{' '.join(mk(v) for v in b) or '—'} | {' '.join(f'{TRI[i]}{mk(v)}' for v in u) or '—'} | "
                       f"{len(b)} | {len(u)} | **{len(b) + len(u)}** |")
        out.append(f"| **{lab[i]} total** | {nxt()} | | | | | | **{sub[0]}** | **{sub[1]}** | **{sub[0] + sub[1]}** |")
        grand[0] += sub[0]; grand[1] += sub[1]
    out.append(f"| **All 15 STARs** | | | | | | | **{grand[0]}** | **{grand[1]}** | **{grand[0] + grand[1]}** |")
    if f4 or test:
        out.append('\n**Marks in [ ] and ( ):** ⭕ = OCJP FINAL 4 (' + ' '.join(f'{x:02d}' for x in f4) + ')' + (' · 🔥 = FINAL 4 TEST only (' + ' '.join(f'{x:02d}' for x in test if x not in f4) + ')' if [x for x in test if x not in f4] else ''))
    if lanes:
        out.append('\n**Link (same family):** ' + ' · '.join(f"{f}{'-family' if f[0].isdigit() else ''} " + '-'.join(f'{x:02d}' for st in stars for x in st if FAMILY[x] == f) for f in lanes))
    return '\n'.join(out) + '\n'

def bracket_set(rk, L):
    """every number shown in the [ ] and ( ) of the 3 STAR rows (logged so the idea can be tested live)"""
    bands = [rk[:20], rk[20:40], rk[40:K]]; sup = supports(L); out = set()
    for bd in bands:
        for x in bd[:5]:
            out |= {v for v in set(bd) | sup if v != x and FAMILY[v] == FAMILY[x]}
    return sorted(out)

BIG = {'80-number list', 'OPEN set 3', 'CLOSE set 3', 'CLOSE weak 3', 'OPEN digit', 'CLOSE digit'}
def gap8(rk, L):
    """GAP FILL 8 (user AF166: 44 was left out of the builder but stood on Rule 28 / STRONGEST FAMILY / yx CUT 12):
    the 8 numbers the builder leaves out that stand on the most page lists (2 or more; the big digit lists and the
    80-number list not counted).  Walk-forward 971 pages (with DECAY 0.99 ranking): 80 vs 76.7 by chance (42 vs 37.9 and 38 vs 38.8 per half) - at chance. Old 938-page test without decay: 86 vs 73.2. Display only."""
    out = set(rk[K:]) if rk else set()
    where = {x: [k.split(':', 1)[-1] for k, ns in (L or {}).items() if k not in BIG and x in ns] for x in out}
    g = [x for x in out if len(where[x]) >= 2]
    g = sorted(g, key=lambda x: (-len(where[x]), rk.index(x)))[:8]
    return [(x, where[x]) for x in g]

def gap_table(g, head, root):
    if not g: return ''
    out = [f'\n### 🔳 GAP FILL 8: left out of the builder but on 2+ lists' + (f': {head}' if head else ''),
           f'| # | Number | Op on ROOT{f" {root:02d}" if root is not None else ""} | Family | Lists | Where |', '|---|---|---|---|---|---|']
    for i, (x, w) in enumerate(g, 1):
        fam = FAMILY[x] + ('-family' if FAMILY[x][0].isdigit() else '')
        out.append(f"| {i} | 🔳**{x:02d}** | {op_on(root, x) if root is not None else '—'} | {fam} | {len(w)} | {' · '.join(w)} |")
    out.append(f"\n**GAP FILL 8:** " + ' '.join(f'🔳{x:02d}' for x, _ in g) + " (display only; walk-forward 971 pages held 80 vs 76.7 by chance, at chance; nothing above is changed by it)")
    return '\n'.join(out) + '\n'

def supports(L):
    """numbers of the Other lists table (O:) and the Watch lines (W:) of the page"""
    return {x for k, ns in (L or {}).items() if k.startswith(('O:', 'W:')) for x in ns}

TRI = ('🟧', '⬜', '🟩')   # saffron / white / green
MKS = 'rrr_records/mks4_live.jsonl'
def mks4(t):
    """FINAL 4 TEST (user AF239, display only): MASTER + KING PICK + STRONG 20 #1 + FINAL 4 #2, filled from FINAL 10.
    Tested on 415 logged rounds: 30 (20|10) vs current FINAL 4 23 (10|13); 2nd half lost, so it is only watched live."""
    m10 = re.search(r'\*\*OCJP FINAL 10:\*\* ([\d · ]+)', t)
    mk = re.search(r'\| KING PICK = ARROW[^|]*\| \*\*(\d\d)\*\*', t)
    ms = re.search(r'\| STRONG 20 #1 \(one number\) \| \*\*(\d\d)\*\*', t)
    if not (m10 and mk and ms): return None
    f10 = [int(x) for x in re.findall(r'\d\d', m10.group(1))]
    if len(f10) < 2: return None
    src = [(f10[0], 'MASTER'), (int(mk.group(1)), 'KING PICK'), (int(ms.group(1)), 'STRONG 20 #1'), (f10[1], 'FINAL 4 #2')]
    src += [(x, f'FINAL 10 #{i + 1}') for i, x in enumerate(f10)]
    out = []
    for x, why in src:
        if len(out) == 4: break
        if x not in [y for y, _ in out]: out.append((x, why))
    return out

def mks4_live():
    rows = [json.loads(l) for l in open(MKS)] if os.path.exists(MKS) else []
    d = [r for r in rows if r.get('result') is not None]
    return sum(r['result'] in r['pick'] for r in d), len(d)

def mks4_section(t):
    p = mks4(t)
    if not p: return ''
    head, root = ep_root(t)
    h, n = mks4_live()
    out = [f'\n### 🧪 FINAL 4 TEST: MASTER + KING PICK + STRONG 20 #1 + #2 (display only)' + (f': {head}' if head else ''),
           f'| # | Number | Op on ROOT{f" {root:02d}" if root is not None else ""} | From |', '|---|---|---|---|']
    for i, (x, why) in enumerate(p, 1):
        out.append(f'| {i} | **{x:02d}** | {op_on(root, x) if root is not None else "—"} | {why} |')
    out.append(f'\n**FINAL 4 TEST:** ' + ' · '.join(f'{x:02d}' for x, _ in p) + f' (live {h} of {n}; tested 415 logged rounds: 30 vs current FINAL 4 23, but lost the 2nd half 10 vs 13, so watched live before any switch; FINAL 4 is not changed by it)')
    return '\n'.join(out) + '\n'

def section(rk, sc, rnd, live, L=None, t=''):
    """Each band gets its own STAR 5 (its 5 best-ranked numbers), shown ●bold like the saffron STAR 5 (user AF150)."""
    top = sorted(rk[:K])
    bands = [rk[:20], rk[20:40], rk[40:K]]
    stars = [b[:5] for b in bands]
    allstar = set(x for st in stars for x in st)
    head, root = ep_root(t)
    out = [mks4_section(t) + f'\n## 🟧⬜🟩 BHARAT BUILDER {K}: every list on this page votes, each list weighted by its own past record (for {rnd})' + (f': {head}' if head else '')]
    sup = supports(L)
    out.append(f'**STAR 5 pickers:** ' + star_row(stars[0], bands[0], sup, TRI[0]))
    for c, nm, st, bd in zip(TRI[1:], ('White', 'Green'), stars[1:], bands[1:]):
        out.append(f'**{c} {nm} STAR 5:** ' + star_row(st, bd, sup, c))
    m10 = re.search(r'\*\*OCJP FINAL 10:\*\* ([\d · ]+)', t or '')
    f4 = [int(x) for x in re.findall(r'\d\d', m10.group(1))][:4] if m10 else []
    tp = mks4(t) if t else None
    out.append(count_table(stars, bands, sup, head, root, f4, [x for x, _ in tp] if tp else []))
    out.append('\n| Band | Numbers |\n|---|---|')
    for i, (c, band) in enumerate(zip(TRI, bands)):
        name = ('🟧 Saffron: rank 1-20 (strongest)', '⬜ White: rank 21-40', f'🟩 Green: rank 41-{K}')[i]
        out.append(f'| {name} | ' + ' '.join((f'{c}●**{x:02d}**' if x in allstar else f'{c}{x:02d}') for x in sorted(band)) + ' |')
    out.append(gap_table(gap8(rk, L), head, root))
    out.append(f'\n**BUILDER {K} ascending:** ' + ' '.join(f'{x:02d}' for x in top))
    out.append(f'**Left out ({100 - K}):** ' + ' '.join(f'{x:02d}' for x in range(100) if x not in rk[:K]))
    out.append(f'\nBuilder {K} = {K} of 100 numbers, so chance alone is {K}%. Each STAR 5 = 5 numbers (chance 5%). ' + live + ' It cannot reach 600 of 1000 with fewer numbers: the lists only beat chance by a little. No hit is promised.')
    return '\n'.join(out) + '\n'

def live_line():
    rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
    done = [r for r in rows if 'result' in r]
    if not done: return 'Live tally starts this round.'
    W = [r for r in done if 'white5' in r]
    return (f"Live: builder {sum(r['result'] in r['builder'] for r in done)} of {len(done)}, STAR 5 {sum(r['result'] in r['star5'] for r in done)} of {len(done)}"
            + (f"; White STAR 5 {sum(r['result'] in r['white5'] for r in W)} of {len(W)}, Green STAR 5 {sum(r['result'] in r['green5'] for r in W)} of {len(W)}" if W else '') + '.')

def page_section(md, rnd):
    """Display only (local terminal runs, tools/chat_page.py): same section, nothing logged."""
    L = lists(md); rk, sc, w = rank(L, state())
    return section(rk, sc, rnd, live_line(), L, md)

if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    a = sys.argv[1:]
    if a[0] == 'backtest': backtest()
    elif a[0] == 'predict':
        t = open(a[2]).read(); L = lists(t); rk, sc, w = rank(L, state())
        rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
        if not any(r['round'] == a[1] for r in rows):
            open(LOG, 'a').write(json.dumps({'round': a[1], 'builder': rk[:K], 'star5': rk[:5], 'white5': rk[20:25], 'green5': rk[40:45], 'brackets': bracket_set(rk, L), 'gap8': [x for x, _ in gap8(rk, L)]}) + '\n')
            rows.append({'round': a[1]})
        done = [r for r in rows if 'result' in r]
        live = (f"Live: builder {sum(r['result'] in r['builder'] for r in done)} of {len(done)}, STAR 5 {sum(r['result'] in r['star5'] for r in done)} of {len(done)}" + (f"; White STAR 5 {sum(r['result'] in r['white5'] for r in W)} of {len(W)}, Green STAR 5 {sum(r['result'] in r['green5'] for r in W)} of {len(W)}" if (W := [r for r in done if 'white5' in r]) else '') + "."
                if done else 'Live tally starts this round.')
        mp = mks4(t)
        if mp:
            M = [json.loads(l) for l in open(MKS)] if os.path.exists(MKS) else []
            M = [r for r in M if r['round'] != a[1]] + [{'round': a[1], 'pick': [x for x, _ in mp], 'result': None}]
            open(MKS, 'w').write(''.join(json.dumps(r) + '\n' for r in M))
        i = t.find('\n### 🧪 FINAL 4 TEST')
        if i < 0: i = t.find('\n## 🟧⬜🟩 BHARAT BUILDER')
        if i >= 0: t = t[:i]
        open(a[2], 'w').write(t.rstrip('\n') + '\n' + section(rk, sc, a[1], live, L, t))
        print(f'BHARAT BUILDER {a[1]} STAR 5', ' '.join(f'{x:02d}' for x in rk[:5]))
    elif a[0] == 'score':
        rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
        for r in rows:
            if r['round'] == a[1] and 'result' not in r: r['result'] = int(a[2])
        open(LOG, 'w').write(''.join(json.dumps(r) + '\n' for r in rows))
        if os.path.exists(MKS):
            M = [json.loads(l) for l in open(MKS)]
            for r in M:
                if r['round'] == a[1] and r.get('result') is None: r['result'] = int(a[2])
            open(MKS, 'w').write(''.join(json.dumps(r) + '\n' for r in M))
            print('FINAL 4 TEST live %d of %d' % mks4_live())
        done = [r for r in rows if 'result' in r]
        W = [r for r in done if 'white5' in r]
        print(f"BHARAT BUILDER live {sum(r['result'] in r['builder'] for r in done)} of {len(done)}; STAR 5 {sum(r['result'] in r['star5'] for r in done)} of {len(done)}; White STAR 5 {sum(r['result'] in r['white5'] for r in W)} of {len(W)}; Green STAR 5 {sum(r['result'] in r['green5'] for r in W)} of {len(W)}")
        B = [r for r in done if 'brackets' in r]
        G = [r for r in done if 'gap8' in r]
        if G: print(f"GAP FILL 8 held {sum(r['result'] in r['gap8'] for r in G)} of {len(G)} (chance {sum(len(r['gap8']) for r in G) / 100:.1f})")
        if B: print(f"STAR brackets [ ] + ( ) held {sum(r['result'] in r['brackets'] for r in B)} of {len(B)} (chance {sum(len(r['brackets']) for r in B) / 100:.1f})")
