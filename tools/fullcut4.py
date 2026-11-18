"""FULL CUT 4 watch line log (rrr_records/fullcut4_live.jsonl): both digits cut of each FINAL 4 number.
Added 2026-11-18 after AD122 (user: 'implement one logic from the missed gaps');
tested 878 live: 23 | 19 per half vs 16.7 by chance (x1.26); series AD 6 of 121.
  python3 tools/fullcut4.py score <ROUND> <result>
  python3 tools/fullcut4.py predict <ROUND> <md page>   (reads the 'FULL CUT 4' row)"""
import sys, json, re, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'rrr_records/fullcut4_live.jsonl'
L = [json.loads(l) for l in open(P)] if os.path.exists(P) else []
if sys.argv[1] == 'score':
    for r in L:
        if r['round'] == sys.argv[2]: r['result'] = int(sys.argv[3])
else:
    m = re.search(r'\| FULL CUT 4 \(both digits cut of each FINAL 4 number\) \| ([\d ·]+) \|', open(sys.argv[3]).read())
    L = [r for r in L if r['round'] != sys.argv[2]] + [dict(round=sys.argv[2], pick=[int(x) for x in re.findall(r'\d\d', m.group(1))], result=None)]
open(P, 'w').write(''.join(json.dumps(r) + '\n' for r in L))
d = [r for r in L if r['result'] is not None]
print(f"FULL CUT 4 live {sum(r['result'] in r['pick'] for r in d)} of {len(d)}")
