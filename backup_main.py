# Create a backup of the original main.py
import shutil
import os

if os.path.exists('main.py.backup'):
    print("Backup already exists")
else:
    shutil.copy('main.py', 'main.py.backup')
    print("Created backup of main.py")