#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
import subprocess

FOLDERS = ['baramFlow/view', 'baramMesh/view', 'widgets']

force_update = False
if len(sys.argv) > 1 and sys.argv[1] == '-f':
    force_update = True

# Convert Translation Files
print('>> Convert Translation Files')
for ts in Path('resources', 'locale').glob('baram_*.ts'):
    qm = ts.with_suffix('.qm')
    if not force_update and qm.is_file() and qm.stat().st_mtime >= ts.stat().st_mtime:
        print(f'  Skipping...   {ts} -> {qm}, Already Up-to-date')
    else:
        print(f'  Converting... {ts} -> {qm}')
        subprocess.run(['pyside6-lrelease', ts, '-qm', qm])


# Convert QResource File
target = Path('resource_rc.py')
source = Path('resource.qrc')
print('>> Convert QResource File')
if not force_update and target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
    print(f'  Skipping...   {source} -> {target}, Already Up-to-date')
else:
    print(f'  Converting... {source} -> {target}')
    subprocess.run(['pyside6-rcc', source, '-o', target])


# Convert QT Designer Files
print('\n>> Convert QT Designer Files')
paths = []
for folder in FOLDERS:
    paths += list(Path(folder).glob('**/*.ui'))  # Convert to 'list' to get the length of it

totalNum = len(paths)

for i, source in enumerate(paths):
    target = source.parent / (source.stem + '_ui.py')
    if not force_update and target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
        print(f'  [{i+1}/{totalNum}] Skipping...   {source.name} -> {source.stem}_ui.py, Already Up-to-date')
    else:
        print(f'  [{i+1}/{totalNum}] Converting... {source.name} -> {source.stem}_ui.py')
        subprocess.run(['pyside6-uic', source, '-o', target])
