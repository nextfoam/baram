#!/usr/bin/env python3
# -*-coding:utf8-*-
# !/bin/bash

import os
import platform
import sys
import fnmatch
from pathlib import Path


# findFiles (v2.02)
def findFiles(startFindPath='.', filters=['*'], recursive=True, excludeDirs=[], excludeFiles=[], includeFullPath=True, sortFiles=True):
    foundFiles = []
    startFindPath = Path(startFindPath)
    for fullPath, subPath, fileNames in os.walk(startFindPath):
        checkExcludeDirs = False
        for exDir in excludeDirs:
            if exDir:   # and exDir != './':
                exDir = Path(startFindPath / exDir)
                if fnmatch.fnmatch(fullPath, str(exDir)):
                    checkExcludeDirs = True
                elif fullPath.find(str(exDir)) == 0:
                    checkExcludeDirs = True

        if not checkExcludeDirs:
            for f in filters:
                for fName in fnmatch.filter(fileNames, f):
                    checkExcludeFiles = False
                    for exFile in excludeFiles:
                        if exFile:
                            exFile = Path(exFile)
                            if fnmatch.fnmatch(fName, str(exFile)):
                                checkExcludeFiles = True

                    if not checkExcludeFiles:
                        if includeFullPath:
                            foundFiles.append(os.path.join(fullPath, fName))
                        else:
                            foundFiles.append(fName)

        if not recursive:
            return foundFiles

    if sortFiles:
        foundFiles.sort()
    return foundFiles


languages = [
    'lang_de', 'lang_en', 'lang_es', 'lang_fr', 'lang_it',
    'lang_ja', 'lang_ko', 'lang_nl', 'lang_pl', 'lang_pt',
    'lang_ru', 'lang_sv', 'lang_tr', 'lang_zh'
]

# Init
typeEXT = ''
if platform.system() == 'Windows':
    typeEXT = '.exe'
elif platform.system() == 'Linux':
    typeEXT = ''

filePath = './'

# Check
selectedFiles = []
if len(sys.argv) > 1:
    selectedFiles = sys.argv[1:]

# Run
print('>> Converting ts data...')
langFiles = findFiles(filePath, ['*.ts'])

if not selectedFiles:
    for d in languages:
        if os.path.exists(f'{d}.ts'):
            print(f' {d}.ts >>> {d}.qm')
            os.system(f'pyside6-lrelease{typeEXT} {d}.ts -qm {d}.qm')
else:
    for d in selectedFiles:
        if d.find('.ts') != -1:
            d = d.replace('.ts', '')
        if os.path.exists(f'{d}.ts'):
            print(f' {d}.ts >>> {d}.qm')
            os.system(f'pyside6-lrelease{typeEXT} {d}.ts -qm {d}.qm')

print(f'\n>> All done')
