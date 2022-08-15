#!/usr/bin/env python3
#-*-coding:utf8-*-
#!/bin/bash

import os
import platform
import sys
import fnmatch

# findFiles (v1.2)
def findFiles(startPath='.', option='*', bPath=True, bView=False, bSort=True, pathExcepts=[]):
    arrFoundFiles = []
    startPath = startPath.replace('"', '')
    for fullPath, subPath, fileNames in os.walk(startPath):
        for f in fnmatch.filter(fileNames, option):
            if bPath:
                f = os.path.join(fullPath, f)

            # Excepts
            if len(pathExcepts) > 0:
                bCheckExcepts = False
                for e in pathExcepts:
                    if f.find(f'{e}') == 0:
                        bCheckExcepts = True
                if not bCheckExcepts:
                    arrFoundFiles.append(f)
                    # View
                    if bView: print(f)
            else:
                arrFoundFiles.append(f)
                # View
                if bView:
                    print(f)
    # Sort
    if bSort:
        arrFoundFiles.sort()
    return arrFoundFiles

#
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

arrFound = findFiles(filePath, 'resource.qrc', pathExcepts=['./venv'])
for d in arrFound:
    print(f'  Converting... resource.qrc -> {d[2:-4]}_rc.py')
    os.system(f'pyside6-rcc{typeEXT} {d} -o {d[2:-4]}_rc.py')

# Run 2
arrFound = findFiles(filePath, '*.ui', pathExcepts=['./venv'])
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
