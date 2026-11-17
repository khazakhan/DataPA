"""ARROW study (2026-11-17, user: 'arrow shoot on middle pointer like hunter'): one single number
per round.  Candidate one-number rules are scored on all live rounds; the arrow rule is chosen on
the FIRST half only and tested on the SECOND half (chance 1%).  python3 tools/arrow_study.py"""
import json
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None and r.get('ep') is not None and r.get('after') is not None]
op = lambda a, b: ((b // 10 - a // 10) % 10, (b % 10 - a % 10) % 10)
app = lambda n, o: ((n // 10 + o[0]) % 10) * 10 + (n % 10 + o[1]) % 10
fc = lambda n: ((n // 10 + 5) % 10) * 10 + (n % 10 + 5) % 10
def f4(r): return (r.get('final8') or [])[:4] or r['ranked'][:4]
R = {
 'MASTER (FINAL 4 #1)': lambda r: f4(r)[0],
 'FINAL 4 #2': lambda r: f4(r)[1],
 'vote rank #1': lambda r: r['ranked'][0], 'vote rank #2': lambda r: r['ranked'][1],
 'vote rank #3': lambda r: r['ranked'][2], 'vote rank #4': lambda r: r['ranked'][3],
 'MASTER yx': lambda r: app(r['ep'], op(r['ep'], f4(r)[0])[::-1]),
 'EP full cut': lambda r: fc(r['after']), 'EP repeat': lambda r: r['after'], 'ROOT repeat': lambda r: r['ep'],
 'ROOT full cut': lambda r: fc(r['ep']),
 'STRONG 20 #1': lambda r: (r['lists'].get('strong') or [None])[0],
 'RECOMMENDED #1': lambda r: (r['lists'].get('rec') or [None])[0],
}
h = len(L) // 2
print('live rounds', len(L), '(chance 1% = about', round(h / 100, 1), 'per half)')
res = {}
for k, f in R.items():
    a = sum(f(r) == r['result'] for r in L[:h]); b = sum(f(r) == r['result'] for r in L[h:]); res[k] = (a, b)
    print(f'  {k:22s} first half {a:3d}  second half {b:3d}  total {a+b:3d} of {len(L)} ({100*(a+b)/len(L):.2f}%)')
best = max(R, key=lambda k: res[k][0])
print('ARROW rule picked on first half:', best, '-> second half', res[best][1], 'of', len(L) - h,
      f'({100*res[best][1]/(len(L)-h):.2f}%, chance 1%)')
