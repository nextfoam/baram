#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math

import matplotlib.pyplot as plt

from vtkmodules.vtkCommonCore import vtkLookupTable


STEP = 256


def getLookupTable(name: str):
    lut = vtkLookupTable()
    lut.SetNumberOfTableValues(STEP)

    cmap = plt.cm.get_cmap(name)

    for i in range(0, STEP):
        rgb = cmap(i/(STEP-1))[:3]  # Extract RGB values excluding Alpha
        lut.SetTableValue(i, *rgb)

    return lut


sequentialRedLut = vtkLookupTable()
# Use a color series to create a transfer function
for i in range(0, STEP):
    o = 1 - math.pow(i/(STEP-1), 2)
    sequentialRedLut.SetTableValue(i, 1, o, o)
