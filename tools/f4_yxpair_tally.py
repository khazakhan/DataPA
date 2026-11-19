"""Block tally FINAL 4 candidates: SHADOW 4 (tools/shadow_f4.py log) vs plain vote top 4 (live.jsonl ranked[:4]).
FINAL 4 = SHADOW AD158-AE49, plain vote AE50-AE56, OPEN 1 x CLOSE 4 from AE57 (user AE56). Switch to whichever leads over a block.
  python3 tools/f4_yxpair_tally.py"""
import json, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
L = {r['round']: r for r in map(json.loads, open('rrr_records/live.jsonl')) if r.get('result') is not None}
S = {r['round']: r for r in map(json.loads, open('rrr_records/shadow_f4.jsonl')) if r.get('result') is not None}
ae = sorted((k for k in L if k.startswith('AE') and k in S), key=lambda k: int(k[2:]))
a = sum(S[k]['result'] in S[k]['pick'] for k in ae); b = sum(L[k]['result'] in L[k]['ranked'][:4] for k in ae)
last = ae[-7:]
a7 = sum(S[k]['result'] in S[k]['pick'] for k in last); b7 = sum(L[k]['result'] in L[k]['ranked'][:4] for k in last)
print(f"FINAL 4 tally series AE: plain vote {b} vs SHADOW {a} of {len(ae)}; last 7: plain {b7} vs SHADOW {a7}")
# FINAL 4 = OPEN 1 x CLOSE 4 from AE57 (user AE56); compare it with the plain vote from AE52
O = {r['round']: r for r in map(json.loads, open('rrr_records/oc14_live.jsonl')) if r.get('result') is not None}
oc = sorted((k for k in O if k.startswith('AE') and k in L), key=lambda k: int(k[2:]))
c = sum(O[k]['result'] in O[k]['pick'] for k in oc); d = sum(L[k]['result'] in L[k]['ranked'][:4] for k in oc)
print(f"OPEN 1 x CLOSE 4 (FINAL 4 from AE57) {c} vs plain vote {d} of {len(oc)} (from AE52)")
