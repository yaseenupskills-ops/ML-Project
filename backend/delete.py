import os
import shutil

frontend_dir = 'frontend'

folders_to_delete = [
    'backend', 'database', 'docs', 'documentations', '.claude', 'data',
    'lib/mock', 'lib/geo', 'lib/store', 'store',
    'components/3d', 'components/map', 'components/chat', 'components/dashboard',
    'app/app/conversations', 'app/app/globe', 'app/app/map'
]

files_to_delete = [
    'TECH_STACK.md', 'FRONTEND_AND_API_SPECIFICATION.md', 'README.md',
    'components/ui/area-chart-1.tsx', 'components/layout/ContextPanel.tsx',
    'lib/languages.ts'
]

for fd in folders_to_delete:
    path = os.path.join(frontend_dir, fd)
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"Deleted folder {path}")

for fl in files_to_delete:
    path = os.path.join(frontend_dir, fl)
    if os.path.exists(path):
        os.remove(path)
        print(f"Deleted file {path}")

# public/: delete everything except app/favicon.ico
public_dir = os.path.join(frontend_dir, 'public')
for root, dirs, files in os.walk(public_dir, topdown=False):
    for name in files:
        file_path = os.path.join(root, name)
        rel = os.path.relpath(file_path, public_dir).replace('\\', '/')
        if rel != 'app/favicon.ico' and rel != 'favicon.ico':
            os.remove(file_path)
            print(f"Deleted public file {file_path}")
    
    for name in dirs:
        dir_path = os.path.join(root, name)
        # remove if empty
        if not os.listdir(dir_path):
            os.rmdir(dir_path)
            print(f"Deleted empty public dir {dir_path}")

