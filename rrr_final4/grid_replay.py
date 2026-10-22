"""Grid replay rounds from an old archive file (2026-10-22).
Round t = the first t full grid rows; result = first number of row t+1.
Usage: python3 grid_replay.py <archive.txt> <series-tag> <t_from> <out.json>
Note: grid numbers are not live results (the tens+5 lean seen live is absent in grids)."""
import json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
src, tag, t0, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
rows = [l.split() for l in open(src) if len(l.split()) > 1]
tmp = tempfile.mkdtemp()
def run(t):
    f = os.path.join(tmp, f'{t}.txt'); dp = os.path.join(tmp, f'{t}.json')
    open(f, 'w').write('\n'.join('    '.join(r) for r in rows[:t]) + '\n')
    subprocess.run([sys.executable, 'DataProcessing.py', f], capture_output=True, text=True,
                   env=dict(os.environ, RRR3_DUMP2=dp), stdin=subprocess.DEVNULL)
    try: d = json.load(open(dp))
    except Exception: d = {}
    d.update(series=tag, k=t, res=int(rows[t][0])); return d
ok = [t for t in range(t0, len(rows) - 1) if rows[t][0].isdigit() and len(rows[t][0]) == 2]
with ThreadPoolExecutor(4) as ex: res = list(ex.map(run, ok))
json.dump(res, open(out, 'w')); print('rounds', len(res), 'empty', sum('ep' not in r for r in res))
