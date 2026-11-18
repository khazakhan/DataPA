"""Block tally: FINAL 4 'top 2 + yx pair' (live from AD143) vs the plain vote top 4 it replaced.
Read from rrr_records/live.jsonl: plain = ranked[:4] (vote order), live FINAL 4 = final8[:4].
Rule: drop the yx pair if it is behind the plain vote over a 7-round block.
  python3 tools/f4_yxpair_tally.py"""
import json, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None and r['round'].startswith('AD') and int(r['round'][2:]) >= 143]
a = sum(r['result'] in (r.get('final8') or [])[:4] for r in L); b = sum(r['result'] in r['ranked'][:4] for r in L)
print(f"FINAL 4 yx-pair {a} vs plain vote {b} of {len(L)} (from AD143)")
