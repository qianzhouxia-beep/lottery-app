content = open('D:/AI/lottery-app/web/index.html', 'rb').read()
# Find all 'if (!pred) return;' occurrences
positions = []
i = 0
while True:
    pos = content.find(b'if (!pred) return;', i)
    if pos == -1:
        break
    positions.append(pos)
    i = pos + 1

print('Found %d occurrences' % len(positions))
for i, pos in enumerate(positions):
    print('  %d at %d: %r' % (i+1, pos, content[pos-50:pos+30]))

# Remove duplicate second occurrence
if len(positions) >= 2:
    # The second occurrence is at positions[1]
    # We want to keep the first and remove the second (duplicate)
    dup_pos = positions[1]
    # Find the start of the line containing the duplicate
    line_start = content.rfind(b'\n', 0, dup_pos) + 1
    print('Removing duplicate at line start %d: %r' % (line_start, content[line_start:dup_pos+20]))
    content = content[:line_start] + content[dup_pos+20:]
    print('Fixed: duplicate removed')
    with open('D:/AI/lottery-app/web/index.html', 'wb') as f:
        f.write(content)
    print('Written. New size:', len(content))
