#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

@dataclass
class Bounds:
    xMin: float
    xMax: float
    yMin: float
    yMax: float
    zMin: float
    zMax: float

    def merge(self, bounds):
        self.xMin = min(self.xMin, bounds.xMin)
        self.xMax = max(self.xMax, bounds.xMax)
        self.yMin = min(self.yMin, bounds.yMin)
        self.yMax = max(self.yMax, bounds.yMax)
        self.zMin = min(self.zMin, bounds.zMin)
        self.zMax = max(self.zMax, bounds.zMax)

    def size(self):
        return self.xMax - self.xMin, self.yMax - self.yMin, self.zMax - self.zMin

    def includes(self, point):
        x, y, z = point

        return self.xMin < x < self.xMax and self.yMin < y < self.yMax and self.zMin < z < self.zMax

    def toTuple(self):
        return self.xMin, self.xMax, self.yMin, self.yMax, self.zMin, self.zMax

    def center(self):
        def center(a, b):
            return (a + b) / 2

        return center(self.xMin, self.xMax), center(self.yMin, self.yMax), center(self.zMin, self.zMax)

    def toInsidePoint(self, point):
        x, y, z = point

        return (self.xMin if x < self.xMin else self.xMax if x > self.xMax else x,
                self.yMin if y < self.yMin else self.yMax if y > self.yMax else y,
                self.zMin if z < self.zMin else self.zMax if z > self.zMax else z)
