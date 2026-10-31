"""Collect, for every replay/live round: EP, table-4 rows and the ranked list
(top 40, FINAL 4 = first 4).  Output: rrr_records/replay/lastprev.json"""
import sys, os, re, json, subprocess, tempfile, glob
from concurrent.futures import ThreadPoolExecutor
os.chdir('/home/khazakhan/DataScinceAnal')
pairs = []
for s in 'FNMKO':
    pairs += [(d, r, s) for d, r in json.load(open(f'rrr_records/replay/pairs{s}.json'))]
for s in 'pqr':
    fs = sorted(glob.glob(f'rrr_datasets/{s}[0-9]*.txt'), key=lambda f: int(re.findall(r'\d+', os.path.basename(f))[0]))
    for a, b in zip(fs, fs[1:]):
        if int(re.findall(r'\d+', os.path.basename(b))[0]) != int(re.findall(r'\d+', os.path.basename(a))[0]) + 1: continue
        r = open(b).read().split()[-1]
        if r.isdigit(): pairs.append((a, int(r), s.upper()))
def one(p):
    ds, res, ser = p
    fd, dj = tempfile.mkstemp(suffix='.json'); os.close(fd)
    env = dict(os.environ, RRR3_ROWS=dj, COLUMNS='230', RRR_ASK='0')
    out = subprocess.run(f"python3 DataProcessing.py < {ds}", shell=True, env=env, capture_output=True, text=True).stdout
    out = re.sub(r'\x1b\[[0-9;]*m', '', out)
    try: d = json.load(open(dj))
    except Exception: d = {}
    os.remove(dj)
    L = out.rfind('OCJP FINAL 4 with operations (the prediction)'); blk = out[L:L+40000]; rk = []
    for lab in ('top 10:', 'top 20 (adds):', 'top 30 (adds):', 'top 40 (adds):'):
        i = blk.find(lab)
        if i >= 0: rk += [int(x) for x in re.findall(r'(\d\d) \(', blk[i+len(lab): i+len(lab)+1500])][:10]
    return {'ds': ds, 'res': res, 'series': ser, 'ep': d.get('ep'), 'rows': d.get('rows', []), 'rk': rk}
with ThreadPoolExecutor(6) as ex: out = list(ex.map(one, pairs))
json.dump(out, open('rrr_records/replay/lastprev.json', 'w'))
print(len(out), 'rounds;', sum(1 for o in out if o['rows']), 'with rows')
