"""CEILING study (user 2026-11-05: 'go another time for deep dive'): how much
do past numbers tell about the next one at all?  Uses every number sequence of
the newest dataset of each series.  For several 'what came before' contexts it
measures, on held-out halves, how often the best 4 numbers for that context
(learnt on the other half) hold the next number.  Compared with the same test
on shuffled sequences (where nothing can be learnt)."""
import glob, re, os, sys, io, contextlib, collections, random
os.chdir('/home/khazakhan/DataScinceAnal'); sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
newest = {}
for f in glob.glob('rrr_datasets/*.txt'):
    m = re.match(r'rrr_datasets/([a-z]+)(\d+)\.txt$', f)
    if m and int(m.group(2)) >= newest.get(m.group(1), (0, ''))[0]: newest[m.group(1)] = (int(m.group(2)), f)
SEQ = []
for s, (_, f) in sorted(newest.items()):
    tk = [int(x) for x in open(f).read().split() if x.isdigit() and int(x) <= 99]
    SEQ.append(tk)
N = sum(len(s) for s in SEQ)
print(f"series {len(SEQ)}, numbers {N}")
c = collections.Counter(v for s in SEQ for v in s)
print(f"most common numbers: {c.most_common(4)}  least: {c.most_common()[-3:]}  (even = {N/100:.0f} each)")
CTX = {
  'nothing (most frequent overall)': lambda s, i: 0,
  'last number': lambda s, i: s[i - 1],
  'last two numbers': lambda s, i: (s[i - 2], s[i - 1]),
  'last op (x,y move of last step)': lambda s, i: (D.find_op(s[i-2]//10, s[i-1]//10), D.find_op(s[i-2]%10, s[i-1]%10)),
  'last two ops': lambda s, i: tuple((D.find_op(s[j-1]//10, s[j]//10), D.find_op(s[j-1]%10, s[j]%10)) for j in (i-2, i-1)),
  'last number tens / units digit': lambda s, i: s[i - 1] // 10,
}
def test(seqs, ctx, predict_op):
    hits = tot = 0
    for half in (0, 1):
        T = collections.defaultdict(collections.Counter)
        for k, s in enumerate(seqs):
            for i in range(3, len(s)):
                if (i % 2) != half:
                    key = ctx(s, i); tgt = s[i]
                    if predict_op: tgt = (D.find_op(s[i-1]//10, s[i]//10), D.find_op(s[i-1]%10, s[i]%10))
                    T[key][tgt] += 1
        for s in seqs:
            for i in range(3, len(s)):
                if (i % 2) == half:
                    key = ctx(s, i)
                    top = [t for t, _ in T[key].most_common(4)]
                    if predict_op: top = [D.apply_op(s[i-1]//10, x)*10 + D.apply_op(s[i-1]%10, y) for x, y in top]
                    hits += s[i] in top; tot += 1
    return hits / tot * 100
rng = random.Random(1)
SH = [rng.sample(s, len(s)) for s in SEQ]
print("best 4 numbers learnt from what came before, held-out, % of next numbers held (chance 4.0%):")
print(f"   {'context':42s} {'real':>6s} {'shuffled':>9s}")
for nm, ctx in CTX.items():
    for po in (False, True):
        if nm.startswith('nothing') and po: continue
        lab = nm + (' -> next op' if po else '')
        print(f"   {lab:42s} {test(SEQ, ctx, po):5.1f}% {test(SH, ctx, po):8.1f}%")
