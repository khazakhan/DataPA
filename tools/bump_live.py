"""Bump the RRR_LIVE counters in DataProcessing.py for one recorded round.

python3 tools/bump_live.py <round> [extra hit keys...]

Reads the round's line in rrr_records/live.jsonl.  '_rounds' keys go up by 1
for every list that is shown every round, and for each user/my rule that had
a number this round; '_hits' keys go up for every list that held the result
(held_by + ladder).  Extra keys (e.g. rrr3_hits) can be passed by hand."""
import sys, os, re, json
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# --undo: take back a round's bump (e.g. a corrected result); --skip=k1,k2 leaves
# keys alone (keys that did not exist when the round was first bumped)
args = sys.argv[1:]
UNDO = '--undo' in args
SKIPK = set(next((a.split('=', 1)[1].split(',') for a in args if a.startswith('--skip=')), []))
args = [a for a in args if not a.startswith('--')]
rnd, extra = args[0], args[1:]
import io, contextlib
sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
rec = [json.loads(l) for l in open('rrr_records/live.jsonl') if json.loads(l)['round'] == rnd][-1]
res, lists = rec['result'], rec['lists']
ALWAYS = ['results', 'table_rounds', 'declared', 'rrr3_rounds', 'rrr3_rec_rounds', 'rrr3_same_rounds',
          'rrr3_wide_rounds', 'rrr3_yx_rounds', 'rrr3_strong_rounds', 'rrr3_same2_rounds', 'rrr3_turn_rounds',
          'rrr3_sameyx_rounds', 'power_rounds', 'rrr3_final4_rounds', 'rrr3_master_rounds', 'rrr3_star1_rounds',
          'rrr3_lastop4_rounds', 'rrr3_lastop8_rounds', 'rrr3_onerow_rounds', 'rrr3_onerow5_rounds',
          'rrr3_prime4fam_rounds', 'rrr3_prime4rev_rounds', 'rrr3_crossgrid_rounds', 'rrr3_finder_rounds',
          'rrr3_prime4_rounds', 'rrr3_prime10_rounds', 'rrr3_prime8_rounds'] + \
         [f'rrr3_lad_{k}_rounds' for k in rec['ladder']]
up = {k: 1 for k in ALWAYS}
for k, v in lists.items():
    if re.fullmatch(r'rule\d+', k) and v:
        up[f'rrr3_{k}_rounds'] = 1
HIT = {'rec': 'rrr3_rec_hits', 'strong': 'rrr3_strong_hits', 'yx': 'rrr3_yx_hits', 'wide': 'rrr3_wide_hits',
       'table': 'table_hits', 'finder': 'rrr3_finder_hits', 'prime10': 'rrr3_prime10_hits',
       'prime4fam': 'rrr3_prime4fam_hits', 'prime4rev': 'rrr3_prime4rev_hits', 'crossgrid': 'rrr3_crossgrid_hits'}
