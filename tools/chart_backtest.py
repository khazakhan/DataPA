"""Frozen back-test of OCJP FINAL 4 on one chart (user 2026-11-15, new dataset AC):
for each of the last K results, run the page on the chart cut just before it (only earlier data),
take FINAL 4, and check whether the next result is in it. The script is not changed between rounds.
    python3 tools/chart_backtest.py <dataset> <K> [workers]   -> rrr_records/backtest_<name>.jsonl"""
import sys, os, json, tempfile, multiprocessing as mp
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.'); sys.path.insert(0, 'tools')
os.environ['OMA_OFF'] = '1'
ds, K = sys.argv[1], int(sys.argv[2]); W = int(sys.argv[3]) if len(sys.argv) > 3 else 4
rows = [l.split() for l in open(ds) if l.strip()]
flat = [(r, c) for r, row in enumerate(rows) for c, t in enumerate(row)]
idx = [k for k, (r, c) in enumerate(flat) if rows[r][c].isdigit()]
def prefix_text(k):                     # tokens before flat position k, rows kept
    out, cur, last = [], [], 0
    for j in range(k):
        r, c = flat[j]
        if r != last and cur: out.append('    '.join(cur)); cur = []
        last = r; cur.append(rows[r][c])
    if cur: out.append('    '.join(cur))
    return '\n'.join(out) + '\n'
def job(k):
    from replay_collect import collect
    fd, tmp = tempfile.mkstemp(suffix='.txt'); os.close(fd)
    open(tmp, 'w').write(prefix_text(k))
    try:
        L = collect(tmp)
        f4 = [int(v) for v in L.get('top4', [])]
    except Exception as e:
        f4 = []
    os.remove(tmp)
    r, c = flat[k]
    return dict(pos=k, result=int(rows[r][c]), f4=f4)
if __name__ == '__main__':
    targets = idx[-K:]
    out = f"rrr_records/backtest_{os.path.basename(ds)[:-4]}.jsonl"
    done = {json.loads(l)['pos'] for l in open(out)} if os.path.exists(out) else set()
    with mp.Pool(W) as p, open(out, 'a') as fh:
        for d in p.imap_unordered(job, [k for k in targets if k not in done]):
            fh.write(json.dumps(d) + '\n'); fh.flush()
    R = sorted((json.loads(l) for l in open(out)), key=lambda d: d['pos'])
    R = [d for d in R if d['f4']]
    h = [d['result'] in d['f4'] for d in R]
    bl = [sum(h[i:i + 7]) for i in range(0, len(h) - 6, 7)]
    print(f"{ds}: FINAL 4 held {sum(h)} of {len(h)} = {100*sum(h)/max(1,len(h)):.1f}% (chance 4%); "
          f"7-round blocks with 4+: {sum(b >= 4 for b in bl)} of {len(bl)}, best {max(bl) if bl else 0}")
