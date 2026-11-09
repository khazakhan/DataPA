"""SHADOW FINAL 4 (2026-11-09): a pre-registered challenger to OCJP FINAL 4.
Pure chart statistics, no RRR rules: score every number n by how often the chart
has moved from the last number's digits to n's digits (tens step x units step,
learned on everything before), skip the last number's tens digit on low-repeat
charts, take the top 4.  Logged BEFORE the result, scored after, never tuned.
  tools/shadow_f4.py predict <dataset> <round>     -> logs + prints the 4
  tools/shadow_f4.py score <round> <result>        -> marks held / missed
  tools/shadow_f4.py walk <dataset>                -> walk-forward on the whole chart"""
import sys, json, collections
LOG = 'rrr_records/shadow_f4.jsonl'
def load(f): return [int(t) for t in open(f).read().split() if t.isdigit()]
def pick(seq, k=4):
    S = list(zip(seq, seq[1:]))
    t = collections.Counter((b // 10 - a // 10) % 10 for a, b in S)
    u = collections.Counter((b % 10 - a % 10) % 10 for a, b in S)
    rep = t[0] / max(len(S), 1)
    e = seq[-1]
    sc = {n: (t[(n // 10 - e // 10) % 10] + 1) * (u[(n % 10 - e % 10) % 10] + 1) for n in range(100)
          if not (rep < 0.06 and n // 10 == e // 10)}
    return sorted(sc, key=lambda n: (-sc[n], n))[:k]
cmd = sys.argv[1]
if cmd == 'predict':
    p = pick(load(sys.argv[2])); rnd = sys.argv[3]
    rows = [json.loads(l) for l in open(LOG)] if __import__('os').path.exists(LOG) else []
    if not any(r['round'] == rnd for r in rows):
        with open(LOG, 'a') as fh: fh.write(json.dumps({'round': rnd, 'pick': p, 'result': None}) + '\n')
    print('SHADOW FINAL 4', rnd, ' '.join(f'{v:02d}' for v in p))
elif cmd == 'score':
    rows = [json.loads(l) for l in open(LOG)]
    for r in rows:
        if r['round'] == sys.argv[2]: r['result'] = int(sys.argv[3])
    open(LOG, 'w').write(''.join(json.dumps(r) + '\n' for r in rows))
    done = [r for r in rows if r['result'] is not None]
    h = sum(r['result'] in r['pick'] for r in done)
    print(f'SHADOW FINAL 4 live {h} of {len(done)} (chance {len(done)*0.04:.1f})')
elif cmd == 'walk':
    s = load(sys.argv[2]); h = n = 0
    for i in range(300, len(s) - 1):
        n += 1; h += s[i + 1] in pick(s[:i + 1])
    print(f'walk-forward {sys.argv[2]}: {h} of {n} = {h/n:.1%} (chance 4%)')