hits = [HIT[h] for h in rec['held_by'] if h in HIT]
hits += [f'rrr3_{h}_hits' for h in rec['held_by'] if re.fullmatch(r'rule\d+', h)]
hits += [f'rrr3_lad_{k}_hits' for k, v in rec['ladder'].items() if res in v]
up['rrr3_twostar_rounds'] = 1
up['rrr3_f4yx_rounds'] = 1
_e = rec['ep']; _f4yx = set()
for v in rec['ranked'][:4]:
    _xo, _yo = D.find_op(_e // 10, v // 10), D.find_op(_e % 10, v % 10)
    _f4yx.add(D.apply_op(_e // 10, _yo) * 10 + D.apply_op(_e % 10, _xo))
if res in _f4yx: hits.append('rrr3_f4yx_hits')
if res in rec['ranked'][:2]: hits.append('rrr3_twostar_hits')
if res in rec['ranked'][:4]: hits.append('rrr3_final4_hits')
if rec['ranked'][:1] == [res]: hits.append('rrr3_master_hits')
if res in rec['prime10'][:4]: hits.append('rrr3_prime4_hits')
if res in rec['prime10'][:8]: hits.append('rrr3_prime8_hits')
if res in rec['lastop'][:4]: hits.append('rrr3_lastop4_hits')
if res in rec['lastop'][:8]: hits.append('rrr3_lastop8_hits')
# *xy / *yx columns + outer-op move (on test from S27, 2026-11-04)
import io, contextlib, sys
sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
ep = rec['ep']; star = set()
for row in rec['rows']:
    sx, sy = D._star_ops(AB[row['old'][0]], AB[row['old'][1]])
    star |= {D.apply_op(ep // 10, sx) * 10 + D.apply_op(ep % 10, sy), D.apply_op(ep // 10, sy) * 10 + D.apply_op(ep % 10, sx)}
up['rrr3_starcol_rounds'] = 1
tilde = set()
for row in rec['rows']:
    tx, ty = D._tilde_ops(AB[row['old'][0]], AB[row['old'][1]])
    tilde |= {D.apply_op(ep // 10, tx) * 10 + D.apply_op(ep % 10, ty), D.apply_op(ep // 10, ty) * 10 + D.apply_op(ep % 10, tx)}
up['rrr3_tilde_rounds'] = 1
if res in tilde: hits.append('rrr3_tilde_hits')
# old xy/yx + newold xy / oldnew yx columns (user 2026-11-05, live from S38)
oldc = set()
for row in rec['rows']:
    _ox, _oy, _nx = AB[row['old'][0]], AB[row['old'][1]], AB[row['new'][0]]
    for _p, _q in ((_ox, _oy), (_nx, _oy)):
        oldc |= {D.apply_op(ep // 10, _p) * 10 + D.apply_op(ep % 10, _q), D.apply_op(ep // 10, _q) * 10 + D.apply_op(ep % 10, _p)}
up['rrr3_oldcols_rounds'] = 1
if res in oldc: hits.append('rrr3_oldcols_hits')
# oldy·newy± / oldx·newx± columns (user 2026-11-05, live from S42)
sfl = set()
for row in rec['rows']:
    _ox, _oy, _nx, _ny = AB[row['old'][0]], AB[row['old'][1]], AB[row['new'][0]], AB[row['new'][1]]
    sfl |= {D.apply_op(ep // 10, _oy) * 10 + D.apply_op(ep % 10, D.SIGN_FLIP[_ny]),
            D.apply_op(ep // 10, _ox) * 10 + D.apply_op(ep % 10, D.SIGN_FLIP[_nx])}
up['rrr3_sflip_rounds'] = 1
if res in sfl: hits.append('rrr3_sflip_hits')
# FINAL 4 BOOSTER (user 2026-11-05, live from S58): cut removed / added, signs flipped, steps +-1
up['rrr3_booster_rounds'] = 1
if res in D._f4_booster_set(ep, rec['ranked'][:4]): hits.append('rrr3_booster_hits')
# ALL COMBINED (FINAL 4 + yx + booster, dedup with counts), live from S58
_cb = dict(D._f4_combined_counts(ep, rec['ranked'][:4]))
up['rrr3_comb_rounds'] = 1; up['rrr3_comb2_rounds'] = 1
if res in _cb: hits.append('rrr3_comb_hits')
if _cb.get(res, 0) >= 2: hits.append('rrr3_comb2_hits')
# ALL + booster of booster (user 2026-11-05, live from S61)
up['rrr3_allbb_rounds'] = 1
if res in D._f4_all_bb(ep, rec['ranked'][:4]): hits.append('rrr3_allbb_hits')
# BEST FORMS (user 2026-11-07, live from T6): 4 best xy/yx forms, old ops on ROOT
_AB = {v: k for k, v in D.OP_ABBREV.items()}
up['rrr3_bestform_rounds'] = 1
if res in [n for n, *_ in D._best_forms(ep, [(r_['pos'], _AB[r_['old'][0]], _AB[r_['old'][1]]) for r_ in rec['rows']])]:
    hits.append('rrr3_bestform_hits')
# FINAL 8 (user 2026-11-07, live from U4): FINAL 4 + PRIME 8 adds, filled by ranking
up['rrr3_final8_rounds'] = 1
_flat = [int(x) for x in open(rec['dataset']).read().split() if x.isdigit()]
if res in D._final8(rec['ranked'][:4], rec['prime10'], rec['ranked'], _flat): hits.append('rrr3_final8_hits')
# Rule 28 picks (auto from U15; before that the counter was bumped by hand)
if rec.get('r28'):
    up['rrr3_rule28_rounds'] = 1
    if res in rec['r28']: hits.append('rrr3_rule28_hits')
# OPEN / CLOSE digit (user 2026-11-07, live from U15): rank-weighted tens / units of OCJP top 10
D._RRR3_PREV['flat'] = [int(x) for x in open(rec['dataset']).read().split() if x.isdigit()]  # step OPEN needs the chart (fix 2026-11-09)
_oo, _cc = D._open_close(rec['ranked'])
up['rrr3_open1_rounds'] = 1; up['rrr3_close1_rounds'] = 1
if res // 10 == _oo[0]: hits.append('rrr3_open1_hits')
if res // 10 in _oo: hits.append('rrr3_open3_hits')
if res % 10 == _cc[0]: hits.append('rrr3_close1_hits')
if res % 10 in _cc: hits.append('rrr3_close3_hits')
# EPROOTGEN (user 2026-11-07, live from U15): EP op + ROOT op crossed, widened to 20
_tg = [int(x) for x in re.findall(r'(?<![\d*])\d{1,2}(?![\d*])', open(rec['dataset']).read())]
if len(_tg) >= 2:
    up['rrr3_eprootgen_rounds'] = 1
    if res in [v for v, *_ in D._eprootgen(_tg[-2], _tg[-1], ep)]: hits.append('rrr3_eprootgen_hits')
# 80-NUMBER NET (user 2026-11-05, live from S61)
up['rrr3_net80_rounds'] = 1
if res in (rec.get('net80') or D._f4_net80(ep, rec['ranked'][:4], rec['ranked'])): hits.append('rrr3_net80_hits')
# after·LAST old xy (user origin-op idea 2026-11-05, live from S54)
_tk = [int(x) for x in open(rec['dataset']).read().split() if x.isdigit()]
_lr = [row for row in rec['rows'] if row['last']]
if _lr:
    _lox, _loy = AB[_lr[-1]['old'][0]], AB[_lr[-1]['old'][1]]
    up['rrr3_afterold_rounds'] = 1
    if res == D.apply_op(_tk[-1] // 10, _lox) * 10 + D.apply_op(_tk[-1] % 10, _loy): hits.append('rrr3_afterold_hits')
if res in star: hits.append('rrr3_starcol_hits')
ep_rows = [row for row in rec['rows'] if row['a'] == ep]
if ep_rows:
    up['rrr3_eprow_rounds'] = 1
    ep_set = set()
    for row in ep_rows:
        nx, ox = AB[row['new'][0]], AB[row['old'][0]]
        ep_set |= {D.apply_op(ep // 10, nx) * 10 + D.apply_op(ep % 10, ox), D.apply_op(ep // 10, ox) * 10 + D.apply_op(ep % 10, nx)}
    if res in ep_set: hits.append('rrr3_eprow_hits')
tok = [int(x) for x in open(rec['dataset']).read().split() if x.isdigit()]
om = D._outer_move(ep, tok[-2], tok[-1])
lr = [row for row in rec['rows'] if row['last']]
if lr:
    up['rrr3_oflip_rounds'] = 1
    ofx = D.SIGN_FLIP[D.find_op(tok[-2] // 10, tok[-1] // 10)]; ofy = D.SIGN_FLIP[AB[lr[-1]['new'][1]]]
    if D.apply_op(ep // 10, ofx) * 10 + D.apply_op(ep % 10, ofy) == res: hits.append('rrr3_oflip_hits')
if om:
    up['rrr3_outer_rounds'] = 1
    if om[0] == res: hits.append('rrr3_outer_hits')
for k in hits + extra:
    up[k] = up.get(k, 0) + 1
src = open('DataProcessing.py').read()
a = src.index('RRR_LIVE = {'); b = src.index('\n}', a)
block = src[a:b]
for k, n in up.items():
    if k in SKIPK: continue
    if UNDO: n = -n
    m = re.search(rf"'{k}': (\d+)", block)
    if not m:
        print('missing key', k); continue
    block = block[:m.start(1)] + str(int(m.group(1)) + n) + block[m.end(1):]
open('DataProcessing.py', 'w').write(src[:a] + block + src[b:])
print('bumped:', ', '.join(f'{k}+{n}' for k, n in up.items() if k.endswith('hits') or n > 1))
