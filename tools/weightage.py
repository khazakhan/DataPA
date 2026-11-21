"""WEIGHTAGE (user AF100: 'before releasing, analyse which one is strong and its weightage').
Each list on the page gets a weight = its own live hit rate per number, shrunk toward chance (1%):
    rate = (hits + A*size/100*0 + A*0.01*... )  ->  lift = (hits + A) / (expected + A),  expected = rounds*size/100
A number's weight = the best lift among the lists holding it (no double count of nested lists);
ties broken by how many lists with lift > 1 hold it.  Display + live tally only.
  python3 tools/weightage.py show  <page.md>
  python3 tools/weightage.py predict <ROUND> <page.md>    (logs top 4 to rrr_records/weightage_live.jsonl)
  python3 tools/weightage.py score <ROUND> <result>
  python3 tools/weightage.py backtest <page.md ...>       (page N+1 holds lists for round N+1; result read from page N+2 title)"""
import re, sys, json, os
A = 5.0
LOG = 'rrr_records/weightage_live.jsonl'
def two(s): return [int(x) for x in re.findall(r'(?<![\d.])\d\d(?![\d.])', s)]
def lof(s):
    m = re.search(r'(\d+) of (\d+)', s); return (int(m.group(1)), int(m.group(2))) if m else None
def uniq(l):
    o = []
    for x in l:
        if x not in o: o.append(x)
    return o
def lists(t):
    L = {}
    m = re.search(r'### OCJP FINAL 4: .*?\n\|.*\n\|.*\n((?:\|.*\n){4})', t)
    if m:
        rows = m.group(1).splitlines()
        f4 = [int(re.findall(r'\*\*(\d\d)\*\*', r)[-1]) for r in rows]
        lv = re.search(r'FINAL 4 for the next round: .*?\(live (\d+) of (\d+)\)', t)
        if lv: L['FINAL 4'] = (f4, (int(lv.group(1)), int(lv.group(2))))
        mm = re.search(r'\| OCJP MASTER \d\d \| [^|]* \| (\d+) of (\d+)', t)
        if mm: L['MASTER'] = ([f4[0]], (int(mm.group(1)), int(mm.group(2))))
    for key, pat in (('Grid', r'\*\*OPEN × CLOSE grid \(9\):\*\* (.*)'), ('OPEN 1 × CLOSE 4', r'\*\*OPEN 1 × CLOSE 4\*\* .*?: \*\*(.*)'),
                     ('OPEN CUT × CLOSE 4', r'\*\*OPEN CUT × CLOSE 4\*\* .*?: \*\*(.*)'), ('FINAL 10', r'\*\*OCJP FINAL 10:\*\* (.*)'),
                     ('FINAL 8', r'\*\*FINAL 8 ascending:\*\* (.*)')):
        m = re.search(pat, t)
        if m:
            s = m.group(1); head = s.split('(live')[0]
            c = lof(s.split('(live')[1]) if '(live' in s else None
            if c: L[key] = (uniq(two(head)), c)
    for key, pat in (('KING PICK', r'\| KING PICK[^|]*\| (.*?) \| (.*?) \|'), ('STRONG 20 #1', r'\| STRONG 20 #1[^|]*\| (.*?) \| (.*?) \|'),
                     ('MASTER CHANGED OPS 10', r'\| MASTER CHANGED OPS 10[^|]*\| (.*?) \| (.*?) \|'), ('HUNTER 20', r'\| HUNTER 20[^|]*\| (.*?) \| (.*?) \|'),
                     ('SHADOW 4', r'\| SHADOW 4[^|]*\| (.*?) \| (.*?) \|'), ('FULL CUT 4', r'\| FULL CUT 4[^|]*\| (.*?) \| (.*?) \|'),
                     ('yx CUT 12', r'\| yx CUT 12[^|]*\| (.*?) \| (.*?) \|'), ('BULL PICK OPS ON EP 8', r'\| BULL PICK OPS ON EP 8[^|]*\| (.*?) \| (.*?) \|'),
                     ('STRONGEST FAMILY', r'\| STRONGEST FAMILY[^|]*\| (.*?) \| (.*?) \|')):
        m = re.search(pat, t)
        if not m: continue
        ns = uniq(two(re.sub(r'\([^)]*\)', '', m.group(1))))
        c = lof(m.group(2))
        if key == 'STRONGEST FAMILY':
            h = re.search(r'(\d+) and (\d+) per half vs ([\d.]+)', m.group(2)); n = re.search(r'tested (\d+)', m.group(2))
            if h and n: c = (int(h.group(1)) + int(h.group(2)), int(n.group(1)))
        if key == 'MASTER CHANGED OPS 10' and m.group(1).count('·') == 0: continue
        if ns and c: L[key] = (ns, c)
    m = re.search(r'## ONE-MEN-ARMY: .*?\(live (\d+) of (\d+)\)\n\*\*Ascending:\*\* (.*)', t)
    if m: L['ONE-MEN-ARMY'] = (uniq(two(m.group(3))), (int(m.group(1)), int(m.group(2))))
    return L
