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
import functools
import textwrap
import os, re, sys, json, tempfile, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSI = re.compile(r'\x1b\[[0-9;]*m')
NUMOP = re.compile(r'(\d\d) \(([^)]*)\)')


# ── running the page ─────────────────────────────────────────────────────────
def _run(text, dump=False):
    # inner runs always at one width, so the page's content never depends on the user's terminal
    # (local window == chat page at any width; only render() adapts to the screen)
    env = dict(os.environ, CHAT_PAGE_OFF='1', COLUMNS='230')
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
    if t1 and len(t1[0]) >= 18 and t1[0][12].startswith('old xy'):
        # wide terminal: both RRR tables in one box (old xy .. oldx·newx± are columns 12-17)
        P['t2'] = [[r[0], r[1]] + r[12:18] for r in t1[1:]]; e2 = e1
    else:
        t2, e2 = box_after(L, e1 + 1)
        P['t2'] = [r[:8] for r in t2[1:]]
    zone = L[s4:e2 + 12]   # the MegaStar / PowerStar box sits just below the RRR table(s)
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
    i = find(L, f, 'OPEN full order:')
    m2 = re.search(r'OPEN full order: ([\d ]+?)\s+CLOSE full order: ([\d ]+)', L[i]) if i is not None else None
    P['open_full'], P['close_full'] = (m2.group(1).split(), m2.group(2).split()) if m2 else ([], [])
    i = find(L, f, 'OPEN x CLOSE grid (9):')
    P['ocgrid'] = nums(L[i].split(':', 1)[1].split('live')[0]) if i is not None else []
    P['ocgrid_live'] = live(L[i]) if i is not None else '—'
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
    i = gf('OC-STRONG 4 (')
    P['ocs'] = NUMOP.findall(L[i].split(':', 1)[1]) if i is not None else []
    P['ocs_live'] = live(L[i + 1]) if i is not None else '—'
    i = gf('OPEN-STRONG 4 (')
    P['os4'] = NUMOP.findall(L[i].split(':', 1)[1]) if i is not None else []
    i = gf('FINAL 8 (FINAL 4 + ')
    P['f8'] = NUMOP.findall(L[i].split(':', 1)[1]); P['f8_live'] = live(L[i + 1])
    i = gf('yx column:'); P['yxcol'] = nums(L[i].split(':', 1)[1].split('live')[0]); P['yx_live'] = live(L[i])
    i = gf('BEST FORMS ('); j = find(L, i, 'ascending:')
    P['bf'] = nums(L[j].split('ascending:')[1]); P['bf_live'] = live(L[j + 1])
    i = gf('BOOSTER ('); j = find(L, i, 'live')
    P['booster'] = re.findall(r'(\d\d) \(', ' '.join(L[i + 1:j]))
    P['booster_ops'] = re.findall(r'(\d\d) \(([^)]+)\)', ' '.join(L[i + 1:j])); P['booster_live'] = live(L[j])
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


