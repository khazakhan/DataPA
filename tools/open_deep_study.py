"""OPEN (tens) deep study (user AE58: 04 came, FINAL 4 had 54 = its tens cut).
Logged rounds rrr_records/live.jsonl (ranked = plain vote; after = EP, ep = ROOT; dataset = chart before result).
Each method gives a full 10-digit OPEN order; scored #1, top 2, top 3 per half.
  python3 tools/open_deep_study.py"""
import json, os, re
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
R = [r for r in map(json.loads, open('rrr_records/live.jsonl')) if r.get('result') is not None and r.get('ranked')]
_cache = {}
def chart(p):
    if p not in _cache:
        try: _cache[p] = [int(x) for x in re.findall(r'\b\d\d\b', open(p).read())]
        except Exception: _cache[p] = []
    return _cache[p]
def nums(l): return [x[0] if isinstance(x, (list, tuple)) else x for x in l if isinstance(x[0] if isinstance(x, (list, tuple)) else x, int)]
def ordr(s): return sorted(range(10), key=lambda d: (-s[d], d))
def m_vote(r, N=10):
    s = [0] * 10
    for i, v in enumerate(nums(r['ranked'])[:N]): s[v // 10] += N - i
    return ordr(s)
def m_cut1(r):   # OPEN #1, then its cut, then the rest of the vote order
    o = m_vote(r); c = (o[0] + 5) % 10
    return [o[0], c] + [d for d in o[1:] if d != c]
def m_step(fl, base):   # chart tens-step mode applied to a base tens digit
    t = [0] * 10
    for a, b in zip(fl, fl[1:]): t[(b // 10 - a // 10) % 10] += 1
    return ordr([t[(d - base) % 10] for d in range(10)])
def m_rootop(fl, root):  # what the tens did after earlier ROOT-tens occurrences
    s = [0] * 10
    for a, b in zip(fl, fl[1:]):
        if a // 10 == root // 10: s[b // 10] += 1
    return ordr(s)
def m_mix(r, fl):  # vote + chart step from EP (normalised)
    s = [0] * 10
    for i, v in enumerate(nums(r['ranked'])[:10]): s[v // 10] += 10 - i
    t = [0] * 10
    for a, b in zip(fl, fl[1:]): t[(b // 10 - a // 10) % 10] += 1
    e = fl[-1] // 10; S = sum(s) or 1; T = sum(t) or 1
    return ordr([s[d] / S + t[(d - e) % 10] / T for d in range(10)])
def m_recent(fl, n=30):  # most common tens in last n results
    s = [0] * 10
    for v in fl[-n:]: s[v // 10] += 1
    return ordr(s)
M = {'vote top10 (current)': lambda r, fl: m_vote(r), 'vote top20': lambda r, fl: m_vote(r, 20),
     'vote top40': lambda r, fl: m_vote(r, 40), '#1 + its cut': lambda r, fl: m_cut1(r),
     'chart step from EP': lambda r, fl: m_step(fl, fl[-1] // 10), 'chart step from ROOT': lambda r, fl: m_step(fl, r['ep'] // 10),
     'after ROOT tens': lambda r, fl: m_rootop(fl, r['ep']), 'after EP tens': lambda r, fl: m_rootop(fl, fl[-1]),
     'vote + EP step': m_mix, 'hot tens last 30': lambda r, fl: m_recent(fl)}
RR = [(r, chart(r['dataset'])) for r in R]
RR = [(r, fl) for r, fl in RR if len(fl) > 60]
h = len(RR) // 2
print(f"{len(RR)} logged rounds, halves {h} | {len(RR) - h}; chance #1 10%, top2 20%, top3 30%")
for nm, f in M.items():
    c = [[0, 0, 0], [0, 0, 0]]
    for i, (r, fl) in enumerate(RR):
        o = f(r, fl); t = r['result'] // 10; k = 0 if i < h else 1
        c[k][0] += o[0] == t; c[k][1] += t in o[:2]; c[k][2] += t in o[:3]
    print(f"{nm:22s} #1 {c[0][0]:3d} | {c[1][0]:3d}   top2 {c[0][1]:3d} | {c[1][1]:3d}   top3 {c[0][2]:3d} | {c[1][2]:3d}")
