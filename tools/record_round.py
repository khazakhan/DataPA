"""Record one live RRR round for the picker study.

python3 tools/record_round.py <round> <dataset before result> <result> [user pick numbers...]

Appends one JSON line to rrr_records/live.jsonl with: EP, after, every RRR
row (old/new ops), every list the page showed (FINAL 4, PRIME 10, STRONG 20,
rules, finder, ONE ROW PICK ...), the result, its op on the EP, every row
change that makes it (0/1/2 changes), which lists held it, and the user pick.
Re-recording a round replaces its line."""
import sys, io, os, re, json, contextlib
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.'); sys.path.insert(0, 'tools')
from replay_collect import collect
import DataProcessing as D

rnd, ds, res = sys.argv[1], sys.argv[2], int(sys.argv[3])
pick = [int(x) for x in sys.argv[4:]]
lists = collect(ds)                                     # runs the page once
out = io.StringIO()
with contextlib.redirect_stdout(out):
    D.run(open(ds), None, None)
txt = re.sub(r'\x1b\[[0-9;]*m', '', out.getvalue())
ep = D._RRR_ASK['ep']; ex, ey = ep // 10, ep % 10
after = int(open(ds).read().split()[-1])

def t(o, f):
    if 'C' in f: o = D.KK_CUT_TOGGLE[o]
    if 'F' in f: o = D.SIGN_FLIP[o]
    return o
rows, makers = [], []
for pos, a, b, ox, oy, nx, ny, mark in D._RRR_ASK['rows']:
    rows.append(dict(pos=pos, a=a, b=b, old=[D.OP_ABBREV[ox], D.OP_ABBREV[oy]],
                     new=[D.OP_ABBREV[nx], D.OP_ABBREV[ny]], last=mark == 'LAST'))
    for nm, (xo, yo) in {'new': (nx, ny), 'old': (ox, oy)}.items():
        for lab, (p, q) in {'xy': (xo, yo), 'yx': (yo, xo)}.items():
            for fx in ('', 'F', 'C', 'FC'):
                for fy in ('', 'F', 'C', 'FC'):
                    x2, y2 = t(p, fx), t(q, fy)
                    if D.apply_op(ex, x2) * 10 + D.apply_op(ey, y2) == res:
                        makers.append(dict(pos=pos, src=f"{a:02d}->{b:02d}", ops=nm, read=lab, x=fx or '-',
                                           y=fy or '-', changes=len(fx) + len(fy)))
# ONE ROW PICK box
one = {}
i = txt.find('ONE ROW PICK')
if i >= 0:
    ls = txt[i:].split('\n')
    m = re.search(r'\[\w*?(\d+)\]', ls[1]); w = re.search(r'why: ([^)]*)', ls[1])
    one = dict(pos=int(m.group(1)) if m else None, why=w.group(1) if w else '',
               lines={re.split(r'\s{2,}', l.strip(' ┃│'))[0]: int(re.search(r'\s(\d\d) \(', l).group(1))
                      for l in ls[2:8] if re.search(r'\s(\d\d) \(', l)})
prime = list(D._RRR3_PREV.get('prime', []))
rec = dict(round=rnd, dataset=ds, after=after, ep=ep, result=res,
           result_op=f"{D.OP_ABBREV[D.find_op(ex, res // 10)]}/{D.OP_ABBREV[D.find_op(ey, res % 10)]}",
           rows=rows, makers=sorted(makers, key=lambda m: m['changes']),
           lists={k: v for k, v in lists.items() if k != 'rk'}, ranked=lists.get('rk', []),
           prime10=prime, prime4fam=list(D._RRR3_PREV.get('prime4fam', [])), prime4rev=list(D._RRR3_PREV.get('prime4rev', [])), ladder=dict(D._RRR3_PREV.get('ladder', {})), one_row=one, user_pick=pick)
rec['held_by'] = sorted(k for k, v in rec['lists'].items() if res in v) + \
    (['prime10'] if res in prime else []) + (['prime4fam'] if res in rec['prime4fam'] else []) + (['prime4rev'] if res in rec['prime4rev'] else []) + (['one_row'] if res in one.get('lines', {}).values() else []) + \
    (['user_pick'] if res in pick else [])
p = 'rrr_records/live.jsonl'
old = [l for l in (open(p).read().splitlines() if os.path.exists(p) else []) if json.loads(l)['round'] != rnd]
open(p, 'w').write('\n'.join(old + [json.dumps(rec)]) + '\n')
print(f"{rnd}: EP {ep:02d} after {after:02d} -> {res:02d} ({rec['result_op']}); "
      f"makers {len(makers)} (min changes {min((m['changes'] for m in makers), default='-')}); held by: {', '.join(rec['held_by']) or 'none'}")
