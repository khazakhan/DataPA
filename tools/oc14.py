"""OPEN 1 x CLOSE 4 line log (rrr_records/oc14_live.jsonl): strongest OPEN digit with the 4 strongest CLOSE digits.
Added 2026-11-19 after AE52 (user request); tools/oc_grid_final4_study.py on 974 logged rounds:
21 | 29 per half vs plain vote top 4 29 | 22 (chance 19.5) -> level, display only.
  python3 tools/fullcut4.py score <ROUND> <result>
  python3 tools/fullcut4.py predict <ROUND> <md page>   (reads the 'OPEN 1 x CLOSE 4' line)"""
import sys, json, re, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'rrr_records/oc14_live.jsonl'
L = [json.loads(l) for l in open(P)] if os.path.exists(P) else []
if sys.argv[1] == 'score':
    for r in L:
        if r['round'] == sys.argv[2]: r['result'] = int(sys.argv[3])
else:
    m = re.search(r'\*\*OPEN 1 × CLOSE 4\*\*[^*]*\*\*([\d ·]+)\*\*', open(sys.argv[3]).read())
    L = [r for r in L if r['round'] != sys.argv[2]] + [dict(round=sys.argv[2], pick=[int(x) for x in re.findall(r'\d\d', m.group(1))], result=None)]
open(P, 'w').write(''.join(json.dumps(r) + '\n' for r in L))
d = [r for r in L if r['result'] is not None]
print(f"OPEN 1 x CLOSE 4 live {sum(r['result'] in r['pick'] for r in d)} of {len(d)}")
