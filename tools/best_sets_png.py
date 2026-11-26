"""PNG of the best data sets (user 2026-11-27): FINAL 4 rate per set (live slot-4 rule) and
40-list rows passing 4 of 7, coloured by chart repeat rate. Output holdout_sets/best_sets_24.png."""
import sys
sys.path.insert(0, 'tools')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from slot4_study import load, picks

col = {'low': '#2a78d6', 'mid': '#1baf7a', 'high': '#eb6834'}
lab = {'low': 'Low repeat (<0.5%)', 'mid': 'Mid repeat (0.5–1.2%)', 'high': 'High repeat (>1.2%)'}
F, V, missing = [], [], []
for k in range(1, 25):
    R = load('set%02d' % k); n = len(R)
    rep = sum(R[i]['result'] == R[i - 1]['result'] for i in range(1, n)) / n
    c = 'low' if rep < 0.005 else 'mid' if rep < 0.012 else 'high'
    F.append(('Set %02d' % k, 100 * sum(r['result'] in picks(r, 0.010) for r in R) / n, c))
    try:   # sets 01-06: 40 list from the re-run file when it is complete
        import json
        extra = {j['pos']: j.get('rank_all') for j in map(json.loads, open(f'holdout_sets/set{k:02d}_r40.jsonl'))}
        for r in R:
            r['rank_all'] = r.get('rank_all') or extra.get(r['pos'])
    except (OSError, ValueError):
        pass
    rows = {}
    for r in R:
        rows.setdefault(r['pos'] // 7, []).append(r)
    full = [rows[x] for x in sorted(rows) if len(rows[x]) == 7 and all(r.get('rank_all') for r in rows[x])]
    if len(full) > 80 and len(full) > 0.5 * len(rows):
        hits = [sum(r['result'] in r['rank_all'][:40] for r in rw) for rw in full]
        V.append(('Set %02d' % k, 100 * sum(h >= 4 for h in hits) / len(hits), c))
    else:
        missing.append('%02d' % k)
INK, MUTED, GRID = '#2b2b29', '#77776f', '#e6e5df'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'text.color': INK,
                     'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': INK})
fig, axs = plt.subplots(1, 2, figsize=(14, 9), dpi=150, facecolor='white')


def panel(ax, data, chance, title, xlab, fmt, xmax):
    data = sorted(data, key=lambda x: x[1])
    y = list(range(len(data)))
    ax.barh(y, [d[1] for d in data], height=0.68, color=[col[d[2]] for d in data], edgecolor='white', linewidth=2)
    for i, d in enumerate(data):
        ax.text(max(d[1], chance) + xmax * 0.012, i, fmt % d[1], va='center', fontsize=9, color=INK,
                fontweight='bold' if d[1] >= chance else 'normal')
    ax.set_yticks(y); ax.set_yticklabels([d[0] for d in data])
    ax.axvline(chance, color=INK, linestyle=(0, (4, 3)), linewidth=1.2)
    ax.text(chance, len(data) - 0.3, f' chance {fmt % chance}', fontsize=9, color=INK, va='bottom')
    ax.set_xlim(0, xmax); ax.set_ylim(-0.6, len(data) + 0.4)
    ax.set_title(title, loc='left', fontsize=12.5, fontweight='bold', color=INK, pad=12)
    ax.set_xlabel(xlab)
    ax.grid(axis='x', color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    for s in ['top', 'right', 'left']:
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID); ax.tick_params(axis='y', length=0)


panel(axs[0], F, 4.0, 'OCJP FINAL 4 hit rate per set (live script)', 'Hit rate per round (%)', '%.2f%%', 6.0)
panel(axs[1], V, 29.0, '40-number list: rows passing 4 of 7', 'Share of 7-round rows with 4+ hits (%)', '%.1f%%', 50)
if missing:
    axs[1].text(0, -0.12, f"Not shown (40 list not saved yet, re-run in progress): sets {', '.join(missing)}.",
                transform=axs[1].transAxes, fontsize=8.5, color=MUTED)
fig.legend(handles=[Patch(color=col[k], label=lab[k]) for k in col], loc='upper center', ncol=3, frameon=False,
           bbox_to_anchor=(0.5, 0.955), fontsize=10)
fig.suptitle('Best data sets — 24-set walk-forward test (54,709 rounds)', x=0.06, y=0.995, ha='left',
             fontsize=15, fontweight='bold', color=INK)
fig.text(0.06, 0.015, 'Each round predicted from earlier numbers only. Bold = above chance. '
         'Low-repeat charts (blue) are where both lists do best.', fontsize=9, color=MUTED)
plt.tight_layout(rect=(0, 0.03, 1, 0.93))
plt.savefig('holdout_sets/best_sets_24.png', facecolor='white')
print('saved holdout_sets/best_sets_24.png')
