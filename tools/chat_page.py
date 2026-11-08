#!/usr/bin/env python3
"""Chat-layout round page (user 2026-11-09: 'save this format and sequence ... when we
run from local also').  Builds the same tables, in the same order, as the chat reply
(template rrr_outputs/v13.md):

  result header + held/missed line -> Result check -> ROOT line -> 4. RRR: NEXT OPERATION
  (2 tables) -> MegaStar/PowerStar -> Other lists with operations on ROOT -> ONE-MEN-ARMY
  -> OCJP FINAL 4 with operations (OPEN/CLOSE, FINAL 4, FINAL 8, count 2+, all, 80-net)

  python3 tools/chat_page.py rrr_datasets/v12.txt            # print in the terminal
  python3 tools/chat_page.py rrr_datasets/v12.txt --md F.md  # also write the markdown

The dataset's last number is the result being checked; the page before it is the same
data without that number.  Everything is read from DataProcessing.py's own output, so
nothing here changes a prediction.  Display only.
"""
import os, re, sys, json, tempfile, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSI = re.compile(r'\x1b\[[0-9;]*m')
NUMOP = re.compile(r'(\d\d) \(([^)]*)\)')


# ── running the page ─────────────────────────────────────────────────────────
def _run(text, dump=False):
    env = dict(os.environ, CHAT_PAGE_OFF='1')
    env.pop('RRR3_DUMP2', None); env.pop('OMA_OFF', None)
    jf = None
    if dump:
        jf = tempfile.mktemp(suffix='.json')
        env['RRR3_DUMP2'] = jf
    p = subprocess.Popen([sys.executable, os.path.join(HERE, 'DataProcessing.py')],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, cwd=HERE, env=env, text=True)
    return p, jf


def _finish(p, jf):
    out = p.stdout.read(); p.wait()
    lines = ANSI.sub('', out).split('\n')
    if jf:
        try:
            with open(jf) as fh:
                d = json.load(fh)
        finally:
            if os.path.exists(jf):
                os.remove(jf)
        return d
    return lines


def _feed(text):
    return text.rstrip('\n') + '\nEND\n'


def drop_last_number(text):
    lines = text.rstrip().split('\n')
    toks = lines[-1].split()
    lines[-1] = ' '.join(toks[:-1])
    if not lines[-1].strip():
        lines.pop()
    return '\n'.join(lines) + '\n', int(toks[-1])


# ── reading the page ─────────────────────────────────────────────────────────
def last_idx(L, key, before=None):
    rng = range((before or len(L)) - 1, -1, -1)
    for i in rng:
        if key in L[i]:
            return i
    return None


def box_after(L, i):
    """Rows (cells joined over wrapped lines) of the first ┌..└ box at/after line i."""
    first = lambda ln: ln.lstrip()[:1]
    while i < len(L) and first(L[i]) != '┌':
        i += 1
    rows, cur = [], None
    i += 1
    while i < len(L) and first(L[i]) != '└':
        ln = L[i]
        if first(ln) == '├':
            if cur:
                rows.append(cur)
            cur = None
        elif '│' in ln:
            cells = [c.strip() for c in ln.split('│')[1:-1]]
            if cur is None:
                cur = cells
            else:
                cur = [(a + ' ' + b).strip() for a, b in zip(cur, cells + [''] * (len(cur) - len(cells)))]
        i += 1
    if cur:
        rows.append(cur)
    return rows, i


def find(L, start, key, stop=None):
    for i in range(start, stop or len(L)):
        if key in L[i]:
            return i
    return None


def live(s):
    m = re.search(r'[Ll]ive (\d+ of \d+)', s)
    return m.group(1) if m else '—'


def nums(s):
    return re.findall(r'\b\d\d\b', s)


