import os
import re

frontend_dir = 'frontend'

keywords = [
    'ORCA', 'RAIN-AI', 'monsoon', 'marine', 'ocean', 'argo',
    'PFZ', 'NWP', 'rainfall', 'MoES', 'NCMRWF', 'SIH', 'fisher', 'globe', 'leaflet', 'Groq'
]
keyword_regex = re.compile(r'\b(' + '|'.join(keywords) + r')\b', re.IGNORECASE)

found = False
for root, dirs, files in os.walk(frontend_dir):
    if 'node_modules' in root or '.next' in root:
        continue
    for f in files:
        if f == 'package-lock.json' or f == 'DESIGN_SYSTEM.md':
            continue
            
        file_path = os.path.join(root, f)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                matches = set(keyword_regex.findall(content))
                if matches:
                    print(f"File {file_path} contains: {', '.join(matches)}")
                    found = True
        except Exception:
            pass

if not found:
    print("Zero matches.")
