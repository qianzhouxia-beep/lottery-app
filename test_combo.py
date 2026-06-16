import sys
sys.path.insert(0, 'D:/AI/lottery-app')
from combo import expand_combo

tests = [
    ([7, 13, 20, 26, 33], [5, 8], 5, 2),
    ([7, 13, 20, 26, 33, 3], [5, 8], 6, 2),
    ([7, 13, 20, 26, 33, 3], [5, 8, 9], 6, 3),
    ([7, 13, 20, 26, 33, 3, 6], [5, 8], 7, 2),
]

labels = ['5+2 (5 front)', '6+2 (6 front)', '6+3 (6+3 front)', '7+2 (7 front)']
for (f, b, fc, bc), label in zip(tests, labels):
    r = expand_combo(f, b, fc, bc)
    print('%s: %d bets, %d yuan' % (label, r['count'], r['cost']))
