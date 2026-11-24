"""Single-pick study (user AF319: 'more MASTER / KING hits').

Walk-forward test of every one-number pick the live log already records,
plus two combined pickers:
  VOTE  - the number named by the most single-pick slots this round
  ADAPT - each round, use the slot with the best record over the PREVIOUS
          rounds only (no look-ahead)
Chance for one number = 1%.  Usage: python3 tools/single_pick_study.py
"""
import json
from collections import Counter, defaultdict

LIVE = 'rrr_records/live.jsonl'


def load_side(path, key):
    out = {}
    try:
        for line in open(path):
            r = json.loads(line)
            out[r['round']] = r.get(key)
    except FileNotFoundError:
        pass
    return out


def slots(r, mops, s1):
    """All single-number picks for one round, as {slot name: number}."""
    s = {}
    f8 = r.get('final8') or []
    for i, n in enumerate(f8):
        s[f'FINAL8 #{i+1}'] = n
    s['KING (EP repeat)'] = r.get('after')
    s['ROOT repeat'] = r.get('ep')
    for i, n in enumerate((r.get('ranked') or [])[:4]):
        s[f'ranked #{i+1}'] = n
    for i, n in enumerate((r.get('prime10') or [])[:2]):
        s[f'PRIME10 #{i+1}'] = n
    for i, n in enumerate((r.get('lastop') or [])[:4]):
        s[f'LAST-OP #{i+1}'] = n
    if r.get('r28'):
        s['Rule 28 #1'] = r['r28'][0]
    for k, v in ((r.get('one_row') or {}).get('lines') or {}).items():
        s['ONE ROW ' + k[:28]] = v
    for k, v in (r.get('lists') or {}).items():
        if k.startswith('rule') and v:
            s[f'gun {k} #1'] = v[0]
    p = mops.get(r['round'])
    if p:
        for i, n in enumerate(p):
            s[f'MASTER op form {i+1}'] = n
    p = s1.get(r['round'])
    if p:
        s['STRONG 20 #1'] = p[0]
    return {k: v for k, v in s.items() if isinstance(v, int)}


def main():
    rows = [json.loads(l) for l in open(LIVE)]
    rows = [r for r in rows if r.get('result') is not None and r.get('final8')]
    mops = load_side('rrr_records/master_ops10_live.jsonl', 'pick')
    s1 = load_side('rrr_records/strong1_live.jsonl', 'pick')
    n = len(rows)
    half = n // 2
    hits = defaultdict(lambda: [0, 0])   # slot -> [hits 1st half, 2nd half]
    seen = defaultdict(lambda: [0, 0])
    vote = [0, 0]
    adapt = [0, 0]
    past = Counter()
    past_n = Counter()
    for i, r in enumerate(rows):
        h = 0 if i < half else 1
        res = r['result']
        s = slots(r, mops, s1)
        # ADAPT: best past rate among slots present now (min 50 past rounds)
        cand = [k for k in s if past_n[k] >= 50]
        if cand:
            best = max(cand, key=lambda k: (past[k] / past_n[k], k == 'FINAL8 #1'))
            adapt[h] += s[best] == res
        else:
            adapt[h] += s.get('FINAL8 #1') == res
        c = Counter(s.values())
        top = max(c, key=lambda x: (c[x], x == s.get('FINAL8 #1')))
        vote[h] += top == res
        for k, v in s.items():
            seen[k][h] += 1
            hits[k][h] += v == res
            past[k] += v == res
            past_n[k] += 1
    print(f'{n} logged rounds (1st half {half}, 2nd half {n-half}); chance 1% per pick')
    print(f"{'slot':40} {'1st half':>12} {'2nd half':>12} {'all %':>7}")
    order = sorted(hits, key=lambda k: -(sum(hits[k]) / max(1, sum(seen[k]))))
    for k in order:
        a, b = hits[k]
        na, nb = seen[k]
        if na + nb < 100:
            continue
        print(f'{k:40} {a:>4} of {na:<5} {b:>4} of {nb:<5} {100*(a+b)/(na+nb):6.2f}')
    print(f"{'VOTE (most slots)':40} {vote[0]:>4} of {half:<5} {vote[1]:>4} of {n-half:<5} {100*sum(vote)/n:6.2f}")
    print(f"{'ADAPT (best past slot)':40} {adapt[0]:>4} of {half:<5} {adapt[1]:>4} of {n-half:<5} {100*sum(adapt)/n:6.2f}")


if __name__ == '__main__':
    main()
