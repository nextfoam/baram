#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from openfoam.file_system import FileSystem


class BoundaryData:
    @classmethod
    def write(cls, rname, bname, field, data):
        rpath = FileSystem.makeDir(FileSystem.constantPath(rname), 'boundaryData')
        pointsPath = FileSystem.makeDir(rpath, bname)
        fieldTablePath = FileSystem.makeDir(pointsPath, '0')

        pointsFile = os.path.join(pointsPath, 'points')
        fieldTableFile = os.path.join(fieldTablePath, field)
        with open(pointsFile, 'w') as points, open(fieldTableFile, 'w') as fieldTable:
            rows = len(data)
            points.write(f'{rows}\n(\n')
            fieldTable.write(f'{rows}\n(\n')

            if len(data.columns) == 6:
                for row in data.itertuples(index=False):
                    points.write(f'({row[0]} {row[1]} {row[2]})\n')
                    fieldTable.write(f'({row[3]} {row[4]} {row[5]})\n')
            else:
                for row in data.itertuples(index=False):
                    points.write(f'({row[0]} {row[1]} {row[2]})\n')
                    fieldTable.write(f'{row[3]}\n')

            points.write(f')')
            fieldTable.write(f')')
