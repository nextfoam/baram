#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from PySide6.QtCore import QFile, QIODevice, QSize, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer


def load_themed_icon(path: str, size: QSize = QSize(256, 256)) -> QIcon:
    data = _readAll(path)
    if data is None or b'<svg' not in data:
        return QIcon(path)

    color = QGuiApplication.palette().color(QPalette.ColorRole.ButtonText).name()
    text = data.decode('utf-8').replace('#000000', color).replace('#000', color)
    text = re.sub(r'<svg\b', f'<svg fill="{color}"', text, count=1)

    renderer = QSvgRenderer(text.encode('utf-8'))
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def _readAll(path: str) -> bytes | None:
    f = QFile(path)
    if not f.open(QIODevice.OpenModeFlag.ReadOnly):
        return None
    try:
        return bytes(f.readAll().data())
    finally:
        f.close()
