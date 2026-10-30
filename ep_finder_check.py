import sys, io, contextlib, os
import os; os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
import DataProcessing as D
from collections import Counter
hits=0; n=0; sizes=[]; kinds=Counter(); firstrow=0
for k in range(int(sys.argv[1]) if len(sys.argv) > 1 else 51, int(sys.argv[2]) if len(sys.argv) > 2 else 70):
    ds=f'rrr_datasets/f{k}.txt'; nxt=f'rrr_datasets/f{k+1}.txt'
    res=int(open(nxt).read().split()[-1])
    with contextlib.redirect_stdout(io.StringIO()):
        D.run(open(ds),None,None)
    ep=D._RRR_ASK['ep']; fd=D.ep_row_finder(ep, D._RRR_ASK['rows'])
    uniq={v[t][0] for *_,v in fd for t in D.EP_FINDER_VARIANTS}
    where=[(f"Op{p}",lab,t) for p,a,b,lab,v in fd for t in D.EP_FINDER_VARIANTS if v[t][0]==res]
    n+=1; sizes.append(len(uniq))
    if res in uniq:
        hits+=1
        for w in where: kinds[w[2]]+=1
        if fd and any(w[0]==f"Op{fd[0][0]}" for w in where): firstrow+=1
    print(f"F{k+1} EP {ep:02d} result {res:02d}: {'IN' if res in uniq else 'no'} ({len(uniq)} nums, {len(fd)} rows) {where[:3]}")
print(f"held {hits} of {n}; avg size {sum(sizes)/n:.1f} -> chance {sum(sizes)/n/100*n:.1f}; first row held {firstrow}; variants {dict(kinds)}")
