"""OPEN (tens) deep chart walk-forward (user AE65 'deep search about open fire').
Every series' longest chart; at each position i >= 300 each feature scores the 10 tens digits using only
results before i.  Scored: #1 right and top 3, per chart and per half (first / second half of positions).
  python3 tools/open_chart_deep.py"""
import os, re, glob, math
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
def load(p):
    seq, w = [], None
    for line in open(p):
        tok = line.split()
        if not tok: continue
        if w is None and len(tok) > 1: w = len(tok)
        for t in tok:
            seq.append(int(t) if re.fullmatch(r'\d\d', t) else None)
    return seq, w or 7
files = {}
for p in glob.glob('rrr_datasets/*.txt'):
    m = re.fullmatch(r'rrr_datasets/([a-z]+)(\d+)\.txt', p)
    if m and (m.group(1) not in files or int(m.group(2)) > files[m.group(1)][0]): files[m.group(1)] = (int(m.group(2)), p)
def ordr(s): return sorted(range(10), key=lambda d: (-s[d], d))
def feats(seq, i, w, fl, cnt):
    """seq: with voids (for column lag); fl: flat non-void results before i (list); cnt: running stats"""
    e = fl[-1]; et = e // 10; pt = fl[-2] // 10
    T1, T2, ST, CL, TF = cnt['T1'], cnt['T2'], cnt['ST'], cnt['CL'], cnt['TF']
    F = {}
    F['step mode'] = [ST[(d - et) % 10] for d in range(10)]
    F['P(t | last t)'] = [T1[et][d] for d in range(10)]
    F['P(t | last 2 t)'] = [T2[(pt, et)][d] for d in range(10)]
    F['tens freq'] = TF[:]
    hot = [0] * 10
    for v in fl[-30:]: hot[v // 10] += 1
    F['hot 30'] = hot
    gap = [0] * 10
    for d in range(10):
        k = next((j for j in range(len(fl) - 1, -1, -1) if fl[j] // 10 == d), -1); gap[d] = len(fl) - k
    F['overdue'] = gap
    # followers of earlier occurrences of the EP number
    fo = [0] * 10
    for j in range(len(fl) - 1):
        if fl[j] == e: fo[fl[j + 1] // 10] += 1
    F['EP followers tens'] = fo
    lag = seq[i - w] if i - w >= 0 else None
    F['P(t | col lag t)'] = [CL[lag // 10][d] if lag is not None else 0 for d in range(10)]
    F['col lag tens'] = [1 if lag is not None and d == lag // 10 else 0 for d in range(10)]
    # naive Bayes mix of the three conditionals
    def nz(x):
        s = sum(x) + 10; return [(y + 1) / s for y in x]
    F['NB mix'] = [math.log(a) + math.log(b) + math.log(c) for a, b, c in
                   zip(nz(F['P(t | last t)']), nz(F['P(t | last 2 t)']), nz(F['P(t | col lag t)']))]
    return F
tot = {}
for s, (_, p) in sorted(files.items()):
    seq, w = load(p)
    if sum(v is not None for v in seq) < 1200: continue
    cnt = dict(T1=[[0] * 10 for _ in range(10)], T2={(a, b): [0] * 10 for a in range(10) for b in range(10)},
               ST=[0] * 10, CL=[[0] * 10 for _ in range(10)], TF=[0] * 10)
    fl = []; lagq = []; res = {}; pos = []
    for i, v in enumerate(seq):
        if v is None: continue
        if len(fl) >= 300:
            F = feats(seq, i, w, fl, cnt)
            pos.append({k: (ordr(x)[0] == v // 10, v // 10 in ordr(x)[:3]) for k, x in F.items()})
        # update counts with v
        if fl:
            a = fl[-1]; cnt['T1'][a // 10][v // 10] += 1; cnt['ST'][(v // 10 - a // 10) % 10] += 1
            if len(fl) >= 2: cnt['T2'][(fl[-2] // 10, a // 10)][v // 10] += 1
        lg = seq[i - w] if i - w >= 0 else None
        if lg is not None: cnt['CL'][lg // 10][v // 10] += 1
        cnt['TF'][v // 10] += 1; fl.append(v)
    h = len(pos) // 2
    for k in pos[0]:
        a = sum(x[k][0] for x in pos[:h]); b = sum(x[k][0] for x in pos[h:])
        c = sum(x[k][1] for x in pos[:h]); d = sum(x[k][1] for x in pos[h:])
        t = tot.setdefault(k, [0, 0, 0, 0, 0, 0, 0]); t[0] += a; t[1] += b; t[2] += c; t[3] += d; t[4] += h; t[5] += len(pos) - h
        if b > (len(pos) - h) * 0.12 and a > h * 0.12: t[6] += 1
    print(s, len(pos), 'w', w, ' '.join(f"{k[:10]}:{sum(x[k][0] for x in pos)/len(pos)*100:.1f}" for k in pos[0]))
print('\nALL charts (per half): #1 right %, top 3 %  | charts with >12% in both halves')
for k, t in tot.items():
    print(f"{k:20s} #1 {t[0]/t[4]*100:5.2f} | {t[1]/t[5]*100:5.2f}   top3 {t[2]/t[4]*100:5.2f} | {t[3]/t[5]*100:5.2f}   ({t[6]} charts)")
