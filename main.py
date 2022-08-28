#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
import asyncio

import qasync

from PySide6.QtCore import QFile, QTextStream, QIODevice, QTranslator, QCoreApplication
from PySide6.QtWidgets import QApplication

# To render SVG files.
# noinspection PyUnresolvedReferences
import PySide6.QtSvg

# To use ".qrc" QT Resource files
# noinspection PyUnresolvedReferences
import resource_rc

from view.main_window.start_window import Baram


if __name__ == '__main__':
    # TODO: The scale value should be save in configuration and loaded/used in next launch
    # This environment variable should be set before QApplication is created
    os.environ["QT_SCALE_FACTOR"] = "1.1"

    logger = logging.getLogger()
    formatter = logging.Formatter("[%(name)s] %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    app = QApplication(sys.argv)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    file = QFile(u":/ElegantDark.qss")
    file.open(QIODevice.ReadOnly | QIODevice.Text)
    stream = QTextStream(file)

    #app.setStyleSheet(app.styleSheet() + '\n' + stream.readAll())

    translator = QTranslator()
    translator.load("./resources/locale/lang_en.qm")
    QCoreApplication.installTranslator(translator)

    background_tasks = set()

    baram = Baram()
    task = asyncio.create_task(baram.start())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    with loop:
        loop.run_forever()

    loop.close()
