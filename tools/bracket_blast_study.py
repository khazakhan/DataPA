"""BRACKET BLAST study (user AF312 'more extra big blasts in [ ] and ( )'): which numbers inside the
STAR [ ] / ( ) brackets are worth marking?  Walk-forward over the saved AF pages (the page before the
result), result from rrr_records/builder60_live.jsonl.   python3 tools/bracket_blast_study.py"""
import json, re, os
B = {}
for l in open('rrr_records/builder60_live.jsonl'):
    r = json.loads(l)
    if r.get('result') is not None and r['round'].startswith('AF') and 'brackets' in r and 'white5' in r: B[r['round']] = r
def page(rd):
    p = f'rrr_outputs/{rd.lower()}.md'
    return open(p).read() if os.path.exists(p) else None
def all_lists(t):
    c = {}
    blk = t.split('### ALL LISTS, UNIQUE')[1].split('###')[0] if '### ALL LISTS, UNIQUE' in t else ''
    nums = []
    for line in blk.split('\n'):
        if line.startswith('| Number |'): nums = [int(x) for x in re.findall(r'\*\*(\d\d)\*\*', line)]
        elif line.startswith('| Lists |'):
            for n, v in zip(nums, re.findall(r'\| (\d+) ', line + ' ')): c[n] = int(v)
    return c
def picks(t):
    m = re.search(r'🎯 Bracket picks\*\*[^:]*: (.*)', t)
    return [int(x) for x in re.findall(r'\*\*(\d\d)\*\*', m.group(1))] if m else []
def gap(t):
    m = re.search(r'\*\*GAP FILL 8:\*\* (.*)', t)
    return [int(x) for x in re.findall(r'🔳(\d\d)', m.group(1))] if m else []
def f4(t):
    m = re.search(r'FINAL 4 for the next round: \*\*([\d, ]+)\*\*', t)
    return [int(x) for x in re.findall(r'\d\d', m.group(1))] if m else []
rows = []
for rd, r in sorted(B.items(), key=lambda t: int(t[0][2:])):
    t = page(rd)
    if not t or '🎯' not in t and 'STAR 5 family count' not in t: continue
    br = set(r['brackets']) - set(r['star5'] + r['white5'] + r['green5'])
    rows.append((rd, r['result'], br, all_lists(t), set(picks(t)), set(gap(t)), set(f4(t))))
n = len(rows); H = n // 2
print(f'BRACKET BLAST study: {n} AF pages (halves {H}/{n - H})')
V = {
 'all bracket numbers (not STARs)': lambda br, c, pk, g, f: br,
 'current 🎯 picks (⭕🔥💥)': lambda br, c, pk, g, f: pk,
 'bracket + on 2+ ALL LISTS': lambda br, c, pk, g, f: {v for v in br if c.get(v, 0) >= 2},
 'bracket + on 3+ ALL LISTS': lambda br, c, pk, g, f: {v for v in br if c.get(v, 0) >= 3},
 'bracket + on 4+ ALL LISTS': lambda br, c, pk, g, f: {v for v in br if c.get(v, 0) >= 4},
 'bracket + on any ALL LIST': lambda br, c, pk, g, f: {v for v in br if c.get(v, 0) >= 1},
 'bracket + GAP FILL 8': lambda br, c, pk, g, f: br & g,
 'picks + bracket∩GAP FILL': lambda br, c, pk, g, f: pk | (br & g),
}
for k, f in V.items():
    h = [0, 0]; sz = [0, 0]
    for i, (rd, res, br, c, pk, g, f4_) in enumerate(rows):
        s = f(br, c, pk, g, f4_); j = i >= H; h[j] += res in s; sz[j] += len(s)
    e = [x / 100 for x in sz]
    print(f'  {k:34s} avg {sum(sz) / n:5.1f} nums  held {h[0]:3d} | {h[1]:3d}  vs chance {e[0]:5.1f} | {e[1]:5.1f}   x{sum(h) / max(sum(e), .01):.2f}')
