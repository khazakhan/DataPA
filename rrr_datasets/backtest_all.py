import os, re, subprocess, sys, json, time
from concurrent.futures import ThreadPoolExecutor
D = 'rrr_datasets'
ansi = re.compile(r'\x1b\[[0-9;]*m')
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
    out = subprocess.run([sys.executable, 'DataProcessing.py'], stdin=open(os.path.join(D, f)),
                         capture_output=True, text=True).stdout
    out = ansi.sub('', out).split('\n')
    strong, cell, box = [], [], []
    li = [i for i, l in enumerate(out) if '3RRR STRONG 16   —' in l]
    if li:
        for l in out[li[-1] + 2: li[-1] + 9]:
            strong += [int(x) for x in re.findall(r'#\d+ +(\d\d) \(', l)]
    li = [i for i, l in enumerate(out) if 'DECLARED CELL ONLY' in l]
    if li:
        for l in out[li[-1] + 2: li[-1] + 30]:
            seg = l[l.rfind('│', 0, l.rfind('│')):] if l.count('│') >= 2 else ''
            if '└' in l[-45:]: break
            cell += [int(x) for x in re.findall(r'(?<!\d)(\d\d)(?!\d)', seg)]
    li = [i for i, l in enumerate(out) if 'POWER BASE — ALL' in l]
    if li:
        for l in out[li[-1] + 2: li[-1] + 12]:
            if '=' in l: break
            box += [int(x) for x in re.findall(r'(?<!\d)(\d\d)(?!\d)', l)]
    return dict(series=s, k=k, res=res, strong=strong, cell=cell, box=box)
t = time.time()
with ThreadPoolExecutor(4) as ex:
    rows = list(ex.map(run, jobs if len(sys.argv) < 2 else jobs[:int(sys.argv[1])]))
json.dump(rows, open(sys.argv[2] if len(sys.argv) > 2 else 'bt.json', 'w'))
print('rounds', len(rows), 'secs', round(time.time() - t))
