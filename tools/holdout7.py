"""Frozen 7-round holdout test for one data set (user AF338: 24 data sets).

The last K numbers of the set are hidden. For each of them the unchanged
script is run on everything BEFORE it (in a throwaway sandbox copy, so no live record changes)
and its picks are compared with the hidden number.
Pass = OCJP FINAL 4 holds the number in >= 4 of the 7 rounds.

Usage: python3 tools/holdout7.py holdout_sets/set01.txt [K=7]
Result is also appended to holdout_sets/results.jsonl.
"""
import json
import os
import re
import shutil
import tempfile
import subprocess
import sys

ANSI = re.compile(r'\x1b\[[0-9;]*m')


def truncate(lines, drop):
    """Remove the last `drop` number tokens (row order), keep layout."""
    out = [l.rstrip('\n') for l in lines]
    while drop > 0 and out:
        l = out[-1]
        m = list(re.finditer(r'\S+', l))
        if not m:
            out.pop()
            continue
        l = l[:m[-1].start()].rstrip()
        drop -= 1
        if l.strip():
            out[-1] = l
        else:
            out.pop()
    return '\n'.join(out) + '\n'


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKED = {'.git', 'rrr_outputs', 'rrr_datasets', 'holdout_sets'}


def sandbox():
    """Fresh throwaway copy of the project: the script may log to its own
    rrr_records there, the real live records are never touched, and every
    round starts from the same frozen records."""
    d = tempfile.mkdtemp(prefix='holdout_')
    for name in os.listdir(REPO):
        src = os.path.join(REPO, name)
        if name in LINKED:
            if name != '.git':
                os.symlink(src, os.path.join(d, name))
        elif os.path.isdir(src):
            shutil.copytree(src, os.path.join(d, name), symlinks=True)
        else:
            shutil.copy2(src, d)
    return d


def picks(text):
    env = {k: v for k, v in os.environ.items() if k != 'CHAT_PAGE_ROUND'}
    box = sandbox()
    try:
        p = subprocess.run([sys.executable, 'DataProcessing.py'], input=text + 'END\n',
                           capture_output=True, text=True, env=env, cwd=box)
    finally:
        shutil.rmtree(box, ignore_errors=True)
    o = ANSI.sub('', p.stdout)
    nums = lambda s: [int(x) for x in re.findall(r'\b\d{2}\b', s)]
    f4 = re.search(r'FINAL 4 for the next round: ([\d, ]+)', o)
    f10 = re.search(r'OCJP FINAL 10: ([\d · ]+)\(', o)
    b60 = re.search(r'BUILDER 60 ascending: ([\d ]+)', o)
    king = re.search(r'KING PICK = ARROW[^│]*│\s*(\d{2})', o)
    f4 = nums(f4.group(1)) if f4 else []
    return {
        'final4': f4,
        'master': f4[0] if f4 else None,
        'king': int(king.group(1)) if king else None,
        'final10': nums(f10.group(1)) if f10 else [],
        'builder60': nums(b60.group(1)) if b60 else [],
    }


def main():
    path = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    lines = open(path).readlines()
    toks = [t for l in lines for t in l.split()]
    rows = []
    for i in range(k, 0, -1):
        hidden = toks[-i]
        res = int(hidden) if hidden.isdigit() else None
        p = picks(truncate(lines, i))
        rows.append((k - i + 1, res, p))
    name = os.path.basename(path)
    print(f'{name}: {len(toks)} numbers, last {k} hidden')
    print('| Round | Result | OCJP FINAL 4 | F4 | MASTER | KING | FINAL 10 | Builder 60 |')
    print('|---|---|---|---|---|---|---|---|')
    tot = {'f4': 0, 'm': 0, 'k': 0, 'f10': 0, 'b': 0}
    for n, res, p in rows:
        hit = lambda c: res is not None and c
        f4 = hit(res in p['final4']); m = hit(res == p['master']); kg = hit(res == p['king'])
        f10 = hit(res in p['final10']); b = hit(res in p['builder60'])
        for key, v in zip(tot, (f4, m, kg, f10, b)):
            tot[key] += bool(v)
        mk = lambda v: '✅' if v else '✗'
        r = f'{res:02d}' if res is not None else '**'
        print(f"| {n} | **{r}** | {' '.join(f'{x:02d}' for x in p['final4'])} | {mk(f4)} | "
              f"{p['master']:02d} {mk(m)} | {p['king']:02d} {mk(kg)} | {mk(f10)} | {mk(b)} |")
    verdict = 'PASS' if tot['f4'] >= 4 else 'not passed'
    print(f"\n**{name}: FINAL 4 {tot['f4']} of {k} — {verdict}** · MASTER {tot['m']} · KING {tot['k']} · "
          f"FINAL 10 {tot['f10']} · Builder 60 {tot['b']} of {k}")
    with open('holdout_sets/results.jsonl', 'a') as fh:
        fh.write(json.dumps({'set': name, 'k': k, 'final4': tot['f4'], 'master': tot['m'],
                             'king': tot['k'], 'final10': tot['f10'], 'builder60': tot['b'],
                             'pass': tot['f4'] >= 4}) + '\n')


if __name__ == '__main__':
    main()
