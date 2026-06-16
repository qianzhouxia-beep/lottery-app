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
    
    top_front = front_pool[:front_count]
    top_back = back_pool[:back_count]
    
    front_combos = list(combinations(range(front_count), 5))
    back_combos = list(combinations(range(back_count), 2))
    
    combos = []
    for fi in front_combos:
        for bi in back_combos:
            combos.append({
                'front': [top_front[i] for i in fi],
                'back': [top_back[i] for i in bi]
            })
    
    return {
        'combos': combos,
        'count': len(combos),
        'cost': len(combos) * 2,
        'front_pool': top_front,
        'back_pool': top_back,
        'type': f'{front_count}+{back_count}'
    }

front_pool = [33, 26, 7, 13, 20, 19, 11, 5, 4, 22, 30, 16]
back_pool = [8, 5, 11, 3, 6, 9]

for fc, bc in [(5,2),(6,2),(7,2),(8,2),(6,3),(7,3),(5,3)]:
    r = expand_combo(front_pool, back_pool, fc, bc)
    print(f'{fc}+{bc}: {r["count"]} combos, {r["cost"]} yuan')