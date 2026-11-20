"""BULL PICK OPS ON EP 8 watch line log (rrr_records/bullop8_live.jsonl).
User AF33/AF34 (2026-11-21): the bull pick (EP repeat) op on the ROOT put on the EP itself,
xy and yx order, signs as is / tens / units / both changed (tools/chat_page.py bull8).
Tested on 71,362 chart positions: 8 forms 1901 | 2225 per half vs chance 1971 | 2185 -> at chance,
display only.  Live from AF35.
  python3 tools/bullop8.py score <ROUND> <result>
  python3 tools/bullop8.py predict <ROUND> <md page>   (reads the 'BULL PICK OPS ON EP 8' row)"""
import sys, json, re, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'rrr_records/bullop8_live.jsonl'
L = [json.loads(l) for l in open(P)] if os.path.exists(P) else []
if sys.argv[1] == 'score':
    for r in L:
        if r['round'] == sys.argv[2]: r['result'] = int(sys.argv[3])
else:
    m = re.search(r'^\| BULL PICK OPS ON EP 8[^|]*\| ([^|]*)\|', open(sys.argv[3]).read(), re.M)
    pick = [int(x) for x in re.findall(r'\b\d\d\b', re.sub(r'\([^)]*\)', '', m.group(1)))] if m else []
    L = [r for r in L if r['round'] != sys.argv[2]] + [dict(round=sys.argv[2], pick=pick, result=None)]
open(P, 'w').write(''.join(json.dumps(r) + '\n' for r in L))
d = [r for r in L if r['result'] is not None]
print(f"BULL PICK OPS ON EP 8 live {sum(r['result'] in r['pick'] for r in d)} of {len(d)}")
