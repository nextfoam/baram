#!/usr/bin/env python3
# -*-coding:utf8-*-
# !/bin/bash

import os
import platform
import sys
import fnmatch


# findFiles (v1.32)
def findFiles(startPath='.', option='*', bPath=True, bView=False, bSort=True, pathExcepts=[], fileExcepts=[]):
    arrFoundFiles = []
    startPath = startPath.replace('"', '')
    for fullPath, subPath, fileNames in os.walk(startPath):
        for f in fnmatch.filter(fileNames, option):
            if bPath:
                f = os.path.join(fullPath, f)

            if len(pathExcepts) > 0:
                bExceptsPath = False
                for g in pathExcepts:
                    if f.find(f'{g}') == 0:
                        bExceptsPath = True
                if not bExceptsPath:
                    if len(fileExcepts) > 0:
                        bExceptsFile = False
                        for h in fileExcepts:
                            if f.find(f'{h}') != -1:
                                bExceptsFile = True
                        if not bExceptsFile:
                            arrFoundFiles.append(f)
                            if bView:
                                print(f)
                    else:
                        arrFoundFiles.append(f)
                        if bView:
                            print(f)
            else:
                if len(fileExcepts) > 0:
                    bExceptsFile = False
                    for h in fileExcepts:
                        if f.find(f'{h}') != -1:
                            bExceptsFile = True
                    if not bExceptsFile:
                        arrFoundFiles.append(f)
                        if bView:
                            print(f)
                else:
                    arrFoundFiles.append(f)
                    if bView:
                        print(f)
    if bSort:
        arrFoundFiles.sort()
    return arrFoundFiles

def getFileNameExt(path):  # Path/Name.ext    >> Name.ext
    if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
        path = path[1:-1]

    splitData = os.path.split(str(path))
    return splitData[1]


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

filePath = '../../view'
tsFileName = './fileList.txt'

# Check
selectedFiles = []
if len(sys.argv) > 1:
    selectedFiles = sys.argv[1:]

# Run
print('>> Extracting linguist data...')
langFiles = []
langFiles += findFiles(filePath, '*.py', fileExcepts=['__init__.py', '_ui.py'])
langFiles += findFiles(filePath, '*.ui')

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
