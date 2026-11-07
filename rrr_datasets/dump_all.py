import os, re, subprocess, sys, json, time, tempfile
from concurrent.futures import ThreadPoolExecutor
D = 'rrr_datasets'
files = {}
for f in os.listdir(D):
    m = re.match(r'^([a-z]+?)(\d+)\.txt$', f)
    if m: files.setdefault(m.group(1), {})[int(m.group(2))] = f
def toks(f): return open(os.path.join(D, f)).read().split()
jobs = []
for s, d in sorted(files.items()):
    for k in sorted(d):
        if k + 1 in d:
            a, b = toks(d[k]), toks(d[k + 1])
            if len(b) == len(a) + 1 and b[:-1] == a and re.fullmatch(r'\d\d', b[-1]):
                jobs.append((s, k, d[k], int(b[-1])))
def run(job):
    s, k, f, res = job
    dp = os.path.join(sys.argv[1], f'{s}{k}.json')
    subprocess.run([sys.executable, 'DataProcessing.py'], stdin=open(os.path.join(D, f)),
                   capture_output=True, text=True, env=dict(os.environ, RRR3_DUMP2=dp))
    try: d = json.load(open(dp))
    except Exception: d = {}
    d.update(series=s, k=k, res=res); return d
t = time.time()
with ThreadPoolExecutor(4) as ex: rows = list(ex.map(run, jobs))
json.dump(rows, open(sys.argv[2], 'w')); print('rounds', len(rows), 'empty', sum('ep' not in r for r in rows), 'secs', round(time.time() - t))