def weigh(L):
    W = {}
    for k, (ns, (h, n)) in L.items():
        e = n * len(ns) / 100.0
        W[k] = ((h + A) / (e + A), h, n, len(ns))
    S = {}
    for k, (ns, _) in L.items():
        for x in ns:
            S.setdefault(x, []).append(k)
    rank = sorted(S, key=lambda x: (-max(W[k][0] for k in S[x]), -sum(1 for k in S[x] if W[k][0] > 1), x))
    return W, S, rank
def show(p):
    W, S, rank = weigh(lists(open(p).read()))
    print('| List | Numbers | Live | Per number vs 1% | Weight (lift) |\n|---|---|---|---|---|')
    for k in sorted(W, key=lambda k: -W[k][0]):
        l, h, n, sz = W[k]
        print(f'| {k} | {sz} | {h} of {n} | {100*h/max(n*sz,1):.2f}% | x{l:.2f} |')
    print('\n| # | Number | Weight (best list) | Lists with weight > 1 | All lists |\n|---|---|---|---|---|')
    for i, x in enumerate(rank[:10], 1):
        best = max(S[x], key=lambda k: W[k][0])
        print(f'| {i} | **{x:02d}** | x{W[best][0]:.2f} ({best}) | {sum(1 for k in S[x] if W[k][0] > 1)} | {len(S[x])} |')
    return rank
if __name__ == '__main__':
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    a = sys.argv[1:]
    if a[0] == 'show': show(a[1])
    elif a[0] == 'predict':
        rank = weigh(lists(open(a[2]).read()))[2]
        rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
        if not any(r['round'] == a[1] for r in rows):
            open(LOG, 'a').write(json.dumps({'round': a[1], 'top4': rank[:4], 'top10': rank[:10]}) + '\n')
        print('WEIGHTAGE TOP 4', a[1], ' '.join(f'{x:02d}' for x in rank[:4]))
    elif a[0] == 'score':
        rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
        for r in rows:
            if r['round'] == a[1] and 'result' not in r: r['result'] = int(a[2])
        open(LOG, 'w').write(''.join(json.dumps(r) + '\n' for r in rows))
        done = [r for r in rows if 'result' in r]
        print(f"WEIGHTAGE TOP 4 live {sum(r['result'] in r['top4'] for r in done)} of {len(done)}")
    elif a[0] == 'backtest':
        pages = a[1:]; got = {'w4': 0, 'f4': 0, 'n': 0}
        for p, q in zip(pages, pages[1:]):
            t = open(p).read(); L = lists(t)
            if 'FINAL 4' not in L or len(L) < 8: continue
            m = re.search(r'result: (\d\d)', open(q).read().split('\n')[0])
            if not m: continue
            r = int(m.group(1)); rank = weigh(L)[2]
            got['n'] += 1; got['w4'] += r in rank[:4]; got['f4'] += r in L['FINAL 4'][0]
        print(got)
