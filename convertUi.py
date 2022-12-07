#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess


# Convert Translation Files
print('>> Convert Translation Files')
for ts in Path('resources', 'locale').glob('baram_*.ts'):
    qm = ts.with_suffix('.qm')
    subprocess.run(['pyside6-lrelease', ts, '-qm', qm])


# Convert QResource File
print('>> Convert QResource File')
print(f'  Converting... resource.qrc -> resource_rc.py')
subprocess.run(['pyside6-rcc', 'resource.qrc', '-o', 'resource_rc.py'])


# Convert QT Designer Files
print('\n>> Convert QT Designer Files')
paths = list(Path('view').glob('**/*.ui'))  # Convert to 'list' to get the length of it
totalNum = len(paths)
for i, p in enumerate(paths):
    print(f'  [{i+1}/{totalNum}] Converting... {p.name} -> {p.stem}_ui.py')
    subprocess.run(['pyside6-uic',  p, '-o', f'{p.parent/p.stem}_ui.py'])
