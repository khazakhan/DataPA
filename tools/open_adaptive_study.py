"""Adaptive OPEN picker study (user AE61 'deep search, more strong pick').
Each round, every OPEN method gives a 10-digit order; the adaptive picker uses the method with the most
#1 hits over the last W rounds of the SAME series (walk-forward, no look-ahead).  Scored per half on the
logged rounds; also as FINAL 4 = adaptive OPEN x current CLOSE 4.
  python3 tools/open_adaptive_study.py"""
import json, os, re
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
exec(open('tools/open_deep_study.py').read().split("RR = [(r, chart")[0].split("os.chdir(")[0])
src = open('tools/open_deep_study.py').read()
exec(src[src.index("R = [r for r"):src.index("RR = [(r, chart")])
def close4(r):
    s = [0] * 10
    for i, v in enumerate(nums(r['ranked'])[:10]): s[v % 10] += 10 - i
    return ordr(s)[:4]
METH = {'vote': lambda r, fl: m_vote(r), 'vote last': lambda r, fl: m_vote(r)[::-1],
        'vote 2nd': lambda r, fl: m_vote(r)[1:] + m_vote(r)[:1], 'vote cut': lambda r, fl: [(d + 5) % 10 for d in m_vote(r)],
        'step EP': lambda r, fl: m_step(fl, fl[-1] // 10), 'after EP tens': lambda r, fl: m_rootop(fl, fl[-1]),
        'step ROOT': lambda r, fl: m_step(fl, r['ep'] // 10), 'mix': m_mix}
RR = [(r, chart(r['dataset'])) for r in R]; RR = [(r, fl) for r, fl in RR if len(fl) > 60]
for W in (10, 20, 30):
    hist = {}; out = []
    for r, fl in RR:
        s = re.match(r'[A-Z]+', r['round']).group(0); H = hist.setdefault(s, [])
        o = {k: f(r, fl)[0] for k, f in METH.items()}
        if len(H) >= 5:
            sc = {k: sum(h[k] for h in H[-W:]) for k in METH}
            best = max(METH, key=lambda k: (sc[k], k == 'vote'))
        else: best = 'vote'
        t = r['result'] // 10; c4 = close4(r)
        out.append((o[best] == t, o[best] == t and r['result'] % 10 in c4, o['vote'] == t, o['vote'] == t and r['result'] % 10 in c4, s))
        H.append({k: o[k] == t for k in METH})
    h = len(out) // 2
    f = lambda i, a, b: sum(x[i] for x in out[a:b])
    ae = [x for x in out if x[4] == 'AE']
    print(f"W={W}: adaptive OPEN #1 {f(0,0,h)} | {f(0,h,len(out))}  vs vote {f(2,0,h)} | {f(2,h,len(out))} (chance {h/10:.0f});"
          f"  FINAL 4 adaptive {f(1,0,h)} | {f(1,h,len(out))} vs current {f(3,0,h)} | {f(3,h,len(out))} (chance {h*.04:.1f});"
          f"  AE OPEN {sum(x[0] for x in ae)} vs {sum(x[2] for x in ae)} of {len(ae)}")
