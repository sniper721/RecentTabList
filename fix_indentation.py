import re

# Read main.py
with open('c:\\RTL\\main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the problematic API function
in_api_function = False
fixed_lines = []
skip_until_next_decorator = False

for i, line in enumerate(lines):
   if skip_until_next_decorator:
       if line.startswith('@app.route'):
            skip_until_next_decorator = False
            fixed_lines.append(line)
       continue
    
   if '# API endpoint for background level loading' in line:
        in_api_function = True
        # Replace with properly indented version
        fixed_lines.extend([
            "# API endpoint for background level loading\n",
            "@app.route('/api/levels/main')\n",
            "def api_get_main_levels():\n",
            '    """API endpoint to get main list levels - for background loading"""\n',
            "  try:\n",
            "        # Get fresh data from MongoDB\n",
            "        main_list = list(mongo_db.levels.find(\n",
            '            {"is_legacy": False},\n',
            '            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1, "min_percentage": 1}\n',
            '        ).sort("position", 1))\n',
            "\n",
            "        # Check for April Fools mode\n",
            "        april_fools_active = is_april_fools_active()\n",
            "      if april_fools_active:\n",
            "            main_list = randomize_level_positions(main_list.copy())\n",
            "\n",
            "      return {\n",
            "            'success': True,\n",
            "            'levels': main_list,\n",
            "            'total_levels': len(main_list),\n",
            "            'april_fools_active': april_fools_active\n",
            "        }\n",
            "    except Exception as e:\n",
            '        print(f"Error in API endpoint for main levels: {e}")\n',
            "      return {\n",
            "            'success': False,\n",
            "            'error': str(e),\n",
            "            'levels': [],\n",
            "            'total_levels': 0\n",
            "        }, 500\n",
            "\n"
        ])
        skip_until_next_decorator = True
        continue
    
   if not skip_until_next_decorator:
        fixed_lines.append(line)

# Write back
with open('c:\\RTL\\main.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ Fixed main.py API endpoint!")
