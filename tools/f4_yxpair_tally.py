"""Block tally FINAL 4 candidates: SHADOW 4 (tools/shadow_f4.py log) vs plain vote top 4 (live.jsonl ranked[:4]).
FINAL 4 = SHADOW AD158-AE49, plain vote again from AE50 (SHADOW behind in AE). Switch to whichever leads over a block.
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
