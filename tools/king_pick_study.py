"""KING PICK study (user AE72 'game changer king pick each time'): one number per round.
Logged rounds rrr_records/live.jsonl; candidates scored per half, chance 1 in 100.
  python3 tools/king_pick_study.py"""
import json, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
R = [r for r in map(json.loads, open('rrr_records/live.jsonl')) if r.get('result') is not None and r.get('ranked')]
def nums(l):
    out = []
    for x in l if isinstance(l, list) else []:
        v = x[0] if isinstance(x, (list, tuple)) else x
        if isinstance(v, int): out.append(v)
    return out
def most_lists(r, keys=None):
    rk = nums(r['ranked']); c = {}
    for k, l in r['lists'].items():
        if keys and k not in keys: continue
        for v in set(nums(l)): c[v] = c.get(v, 0) + 1
    return max(c, key=lambda v: (c[v], -(rk.index(v) if v in rk else 999))) if c else None
def oc_master(r):
    rk = nums(r['ranked'])[:10]; o = [0]*10; u = [0]*10
    for i, v in enumerate(rk): o[v//10] += 10-i; u[v%10] += 10-i
    return max(range(10), key=lambda d:(o[d],-d))*10 + max(range(10), key=lambda d:(u[d],-d))
C = {'MASTER (plain #1)': lambda r: nums(r['ranked'])[0],
     'OPEN #1 x CLOSE #1': oc_master,
     'in most tables (all)': lambda r: most_lists(r),
     'in most main tables': lambda r: most_lists(r, {'strong','rec','yx','wide','ncspec','table','charrow','hot'}),
     'STRONG 20 #1': lambda r: (nums(r['lists'].get('strong', [])) or [None])[0],
     'EP repeat (ARROW)': lambda r: r['after']}
h = len(R) // 2
print(f"{len(R)} logged rounds; chance {h/100:.1f} per half")
for nm, f in C.items():
    a = sum(f(r) == r['result'] for r in R[:h]); b = sum(f(r) == r['result'] for r in R[h:])
    ae = [r for r in R if r['round'].startswith('AE')]
    print(f"{nm:22s} {a:3d} | {b:3d}   AE {sum(f(r)==r['result'] for r in ae)} of {len(ae)}")
