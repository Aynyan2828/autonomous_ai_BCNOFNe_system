import os
import glob

search_text = '/home/pi/autonomous_ai'
replace_text = '/home/pi/autonomous_ai_BCNOFNe_system'

count = 0
for ext in ['**/*.py', '**/*.yaml', '**/*.json', '**/*.md']:
    for filepath in glob.glob(ext, recursive=True):
        if 'venv' in filepath or '.git' in filepath or 'replace_paths' in filepath:
            continue
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            # Only replace if the target is NOT already the replaced version
            # E.g., if it says '/home/pi/autonomous_ai_something' we should be careful,
            # but usually it's exactly the search string.
            if search_text in content:
                # To prevent double replacing if it's already `/home/pi/autonomous_ai_BCNOFNe_system`
                # we can do a naive replace, then replace `autonomous_ai_BCNOFNe_system_BCNOFNe_system` back.
                
                content = content.replace(search_text, replace_text)
                content = content.replace(replace_text + '_BCNOFNe_system', replace_text)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f'Updated {filepath}')
                count += 1
        except Exception as e:
            pass
            
print(f"Total files updated: {count}")
