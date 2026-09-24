import os
import re

frontend_dir = 'frontend'

hex_to_ink = {
    '#040c1d': 'ink-800',
    '#020612': 'ink-900',
    '#010613': 'ink-950',
    '#050c1e': 'ink-700'
}

# Regex to match these hex codes (case-insensitive)
hex_regex = re.compile(r'(?i)(#040c1d|#020612|#010613|#050c1e)')

# Regex for animation classes
anim_regex = re.compile(r'\b(animate-in|fade-in|duration-\w+)\b')

def replace_hex(match):
    return hex_to_ink[match.group(1).lower()]

for root, dirs, files in os.walk(frontend_dir):
    if 'node_modules' in root or '.next' in root:
        continue
    for f in files:
        if not f.endswith(('.tsx', '.ts', '.css')):
            continue
            
        file_path = os.path.join(root, f)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Replace hex codes
            # Actually wait, hex codes inside Tailwind classes like `bg-[#040c1d]` should become `bg-ink-800`.
            # If they are `bg-[hex]`, we need to replace `bg-[#040c1d]` with `bg-ink-800`.
            
            # Replace bg-[hex] pattern
            for hex_code, ink_token in hex_to_ink.items():
                content = re.sub(r'bg-\[' + hex_code + r'\]', f'bg-{ink_token}', content, flags=re.IGNORECASE)
                content = re.sub(r'border-\[' + hex_code + r'\]', f'border-{ink_token}', content, flags=re.IGNORECASE)
                content = re.sub(r'text-\[' + hex_code + r'\]', f'text-{ink_token}', content, flags=re.IGNORECASE)
                content = re.sub(r'from-\[' + hex_code + r'\]', f'from-{ink_token}', content, flags=re.IGNORECASE)
                content = re.sub(r'to-\[' + hex_code + r'\]', f'to-{ink_token}', content, flags=re.IGNORECASE)
                content = re.sub(r'via-\[' + hex_code + r'\]', f'via-{ink_token}', content, flags=re.IGNORECASE)

            # Replace animation classes
            content = anim_regex.sub('', content)

            # Also replace any remaining raw hexes just in case
            # Wait, replacing raw hex in CSS
            if f.endswith('.css'):
                for hex_code, ink_token in hex_to_ink.items():
                    # We will just map them using CSS variables in globals.css anyway
                    pass

            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
