"""T13 idea test (user 2026-11-07 'improvise the logic', result 17 = cut/cut on ROOT 62):
does the result come from (a) full cut of ROOT, (b) the previous round's result op again on the
new ROOT or on the EP, (c) the ROOT->EP move op again? All rounds in order, per series."""
import sys; sys.argv = ['x']
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('tools/final4_full_study.py').read().split('n = len(R)')[0])
n = len(R); c = dict(a=0, b_root=0, b_ep=0, c_root=0, c_ep=0, any4=0)
for i, r in enumerate(R):
    got = set()
    if r['res'] == ap(r['root'], 'cut', 'cut'): c['a'] += 1
    got.add(ap(r['root'], 'cut', 'cut'))
    if i and R[i-1]['series'] == r['series']:
        p = op_of(R[i-1]['root'], R[i-1]['res'])
        c['b_root'] += r['res'] == ap(r['root'], *p); c['b_ep'] += r['res'] == ap(r['ep'], *p)
        got |= {ap(r['root'], *p), ap(r['ep'], *p)}
    m = op_of(r['root'], r['ep'])
    c['c_root'] += r['res'] == ap(r['root'], *m); c['c_ep'] += r['res'] == ap(r['ep'], *m)
    got |= {ap(r['root'], *m)}
    c['any4'] += r['res'] in got
print(f"rounds {n}; one number each, chance {n/100:.1f}")
for k, t in (('a', 'full cut of ROOT (cut/cut)'), ('b_root', 'previous result op again on ROOT'),
             ('b_ep', 'previous result op again on EP'), ('c_root', 'ROOT->EP op again on ROOT'),
             ('c_ep', 'ROOT->EP op again on EP')):
    print(f"  {t:36s} {c[k]:3d}")
print(f"  all 4 together (~4 numbers, chance {4*n/100:.0f}): {c['any4']}")
