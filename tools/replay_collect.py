import sys, os, re, json, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
os.chdir('/home/khazakhan/DataScinceAnal'); sys.path.insert(0,'.')
def nums(t): return [int(x) for x in re.findall(r'\b(\d\d)\b', t)]
def collect(ds):
    fd, dj = tempfile.mkstemp(suffix='.json'); os.close(fd)
    env = dict(os.environ, RRR3_DUMP2=dj, RRR3_VOTES='1', COLUMNS='230', RRR_ASK='0')
    out = subprocess.run(f"python3 DataProcessing.py < {ds}", shell=True, env=env, capture_output=True, text=True).stdout
    out = re.sub(r'\x1b\[[0-9;]*m', '', out)
    try: d = json.load(open(dj))
    except Exception: d = {}
    os.remove(dj)
    src = {}
    for k in ('strong','rec','yx','wide','ncspec'):
        if k in d: src[k] = {v for v in d[k] if isinstance(v,int)}
    if 'table' in d: src['table'] = {v[0] if isinstance(v,list) else v for v in d['table']}
    # CharRow box
    m = re.search(r'CharRow — \d+ numbers, no repeats[^\n]*\n(.*?)└', out, re.S)
    if m: src['charrow'] = set(int(x) for x in re.findall(r'(\d\d)\+? \(', m.group(1)))
    m = re.search(r'HOT 20\s+│ ([\d ]+)│', out)
    if m: src['hot'] = set(nums(m.group(1)))
    # ranked list from the final box: top 10 / 20 / 30 / 40
    L = out.rfind('OCJP FINAL 4 with operations (the prediction)')
    blk = out[L:L+40000]
    rk = []
    for lab in ('top 10:', 'top 20 (adds):', 'top 30 (adds):', 'top 40 (adds):'):
        i = blk.find(lab)
        if i < 0: continue
        seg = blk[i+len(lab): i+len(lab)+1500]
        rk += [int(x) for x in re.findall(r'(\d\d) \(', seg)][:10]
    src['top4'] = set(rk[:4]); src['top10'] = set(rk[:10]); src['top20'] = set(rk[:20]); src['top40'] = set(rk[:40])
    # rules on test
    for m in re.finditer(r'│ (\d+)\. [^│]*│ ([^│]*)│', blk):
        r = int(m.group(1)); txt = m.group(2)
        if r <= 28 and txt.strip() and not txt.strip().startswith('-'):
            ns = [int(x) for x in re.findall(r'(\d\d) \(', txt)] or ([] if r != 5 else nums(txt))
            if r == 5: ns = nums(txt)
            src.setdefault(f'rule{r}', set()).update(ns)
    # finder
    i = blk.find('EP ROW FINDER'); j = blk.find('different numbers', i)
    if i >= 0 and j > 0:
        line = blk[j-5:j+400].split('\n')[0]
        src['finder'] = set(nums(line.split(':',1)[1].split('(live')[0]))
    res = {k: sorted(v) for k, v in src.items()}
    res['rk'] = rk
    return res
if __name__ == '__main__':
    pairs = json.load(open(sys.argv[1])); outp = sys.argv[2]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda p: (p[0], p[1], collect(p[0])), pairs))
    json.dump([{'ds':a,'res':b,'src':c} for a,b,c in res], open(outp,'w'))
    print(len(res), 'rounds collected')
