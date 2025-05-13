#!/usr/bin/env python
# -*- coding: utf-8 -*-

from colorsys import hsv_to_rgb, rgb_to_hsv
from enum import Enum
import io
import json

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QImage
from matplotlib.colors import ListedColormap
import matplotlib as mpl
mpl.use('Agg')  # Use the 'Agg' backend, which is non-interactive. This line should come before "pyplot" is imported
import matplotlib.pyplot as plt

import numpy as np

from resources import resource


# The value of enumeration corresponds to matplotlib "Colormap" name
class ColormapScheme(Enum):
    BlueToRedRainbow = 'Blue to Red Rainbow'
    CoolToWarm = 'Cool to Warm'
    Gray    = 'gray'
    Inferno = 'inferno'
    Jet     = 'jet'
    Plasma  = 'plasma'
    RainbowBlendedWhite = 'Rainbow Blended White'
    Reds    = 'Reds'
    Turbo   = 'turbo'
    Viridis = 'viridis'


colormapName = {
    ColormapScheme.BlueToRedRainbow: QCoreApplication.translate('Colormap', u'Blue to Red Rainbow'),
    ColormapScheme.CoolToWarm: QCoreApplication.translate('Colormap', u'Cool to Warm'),
    ColormapScheme.Gray:    QCoreApplication.translate('Colormap', u'Gray'),
    ColormapScheme.Inferno: QCoreApplication.translate('Colormap', u'inferno'),
    ColormapScheme.Jet:     QCoreApplication.translate('Colormap', u'jet'),
    ColormapScheme.Plasma:  QCoreApplication.translate('Colormap', u'plasma'),
    ColormapScheme.RainbowBlendedWhite:    QCoreApplication.translate('Colormap', u'Rainbow Blended White'),
    ColormapScheme.Reds:    QCoreApplication.translate('Colormap', u'Reds'),
    ColormapScheme.Turbo:   QCoreApplication.translate('Colormap', u'turbo'),
    ColormapScheme.Viridis: QCoreApplication.translate('Colormap', u'viridis'),
}


def getColormapSchemeImage(scheme: ColormapScheme, width: int, height: int) -> QImage:
    gradient = np.linspace(0, 1, 256)
    gradient = np.vstack((gradient, gradient))

    fig, ax = plt.subplots(figsize=(width/100, height/100))  # Default DPI = 100
    ax.imshow(gradient, aspect='auto', cmap = scheme.value)
    ax.set_axis_off()

    plt.tight_layout(pad=0)

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)

    image_bytes = buffer.read()
    buffer.close()

    image = QImage.fromData(image_bytes, 'PNG')

    plt.close(fig)

    return image

def initializeBaramPresetColorSchemes():
    path = resource.file('ColorMaps.json')
    with open(path, "r") as file:
        maps = json.load(file)

    vtkMaps = {}
    for cmap in maps:
         vtkMaps[cmap['Name']] = cmap

    for scheme in ColormapScheme:
        if scheme.value in mpl.colormaps:
             continue

        # Only the colormaps from matplotlib and VTK are supported for now
        if scheme.value not in vtkMaps:
             raise AssertionError

        vtkScheme = vtkMaps[scheme.value]
        if vtkScheme['ColorSpace'] == 'HSV':
            newcmap = createColormapInHsv(scheme.value, vtkScheme['RGBPoints'])
        elif vtkScheme['ColorSpace'] in ['RGB', 'Diverging']:
            newcmap = createColormapInRgb(scheme.value, vtkScheme['RGBPoints'])
        else:
            raise AssertionError

        mpl.colormaps.register(newcmap)


def createColormapInRgb(name: str, rgbPoints: list) -> ListedColormap:
    if len(rgbPoints) % 4 != 0:
            raise AssertionError

    N = 256
    rgbArray = np.array(rgbPoints)

    # Process HSV Colormap
    xp = rgbArray[0::4]

    rp = rgbArray[1::4]
    gp = rgbArray[2::4]
    bp = rgbArray[3::4]

    x = np.linspace(0, 1, N)

    r = np.interp(x, xp, rp)
    g = np.interp(x, xp, gp)
    b = np.interp(x, xp, bp)

    colors = np.ones((N, 4))
    colors[:, 0] = r
    colors[:, 1] = g
    colors[:, 2] = b

    return ListedColormap(colors, name=name)


def createColormapInHsv(name: str, rgbPoints: list) -> ListedColormap:
    if len(rgbPoints) % 4 != 0:
            raise AssertionError

    N = 256
    rgbArray = np.array(rgbPoints)

    # Process HSV Colormap
    xp = rgbArray[0::4]

    r = rgbArray[1::4]
    g = rgbArray[2::4]
    b = rgbArray[3::4]
    # rgb = np.dstack((r, g, b))
    rgb = np.stack((r, g, b), axis=-1)

    hsv = np.array([rgb_to_hsv(e[0], e[1], e[2]) for e in rgb])
    hp = hsv[:, 0]
    sp = hsv[:, 1]
    vp = hsv[:, 2]

    x = np.linspace(0, 1, N)

    h = np.interp(x, xp, hp)
    s = np.interp(x, xp, sp)
    v = np.interp(x, xp, vp)

    hsv = np.stack((h, s, v), axis=-1)
    rgb = np.array([hsv_to_rgb(e[0], e[1], e[2]) for e in hsv])

    colors = np.ones((N, 4))
    colors[:, 0] = rgb[:, 0]
    colors[:, 1] = rgb[:, 1]
    colors[:, 2] = rgb[:, 2]

    return ListedColormap(colors, name=name)


if __name__ == '__main__':
    initializeBaramPresetColorSchemes()