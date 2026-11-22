"""LAST-OP FULL CUT 4 watch line log (rrr_records/lofc4_live.jsonl): both digits cut of each LAST-OP 4 number.
Added 2026-11-22 after AF108 (user: 14 in LAST-OP 4, full cut 69 came).
tested 1067 logged rounds: 25 | 29 per half vs 21.0 | 21.1 by chance (x1.28).
  python3 tools/lofc4.py score <ROUND> <result>
  python3 tools/lofc4.py predict <ROUND> <md page>   (reads the 'FULL CUT 4' row)"""
import sys, json, re, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'rrr_records/lofc4_live.jsonl'
L = [json.loads(l) for l in open(P)] if os.path.exists(P) else []
if sys.argv[1] == 'score':
    for r in L:
        if r['round'] == sys.argv[2]: r['result'] = int(sys.argv[3])
else:
    m = re.search(r'\| LAST-OP FULL CUT 4 [^|]*\| ([\d ·]+) \|', open(sys.argv[3]).read())
    L = [r for r in L if r['round'] != sys.argv[2]] + [dict(round=sys.argv[2], pick=[int(x) for x in re.findall(r'\d\d', m.group(1))], result=None)]
open(P, 'w').write(''.join(json.dumps(r) + '\n' for r in L))
d = [r for r in L if r['result'] is not None]
print(f"LAST-OP FULL CUT 4 live {sum(r['result'] in r['pick'] for r in d)} of {len(d)}")
