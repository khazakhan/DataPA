"""ROOT / EP naming check on every data position (user 2026-11-05: 'after is
EP, EP is ROOT; check from where we started, back over all data rounds').

For the newest dataset of every series, every position k (from 100 on) is a
round: EP = s[k] (last number = the old 'after'), ROOT = the number that
followed the latest earlier EP (the old 'EP'), result = s[k+1].
Tests simple ROOT-based and EP-based moves against chance (1 in 100 for one
number; group size / 100 for the group index array)."""
import sys, io, os, glob, re, contextlib, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
fo, ap = D.find_op, D.apply_op
op2 = lambda a, b: (fo(a // 10, b // 10), fo(a % 10, b % 10))
on = lambda n, o: ap(n // 10, o[0]) * 10 + ap(n % 10, o[1])
newest = {}
for f in glob.glob('rrr_datasets/*.txt'):
    m = re.match(r'rrr_datasets/([a-z]+)(\d+)\.txt$', f)
    if m and int(m.group(2)) >= newest.get(m.group(1), (0, ''))[0]:
        newest[m.group(1)] = (int(m.group(2)), f)
H = collections.Counter(); N = collections.Counter(); gsize = 0; per = collections.defaultdict(collections.Counter)
for ser, (_, f) in sorted(newest.items()):
    with contextlib.redirect_stdout(io.StringIO()):
        rows = D.load_data(open(f))
    s = [v for r in rows for v in r if isinstance(v, int) and 0 <= v <= 99]
    last = {}; follow = {}; GI = collections.defaultdict(list); prev_root = None          # value -> latest index; value -> what followed it last time
    for k in range(len(s) - 1):
        ep, res = s[k], s[k + 1]
        if k >= 100 and ep in follow:
            root = follow[ep]; grp = set(GI[ep]); N['rounds'] += 1; per[ser]['rounds'] += 1
            tests = {
                'result = ROOT': res == root,
                'result = EP (repeat)': res == ep,
                'result in group index array': res in grp,
                'last op (prev->EP) on ROOT': res == on(root, op2(s[k - 1], ep)),
                'last op (prev->EP) on EP': res == on(ep, op2(s[k - 1], ep)),
                'op EP->ROOT on ROOT': res == on(root, op2(ep, root)),
                'chain op (prev ROOT->ROOT) on ROOT': len(GI[ep]) > 1 and res == on(root, op2(GI[ep][-2], root)),
                'what followed ROOT last time': res == follow.get(root, -1),
                'same op again (prev round ROOT->EP) on ROOT': prev_root is not None and res == on(root, op2(prev_root, ep)),
            }
            gsize += len(grp)
            for t, v in tests.items():
                H[t] += v; per[ser][t] += v
        prev_root = follow.get(ep)
        follow[ep] = res; last[ep] = k
        GI[ep].append(res)
n = N['rounds']
print(f"series {len(newest)}, data rounds {n}")
for t, v in H.items():
    ch = gsize / 100 if t == 'result in group index array' else n / 100
    print(f"   {t:38s} {v:6d}   chance {ch:8.1f}   x{v / ch:.2f}")
print("S series only:", {t: v for t, v in per['s'].items()})
