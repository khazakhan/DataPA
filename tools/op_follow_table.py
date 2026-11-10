"""History table (user 2026-11-11: 'some times replaces nc with cut, -1 with nc, +1 with cut ... check from
history'): after an operation, which operation came next and how often, per side (x = tens, y = units).
Frame A: op into the EP -> op of the next number.  Frame B: op earlier-EP -> ROOT -> op ROOT -> result.
Usage: python3 tools/op_follow_table.py [series letters, default z]"""
import os, sys, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, 'tools')
from oc_deep_study import charts
NAME = {0: 'nc', 1: '+1', 2: '+2', 3: 'c-2', 4: 'c-1', 5: 'cut', 6: 'c+1', 7: 'c+2', 8: '-2', 9: '-1'}
ORDER = [0, 1, 9, 2, 8, 5, 6, 4, 7, 3]
want = sys.argv[1] if len(sys.argv) > 1 else 'z'
T, U = (lambda v: v // 10), (lambda v: v % 10)
for frame in ('A', 'B'):
    C = [[collections.Counter() for _ in range(10)] for _ in range(2)]
    for name, fl in charts():
        if name not in want:
            continue
        last = {}
        for i in range(1, len(fl) - 1):
            ep, nx = fl[i], fl[i + 1]
            if frame == 'A':
                src, tgt = (fl[i - 1], ep), (ep, nx)
            else:
                j = last.get(ep)
                last[ep] = i
                if j is None or j + 1 >= i:
                    continue
                root = fl[j + 1]; src, tgt = (ep, root), (root, nx)
            for side, f in enumerate((T, U)):
                C[side][(f(src[1]) - f(src[0])) % 10][(f(tgt[1]) - f(tgt[0])) % 10] += 1
            if frame == 'A':
                last[ep] = i
    for side, lab in enumerate(('x (tens)', 'y (units)')):
        print(f"\nFrame {frame} ({'op into EP -> next op' if frame == 'A' else 'ROOT op -> op on ROOT to result'}), {lab}, charts '{want}': % of next ops")
        print('   after  ' + ''.join(f"{NAME[o]:>6s}" for o in ORDER) + '    n   top next op')
        for s in ORDER:
            row = C[side][s]; n = sum(row.values())
            if not n:
                continue
            best = max(row, key=row.get)
            print(f"   {NAME[s]:6s} " + ''.join(f"{100*row[o]/n:6.1f}" for o in ORDER) + f"  {n:4d}   {NAME[best]} {100*row[best]/n:.1f}%")
