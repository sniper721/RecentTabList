#!/usr/bin/env python3
"""
Clean up the main.py file by removing orphaned code
"""

def clean_main_file():
    """Remove orphaned code sections"""
    
    try:
        with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Find the last proper function end
        lines = content.split('\n')
        cleaned_lines = []
        in_orphaned_section = False
        
        for i, line in enumerate(lines):
            # Skip orphaned code that starts with indentation but no function
            if line.strip().startswith('# Handle password change') and not any('def ' in prev_line for prev_line in lines[max(0, i-10):i]):
                in_orphaned_section = True
                continue
            
            # Skip lines that are clearly orphaned (indented but no function context)
            if in_orphaned_section and (line.startswith('    ') or line.strip() == ''):
                continue
            
            # Reset when we hit a proper function or route
            if line.startswith('@app.route') or line.startswith('def ') or line.startswith('if __name__'):
                in_orphaned_section = False
            
            cleaned_lines.append(line)
        
        # Write cleaned content
        cleaned_content = '\n'.join(cleaned_lines)
        
        with open('main.py', 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print("✅ Cleaned main.py file")
        print(f"Removed {len(lines) - len(cleaned_lines)} orphaned lines")
        
    except Exception as e:
        print(f"❌ Error cleaning file: {e}")

if __name__ == "__main__":
    clean_main_file()