def step_list(P):
    """FINAL 4 numbers with ONE side's step moved +1/-1 (user 2026-11-09, X5: 85 = 75 with x -2 -> -1).
    History 1293 rounds: held 165 vs chance 186.5 (~14 numbers) -> display only."""
    try:
        sys.path.insert(0, HERE)
        import io as _io, contextlib as _cl
        with _cl.redirect_stdout(_io.StringIO()):
            import DataProcessing as D
        rt = int(P['root']); ex, ey = rt // 10, rt % 10; stp = []
        f4 = [x['n'] for x in P['f4']]
        for v in map(int, f4):
            sx = D._op_side(D.OP_ABBREV[D.find_op(ex, v // 10)]); sy = D._op_side(D.OP_ABBREV[D.find_op(ey, v % 10)])
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = D._op_apply(ex, sx[0], sx[1] + dx) * 10 + D._op_apply(ey, sy[0], sy[1] + dy)
                if f'{n:02d}' not in f4 and n not in [q for q, _ in stp]:
                    stp.append((n, f"{D.OP_ABBREV[D.find_op(ex, n // 10)]}/{D.OP_ABBREV[D.find_op(ey, n % 10)]}"))
        return stp
    except Exception:
        return []


def turned_lists(P):
    """Digits turned (user 2026-11-09, X6: 51 = yx-column 15 turned).  rev(FINAL 4) and
    rev(FINAL 4 yx column).  History 1293: rev FINAL 4 54 vs 44.6, rev yx 48 vs 44.0;
    live 266: 9 vs 9.2 and 16 vs 9.1 -> display only."""
    try:
        sys.path.insert(0, HERE)
        import io as _io, contextlib as _cl
        with _cl.redirect_stdout(_io.StringIO()):
            import DataProcessing as D
        rt = int(P['root']); ex, ey = rt // 10, rt % 10
        op = lambda n: f"{D.OP_ABBREV[D.find_op(ex, n // 10)]}/{D.OP_ABBREV[D.find_op(ey, n % 10)]}"
        rev = lambda n: (n % 10) * 10 + n // 10
        f4 = [int(x['n']) for x in P['f4']]
        yxs = [int(NUMOP.search(x['yx']).group(1)) for x in P['f4'] if NUMOP.search(x['yx'])]
        a = [(rev(v), op(rev(v))) for v in f4 if rev(v) not in f4]
        b = [(rev(v), op(rev(v))) for v in yxs if rev(v) not in f4]
        return list(dict.fromkeys(a)), list(dict.fromkeys(b))
    except Exception:
        return [], []


def fullcut_list(P):
    """Both digits cut (n+5 on each digit) of FINAL 4 and of its yx column (user 2026-11-09,
    X7: 34 -> 89).  History 1293: FINAL 4 54 vs 49.2, yx 60 vs 45.5; live 266: 17 vs 10.1,
    11 vs 9.4 (one-digit cuts are below chance, not shown).  Display only."""
    try:
        sys.path.insert(0, HERE)
        import io as _io, contextlib as _cl
        with _cl.redirect_stdout(_io.StringIO()):
            import DataProcessing as D
        rt = int(P['root']); ex, ey = rt // 10, rt % 10
        op = lambda n: f"{D.OP_ABBREV[D.find_op(ex, n // 10)]}/{D.OP_ABBREV[D.find_op(ey, n % 10)]}"
        cut = lambda n: ((n // 10 + 5) % 10) * 10 + (n % 10 + 5) % 10
        f4 = [int(x['n']) for x in P['f4']]
        yxs = [int(NUMOP.search(x['yx']).group(1)) for x in P['f4'] if NUMOP.search(x['yx'])]
        out = []
        for v in f4 + yxs:
            n = cut(v)
            if n not in f4 and n not in [q for q, _ in out]:
                out.append((n, op(n)))
        return out
    except Exception:
        return []


LIVE_ROWS = os.path.join(HERE, 'rrr_records', 'display_rows_live.jsonl')


def row_live(series_round, res, prevP):
    """Live record of the display-only rows (STEP ±1, digits turned, FULL CUT), counted
    from 2026-11-09 X5.  One line per round in rrr_records/display_rows_live.jsonl."""
    R = f'{res:02d}'
    held = {'step': R in [f'{n:02d}' for n, _ in prevP['step']],
            'trf4': R in [f'{n:02d}' for n, _ in prevP['trf4']],
            'tryx': R in [f'{n:02d}' for n, _ in prevP['tryx']],
            'fcut': R in [f'{n:02d}' for n, _ in prevP['fcut']]}
    sizes = {k: len(prevP[k]) for k in held}
    recs = []
    if os.path.exists(LIVE_ROWS):
        recs = [json.loads(l) for l in open(LIVE_ROWS) if l.strip()]
    if series_round and not any(r['round'] == series_round for r in recs):
        recs.append({'round': series_round, 'result': res, 'held': held, 'sizes': sizes})
        with open(LIVE_ROWS, 'a') as fh:
            fh.write(json.dumps(recs[-1]) + '\n')
    out = {}
    for k in held:
        rr = [r for r in recs if k in r['held']]
        out[k] = f"live {sum(r['held'][k] for r in rr)} of {len(rr)} (chance {sum(r['sizes'][k] for r in rr) / 100:.1f})"
    return out


def build(series_round, prevP, prevD, P, res, curD=None):
    R = f'{res:02d}'
    prevP['step'] = step_list(prevP); P['step'] = step_list(P)
    prevP['trf4'], prevP['tryx'] = turned_lists(prevP); P['trf4'], P['tryx'] = turned_lists(P)
    prevP['fcut'] = fullcut_list(prevP); P['fcut'] = fullcut_list(P)
    LV = row_live(series_round, res, prevP)
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
    if prevP.get('ocs'):
        note('OC-STRONG 4', R in [n for n, _ in prevP['ocs']])
    if prevP.get('os4'):
        note('OPEN-STRONG 4', R in [n for n, _ in prevP['os4']])
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
    note('EP·LAST old xy (test)', bool(prevP.get('eplast')) and R == prevP['eplast'][0])
    note('MegaStar/PowerStar', R in [b for _, b, _ in prevP['stars']])
    cells = lambda rows, cols: {m for r in rows for c in cols if c < len(r) for m in re.findall(r'\b\d\d\b', r[c])}
    note('the ~ / ± / * numbers', R in (prevP['tl'] + ' ' + prevP['pm'] + ' ' + prevP['st']).split()
         or R in cells(prevP['t1'], (8, 9, 10, 11)) or R in cells(prevP['t2'], (6, 7)))
    note('FULL CUT (both digits) of FINAL 4 / yx', R in [f'{n:02d}' for n, _ in prevP['fcut']])
    note('FINAL 4 digits turned', R in [f'{n:02d}' for n, _ in prevP['trf4']])
    note('yx column digits turned', R in [f'{n:02d}' for n, _ in prevP['tryx']])
    note('FINAL 4 STEP ±1', R in [f'{n:02d}' for n, _ in prevP.get('step', [])])
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
    tc, tcl = topcolor_live(series_round, int(R)) if series_round else (None, '')
    A(mk([['List', f'Held {R}?', 'Live now'],
          [f"OCJP FINAL 4 ({' '.join(f4)})", ck(R in f4), P['f4_rec']],
          [f"OCJP MASTER {f4[0]}", ck(R == f4[0]), P['ms_rec']],
          [f"FINAL 8 (+{' '.join(f8[4:])})", ck(R in f8), P['f8_live']],
          *([[f"OC-STRONG 4 ({' '.join(n for n, _ in prevP['ocs'])})", ck(R in [n for n, _ in prevP['ocs']]), P['ocs_live']]]
            if prevP.get('ocs') else []),
          *([[f"CLOSE weak 3 ({' '.join(prevP['close_full'][-3:])}) (actual {u})", ck(u in prevP['close_full'][-3:]),
              closeweak3_live(series_round, int(R))[1] if series_round else '—']]
            if len(prevP.get('close_full') or []) == 10 else []),
          *([[f"OPEN-STRONG 4 ({' '.join(n for n, _ in prevP['os4'])})", ck(R in [n for n, _ in prevP['os4']]),
              openstrong4_live(series_round, int(R))[1] if series_round else '—']]
            if prevP.get('os4') else []),
          *([[f"OPEN × CLOSE grid ({' '.join(prevP['ocgrid'])})", ck(R in prevP['ocgrid']), P['ocgrid_live']]]
            if prevP.get('ocgrid') else []),
          *([[f"Top colour family {tc['colour']} {tc['family']} ({' '.join(f'{v:02d}' for v in tc['members'])})",
              ck(int(R) in tc['members']), tcl]] if tc else []),
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
          [f"FULL CUT of FINAL 4 + yx ({' '.join(f'{n:02d}' for n, _ in prevP['fcut'])})", ck(R in [f'{n:02d}' for n, _ in prevP['fcut']]), 'test 114 vs 94.7'],
          [f"CROSSED grid ({len(prevP['grid'])} numbers)", ck(R in prevP['grid']), P['grid_live']],
          [f"ONE ROW PICK ({prevP['orp'][0] if prevP['orp'] else '—'})", ck(bool(prevP['orp']) and R == prevP['orp'][0]), P['orp'][2] if P['orp'] else '—'],
          ['80-number list' + (f' ({R} left out)' if R in prevP['left'] else ''), ck(R not in prevP['left']), P['net_live']]]))
    _src = P['rootop'].split('→')[0]
    if _src != P['ep']:   # first-time EP: ROOT came from the stand-in (digits turned / cut)
        A(f"\n{P['ep']} is new on this chart (no earlier {P['ep']}), so its stand-in {_src} (digits turned / cut) is used: the earlier {_src} was followed by {P['root']}, so **ROOT = {P['root']} ({P['rootop']})**. {len(P['t1'])} rows qualify.\n")
    else:
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
    rows.append(['FULL CUT, both digits, of FINAL 4 + yx (display only)', ' · '.join(f'{n:02d} ({o})' for n, o in P['fcut']) or '—',
                 f"history 114 vs 94.7; {LV['fcut']}"])
    rows.append(['FINAL 4 digits turned (display only)', ' · '.join(f'{n:02d} ({o})' for n, o in P['trf4']) or '—',
                 f"history 54 vs 44.6; {LV['trf4']}"])
    rows.append(['yx column digits turned (display only)', ' · '.join(f'{n:02d} ({o})' for n, o in P['tryx']) or '—',
                 f"history 48 vs 44.0; {LV['tryx']}"])
    rows.append(['FINAL 4 STEP ±1 (one side, display only)', ' · '.join(f'{n:02d} ({o})' for n, o in P['step']) or '—',
                 f"history 165 vs chance 186; {LV['step']}"])
    rows.append(['~ / ± / *', ' · '.join(x for x in (P['tl'], P['pm'], P['st']) if x), '—'])
    rows.append(['old/newold', P['oldnew'], '—'])
    rows, legend = mark_families(rows)
    if series_round and TOP_COLOUR:
        nxt = re.sub(r'\d+$', lambda m: str(int(m.group()) + 1), series_round)
        topcolor_live(None, entry={'round': nxt, 'colour': TOP_COLOUR[0], 'family': TOP_COLOUR[1],
                                   'members': TOP_COLOUR[2], 'times': TOP_COLOUR[3]})
    A(mk(rows))
    if legend:
        A(f"\n{legend}\n")
    A(f"\n## ONE-MEN-ARMY: {hd} (live {P['oma_live']})")
    A(f"**Ascending:** {' '.join(P['oma_asc'])}\n")
    cs = sorted(f'{x:02d}' for x in (curD or {}).get('strong', []))
    if cs:
        extra = sorted(set(cs) - set(P['oma_asc']))
        A(f"**STRONG 20** shares {20 - len(extra)} of 20 with ONE-MEN-ARMY"
          + (f"; STRONG 20 only: {' '.join(extra)}\n" if extra else " (same list this round)\n"))
    A(f"## OCJP FINAL 4 with operations: {hd}\n")
    A(f"### OPEN / CLOSE digits: {hd}")
    A(mk([['', 'Strongest digit', 'Strongest 3', 'Full order (strong → weak)'],
          ['**OPEN (tens)**', f"**{P['open']}**", ' · '.join(P['open3']), ' '.join(P.get('open_full') or []) or '—'],
          ['**CLOSE (units)**', f"**{P['close']}**", ' · '.join(P['close3']), ' '.join(P.get('close_full') or []) or '—']]))
    if len(P.get('close_full') or []) == 10:
        A(f"\n**CLOSE weak 3** (the 3 weakest CLOSE digits, watch line): {' · '.join(P['close_full'][-3:])} (live {closeweak3_live(None)[1]})")
    if P.get('ocgrid'):
        A(f"\n**OPEN × CLOSE grid (9):** {' '.join(P['ocgrid'])} (live {P['ocgrid_live']}; chance 9%, logged X/Y/Z rounds 18 of 106)")
    A('')
    if P.get('ocs'):
        A(f"**OC-STRONG 4** (STRONG 20 numbers inside OPEN × CLOSE; low tens-repeat charts only): "
          + ' · '.join(f'**{n}** ({o})' for n, o in P['ocs'])
          + f" (live {P['ocs_live']}; logged X/Y/Z rounds 14 of 106 vs chance 4.2, FINAL 4 6 of 106)\n")
    if P.get('os4'):
        A(f"**OPEN-STRONG 4** (STRONG 20 numbers with tens = OPEN digit {P['open']}, OCJP rank order; live test): "
          + ' · '.join(f'**{n}** ({o})' for n, o in P['os4'])
          + f" (live {openstrong4_live(None)[1]}; logged Z rounds 7 of 60 vs chance 2.4, FINAL 4 1 of 60; X/Y 3 of 89 — not confirmed)\n")
    A(f"### OCJP FINAL 4: {hd}")
    rows = [['#', 'Number', f"Op on ROOT {P['root']} ({P['rootop']})", 'yx (op)', 'Booster xy / yx (first)', 'From which Op', 'Votes']]
    for d in P['f4']:
        rk = '**MASTER = 1**' if d['rank'].startswith('MASTER') else d['rank']
        rows.append([rk, f"**{d['n']}**", d['op'], d['yx'], f"{d['bxy']} / {d['byx']}", d['src'], d['votes']])
    A(mk(rows))
    A(f"\n### FINAL 8 / Count 2+ / All / 80-number list: {hd}\n")
    A(f"**FINAL 8 (FINAL 4 + OPEN-STRONG / OC-STRONG / SHADOW):** " + ' · '.join(f'{n}' if k < 4 else f'**{n}** ({o})' for k, (n, o) in enumerate(P['f8'])))
    A(f"**FINAL 8 ascending:** {' '.join(sorted(n for n, _ in P['f8']))} (live {P['f8_live']})\n")
    if P.get('booster_ops'):
        A(f"**BOOSTER, full list ({len(P['booster_ops'])}, FINAL 4 left out, live {P['booster_live']}):** "
          + ' · '.join(f'{n} ({o})' for n, o in P['booster_ops']) + "\n")
    A(f"**Count 2+ ({len(P['c2'])}):** {' '.join(P['c2'])}\n")
    A(f"**Ascending, all ({len(P['all'])}):** {' '.join(P['all'])}\n")
    A(f"**80-number list, left out (20):** {' '.join(P['left'])}\n")
    A(f"FINAL 4 for the next round: **{', '.join(d['n'] for d in P['f4'])}** (live {P['f4_rec']}). Display of the script's own lists; no hit is promised.")
    return '\n'.join(out) + '\n'


# ── terminal view of the markdown ────────────────────────────────────────────
def _cols():
    """Real terminal width, even when stdout is piped through tee (round.sh):
    COLUMNS, then any fd that is a tty, then /dev/tty; 200 if none."""
    if os.environ.get('COLUMNS', '').isdigit():
        return int(os.environ['COLUMNS'])
    for fd in (1, 2, 0):
        try:
            return os.get_terminal_size(fd).columns
        except OSError:
            pass
    try:
        fd = os.open('/dev/tty', os.O_RDONLY)
        try:
            return os.get_terminal_size(fd).columns
        finally:
            os.close(fd)
    except OSError:
        return 200


RING = '\u2b55'   # ⭕ red ring, no fill (user 2026-11-09)
# one colour per number family (user screenshot 2026-11-10: "same family numbers with one colour code")
FAM_COLORS = ['\U0001f7e5', '\U0001f7e6', '\U0001f7e9', '\U0001f7e8', '\U0001f7ea', '\U0001f7e7', '\U0001f7eb', '\u2b1b', '\u2b1c']
WIDE = [RING] + FAM_COLORS          # each is 2 columns wide in the terminal
strip_marks = lambda s: re.sub('[' + ''.join(WIDE) + ']', '', s)


def _family_map():
    """DataProcessing.build_family_map: 10 cut-pair families of 8 (12 = 1/6 x 2/7), HALF CUT (d, cut d), DOUBLE (dd)."""
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
TOP_COLOUR = []      # [colour, family label, all members, times] of the last marked table
TOPCOL_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rrr_records', 'topcolor_live.jsonl')


def topcolor_live(series_round, res=None, entry=None):
    """Top colour family live log (user 2026-11-10, Z22: 40 came from the 🟦 45-family, the highest
    colour count).  The page of round N saves its top family; the result of N scores it.
    Chance = family size / 100 (8 numbers -> 8%).  Display/test only."""
    recs = [json.loads(l) for l in open(TOPCOL_LOG)] if os.path.exists(TOPCOL_LOG) else []
    if entry:
        recs = [r for r in recs if r['round'] != entry['round']] + [entry]
    if res is not None:
        for r in recs:
            if r['round'] == series_round:
                r['result'] = res
    with open(TOPCOL_LOG, 'w') as fh:
        fh.write(''.join(json.dumps(r) + '\n' for r in recs))
    done = [r for r in recs if r.get('result') is not None]
    hits = sum(r['result'] in r['members'] for r in done)
    cur = next((r for r in recs if r['round'] == series_round), None)
    return cur, f"{hits} of {len(done)} (chance {sum(len(r['members']) for r in done) / 100:.2f})"


def mark_families(rows):
    """Other lists table (user 2026-11-10): the strongest numbers (on the most lists of the table)
    get a ⭕ ring, and every family with 2+ different numbers in the table gets one colour square.
    Numbers inside an op's brackets (e.g. 'on EP 41') are left alone.  Display only."""
    tok = re.compile(r'(?<![\d(])(\d\d)(?!\d)')
    def outside(cell):
        return re.sub(r'\([^)]*\)', lambda m: ' ' * len(m.group(0)), cell)
    cnt = {}
    for r in rows[1:]:
        for v in {m.group(1) for m in tok.finditer(outside(r[1]))}:
            cnt[v] = cnt.get(v, 0) + 1
    if not cnt:
        return rows, ''
    top = max(cnt.values())
    strong = sorted(v for v, c in cnt.items() if c == top and c >= 2)
    fams = {}
    for v in cnt:
        fams.setdefault(FAMILY[int(v)], set()).add(v)
    fams = sorted(((f, m) for f, m in fams.items() if len(m) >= 2), key=lambda t: (-len(t[1]), t[0]))[:len(FAM_COLORS)]
    col = {v: FAM_COLORS[k] for k, (f, m) in enumerate(fams) for v in m}
    out = [rows[0]]
    times = {}                       # colour count: how many times each family's numbers stand in the table
    for r in rows[1:]:
        c, o = r[1], outside(r[1])
        for m in tok.finditer(o):
            if m.group(1) in col:
                times[col[m.group(1)]] = times.get(col[m.group(1)], 0) + 1
        parts, last = [], 0
        for m in tok.finditer(o):
            v = m.group(1)
            parts.append(c[last:m.start()] + (RING if v in strong else '') + col.get(v, '') + v)
            last = m.end()
        out.append([r[0], ''.join(parts) + c[last:]] + list(r[2:]))
    fl = lambda f: f"{f}-family" if f[0].isdigit() else f
    legend = ((f"{RING} strongest: {' '.join(strong)} (on {top} lists of this table)" if strong else '')
              + ('  ·  ' if strong and fams else '')
              + '  ·  '.join(f"{FAM_COLORS[k]} {fl(f)} {' '.join(sorted(m))}" for k, (f, m) in enumerate(fams)))
    if times:
        fam_of = {FAM_COLORS[k]: f for k, (f, m) in enumerate(fams)}
        order = sorted(times, key=lambda k: (-times[k], FAM_COLORS.index(k)))
        TOP_COLOUR[:] = [order[0], fl(fam_of[order[0]]), sorted(v for v, f in FAMILY.items() if f == fam_of[order[0]]), times[order[0]]]
        legend += ("\n\n**Colour count** (times each family's numbers stand in this table, highest first): "
                   + '  ·  '.join((f"**{k} {fl(fam_of[k])} {times[k]}**" if times[k] == times[order[0]] else f"{k} {fl(fam_of[k])} {times[k]}")
                                  for k in order))
    return out, legend


def _near(r):
    """The result and the numbers one digit-step away from it (tens or units +-1, wrapping)."""
    a, b = r // 10, r % 10
    return {r, ((a + 1) % 10) * 10 + b, ((a - 1) % 10) * 10 + b, a * 10 + (b + 1) % 10, a * 10 + (b - 1) % 10}


def _scan(md):
    """Every number on a page with the place it stands (table cells and '**Name:** ...' lines),
    the same places the ⭕ Where section looks at.  Yields (place, value, text, has_op)."""
    tok = re.compile(r'(?<!\d)(\d\d)(?!\d)( \([^)]*\))?')
    head, sec = None, ''
    def grab(cell, allnum):
        c = strip_marks(cell.replace('**', ''))
        for m in tok.finditer(c):
            if allnum or m.group(2):
                yield int(m.group(1)), m.group(1) + (m.group(2) or ''), bool(m.group(2))
    for ln in md.split('\n'):
        if ln.startswith('## ') or ln.startswith('### '):
            sec = re.sub(r':.*', '', ln.lstrip('# ')); head = None; continue
        if ln.startswith('|'):
            cells = [c.strip() for c in ln.strip().strip('|').split('|')]
            if re.match(r'^[-| ]+$', ln.strip()):
                continue
            if head is None:
                head = cells; continue
            if sec.startswith('Result check') or sec.startswith(RING):   # not a ⭕ section
                continue
            for i, c in enumerate(cells[1:], 1):
                if head[i].lower().startswith(('live', 'votes', 'from which', 'source', 'op on', 'times', 'places')):
                    continue
                lab = f"{cells[0].replace('**', '')}" + ('' if head[i].startswith('Numbers') else f" · {head[i]}")
                pre = '' if sec.startswith('Other lists') else re.sub(r' with operations$', '', sec) + ' · '
                for v, t, op in grab(c, bool(re.fullmatch(r'[\d\s·*]+', strip_marks(c.replace('**', ''))))):
                    yield pre + lab, v, t, op
        elif ln.startswith('**') and ':**' in ln and not ln.startswith('**Colour count'):
            name, rest = ln.split(':**', 1)
            rest = re.sub(r'\(live[^)]*\)', '', rest)
            nm = name.strip('*')
            lab = 'ONE-MEN-ARMY ascending' if nm == 'Ascending' and sec.startswith('ONE-MEN') else nm
            for v, t, op in grab(rest, '(' not in rest):
                yield lab, v, t, op
        else:
            head = None if not ln.strip() else head


def ring_section(prev_md, R, label):
    """'Where R was' (user 2026-11-09, screenshot Y48): every place on the previous page where the
    result itself (exact, bold) or a number one step away from it stood, marked with a red ring."""
    near = _near(R)
    rows = []
    for place, v, t, op in _scan(prev_md):
        if v in near:
            m = f"{RING}{t}"
            m = f"**{m}**" if v == R else m + ' near'
            if rows and rows[-1][0] == place:
                rows[-1][1].append(m)
            else:
                rows.append([place, [m]])
    if not rows:
        return f"\n## {RING} Where {R:02d} was on the {label} page\n\n{R:02d} and its one-step neighbours were on no list of the {label} page.\n"
    body = '\n'.join(f"| {a} | {' · '.join(b)} |" for a, b in rows)
    return (f"\n## {RING} Where {R:02d} was on the {label} page ({RING} bold = exact, {RING} near = one digit-step away: "
            f"{' '.join(f'{v:02d}' for v in sorted(_near(R) - {R}))})\n| Where | Marked |\n|---|---|\n{body}\n")


STRONGEST = []
STRONG_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rrr_records', 'strongest_live.jsonl')


def strongest_live(series_round, res=None, entry=None):
    """Live log of the page's ⭕ strongest 4 (saved by the page of round N, scored by its result)."""
    recs = [json.loads(l) for l in open(STRONG_LOG)] if os.path.exists(STRONG_LOG) else []
    if entry:
        recs = [r for r in recs if r['round'] != entry['round']] + [entry]
    if res is not None:
        for r in recs:
            if r['round'] == series_round:
                r['result'] = res
    with open(STRONG_LOG, 'w') as fh:
        fh.write(''.join(json.dumps(r) + '\n' for r in recs))
    done = [r for r in recs if r.get('result') is not None]
    cur = next((r for r in recs if r['round'] == series_round), None)
    return cur, f"{sum(r['result'] in r['nums'] for r in done)} of {len(done)} (chance {sum(len(r['nums']) for r in done) / 100:.2f})"


OPH_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rrr_records', 'ophistory_live.jsonl')
OPN = {0: 'nc', 1: '+1', 2: '+2', 3: 'c-2', 4: 'c-1', 5: 'cut', 6: 'c+1', 7: 'c+2', 8: '-2', 9: '-1'}


def op_history(fl):
    """OP HISTORY 4 (user 2026-11-11: pick the operation history says is most suitable - same op,
    nc->cut, -1->nc, +1->cut, sign change, +-1, xy/yx crossed).  tools/op_transform_study.py model:
    A = op into the EP -> next op, B = ROOT op -> op on ROOT; every change counted from the chart's
    past.  Walk-forward 5,778 low-repeat predictions: top 4 A 5.1%, B 4.9% vs chance 4.4%."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from op_transform_study import Model, step, T, U
    low = len(fl) > 300 and sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / (len(fl) - 1) < 0.06
    MA, MB, last = Model(), Model(), {}
    for i in range(1, len(fl) - 1):
        ep, nx = fl[i], fl[i + 1]
        if i >= 2:
            MA.learn(step(fl[i - 2], fl[i - 1]), step(fl[i - 1], ep))
        j = last.get(ep)
        if j is not None and j + 1 < i:
            MB.learn(step(ep, fl[j + 1]), step(fl[j + 1], nx))
        last[ep] = i
    if len(fl) >= 3:
        MA.learn(step(fl[-3], fl[-2]), step(fl[-2], fl[-1]))
    ep = fl[-1]; j = max((k for k in range(len(fl) - 1) if fl[k] == ep), default=None)
    av = T(ep) if low else None
    cands = [n for n in range(100) if av is None or T(n) != av]
    out = {}
    for lab, M, base, src in (('A', MA, ep, step(fl[-2], ep)), ('B', MB, fl[j + 1] if j is not None else None, None)):
        if lab == 'B':
            if base is None:
                continue
            src = step(ep, base)
        st, su = M.side_scores(src, 0), M.side_scores(src, 1)
        sc = {n: st[(T(n) - T(base)) % 10] * su[(U(n) - U(base)) % 10] for n in cands}
        top = sorted(cands, key=lambda n: -sc[n])[:4]
        out[lab] = (base, [(n, f"{OPN[(T(n) - T(base)) % 10]}/{OPN[(U(n) - U(base)) % 10]}") for n in top])
    # C: the 4 best fixed EP/ROOT direct rules on low-repeat charts (tools/ep_root_direct_study.py,
    # 5,778 rounds: 1.44 / 1.38 / 1.35 / 1.33% each vs ~1.1% chance, both halves steady)
    if low and j is not None:
        root = fl[j + 1]; eo, ro = step(fl[-2], ep), step(ep, root)
        rules = [('EP op crossed, x sign, y cut sw', ep, (eo[1], eo[0]), lambda a: -a, lambda a: a + 5),
                 ('ROOT op crossed, x -1, y cut sw', ep, (ro[1], ro[0]), lambda a: a - 1, lambda a: a + 5),
                 ('ROOT op, both signs', ep, ro, lambda a: -a, lambda a: -a),
                 ('EP op crossed, y sign', ep, (eo[1], eo[0]), lambda a: a, lambda a: -a)]
        L = []
        for nm, b, s_, fx, fy in rules:
            n = ((T(b) + fx(s_[0])) % 10) * 10 + (U(b) + fy(s_[1])) % 10
            if n not in [q for q, _ in L]:
                L.append((n, f"{OPN[(T(n) - T(ep)) % 10]}/{OPN[(U(n) - U(ep)) % 10]} on EP"))
        out['C'] = (ep, L)
    return out


def oph_live(series_round, res=None, entry=None):
    recs = [json.loads(l) for l in open(OPH_LOG)] if os.path.exists(OPH_LOG) else []
    if entry:
        recs = [r for r in recs if r['round'] != entry['round']] + [entry]
    if res is not None:
        for r in recs:
            if r['round'] == series_round:
                r['result'] = res
    with open(OPH_LOG, 'w') as fh:
        fh.write(''.join(json.dumps(r) + '\n' for r in recs))
    done = [r for r in recs if r.get('result') is not None]
    cur = next((r for r in recs if r['round'] == series_round), None)
    lv = {k: f"{sum(r['result'] in r[k] for r in done if k in r)} of {sum(k in r for r in done)}" for k in ('A', 'B', 'C')}
    return cur, lv


NEAR_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rrr_records', 'near8_live.jsonl')


def near8_live(series_round, res=None, entry=None):
    """NEAR 8 live log (2026-11-11, tools/f4_step_study.py): MASTER and #2 with one digit +-1.
    Low-repeat logged rounds 30 of 281 vs chance 19.6 (x1.53; live x1.45, history x1.65); normal charts at chance."""
    recs = [json.loads(l) for l in open(NEAR_LOG)] if os.path.exists(NEAR_LOG) else []
    if entry:
        recs = [r for r in recs if r['round'] != entry['round']] + [entry]
    if res is not None:
        for r in recs:
            if r['round'] == series_round:
                r['result'] = res
    with open(NEAR_LOG, 'w') as fh:
        fh.write(''.join(json.dumps(r) + '\n' for r in recs))
    done = [r for r in recs if r.get('result') is not None]
    cur = next((r for r in recs if r['round'] == series_round), None)
    return cur, f"{sum(r['result'] in r['nums'] for r in done)} of {len(done)} (chance {sum(len(r['nums']) for r in done) / 100:.2f})"


STEP_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rrr_records', 'tensstep8_live.jsonl')


def tensstep8_live(series_round, res=None, entry=None):
    """TENS-STEP 8 live log (user 2026-11-11 'close with +1 -1 +2 -2'; tools/f4_change_study.py): FINAL 4 numbers with
    the tens -1 / -2.  Low-repeat logged rounds: tens -1 24/285 (x2.45; live x2.58, history x2.27), tens -1/-2 41/285
    vs 19.3 (x2.12); cut changes were below chance."""
    global NEAR_LOG
    keep = NEAR_LOG
    NEAR_LOG = STEP_LOG
    try:
        return near8_live(series_round, res, entry)
    finally:
        NEAR_LOG = keep


CW3_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rrr_records', 'closeweak3_live.jsonl')


def closeweak3_live(series_round, res=None, entry=None):
    """CLOSE weak 3 live log (user 2026-11-11, Z70-Z75 'open and close from weak'): the 3 weakest CLOSE
    digits.  419 logged rounds: weakest 3 positions 30% vs strongest 3 32% (chance 30%) - watch only."""
    recs = [json.loads(l) for l in open(CW3_LOG)] if os.path.exists(CW3_LOG) else []
    if entry:
        recs = [r for r in recs if r['round'] != entry['round']] + [entry]
    if res is not None:
        for r in recs:
            if r['round'] == series_round:
                r['result'] = res
    with open(CW3_LOG, 'w') as fh:
        fh.write(''.join(json.dumps(r) + '\n' for r in recs))
    done = [r for r in recs if r.get('result') is not None]
    cur = next((r for r in recs if r['round'] == series_round), None)
    return cur, f"{sum(r['result'] % 10 in r['digits'] for r in done)} of {len(done)} (chance 30%)"


OS4_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rrr_records', 'openstrong4_live.jsonl')


def openstrong4_live(series_round, res=None, entry=None):
    """OPEN-STRONG 4 live log (user 2026-11-11, Z61): STRONG 20 numbers with tens = OPEN digit,
    OCJP rank order, first 4 (DataProcessing._open_strong4).  Z pages 7 of 60 vs 2.4; X/Y not confirmed."""
    global NEAR_LOG
    keep = NEAR_LOG
    NEAR_LOG = OS4_LOG
    try:
        return near8_live(series_round, res, entry)
    finally:
        NEAR_LOG = keep


MFAM_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rrr_records', 'masterfam_live.jsonl')


def masterfam_live(series_round, res=None, entry=None):
    """MASTER family live log (user 2026-11-11, Z30: MASTER 14 and result 96 same family).
    tools/f4_family_study.py: low-repeat charts 32 of 267 vs chance 19.9 (x1.6); normal charts at chance."""
    recs = [json.loads(l) for l in open(MFAM_LOG)] if os.path.exists(MFAM_LOG) else []
    if entry:
        recs = [r for r in recs if r['round'] != entry['round']] + [entry]
    if res is not None:
        for r in recs:
            if r['round'] == series_round:
                r['result'] = res
    with open(MFAM_LOG, 'w') as fh:
        fh.write(''.join(json.dumps(r) + '\n' for r in recs))
    done = [r for r in recs if r.get('result') is not None]
    cur = next((r for r in recs if r['round'] == series_round), None)
    return cur, f"{sum(r['result'] in r['nums'] for r in done)} of {len(done)} (chance {sum(len(r['nums']) for r in done) / 100:.2f})"


def strongest_section(md, label, k=4, avoid=None):
    """The same ⭕ view for the CURRENT page (user 2026-11-10, screenshot Z23): before the result
    is known, the numbers standing in the most places of this page, each with its places and how
    many places its one-step neighbours hold.  Display only - not a prediction."""
    places = {}
    for place, v, t, op in _scan(md):
        places.setdefault(v, [])
        if place not in places[v]:
            places[v].append(place)
    if not places:
        return ''
    # low tens-repeat chart: the EP's tens digit is left out, as in FINAL 4 (DataProcessing._tens_avoid)
    top = sorted((v for v in places if avoid is None or v // 10 != avoid), key=lambda v: (-len(places[v]), v))[:k]
    STRONGEST[:] = top
    rows = []
    for v in top:
        nb = sum(len(places.get(u, [])) for u in _near(v) - {v})
        rows.append(f"| {RING}**{v:02d}** | {len(places[v])} | {nb} | {' · '.join(places[v])} |")
    return (f"\n## {RING} Strongest on the {label} page (the {k} numbers in the most places; no result yet)\n"
            + (f"EP tens {avoid} left out (this chart repeats tens < 6%).\n\n" if avoid is not None else '')
            + f"| Number | Places | Near places (one step) | Where |\n|---|---|---|---|\n" + '\n'.join(rows) + '\n')


def render(md, width=None):
    """Terminal view: every markdown table becomes a box whose top bar names the
    EP and ROOT with their operations (user 2026-11-09), taken from the heading above."""
    B, N = '\x1b[1m', '\x1b[0m'
    bold = lambda s: re.sub(r'\*\*(.+?)\*\*', B + r'\1' + N, s)
    plain = lambda s: s.replace('**', '') + ' ' * sum(s.count(w) for w in WIDE)   # ⭕ and colour squares are 2 columns wide
    W = min(width or _cols(), 230) - 1
    out, tbl = [], []
    title = ['']
    def flush():
        if not tbl:
            return
        rows = [[c.strip() for c in r.strip().strip('|').split('|')] for r in tbl if not re.match(r'^\|[-|]+\|$', r.strip())]
        w = [max(len(plain(r[k])) for r in rows) for k in range(len(rows[0]))]
        t = title[0]
        # fit the box inside the terminal (user paste X33: wide rows wrapped and
        # overwrote each other): shrink the widest column, cells wrap inside it
        while 2 + sum(x + 3 for x in w) + 1 > W and max(w) > 6:
            w[w.index(max(w))] -= 1
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
            # wrap by screen width: each 2-column mark becomes two private chars while wrapping
            enc = lambda s: functools.reduce(lambda a, kw: a.replace(kw[1], chr(0xE000 + kw[0]) + '\ue0ff'), enumerate(WIDE), s)
            dec = lambda s: functools.reduce(lambda a, kw: a.replace(chr(0xE000 + kw[0]) + '\ue0ff', kw[1]), enumerate(WIDE), s)
            parts = [[c] if len(plain(c)) <= w[i] else [dec(x.replace('\x00', ' ')) for x in textwrap.wrap(enc(c.replace('**', '')).replace(' (', '\x00('), w[i], break_on_hyphens=False)] or [''] for i, c in enumerate(r)]
            for j in range(max(len(x) for x in parts)):
                cells = [x[j] if j < len(x) else '' for x in parts]
                out.append('  │' + '│'.join(' ' + bold(c) + ' ' * (w[i] - len(plain(c)) + 1) for i, c in enumerate(cells)) + '│')
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
            out += ['  ' + bold(x) for x in textwrap.wrap(ln, min(190, W - 4))]
        else:
            out.append('')
    flush()
    return '\n'.join(out)


# 5 stars (red, blue, green, yellow, white): the local output window starts after this
# line, with the same tables and order as the chat reply (user 2026-11-09).
FIVE_STARS = '  ' + '  '.join(f'\033[1;{c}m★\033[0m' for c in (31, 34, 32, 33, 97))


def _label_from_datasets(text):
    """Round label (e.g. Z9) of a local run: the rrr_datasets/<s><n>.txt with the same numbers."""
    import glob
    want = re.findall(r'\d\d|\*\*', text)
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rrr_datasets')
    for f in sorted(glob.glob(os.path.join(base, '*.txt')), key=os.path.getmtime, reverse=True):
        m = re.match(r'([a-z]+)(\d+)\.txt$', os.path.basename(f))
        if m and re.findall(r'\d\d|\*\*', open(f).read()) == want:
            return f'{m.group(1).upper()}{m.group(2)}'
    return ''


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
        label = f'{m.group(1).upper()}{m.group(2)}' if m else _label_from_datasets(text)
    jobs = [_run(prev_text), _run(prev_text, dump=True), _run(text), _run(text, dump=True)]
    for k, (p, _) in enumerate(jobs):
        p.stdin.write(_feed(prev_text) if k < 2 else _feed(text)); p.stdin.close()
    prevL, prevD, curL, curD = [_finish(p, j) for p, j in jobs]
    md = build(label, parse(prevL), prevD, parse(curL), res, curD)
    # red rings on the previous page's numbers that matched / were one step from the result
    # (local runs too: the previous page is rrr_outputs/<round>.md of the result's round)
    prev_md = prev_lab = None
    if md_out and res is not None:
        m = re.match(r'(.*?)([a-z]+)(\d+)\.md$', md_out)
        if m:
            prev_md = f"{m.group(1)}{m.group(2)}{int(m.group(3)) - 1}.md"
            prev_lab = f"{m.group(2).upper()}{int(m.group(3)) - 1}"
    elif res is not None and re.match(r'[A-Z]+\d+$', label or ''):
        prev_md = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rrr_outputs', label.lower() + '.md')
        prev_lab = label
    if True:
        if prev_md and os.path.exists(prev_md):
            sec = ring_section(open(prev_md).read(), int(res), prev_lab)
            oc_, olv = oph_live(label, int(res))
            if oc_:
                sec += ''.join(f"\n{RING} OP HISTORY {k} of the {prev_lab} page ({' '.join(f'{v:02d}' for v in oc_[k])}): "
                               f"{'✓ held' if int(res) in oc_[k] else '✗'} {res:02d} · live {olv[k]} (chance 4%)\n" for k in ('A', 'B', 'C') if k in oc_)
            nr, nlv = near8_live(label, int(res))
            if nr:
                sec += (f"\n{RING} NEAR 8 of the {prev_lab} page ({' '.join(f'{v:02d}' for v in nr['nums'])}): "
                        f"{'✓ held' if int(res) in nr['nums'] else '✗'} {res:02d} · live {nlv}\n")
            ts_, tlv = tensstep8_live(label, int(res))
            if ts_:
                sec += (f"\n{RING} TENS-STEP 8 of the {prev_lab} page ({' '.join(f'{v:02d}' for v in ts_['nums'])}): "
                        f"{'✓ held' if int(res) in ts_['nums'] else '✗'} {res:02d} · live {tlv}\n")
            mf, mlv = masterfam_live(label, int(res))
            if mf:
                sec += (f"\n{RING} MASTER {mf['master']:02d} family of the {prev_lab} page ({' '.join(f'{v:02d}' for v in mf['nums'])}): "
                        f"{'✓ held' if int(res) in mf['nums'] else '✗'} {res:02d} · live {mlv}\n")
            cur, lv = strongest_live(label, int(res))
            if cur:
                sec += (f"\n{RING} strongest 4 of the {prev_lab} page ({' '.join(f'{v:02d}' for v in cur['nums'])}): "
                        f"{'✓ held' if int(res) in cur['nums'] else '✗'} {res:02d} · live {lv}\n")
            i = md.find('\nThe earlier ')
            md = md[:i] + '\n' + sec + md[i:] if i >= 0 else md + sec
    # the same ⭕ view for the current page, just before the OCJP FINAL 4 section
    cur_lab = re.sub(r'\d+$', lambda m: str(int(m.group()) + 1), label) if re.search(r'\d+$', label or '') else 'current'
    mcw = re.search(r'^\*\*CLOSE weak 3\*\* \([^)]*\)[^:]*: ([\d ·]+)', md, re.M)
    if mcw and re.search(r'\d+$', label or ''):
        closeweak3_live(None, entry={'round': cur_lab, 'digits': [int(x) for x in re.findall(r'\d', mcw.group(1))]})
    mo4 = re.search(r'^\*\*OPEN-STRONG 4\*\* \(STRONG 20[^:]*: (.*)', md, re.M)
    if mo4 and re.search(r'\d+$', label or ''):
        openstrong4_live(None, entry={'round': cur_lab, 'nums': [int(x) for x in re.findall(r'\*\*(\d\d)\*\*', mo4.group(1).split(' (live')[0])]})
    fl = [int(x) for x in re.findall(r'(?<![\d*])\d\d(?![\d*])', text)]
    rep_ = sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / max(1, len(fl) - 1)
    sec = strongest_section(md, cur_lab, avoid=fl[-1] // 10 if len(fl) > 300 and rep_ < 0.06 else None)
    if STRONGEST and re.search(r'\d+$', label or ''):
        strongest_live(None, entry={'round': cur_lab, 'nums': STRONGEST})
    # OP HISTORY 4 (models A / B), just before the OCJP FINAL 4 section
    oh = op_history(fl)
    if oh:
        _, lv0 = oph_live(None)
        frm = lambda k, b: {'A': f'op into EP {fl[-2]:02d}→{fl[-1]:02d}', 'B': f'ROOT op {fl[-1]:02d}→{b:02d}',
                            'C': 'best 4 direct EP/ROOT rules'}[k]
        rows_ = [f"| {k} | {frm(k, b)} | "
                 + ' · '.join(f"**{n:02d}** ({o})" for n, o in L4) + f" | {lv0[k]} |" for k, (b, L4) in oh.items()]
        sec2 = (f"\n## OP HISTORY 4: the ops history says come next (on {cur_lab})\n"
                f"Learned from this chart's past: after an op, how often the next op was the same, sign flipped, ±1/±2, cut switched, or crossed xy/yx. "
                f"A applies it on the EP, B on the ROOT. Walk-forward 5,778 low-repeat rounds: top 4 held 5.1% (A) / 4.9% (B) vs chance 4.4% — close to chance. C = the 4 best of 200 fixed rules (EP or ROOT op on EP or ROOT, as is or crossed, each side same / cut sw / sign / ±1): 1.33–1.44% each vs ~1.1%.\n\n"
                f"| Model | From | 4 numbers (op) | Live |\n|---|---|---|---|\n" + '\n'.join(rows_) + '\n')
        k3 = md.find('\n## OCJP FINAL 4 with operations')
        md = md[:k3] + '\n' + sec2 + md[k3:] if k3 >= 0 else md + sec2
        if re.search(r'\d+$', label or ''):
            oph_live(None, entry={'round': cur_lab, **{k: [n for n, _ in L4] for k, (b, L4) in oh.items()}})
    # MASTER family under the FINAL 4 table (low tens-repeat charts only; normal charts at chance)
    mm = re.search(r'\| \*\*MASTER = 1\*\* \| \*\*(\d\d)\*\*', md)
    av_ = fl[-1] // 10 if len(fl) > 300 and rep_ < 0.06 else None
    if mm and av_ is not None:
        mv = int(mm.group(1)); fam = FAMILY[mv]
        mem = sorted(v for v, f in FAMILY.items() if f == fam and v // 10 != av_)
        flab = f"{fam}-family" if fam[0].isdigit() else fam
        line = (f"\n**MASTER {mv:02d} family** ({flab}, EP tens {av_} out): {' '.join(f'{v:02d}' for v in mem)}"
                f" (logged low-repeat rounds 32 of 267 vs chance 19.9; live {masterfam_live(None)[1]})\n")
        # NEAR 8: MASTER and #2 with one digit +-1 (tens or units), FINAL 4 and EP tens left out
        m2 = re.search(r'\n\| 2 \| \*\*(\d\d)\*\*', md)
        f4n = [int(x) for x in re.findall(r'\n\| (?:\*\*MASTER = 1\*\*|[234]) \| \*\*(\d\d)\*\*', md)]
        if m2:
            nb = lambda n: [((n // 10 + d) % 10) * 10 + n % 10 for d in (1, -1)] + [(n // 10) * 10 + (n % 10 + d) % 10 for d in (1, -1)]
            near = []
            for base in (mv, int(m2.group(1))):
                for v in nb(base):
                    if v not in near and v not in f4n and v // 10 != av_:
                        near.append(v)
            line += (f"\n**NEAR 8** (MASTER {mv:02d} and #2 {int(m2.group(1)):02d}, one digit ±1): {' '.join(f'{v:02d}' for v in near)}"
                     f" (logged low-repeat rounds 30 of 281 vs chance 19.6; live {near8_live(None)[1]})\n")
            if re.search(r'\d+$', label or ''):
                near8_live(None, entry={'round': cur_lab, 'nums': near})
        # TENS-STEP 8: every FINAL 4 number with the tens -1, then with the tens -2
        if f4n:
            st8 = []
            for d in (9, 8):
                for n in f4n:
                    v = ((n // 10 + d) % 10) * 10 + n % 10
                    if v not in st8 and v not in f4n and v // 10 != av_:
                        st8.append(v)
            line += (f"\n**TENS-STEP 8** (FINAL 4 with the tens −1, then −2): {' '.join(f'{v:02d}' for v in st8)}"
                     f" (logged low-repeat rounds: tens −1 24 of 285 vs 9.8, tens −1/−2 41 of 285 vs 19.3; live {tensstep8_live(None)[1]})\n")
            if re.search(r'\d+$', label or ''):
                tensstep8_live(None, entry={'round': cur_lab, 'nums': st8})
        k2 = md.find('\n### FINAL 8')
        md = md[:k2] + '\n' + line + md[k2:] if k2 >= 0 else md + line
        if re.search(r'\d+$', label or ''):
            masterfam_live(None, entry={'round': cur_lab, 'master': mv, 'nums': mem})
    k = md.find('\n## OCJP FINAL 4 with operations')
    md = md[:k] + '\n' + sec + md[k:] if k >= 0 else md + sec
    if md_out:
        with open(md_out, 'w') as fh:
            fh.write(md)
    print('\n' + FIVE_STARS)
    print(render(md))


if __name__ == '__main__':
    main()
