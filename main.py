#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

from PySide6.QtCore import QFile, QTextStream, QIODevice
from PySide6.QtWidgets import QApplication

# To render SVG files.
# noinspection PyUnresolvedReferences
import PySide6.QtSvg

# To use ".qrc" QT Resource files
# noinspection PyUnresolvedReferences
import resource_rc

from view.main_window.main_window import MainWindow

if __name__ == '__main__':
    # TODO: The scale value should be save in configuration and loaded/used in next launch
    # This environment variable should be set before QApplication is created
    os.environ["QT_SCALE_FACTOR"] = "1.1"

    app = QApplication(sys.argv)

    file = QFile(u":/ElegantDark.qss")
    file.open(QIODevice.ReadOnly | QIODevice.Text)
    stream = QTextStream(file)

    #app.setStyleSheet(app.styleSheet() + '\n' + stream.readAll())

    window = MainWindow()
    window.show()

    app.exec()
