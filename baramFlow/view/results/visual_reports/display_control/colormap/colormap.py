#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass

from PySide6.QtCore import QCoreApplication

from baramFlow.coredb.color_scheme import ColormapScheme

from .spectral import vision64SpectralColormapData
from .turbo import turboColormapData
from .grey import greyColormapData


colormapName = {
    ColormapScheme.Spectral:  QCoreApplication.translate('Colormap', u'Spectral'),
    ColormapScheme.Turbo:     QCoreApplication.translate('Colormap', u'Turbo'),
    ColormapScheme.Grey:      QCoreApplication.translate('Colormap', u'Grey'),
}

colormapImage = {
    ColormapScheme.Spectral: ':/colorSchemes/spectral.png',
    ColormapScheme.Turbo:    ':/colorSchemes/turbo.png',
    ColormapScheme.Grey:     ':/colorSchemes/grey.png',
}

def colormapData(scheme):
    if scheme == ColormapScheme.Spectral:
        return vision64SpectralColormapData()
    elif scheme == ColormapScheme.Turbo:
        return turboColormapData()
    elif scheme == ColormapScheme.Grey:
        return greyColormapData()

    return vision64SpectralColormapData()
