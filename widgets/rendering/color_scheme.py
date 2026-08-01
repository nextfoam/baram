#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
import json

from PySide6.QtCore import QCoreApplication, QSize
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget
from vtkmodules.vtkRenderingCore import vtkColorTransferFunction

from resources import resource


# The value of enumeration corresponds to VTK "ColorMaps.json" name
class ColormapScheme(Enum):
    BlueToRedRainbow = 'Blue to Red Rainbow'
    CoolToWarm = 'Cool to Warm'
    Gray    = 'Grayscale'
    Inferno = 'Inferno (matplotlib)'
    Jet     = 'Jet'
    Plasma  = 'Plasma (matplotlib)'
    RainbowBlendedWhite = 'Rainbow Blended White'
    Reds    = 'Reds'
    Turbo   = 'Turbo'
    Viridis = 'Viridis (matplotlib)'


colormapName = {
    ColormapScheme.BlueToRedRainbow: QCoreApplication.translate('Colormap', u'Blue to Red Rainbow'),
    ColormapScheme.CoolToWarm: QCoreApplication.translate('Colormap', u'Cool to Warm'),
    ColormapScheme.Gray:    QCoreApplication.translate('Colormap', u'Gray'),
    ColormapScheme.Inferno: QCoreApplication.translate('Colormap', u'Inferno'),
    ColormapScheme.Jet:     QCoreApplication.translate('Colormap', u'Jet'),
    ColormapScheme.Plasma:  QCoreApplication.translate('Colormap', u'Plasma'),
    ColormapScheme.RainbowBlendedWhite: QCoreApplication.translate('Colormap', u'Rainbow Blended White'),
    ColormapScheme.Reds:    QCoreApplication.translate('Colormap', u'Reds'),
    ColormapScheme.Turbo:   QCoreApplication.translate('Colormap', u'Turbo'),
    ColormapScheme.Viridis: QCoreApplication.translate('Colormap', u'Viridis'),
}


vtkMaps = {}


def getColorTable(scheme: ColormapScheme, numberOfValues: int):

    if scheme.value not in vtkMaps:
            raise AssertionError

    ctf = vtkColorTransferFunction()
    ctf.HSVWrapOff()

    vtkSchemeInfo = vtkMaps[scheme.value]
    if 'ColorSpace' not in vtkSchemeInfo:
         raise AssertionError

    if vtkSchemeInfo['ColorSpace'] == 'RGB':
        ctf.SetColorSpaceToRGB()
    elif vtkSchemeInfo['ColorSpace'] == 'HSV':
        ctf.SetColorSpaceToHSV()
    elif vtkSchemeInfo['ColorSpace'] == 'Diverging':
        ctf.SetColorSpaceToDiverging()
    elif vtkSchemeInfo['ColorSpace'] == 'Lab':
        ctf.SetColorSpaceToLab()
    else:
        raise AssertionError

    rgbPoints = vtkSchemeInfo['RGBPoints']

    for i in range(0, len(rgbPoints), 4):
        ctf.AddRGBPoint(rgbPoints[i], rgbPoints[i+1], rgbPoints[i+2], rgbPoints[i+3])

    rMin, rMax = ctf.GetRange()
    table = [0.0] * numberOfValues * 3
    ctf.GetTable(rMin, rMax, numberOfValues, table)

    return table


class ColorbarWidget(QWidget):
    NUMBER_OF_VALUES = 256
    def __init__(self, scheme: ColormapScheme, width: int, height: int, parent=None):
        super().__init__(parent)
        self._scheme = scheme
        self._width = width
        self._height = height
        self._colorTable = getColorTable(scheme, self.NUMBER_OF_VALUES)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        for i in range(self.NUMBER_OF_VALUES):
            gradient.setColorAt(i / (self.NUMBER_OF_VALUES-1), QColor.fromRgbF(self._colorTable[i*3], self._colorTable[i*3+1], self._colorTable[i*3+2]))

        painter.fillRect(rect, gradient)

        painter.end()

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        return QSize(self._width, self._height)


def initializeBaramPresetColorSchemes():
    path = resource.file('ColorMaps.json')
    with open(path, "r") as file:
        maps = json.load(file)

    for cmap in maps:
         vtkMaps[cmap['Name']] = cmap
