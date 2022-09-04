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

startPath = '../../view'
tsFileName = './fileList.txt'

# Check
selectedFiles = []
if len(sys.argv) > 1:
    selectedFiles = sys.argv[1:]

# Run
print('>> Extracting linguist data...')
langFiles = findFiles(startPath, ['*.py', '*.ui'], excludeFiles=['__init__.py', '*_ui.py'])

with open(f'{tsFileName}', 'w') as file:
    for d in langFiles:
        file.writelines(f'{d}\n')
os.system(f'pyside6-lupdate{typeEXT} @fileList.txt -ts extract.ts')
os.system(f'rm ./fileList.txt')

print('\n>> Copying... extract.ts')
if not selectedFiles:
    for d in languages:
        print(f' extract.ts >>> {d}.ts')
        os.system(f'cp -f extract.ts {d}.ts')
else:
    for d in selectedFiles:
        print(f' extract.ts >>> {d}.ts')
        os.system(f'cp -f extract.ts {d}.ts')
os.system(f'rm ./extract.ts')

print(f'\n>> All done')

# # pyside6-linguist
# # pyside6-lrelease lang_ko.ts -qm lang_ko.qm