def parse(L):
    P = {}
    s4 = last_idx(L, '■ 4. RRR: NEXT OPERATION')
    m = re.search(r'EP (\d+) \(([^)]*)\), ROOT (\d+) \(([^)]*)\)', L[s4])
    P['ep'], P['epop'], P['root'], P['rootop'] = m.group(1), m.group(2), m.group(3), m.group(4)
    t1, e1 = box_after(L, s4)
    P['t1'] = [r[:12] for r in t1[1:]]
    P['stars'] = [(r[13], r[14], r[15]) for r in t1[1:] if len(r) > 15 and r[13] in ('MegaStar', 'PowerStar')]
    P['stars_live'] = live(' '.join(L[s4:e1 + 3]))
    t2, e2 = box_after(L, e1 + 1)
    P['t2'] = [r[:8] for r in t2[1:]]
    zone = L[s4:e2 + 2]
    st = []
    for ln in zone:
        for m in re.finditer(r'(MegaStar|PowerStar)\s*│\s*(\d\d)\s*│\s*([^\s│]+)', ln):
            if m.group(1) not in [x[0] for x in st]:
                st.append(m.groups())
    if st:
        P['stars'] = st
    P['stars_live'] = live(' '.join(zone))
    g = lambda key: L[find(L, e2, key)] if find(L, e2, key) is not None else ''
    gi = lambda key: find(L, e2, key)
    i = gi('old/newold numbers:'); P['oldnew'] = ' '.join(nums(L[i].split(':', 1)[1])) if i else ''
    i = gi('± numbers:'); P['pm'] = ' '.join(nums(L[i].split(':', 1)[1])) if i else ''
    i = gi('~ numbers:'); P['tl'] = ' '.join(nums(L[i].split(':', 1)[1])) if i else ''
    i = gi('* numbers:'); P['st'] = ' '.join(nums(L[i].split(':', 1)[1])) if i else ''
    ln = g('EP·LAST old xy')
    m = re.search(r'number\) (\d+): (\d\d) \(([^)]*)\)', ln)
    P['eplast'] = (m.group(2), m.group(3), m.group(1), live(ln)) if m else None
    i = gi('EPROOTGEN (EP')
    if i:
        P['eprg_head'] = L[i].split('(', 1)[1].split(';')[0]
        j = find(L, i, 'ascending:')
        P['eprg'] = ' '.join(re.findall(r'(\d\d) \(', ' '.join(L[i + 1:j])))
        P['eprg_set'] = nums(L[j].split('ascending:')[1].split('live')[0])
        P['eprg_live'] = live(L[j])
    ln = g('Outer flip move'); m = NUMOP.search(ln.split(':', 1)[-1]) if ln else None
    P['oflip'] = (m.group(1), m.group(2), live(ln)) if m else None
    ln = g('Outer op move'); m = NUMOP.search(ln.split(':', 1)[-1]) if ln else None
    P['oop'] = (m.group(1), m.group(2), live(ln)) if m else None
    i = gi('■ CROSSED options')
    P['grid'] = []
    if i:
        b1, e = box_after(L, i); b2, _ = box_after(L, e + 1)
        P['grid'] = [c for r in b2[1:] for c in r[1:] if re.fullmatch(r'\d\d', c)]
    P['grid_live'] = live(L[find(L, i, 'different numbers')]) if i else '—'
    ln = g('Rule 28 (crossed) picks:')
    P['r28'] = NUMOP.findall(ln.split(':', 1)[1]) if ln else []
    P['r28_live'] = (re.search(r'\((\d+ of \d+)\)', ln) or [None, '—'])[1] if ln else '—'
    i = gi('■ LAST-OP 4:')
    P['lo_live'] = (re.search(r'top 4 (\d+ of \d+)', L[i]) or [None, '—'])[1] if i else '—'
    lo, _ = box_after(L, i) if i else ([], 0)
    P['lastop'] = [(r[1], r[2]) for r in lo[1:5]]
    f = last_idx(L, '■ OCJP FINAL 4 with operations')
    m = re.search(r'OPEN digit \(tens\): (\d)\s+strongest 3: (\d \d \d)\s+CLOSE digit \(units\): (\d)\s+strongest 3: (\d \d \d)', L[f + 2])
    P['open'], P['open3'], P['close'], P['close3'] = m.group(1), m.group(2).split(), m.group(3), m.group(4).split()
    m = re.search(r'live OPEN (\S+) of (\d+), CLOSE (\S+) of (\d+)', L[f + 3])
    P['oc_live'] = m.groups() if m else ('—', '—', '—', '—')
    fb, fe = box_after(L, f)
    P['f4'] = []
    for r in fb[1:]:
        b1 = NUMOP.search(r[4]); b2 = NUMOP.search(r[5])
        P['f4'].append(dict(rank=r[0], n=r[1], op=r[2], yx=r[3],
                            bxy=f'{b1.group(1)} ({b1.group(2)})' if b1 else '—',
                            byx=f'{b2.group(1)} ({b2.group(2)})' if b2 else '—',
                            how=r[6], src=r[7], votes=r[9] if len(r) > 9 else ''))
    gf = lambda key: find(L, fe, key)
    i = gf('FINAL 8 (FINAL 4 + PRIME 8 adds):')
    P['f8'] = NUMOP.findall(L[i].split(':', 1)[1]); P['f8_live'] = live(L[i + 1])
    i = gf('yx column:'); P['yxcol'] = nums(L[i].split(':', 1)[1].split('live')[0]); P['yx_live'] = live(L[i])
    i = gf('BEST FORMS ('); j = find(L, i, 'ascending:')
    P['bf'] = nums(L[j].split('ascending:')[1]); P['bf_live'] = live(L[j + 1])
    i = gf('BOOSTER ('); j = find(L, i, 'live')
    P['booster'] = re.findall(r'(\d\d) \(', ' '.join(L[i + 1:j]))
    i = gf('ascending, count 2+ ('); P['c2'] = nums(L[i].split(':', 1)[1])
    i = gf('ascending, all ('); P['all'] = nums(L[i].split(':', 1)[1])
    i = gf('left out (20):'); P['left'] = nums(L[i].split(':', 1)[1]); P['net_live'] = live(L[i + 1])
    o = last_idx(L, 'ONE-MEN-ARMY  —')
    P['oma'], P['oma_asc'], P['oma_live'] = [], [], '—'
    if o is not None:
        for k in range(o, o + 20):
            P['oma'] += re.findall(r'(\d+)\. (\d\d) \(([^)]*)\)', L[k])
            if 'ascending:' in L[k]:
                P['oma_asc'] = nums(L[k].split('ascending:')[1]); P['oma_live'] = live(L[k + 1]); break
    o = last_idx(L, 'ONE ROW PICK  —')
    P['orp'] = None
    if o is not None:
        k = find(L, o, 'PICK:'); m = NUMOP.findall(L[k]); t = find(L, o, 'On test')
        P['orp'] = (m[-1][0], m[-1][1], (re.search(r'live (\d+ of \d+)', L[t]) or [None, '—'])[1])
    def rec(key):
        i = last_idx(L, key)
        if i is None:
            return '—', ''
        c = [x.strip() for x in L[i].split('│')]
        return c[-2] if len(c) > 2 else '—', c[2] if len(c) > 3 else ''
    P['f4_rec'] = rec('│ OCJP FINAL 4 │')[0]; P['ms_rec'] = rec('│ OCJP MASTER  │')[0]
    i = last_idx(L, '│ PRIME 10 │')
    if i is not None:
        c = [x.strip() for x in L[i].split('│')]
        P['p10'] = NUMOP.findall(c[2]); P['p10_rec'] = c[3]
    else:
        P['p10'], P['p10_rec'] = [], '—'
    return P


