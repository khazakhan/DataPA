import json, sys
from collections import defaultdict
data = json.load(open(sys.argv[1]))
st = defaultdict(lambda: [0, 0, 0])   # rounds present, hits, total size
for r in data:
    for k, v in r['src'].items():
        if not v: continue
        st[k][0] += 1; st[k][2] += len(v); st[k][1] += r['res'] in v
print(f"{'source':10} {'rounds':>6} {'hits':>5} {'avg size':>8} {'expected':>8} {'ratio':>6}")
for k, (n, h, s) in sorted(st.items(), key=lambda kv: -(kv[1][1] / max(0.01, kv[1][2] / 100))):
    exp = s / 100
    print(f"{k:10} {n:6} {h:5} {s/n:8.1f} {exp:8.1f} {h/exp if exp else 0:6.2f}")
