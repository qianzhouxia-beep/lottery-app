"""
Combination expansion for multi-select bets
Supports 5+2, 6+2, 7+2, 8+2, 6+3, 7+3, etc.
"""
from itertools import combinations

def expand_combo(front_pool, back_pool, front_count, back_count):
    if front_count < 5:
        front_count = 5
    if front_count > len(front_pool):
        front_count = len(front_pool)
    if back_count < 2:
        back_count = 2
    if back_count > len(back_pool):
        back_count = len(back_pool)

    top_front = list(front_pool[:front_count])
    top_back = list(back_pool[:back_count])

    front_combos = list(combinations(range(front_count), 5))
    back_combos = list(combinations(range(back_count), 2))

    combos = []
    for fi in front_combos:
        for bi in back_combos:
            combos.append({
                'front': [top_front[i] for i in fi],
                'back': [top_back[i] for i in bi]
            })

    n_combos = len(combos)
    cost = n_combos * 2

    return {
        'combos': combos,
        'count': n_combos,
        'cost': cost,
        'front_pool': top_front,
        'back_pool': top_back,
        'type': str(front_count) + '+' + str(back_count)
    }

def format_combo_display(result):
    typ = result['type']
    cnt = result['count']
    cost = result['cost']
    fp = result['front_pool']
    bp = result['back_pool']

    lines = ['=' * 40]
    lines.append('[COMBO: ' + typ + '] Total: ' + str(cnt) + ' bets, ' + str(cost) + ' yuan')
    lines.append('Front candidates: ' + str(fp))
    lines.append('Back candidates:  ' + str(bp))
    lines.append('-' * 40)
    for i, c in enumerate(result['combos'], 1):
        f = ','.join('%02d' % x for x in c['front'])
        b = ','.join('%02d' % x for x in c['back'])
        lines.append('  %2d. [%s] + [%s]' % (i, f, b))
    lines.append('=' * 40)
    return '\n'.join(lines)

if __name__ == '__main__':
    front_pool = [33, 26, 7, 13, 20, 19, 11, 5, 4, 22, 30, 16]
    back_pool = [8, 5, 11, 3, 6, 9]

    print('=== 5+2 (standard) ===')
    r = expand_combo(front_pool, back_pool, 5, 2)
    print(format_combo_display(r))

    print('\n=== 6+2 (double) ===')
    r = expand_combo(front_pool, back_pool, 6, 2)
    print(format_combo_display(r))

    print('\n=== 7+2 (triple) ===')
    r = expand_combo(front_pool, back_pool, 7, 2)
    print('  Total: ' + str(r['count']) + ' bets, ' + str(r['cost']) + ' yuan')

    print('\n=== 6+3 (double back) ===')
    r = expand_combo(front_pool, back_pool, 6, 3)
    print('  Total: ' + str(r['count']) + ' bets, ' + str(r['cost']) + ' yuan')

    print('\n=== 8+2 (quad) ===')
    r = expand_combo(front_pool, back_pool, 8, 2)
    print('  Total: ' + str(r['count']) + ' bets, ' + str(r['cost']) + ' yuan')
