"""OPEN / CLOSE deep dive (user 2026-11-10: "open close table improvise strongly ... best of best").
Walk-forward on every distinct chart: at each number from #300 on, every method scores the 10
digits from the PAST only; we count top-1 and top-3 hits for the next number's tens (OPEN) and
units (CLOSE).  Low tens-repeat charts (< 6%): the EP's tens digit is put last for OPEN methods.
Usage: python3 tools/oc_deep_study.py"""
import os, re, glob, collections, math
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

def charts():
    by, seen, out = {}, set(), []
    for f in glob.glob('rrr_datasets/*.txt'):
        m = re.match(r'([a-z]+)(\d+)\.txt$', os.path.basename(f))
        if m and (m.group(1) not in by or int(m.group(2)) > by[m.group(1)][0]):
            by[m.group(1)] = (int(m.group(2)), f)
    for s, (n, f) in sorted(by.items(), key=lambda t: -len(open(t[1][1]).read())):
        fl = [int(x) for x in re.findall(r'(?<![\d*])\d\d(?![\d*])', open(f).read())]
        key = tuple(fl[:12])
        if len(fl) > 600 and key not in seen:
            seen.add(key); out.append((s, fl))
    return out

D = lambda v, k: v // 10 if k == 't' else v % 10

class State:
    """running counts for one digit side (k = 't' tens / 'u' units), updated one number at a time."""
    def __init__(self, k):
        self.k = k; self.step = [0]*10; self.rstep = [0.0]*10; self.freq = [0]*10; self.last = [-1]*10
        self.mk1 = [[0]*10 for _ in range(10)]; self.rmk1 = [[0.0]*10 for _ in range(10)]
        self.mk2 = collections.defaultdict(lambda: [0]*10); self.hist = []
    def add(self, v):
        d = D(v, self.k); h = self.hist
        self.rstep = [x * 0.997 for x in self.rstep]
        self.rmk1 = [[x * 0.997 for x in r] for r in self.rmk1]
        if h:
            a = h[-1]
            self.step[(d - a) % 10] += 1; self.rstep[(d - a) % 10] += 1
            self.mk1[a][d] += 1; self.rmk1[a][d] += 1
            if len(h) >= 2:
                self.mk2[(h[-2], a)][d] += 1
        self.freq[d] += 1; self.last[d] = len(h); h.append(d)
    def scores(self):
        e, p, n = self.hist[-1], self.hist[-2], len(self.hist)
        S = {}
        tot = lambda x: sum(x) or 1
        S['step'] = [self.step[(d - e) % 10] for d in range(10)]
        S['markov1'] = list(self.mk1[e])
        S['markov2'] = [self.mk2[(p, e)][d] + 0.1 * self.mk1[e][d] for d in range(10)]
        S['freq'] = list(self.freq)
        S['recent step'] = [self.rstep[(d - e) % 10] for d in range(10)]
        S['recent markov1'] = list(self.rmk1[e])
        S['overdue'] = [n - self.last[d] for d in range(10)]
        st, m1, rs, rm = S['step'], S['markov1'], S['recent step'], S['recent markov1']
        S['step+markov1'] = [st[d] / tot(st) + m1[d] / tot(m1) for d in range(10)]
        S['step+markov1+recent'] = [S['step+markov1'][d] + rs[d] / tot(rs) + rm[d] / tot(rm) for d in range(10)]
        S['step x freq'] = [(st[d] + 1) * (self.freq[d] + 1) for d in range(10)]
        return S


def rank(sc, avoid=None):
    return sorted(range(10), key=lambda d: (d == avoid, -sc[d], d))

def main():
    res = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))
    for name, fl in charts():
        rep = sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / (len(fl) - 1)
        grp = 'low-repeat' if rep < 0.06 else 'normal'
        st = {'t': State('t'), 'u': State('u')}
        for i in range(len(fl) - 1):
            for x in st.values():
                x.add(fl[i])
            if i < 300:
                continue
            nxt = fl[i + 1]; half = 'H1' if i < (len(fl) + 300) // 2 else 'H2'
            for k, lab in (('t', 'OPEN'), ('u', 'CLOSE')):
                av = D(fl[i], 't') if (k == 't' and grp == 'low-repeat') else None
                for m, sc in st[k].scores().items():
                    r = rank(sc, av)
                    for g in (grp, 'all', f'{grp}:{name}', f'{grp}#{half}'):
                        a = res[(g, lab)][m]; a[0] += 1; a[1] += D(nxt, k) == r[0]; a[2] += D(nxt, k) in r[:3]
    for (g, lab), d in sorted(res.items()):
        if ':' in g or '#' in g:
            continue
        n = next(iter(d.values()))[0]
        print(f"\n{lab} — {g} charts ({n} predictions)   chance 10.0% / 30.0%")
        for m, (n_, h1, h3) in sorted(d.items(), key=lambda t: -(t[1][1] + t[1][2] / 3)):
            print(f"   {m:22s} top1 {100*h1/n_:5.1f}%   top3 {100*h3/n_:5.1f}%")
    print("\nper low-repeat chart (OPEN top1 / top3):")
    for (g, lab), d in sorted(res.items()):
        if g.startswith('low-repeat:') and lab == 'OPEN':
            print(f"   {g[11:]:4s}", '  '.join(f"{m} {100*v[1]/v[0]:.1f}/{100*v[2]/v[0]:.1f}" for m, v in d.items() if m in ('step', 'markov1', 'step+markov1', 'step+markov1+recent')))
    print("\nhalves (top1/top3) for the best few:")
    for (g, lab), d in sorted(res.items()):
        if '#' in g:
            print(f"   {lab:5s} {g:16s}", '  '.join(f"{m} {100*v[1]/v[0]:.1f}/{100*v[2]/v[0]:.1f}" for m, v in d.items() if m in ('step', 'markov1', 'step+markov1', 'step+markov1+recent', 'freq')))


if __name__ == '__main__':
    main()
