"""OCJP FINAL 10 (user 2026-11-15, AC53: 'if required widen OCJP FINAL 4 up to 10').
FINAL 10 = OCJP FINAL 4 + their 4 yx partners + the first SHADOW numbers, different numbers only,
topped up from the page's 'Ascending, all' list when short. Chance = 10%.
Chosen on the 329 live rounds that have all three logged (Y26..AC53): 54 hits = 16.4%
(F4 alone 16 = 4.9%, F4+SHADOW 8 numbers 43 = 13.1%). Picked after looking, so only the
live record from AC54 on is a clean test. Logged BEFORE each result, never tuned.
  tools/final10.py predict <round> <page.md>   -> logs + prints the 10
  tools/final10.py score <round> <result>      -> marks held / missed, prints live"""
import sys, re, json, os
LOG = 'rrr_records/final10_live.jsonl'
SH = 'rrr_records/shadow_f4.jsonl'
def rows():
    return [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
def page_lists(md):
    t = open(md).read()
    sec = t[t.index('### OCJP FINAL 4'):].split('\n\n')[0].split('\n')[3:]
    f4, yx = [], []
    for l in sec:
        c = [x.strip() for x in l.strip('|').split('|')]
        if len(c) < 4: continue
        f4.append(int(re.search(r'\d\d', c[1]).group())); yx.append(int(c[3][:2]))
    m = re.search(r'\*\*Ascending, all \(\d+\):\*\* ([\d ]+)', t)
    allv = [int(v) for v in m.group(1).split()] if m else []
    return f4, yx, allv
cmd = sys.argv[1]
if cmd == 'predict':
    rnd, md = sys.argv[2], sys.argv[3]
    f4, yx, allv = page_lists(md)
    sh = next((json.loads(l)['pick'] for l in open(SH) if json.loads(l)['round'] == rnd), [])
    out = []
    for v in f4 + yx + sh + allv:
        if v not in out: out.append(v)
        if len(out) == 10: break
    R = rows()
    if not any(r['round'] == rnd for r in R):
        with open(LOG, 'a') as fh: fh.write(json.dumps({'round': rnd, 'pick': out, 'result': None}) + '\n')
    print('OCJP FINAL 10', rnd, ' '.join(f'{v:02d}' for v in out))
elif cmd == 'score':
    R = rows()
    for r in R:
        if r['round'] == sys.argv[2]: r['result'] = int(sys.argv[3])
    open(LOG, 'w').write(''.join(json.dumps(r) + '\n' for r in R))
    done = [r for r in R if r['result'] is not None]
    h = sum(r['result'] in r['pick'] for r in done)
    print(f'OCJP FINAL 10 live {h} of {len(done)} (chance {len(done)*0.10:.1f}); history 54 of 329 (16.4%)')