# ── building the markdown ────────────────────────────────────────────────────
def op_on(root, res):
    sys.path.insert(0, HERE)
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        import DataProcessing as D
    r, x = int(root), int(res)
    return f"{D.OP_ABBREV[D.find_op(r // 10, x // 10)]}/{D.OP_ABBREV[D.find_op(r % 10, x % 10)]}"


def mk(rows):
    return '\n'.join('| ' + ' | '.join(str(c) for c in r) + ' |' if k != 1 else
                     '|' + '---|' * len(rows[0]) for k, r in enumerate([rows[0], None] + rows[1:]))


def build(series_round, prevP, prevD, P, res):
    R = f'{res:02d}'
    op = op_on(prevP['root'], res)
    ck = lambda b: '✓' if b else '✗'
    f4 = [d['n'] for d in prevP['f4']]
    f8 = [n for n, _ in prevP['f8']]
    oma = {n: k for k, n, _ in prevP['oma']}
    strong = [f'{x:02d}' for x in prevD.get('strong', [])]
    recl = [f'{x:02d}' for x in prevD.get('rec', [])]
    t, u = R[0], R[1]
    held, miss = [], []
    def note(name, b):
        (held if b else miss).append(name)
    note('OCJP FINAL 4', R in f4); note('FINAL 8', R in f8)
    note('the OPEN digit', t == prevP['open']); note('the CLOSE digit', u == prevP['close'])
    note(f"the OPEN 3-digit set ({' '.join(prevP['open3'])})", t in prevP['open3'] and t != prevP['open'])
    note(f"the CLOSE 3-digit set ({' '.join(prevP['close3'])})", u in prevP['close3'] and u != prevP['close'])
    note('the yx column', R in prevP['yxcol']); note('EPROOTGEN', R in prevP['eprg_set'])
    note(f"ONE-MEN-ARMY (#{oma[R]})" if R in oma else 'ONE-MEN-ARMY', R in oma)
    note(f"STRONG 20 (#{strong.index(R) + 1})" if R in strong else 'STRONG 20', R in strong)
    note('RECOMMENDED', R in recl)
    note('LAST-OP 4', R in [n for n, _ in prevP['lastop']])
    note('Rule 28', R in [n for n, _ in prevP['r28']])
    note('the CROSSED grid', R in prevP['grid'])
    note('the outer flip / outer op move', R in [x[0] for x in (prevP['oflip'], prevP['oop']) if x])
    yxl = [f'{x:02d}' for x in prevD.get('yx', [])]
    note('the RRR yx list', R in yxl)
    tbl = sorted({f'{(x[0] if isinstance(x, list) else x):02d}' for x in prevD.get('table', [])})
    note('the RRR table', R in tbl)
    note('the BOOSTER', R in prevP['booster']); note('count 2+', R in prevP['c2'])
    note('BEST FORMS', R in prevP['bf'])
    note('ONE ROW PICK', bool(prevP['orp']) and R == prevP['orp'][0])
    note('MegaStar/PowerStar', R in [b for _, b, _ in prevP['stars']])
    cells = lambda rows, cols: {m for r in rows for c in cols if c < len(r) for m in re.findall(r'\b\d\d\b', r[c])}
    note('the ~ / ± / * numbers', R in (prevP['tl'] + ' ' + prevP['pm'] + ' ' + prevP['st']).split()
         or R in cells(prevP['t1'], (8, 9, 10, 11)) or R in cells(prevP['t2'], (6, 7)))
    note('the RRR table old / newold columns', R in cells(prevP['t2'], (2, 3, 4, 5)) or R in prevP['oldnew'].split())
    note('the 80-number list', R not in prevP['left'])
    # every list the round record says held the result (rrr_records/live.jsonl, written by
    # record_round.py), so nothing the counters saw is left off the page
    NAMES = {'rec': None, 'strong': None, 'yx': None, 'table': None, 'wide': 'the wide list',
             'charrow': 'CharRow', 'hot': 'the hot list', 'top4': None, 'top10': 'ranked top 10',
             'top20': 'ranked top 20', 'top40': 'ranked top 40', 'prime10': 'PRIME 10',
             'prime4fam': 'PRIME 4 family', 'prime4rev': 'PRIME 4 reversed', 'finder': 'the finder',
             'lastop8': 'LAST-OP 8', 'ncspec': 'NC/CUT special', 'one_row': None}
    try:
        recs = [json.loads(l) for l in open(os.path.join(HERE, 'rrr_records', 'live.jsonl'))]
        rr = [r for r in recs if r.get('round') == series_round and r.get('result') == res]
        for k in (rr[-1]['held_by'] if rr else []):
            nm = NAMES.get(k, k.replace('rule', 'rule ') if k.startswith('rule') else k)
            if nm and nm not in held:
                held.append(nm)
    except Exception:
        pass
    miss[:] = [m for m in miss if '3-digit set' not in m]
    out = []
    A = out.append
    sr = series_round
    A(f"# {'Round ' + sr + ' result' if sr else 'Last result'}: {R} = {op} on ROOT {prevP['root']} ({prevP['rootop']}), EP {prevP['ep']} ({prevP['epop']})\n")
    A(f"{R} was held by " + (', '.join(f'**{h}**' for h in held) or 'no list') + '. '
      + ('Missed: ' + ', '.join(miss) + '.' if miss else '') + '\n')
    phd = f"EP {prevP['ep']} ({prevP['epop']}), ROOT {prevP['root']} ({prevP['rootop']})"
    A(f"## Result check: {sr or 'last result'} = {R} ({op} on ROOT {prevP['root']}): {phd}")
    ol = P['oc_live']
    A(mk([['List', f'Held {R}?', 'Live now'],
          [f"OCJP FINAL 4 ({' '.join(f4)})", ck(R in f4), P['f4_rec']],
          [f"OCJP MASTER {f4[0]}", ck(R == f4[0]), P['ms_rec']],
          [f"FINAL 8 (+{' '.join(f8[4:])})", ck(R in f8), P['f8_live']],
          [f"OPEN digit {prevP['open']} / set {' '.join(prevP['open3'])}", f"{ck(t == prevP['open'])} / {ck(t in prevP['open3'])}", f"{ol[0].replace('/', ' / ')} of {ol[1]}"],
          [f"CLOSE digit {prevP['close']} / set {' '.join(prevP['close3'])} (actual {u})", f"{ck(u == prevP['close'])} / {ck(u in prevP['close3'])}", f"{ol[2].replace('/', ' / ')} of {ol[3]}"],
          ['EPROOTGEN', ck(R in prevP['eprg_set']), P.get('eprg_live', '—')],
          [f"ONE-MEN-ARMY" + (f" (#{oma[R]} {R})" if R in oma else ''), ck(R in oma), P['oma_live']],
          [f"STRONG 20" + (f" (#{strong.index(R) + 1})" if R in strong else ''), ck(R in strong), '—'],
          ['RECOMMENDED', ck(R in recl), '—'],
          [f"yx column ({' '.join(prevP['yxcol'])})", ck(R in prevP['yxcol']), P['yx_live']],
          [f"LAST-OP 4 ({' '.join(n for n, _ in prevP['lastop'])})", ck(R in [n for n, _ in prevP['lastop']]), P['lo_live']],
          [f"Rule 28 ({' '.join(n for n, _ in prevP['r28'])})", ck(R in [n for n, _ in prevP['r28']]), P['r28_live']],
          [f"Outer flip / outer op ({' / '.join(x[0] for x in (prevP['oflip'], prevP['oop']) if x)})", ck(R in [x[0] for x in (prevP['oflip'], prevP['oop']) if x]), ' / '.join(x[2] for x in (P['oflip'], P['oop']) if x) or '—'],
          [f"RRR yx list ({' '.join(yxl)})", ck(R in yxl), '—'],
          [f"RRR table ({' '.join(tbl)})", ck(R in tbl), '—'],
          [f"CROSSED grid ({len(prevP['grid'])} numbers)", ck(R in prevP['grid']), P['grid_live']],
          [f"ONE ROW PICK ({prevP['orp'][0] if prevP['orp'] else '—'})", ck(bool(prevP['orp']) and R == prevP['orp'][0]), P['orp'][2] if P['orp'] else '—'],
          ['80-number list' + (f' ({R} left out)' if R in prevP['left'] else ''), ck(R not in prevP['left']), P['net_live']]]))
    A(f"\nThe earlier {P['ep']} was followed by {P['root']}, so **ROOT = {P['root']} ({P['rootop']})**. {len(P['t1'])} rows qualify.\n")
    hd = f"EP {P['ep']} ({P['epop']}), ROOT {P['root']} ({P['rootop']})"
    A(f"## 4. RRR: NEXT OPERATION: {hd}")
    A(mk([['Pos', 'Source', 'old x', 'old y', 'new x', 'new y', 'xy (op)', 'yx (op)', '*xy (op)', '*yx (op)', '~xy (op)', '~yx (op)']] + P['t1']))
    A('')
    A(mk([['Pos', 'Source', 'old xy (op)', 'old yx (op)', 'newold xy', 'oldnew yx', 'oldy·newy±', 'oldx·newx±']] + P['t2']))
    A('')
    if P['stars']:
        A(f"## MegaStar / PowerStar: {hd}")
        A(mk([['Pick', 'Number', f"Op on ROOT {P['root']} ({P['rootop']})"]] + [[f'**{a}**', f'**{b}**', c] for a, b, c in P['stars']]))
        A(f"\nMegaStar / PowerStar live {P['stars_live']}.\n")
    A(f"## Other lists with operations: {hd}")
    rows = [['List', 'Numbers (op)', 'Live']]
    if P.get('eprg'):
        rows.append([f"EPROOTGEN ({P['eprg_head']})", P['eprg'], P['eprg_live']])
    rows.append(['Rule 28', ' · '.join(f'{n} ({o})' for n, o in P['r28']), P['r28_live']])
    yxo = ' · '.join(f"{d['yx']}" for d in P['f4'])
    rows.append(['FINAL 4 yx column', yxo, P['yx_live']])
    if P['oflip'] or P['oop']:
        rows.append(['Outer flip / outer op move',
                     ' · '.join(f'{a} ({b})' for a, b, _ in [x for x in (P['oflip'], P['oop']) if x]),
                     ' / '.join(x[2] for x in (P['oflip'], P['oop']) if x)])
    if P['p10']:
        rows.append(['PRIME 10 adds', ' · '.join(f'{n} ({o})' for n, o in P['p10']), P['p10_rec']])
    rows.append(['LAST-OP 4', ' · '.join(f'{n} ({o})' for n, o in P['lastop']), P['lo_live']])
    rows.append([f"BEST FORMS ({len(P['bf'])})", ' '.join(P['bf']), P['bf_live']])
    if P['eplast']:
        n, o, e, lv = P['eplast']
        rows.append(['EP·LAST old xy (test)', f'{n} ({o} on EP {e})', lv])
    if P['orp']:
        rows.append(['ONE ROW PICK', f"{P['orp'][0]} ({P['orp'][1]})", P['orp'][2]])
    rows.append(['~ / ± / *', ' · '.join(x for x in (P['tl'], P['pm'], P['st']) if x), '—'])
    rows.append(['old/newold', P['oldnew'], '—'])
    A(mk(rows))
    A(f"\n## ONE-MEN-ARMY: {hd} (live {P['oma_live']})")
    A(f"**Ascending:** {' '.join(P['oma_asc'])}\n")
    A(f"## OCJP FINAL 4 with operations: {hd}\n")
    A(f"### OPEN / CLOSE digits: {hd}")
    A(mk([['', 'Strongest digit', 'Strongest 3'],
          ['**OPEN (tens)**', f"**{P['open']}**", ' · '.join(P['open3'])],
          ['**CLOSE (units)**', f"**{P['close']}**", ' · '.join(P['close3'])]]))
    A('')
    A(f"### OCJP FINAL 4: {hd}")
    rows = [['#', 'Number', f"Op on ROOT {P['root']} ({P['rootop']})", 'yx (op)', 'Booster xy / yx (first)', 'From which Op', 'Votes']]
    for d in P['f4']:
        rk = '**MASTER = 1**' if d['rank'].startswith('MASTER') else d['rank']
        rows.append([rk, f"**{d['n']}**", d['op'], d['yx'], f"{d['bxy']} / {d['byx']}", d['src'], d['votes']])
    A(mk(rows))
    A(f"\n### FINAL 8 / Count 2+ / All / 80-number list: {hd}\n")
    A(f"**FINAL 8:** " + ' · '.join(f'{n}' if k < 4 else f'**{n}** ({o})' for k, (n, o) in enumerate(P['f8'])))
    A(f"**FINAL 8 ascending:** {' '.join(sorted(n for n, _ in P['f8']))} (live {P['f8_live']})\n")
    A(f"**Count 2+ ({len(P['c2'])}):** {' '.join(P['c2'])}\n")
    A(f"**Ascending, all ({len(P['all'])}):** {' '.join(P['all'])}\n")
    A(f"**80-number list, left out (20):** {' '.join(P['left'])}\n")
    A(f"FINAL 4 for the next round: **{', '.join(d['n'] for d in P['f4'])}** (live {P['f4_rec']}). Display of the script's own lists; no hit is promised.")
    return '\n'.join(out) + '\n'


