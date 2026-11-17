import re
src = open('/root/Documents/stockmarket/php/stockmarket-app/detection_triggers.py').read()
for name in ('KNOWN_TSX', 'KNOWN_US'):
    m = re.search(name + r' = \{(.*?)\}', src, re.DOTALL)
    if m:
        content = m.group(1)
        items = re.findall(r"'([^']+)'", content)
        print(name, len(items))
        print(sorted(items))
