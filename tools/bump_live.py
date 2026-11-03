"""Bump the RRR_LIVE counters in DataProcessing.py for one recorded round.

python3 tools/bump_live.py <round> [extra hit keys...]

Reads the round's line in rrr_records/live.jsonl.  '_rounds' keys go up by 1
for every list that is shown every round, and for each user/my rule that had
a number this round; '_hits' keys go up for every list that held the result
(held_by + ladder).  Extra keys (e.g. rrr3_hits) can be passed by hand."""
import sys, os, re, json
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
rnd, extra = sys.argv[1], sys.argv[2:]
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
    m = re.search(rf"'{k}': (\d+)", block)
    if not m:
        print('missing key', k); continue
    block = block[:m.start(1)] + str(int(m.group(1)) + n) + block[m.end(1):]
open('DataProcessing.py', 'w').write(src[:a] + block + src[b:])
print('bumped:', ', '.join(f'{k}+{n}' for k, n in up.items() if k.endswith('hits') or n > 1))
