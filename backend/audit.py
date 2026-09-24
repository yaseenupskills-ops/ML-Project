import os
import json
import re

frontend_dir = 'frontend'

folders_to_delete = {
    'backend', 'database', 'docs', 'documentations', '.claude', 'data',
    'lib/mock', 'lib/geo', 'lib/store', 'store',
    'components/3d', 'components/map', 'components/chat', 'components/dashboard',
    'app/app/conversations', 'app/app/globe', 'app/app/map'
}

files_to_delete = {
    'TECH_STACK.md', 'FRONTEND_AND_API_SPECIFICATION.md', 'README.md',
    'components/ui/area-chart-1.tsx', 'components/layout/ContextPanel.tsx',
    'lib/languages.ts'
}

keep_untouched = {
    'AGENTS.md', 'CLAUDE.md', 'DESIGN_SYSTEM.md', '.gitignore',
    '.gitattributes', 'eslint.config.mjs', 'postcss.config.mjs', 'tsconfig.json'
}

keywords = [
    'ORCA', 'RAIN-AI', 'monsoon', 'marine', 'ocean', 'argo',
    'PFZ', 'NWP', 'rainfall', 'MoES', 'NCMRWF', 'SIH', 'fisher', 'globe', 'leaflet', 'Groq'
]

def normalize_path(p):
    return p.replace('\\', '/')

print("=== PHASE 1: AUDIT ===")
print("\n--- FILES & FOLDERS ---")

for root, dirs, files in os.walk(frontend_dir):
    rel_root = normalize_path(os.path.relpath(root, frontend_dir))
    if rel_root == '.':
        rel_root = ''
    
    for d in dirs:
        rel_path = normalize_path(os.path.join(rel_root, d)) if rel_root else d
        status = 'KEEP'
        if any(rel_path == fd or rel_path.startswith(fd + '/') for fd in folders_to_delete):
            status = 'DELETE'
        elif rel_path == 'public':
            status = 'KEEP (contents will be deleted except favicon)'
        print(f"Folder: {rel_path} -> {status}")
        
    for f in files:
        rel_path = normalize_path(os.path.join(rel_root, f)) if rel_root else f
        status = 'REWRITE'
        if any(rel_path.startswith(fd + '/') for fd in folders_to_delete):
            status = 'DELETE'
        elif rel_path in files_to_delete:
            status = 'DELETE'
        elif rel_path.startswith('public/') and rel_path != 'public/app/favicon.ico' and rel_path != 'public/favicon.ico' and rel_path != 'public/app/favicon.ico' and rel_path != 'app/favicon.ico':
            status = 'DELETE'
        elif rel_path in keep_untouched:
            status = 'KEEP'
        print(f"File: {rel_path} -> {status}")

print("\n--- KEYWORD MATCHES ---")
keyword_regex = re.compile(r'\b(' + '|'.join(keywords) + r')\b', re.IGNORECASE)

for root, dirs, files in os.walk(frontend_dir):
    for f in files:
        file_path = os.path.join(root, f)
        rel_path = normalize_path(os.path.relpath(file_path, frontend_dir))
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                matches = set(keyword_regex.findall(content))
                if matches:
                    print(f"File {rel_path} contains: {', '.join(matches)}")
        except Exception:
            pass

print("\n--- DEPENDENCIES ---")
try:
    with open(os.path.join(frontend_dir, 'package.json'), 'r') as f:
        pkg = json.load(f)
        deps = list(pkg.get('dependencies', {}).keys()) + list(pkg.get('devDependencies', {}).keys())
        
        deps_to_remove = {
            'three', '@react-three/fiber', '@react-three/drei', '@types/three', 'leaflet',
            'react-leaflet', '@types/leaflet', 'lottie-react', 'reaviz', 'react-markdown', 'framer-motion'
        }
        for d in deps:
            if d in deps_to_remove:
                print(f"{d} -> unused (to remove)")
            else:
                print(f"{d} -> used (to keep)")
except Exception as e:
    print("Could not read package.json:", e)
