#!/usr/bin/env python3
#-*-coding:utf8-*-
#!/bin/bash

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

def getFileNameExt(path):  # Path/Name.ext    >> Name.ext
    if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
        path = path[1:-1]

    splitData = os.path.split(str(path))
    return splitData[1]


# Init
typeEXT = ''
if platform.system() == 'Windows':
    typeEXT = '.exe'
elif platform.system() == 'Linux':
    typeEXT = ''

filePath = '.'

# Check
selectedFiles = []
if len(sys.argv) > 1:
    selectedFiles = sys.argv[1:]

# Run 1
print('>> Convert qrc files')
arrFound = findFiles(filePath, ['resource.qrc'], excludeDirs=['./venv'])
for d in arrFound:
    print(f'  Converting... resource.qrc -> {d[2:-4]}_rc.py')
    os.system(f'pyside6-rcc{typeEXT} {d} -o {d[2:-4]}_rc.py')

# Run 2
arrFound = findFiles(filePath, ['*.ui'], excludeDirs=['./venv'])
if not selectedFiles:
    print('\n>> Convert ui files')
    totalNum = len(arrFound)
else:
    print(f'\n>> Convert selected ui file(s)')    # {" ".join(selectedFiles)}
    totalNum = len(selectedFiles)

count = 0
for d in arrFound:
    if not selectedFiles:
        count += 1
        print(f'  [{count}/{totalNum}] Converting... {getFileNameExt(d)} -> {getFileNameExt(d)[:-3]}_ui.py')
        os.system(f'pyside6-uic{typeEXT} {d} -o {d[:-3]}_ui.py')
    else:
        for e in selectedFiles:
            if e == getFileNameExt(d):
                count += 1
                print(f'  [{count}/{totalNum}] Converting... {getFileNameExt(d)} -> {getFileNameExt(d)[:-3]}_ui.py')
                os.system(f'pyside6-uic{typeEXT} {d} -o {d[:-3]}_ui.py')

# End
if not count == totalNum:
    print('\nFailed to convert some files!!')
else:
    print('\nAll done')
