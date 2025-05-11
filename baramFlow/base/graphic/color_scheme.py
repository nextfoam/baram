#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QImage
from matplotlib.backends.backend_qtagg import FigureCanvas
import matplotlib.pyplot as plt

import numpy as np


# The value of enumeration corresponds to matplotlib "Colormap" name
class ColormapScheme(Enum):
    Gray    = 'gray'
    Inferno = 'inferno'
    Jet     = 'jet'
    Plasma  = 'plasma'
    Rainbow = 'rainbow'
    Reds    = 'Reds'
    Turbo   = 'turbo'
    Viridis = 'viridis'


colormapName = {
    ColormapScheme.Gray:    QCoreApplication.translate('Colormap', u'Gray'),
    ColormapScheme.Inferno: QCoreApplication.translate('Colormap', u'inferno'),
    ColormapScheme.Jet:     QCoreApplication.translate('Colormap', u'jet'),
    ColormapScheme.Plasma:  QCoreApplication.translate('Colormap', u'plasma'),
    ColormapScheme.Rainbow: QCoreApplication.translate('Colormap', u'rainbow'),
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

        canvas = FigureCanvas(fig)
        canvas.draw()

        image = QImage(canvas.buffer_rgba(), width, height, QImage.Format.Format_RGBA8888)

        plt.close(fig)

        return image