# ── terminal view of the markdown ────────────────────────────────────────────
def render(md):
    """Terminal view: every markdown table becomes a box whose top bar names the
    EP and ROOT with their operations (user 2026-11-09), taken from the heading above."""
    B, N = '\x1b[1m', '\x1b[0m'
    bold = lambda s: re.sub(r'\*\*(.+?)\*\*', B + r'\1' + N, s)
    plain = lambda s: s.replace('**', '')
    out, tbl = [], []
    title = ['']
    def flush():
        if not tbl:
            return
        rows = [[c.strip() for c in r.strip().strip('|').split('|')] for r in tbl if not re.match(r'^\|[-|]+\|$', r.strip())]
        w = [max(len(plain(r[k])) for r in rows) for k in range(len(rows[0]))]
        t = title[0]
        inner = sum(x + 2 for x in w) + len(w) - 1
        if t and len(t) + 2 > inner:
            w[-1] += len(t) + 2 - inner; inner = len(t) + 2
        line = lambda a, b, c: '  ' + a + b.join('─' * (x + 2) for x in w) + c
        if t:
            out.append('  ┌' + '─' * inner + '┐')
            out.append('  │ ' + B + t + N + ' ' * (inner - len(t) - 1) + '│')
            out.append(line('├', '┬', '┤'))
        else:
            out.append(line('┌', '┬', '┐'))
        for k, r in enumerate(rows):
            out.append('  │' + '│'.join(' ' + bold(c) + ' ' * (w[i] - len(plain(c)) + 1) for i, c in enumerate(r)) + '│')
            out.append(line('├', '┼', '┤') if k < len(rows) - 1 else line('└', '┴', '┘'))
        tbl.clear()
    for ln in md.split('\n'):
        if ln.startswith('|'):
            tbl.append(ln); continue
        flush()
        if ln.startswith('#'):
            out.append('  ' + B + '■ ' + ln.lstrip('# ') + N)
            m = re.search(r'EP \d+ \([^)]*\), ROOT \d+ \([^)]*\)', ln)
            title[0] = m.group(0) if m else ''
        elif ln:
            import textwrap
            out += ['  ' + bold(w) for w in textwrap.wrap(ln, 190)]
        else:
            out.append('')
    flush()
    return '\n'.join(out)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    path = a[0]
    md_out = a[a.index('--md') + 1] if '--md' in a else None
    label = a[a.index('--round') + 1] if '--round' in a else None
    text = open(path).read()
    prev_text, res = drop_last_number(text)
    if label is None:
        m = re.match(r'([a-z]+)(\d+)\.txt$', os.path.basename(path))
        label = f'{m.group(1).upper()}{m.group(2)}' if m else ''
    jobs = [_run(prev_text), _run(prev_text, dump=True), _run(text)]
    for p, _ in jobs:
        p.stdin.write(_feed(prev_text) if p is not jobs[2][0] else _feed(text)); p.stdin.close()
    prevL, prevD, curL = [_finish(p, j) for p, j in jobs]
    md = build(label, parse(prevL), prevD, parse(curL), res)
    if md_out:
        with open(md_out, 'w') as fh:
            fh.write(md)
    print('\n' + '═' * 100)
    print('  CHAT PAGE  —  same tables and order as the chat reply')
    print('═' * 100)
    print(render(md))


if __name__ == '__main__':
    main()
