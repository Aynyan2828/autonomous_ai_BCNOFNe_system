import os
import glob

def fix_git_conflict(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    kept_lines = []
    state = 'NORMAL'  # NORMAL, KEEP_UPSTREAM, DISCARD_STASHED
    
    has_conflict = False
    for line in lines:
        if line.startswith('<<<<<<< Updated upstream'):
            has_conflict = True
            state = 'KEEP_UPSTREAM'
            continue
        elif line.startswith('======='):
            if state == 'KEEP_UPSTREAM':
                state = 'DISCARD_STASHED'
            continue
        elif line.startswith('>>>>>>> Stashed changes'):
            if state == 'DISCARD_STASHED':
                state = 'NORMAL'
            continue
            
        if state == 'NORMAL' or state == 'KEEP_UPSTREAM':
            kept_lines.append(line)
            
    if has_conflict:
        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(kept_lines)
    return has_conflict

changed = 0
for filepath in glob.glob('src/**/*.py', recursive=True):
    if fix_git_conflict(filepath):
        print(f"Fixed {filepath}")
        changed += 1

print(f"Total fixed: {changed}")
