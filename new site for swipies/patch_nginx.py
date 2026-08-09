import os
import re

for f_name in os.listdir('/etc/nginx/sites-enabled'):
    p = os.path.join('/etc/nginx/sites-enabled', f_name)
    if os.path.isfile(p):
        try:
            with open(p, 'r') as f:
                content = f.read()
            
            pattern = r"(add_header\s+['\"]Access-Control-Expose-Headers['\"]\s+['\"])([^'\"]+)(['\"]\s+always;)"
            
            def repl(m):
                prefix = m.group(1)
                values = m.group(2)
                suffix = m.group(3)
                if 'Authorization' not in values:
                    values = values + ',Authorization'
                return prefix + values + suffix
                
            new_content = re.sub(pattern, repl, content)
            if new_content != content:
                with open(p, 'w') as f:
                    f.write(new_content)
                print(f"Updated Nginx config: {p}")
            else:
                print(f"Nginx config {p} is already up to date.")
        except Exception as e:
            print(f"Error patching {p}: {e}")
