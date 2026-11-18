"""STRONG 20 #1 watch line log (rrr_records/strong1_live.jsonl).
  python3 tools/strong1.py score <ROUND> <result>
  python3 tools/strong1.py predict <ROUND> <md page>   (reads the 'STRONG 20 #1' row)"""
import sys, json, re, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'rrr_records/strong1_live.jsonl'
L = [json.loads(l) for l in open(P)] if os.path.exists(P) else []
if sys.argv[1] == 'score':
    for r in L:
        if r['round'] == sys.argv[2]: r['result'] = int(sys.argv[3])
else:
    m = re.search(r'\| STRONG 20 #1 \(one number\) \| \*\*(\d\d)\*\*', open(sys.argv[3]).read())
    L = [r for r in L if r['round'] != sys.argv[2]] + [dict(round=sys.argv[2], pick=[int(m.group(1))], result=None)]
open(P, 'w').write(''.join(json.dumps(r) + '\n' for r in L))
d = [r for r in L if r['result'] is not None]
print(f"STRONG 20 #1 live {sum(r['result'] in r['pick'] for r in d)} of {len(d)}")
