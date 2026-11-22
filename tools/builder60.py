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

TRI = ('🟧', '⬜', '🟩')   # saffron / white / green
def section(rk, sc, rnd, live):
    star = rk[:5]; top = sorted(rk[:K])
    third = [sorted(rk[:20]), sorted(rk[20:40]), sorted(rk[40:K])]
    out = [f'\n## 🟧⬜🟩 BHARAT BUILDER {K}: every list on this page votes, each list weighted by its own past record (for {rnd})']
    out.append(f'**STAR 5 pickers:** ' + ' · '.join(f'●**{x:02d}**' for x in star))
    out.append('\n| Band | Numbers |\n|---|---|')
    for i, (c, band) in enumerate(zip(TRI, third)):
        name = ('🟧 Saffron: rank 1-20 (strongest)', '⬜ White: rank 21-40', f'🟩 Green: rank 41-{K}')[i]
        out.append(f'| {name} | ' + ' '.join((f'●**{x:02d}**' if x in star else f'{c}{x:02d}') for x in band) + ' |')
    out.append(f'\n**BUILDER {K} ascending:** ' + ' '.join(f'{x:02d}' for x in top))
    out.append(f'**Left out ({100 - K}):** ' + ' '.join(f'{x:02d}' for x in range(100) if x not in rk[:K]))
    out.append(f'\nBuilder {K} = {K} of 100 numbers, so chance alone is {K}%. ' + live + ' It cannot reach 600 of 1000 with fewer numbers: the lists only beat chance by a little. No hit is promised.')
    return '\n'.join(out) + '\n'

if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    a = sys.argv[1:]
    if a[0] == 'backtest': backtest()
    elif a[0] == 'predict':
        t = open(a[2]).read(); L = lists(t); rk, sc, w = rank(L, state())
        rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
        if not any(r['round'] == a[1] for r in rows):
            open(LOG, 'a').write(json.dumps({'round': a[1], 'builder': rk[:K], 'star5': rk[:5]}) + '\n')
            rows.append({'round': a[1]})
        done = [r for r in rows if 'result' in r]
        live = (f"Live: builder {sum(r['result'] in r['builder'] for r in done)} of {len(done)}, STAR 5 {sum(r['result'] in r['star5'] for r in done)} of {len(done)}."
                if done else 'Live tally starts this round.')
        if 'BHARAT BUILDER' not in t:
            open(a[2], 'a').write(section(rk, sc, a[1], live))
        print(f'BHARAT BUILDER {a[1]} STAR 5', ' '.join(f'{x:02d}' for x in rk[:5]))
    elif a[0] == 'score':
        rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
        for r in rows:
            if r['round'] == a[1] and 'result' not in r: r['result'] = int(a[2])
        open(LOG, 'w').write(''.join(json.dumps(r) + '\n' for r in rows))
        done = [r for r in rows if 'result' in r]
        print(f"BHARAT BUILDER live {sum(r['result'] in r['builder'] for r in done)} of {len(done)}; STAR 5 {sum(r['result'] in r['star5'] for r in done)} of {len(done)}")
