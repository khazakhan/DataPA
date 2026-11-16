"""Live audit (2026-11-17, after AC122, user: 'get by strong and accurate matched fires'):
per fired list, hits vs chance (= set size / 100) on all live rounds, and hit rate
by AGREEMENT (how many of the main lists hold a number).  python3 tools/list_lift_audit.py"""
import json, collections
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None and r.get('lists')]
print('rounds', len(L))
st = collections.defaultdict(lambda: [0, 0.0, 0])
for r in L:
    for k, v in r['lists'].items():
        s = set(v)
        if s:
            st[k][0] += r['result'] in s; st[k][1] += len(s) / 100; st[k][2] += 1
for k, (h, e, n) in sorted(st.items(), key=lambda x: -x[1][0] / max(x[1][1], 1e-9)):
    print(f'{k:8s} hits {h:4d} chance {e:6.1f} lift {h / e:4.2f} rounds {n}')
by = collections.defaultdict(lambda: [0, 0])
MAIN = ('strong', 'rec', 'yx', 'wide', 'ncspec', 'table', 'charrow', 'hot')
for r in L:
    c = collections.Counter(v for k in MAIN for v in set(r['lists'].get(k, [])))
    for v in range(100):
        by[c[v]][0] += 1; by[c[v]][1] += r['result'] == v
print('lists agreeing -> numbers, hits, rate % (chance 1%)')
for k in sorted(by):
    print(k, by[k][0], by[k][1], round(100 * by[k][1] / by[k][0], 2))
