#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess


# Convert Translation Files
print('>> Convert Translation Files')
for ts in Path('resources', 'locale').glob('baram_*.ts'):
    qm = ts.with_suffix('.qm')
    if qm.is_file() and qm.stat().st_mtime >= ts.stat().st_mtime:
        print(f'  Skipping...   {ts} -> {qm}, Already Up-to-date')
    else:
        print(f'  Converting... {ts} -> {qm}')
        subprocess.run(['pyside6-lrelease', ts, '-qm', qm])


# Convert QResource File
target = Path('resource_rc.py')
source = Path('resource.qrc')
print('>> Convert QResource File')
if target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
    print(f'  Skipping...   {source} -> {target}, Already Up-to-date')
else:
    print(f'  Converting... {source} -> {target}')
    subprocess.run(['pyside6-rcc', source, '-o', target])


# Convert QT Designer Files
print('\n>> Convert QT Designer Files')
paths = list(Path('view').glob('**/*.ui'))  # Convert to 'list' to get the length of it
totalNum = len(paths)
for i, source in enumerate(paths):
    target = source.parent / (source.stem + '_ui.py')
    if target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
        print(f'  [{i+1}/{totalNum}] Skipping...   {source.name} -> {source.stem}_ui.py, Already Up-to-date')
    else:
        print(f'  [{i+1}/{totalNum}] Converting... {source.name} -> {source.stem}_ui.py')
        subprocess.run(['pyside6-uic', source, '-o', target])
