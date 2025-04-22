#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication

from baramFlow.base.graphic.color_scheme import ColormapScheme


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
