"""HUNTER BAAGBAKRI 20 (2026-11-17, user after AD31: 'super most 20 results').  Candidate
20-number builds from the parts that measured best live; each is scored on all live rounds
(chance 20%); the build is chosen on the FIRST half and tested on the SECOND half.
  python3 tools/hunter20.py                -> study
  python3 tools/hunter20.py show <md page> -> the HUNTER 20 for a declared round (from its page)"""
import json, sys, re, os
op = lambda a, b: ((b // 10 - a // 10) % 10, (b % 10 - a % 10) % 10)
app = lambda n, o: ((n // 10 + o[0]) % 10) * 10 + (n % 10 + o[1]) % 10
fc = lambda n: ((n // 10 + 5) % 10) * 10 + (n % 10 + 5) % 10
C = lambda d: (d + 5) % 10
def core(f4, R, E):
    """FINAL 4, their yx, EP repeat, EP full cut, MASTER changed ops (x-1, x cut, swap+cut)."""
    out = []
    add = lambda v: out.append(v) if v is not None and v not in out else None
    for v in f4: add(v)
    for v in f4: add(app(R, op(R, v)[::-1]))
    add(E); add(fc(E))
    x, y = op(R, f4[0])
    add(app(R, ((x - 1) % 10, y))); add(app(R, (5, y))); add(app(R, (C(y), C(x))))
    return out
def fill(base, *lists, n=20):
    out = list(base)
    for l in lists:
        for v in l:
            if len(out) >= n: return out
            if v not in out: out.append(v)
    return out[:n]
BUILDS = {
 'STRONG 20 alone': lambda r, f4: fill([], r['lists'].get('strong', [])),
 'vote top 20': lambda r, f4: fill([], r['ranked']),
 'core + STRONG': lambda r, f4: fill(core(f4, r['ep'], r['after']), r['lists'].get('strong', []), r['ranked']),
 'core + vote rank': lambda r, f4: fill(core(f4, r['ep'], r['after']), r['ranked'], r['lists'].get('strong', [])),
 'FINAL 4 + yx + STRONG': lambda r, f4: fill(fill(f4, [app(r['ep'], op(r['ep'], v)[::-1]) for v in f4], n=8), r['lists'].get('strong', []), r['ranked']),
}
def f4_of(r):
    f = list(r['ranked'][:4]); E = r['after']; R = r['ep']
    if E not in f: f[2] = E
    y = app(R, op(R, f[3])[::-1])
    if y not in f: f[3] = y
    return f
if len(sys.argv) == 1:
    L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
    L = [r for r in L if r.get('result') is not None and r.get('ep') is not None and r.get('after') is not None
         and len(r['ranked']) >= 20 and r.get('lists')]
    h = len(L) // 2
    print('live rounds', len(L), '(chance 20%)')
    sc = {}
    for k, b in BUILDS.items():
        a = sum(r['result'] in b(r, f4_of(r)) for r in L[:h]); c = sum(r['result'] in b(r, f4_of(r)) for r in L[h:])
        sc[k] = (a, c)
        print(f'  {k:24s} {a:3d} of {h} ({100*a/h:.1f}%)  |  {c:3d} of {len(L)-h} ({100*c/(len(L)-h):.1f}%)')
    best = max(BUILDS, key=lambda k: sc[k][0])
    print('picked on first half:', best, '-> second half', f'{100*sc[best][1]/(len(L)-h):.1f}%')
    blocks = [L[i:i + 7] for i in range(0, len(L) - 6, 7)]
    full = sum(all(r['result'] in BUILDS[best](r, f4_of(r)) for r in b) for b in blocks)
    print(f'7-round blocks where {best} held all 7: {full} of {len(blocks)}')

# Live HUNTER 20 (build 'FINAL 4 + yx + STRONG', picked on the first half above):
#   python3 tools/hunter20.py predict AD33 <dataset> <md page>   (logs rrr_records/hunter20_live.jsonl)
#   python3 tools/hunter20.py score AD33 <result>
LOG = 'rrr_records/hunter20_live.jsonl'
if len(sys.argv) > 1 and sys.argv[1] == 'predict':
    import os, subprocess, tempfile
    rnd, ds, md = sys.argv[2], sys.argv[3], sys.argv[4]
    tf = tempfile.NamedTemporaryFile(suffix='.json', delete=False).name
    subprocess.run([sys.executable, 'DataProcessing.py'], stdin=open(ds), stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, env=dict(os.environ, RRR3_DUMP2=tf, OMA_OFF='1'))
    d = json.load(open(tf)); os.unlink(tf); R = d['ep']
    t = open(md).read(); blk = t[t.index('### OCJP FINAL 4:'):]
    f4 = [int(m) for m in re.findall(r'^\| (?:\*\*MASTER[^|]*|\d) \| \*\*(\d\d)\*\*', blk, re.M)][:4]
    pick = fill(fill(f4, [app(R, op(R, v)[::-1]) for v in f4], n=8), d['strong'])
    open(LOG, 'a').write(json.dumps({'round': rnd, 'pick': pick, 'result': None}) + '\n')
    print('HUNTER 20', rnd, ' '.join(f'{v:02d}' for v in pick))
if len(sys.argv) > 1 and sys.argv[1] == 'score':
    rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
    for r in rows:
        if r['round'] == sys.argv[2]: r['result'] = int(sys.argv[3])
    open(LOG, 'w').writelines(json.dumps(r) + '\n' for r in rows)
    done = [r for r in rows if r['result'] is not None]
    print('HUNTER 20 live', sum(r['result'] in r['pick'] for r in done), 'of', len(done))
