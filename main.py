#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
import asyncio

import qasync
from PySide6.QtWidgets import QApplication

# To render SVG files.
# noinspection PyUnresolvedReferences
import PySide6.QtSvg

# To use ".qrc" QT Resource files
# noinspection PyUnresolvedReferences
import resource_rc

from app import app
from settings.app_properties import AppProperties
from view.main_window.main_window import MainWindow


def handle_exception(eType, eValue, eTraceback):
    if issubclass(eType, KeyboardInterrupt):
        sys.__excepthook__(eType, eValue, eTraceback)
        return

    logger.critical("Uncaught exception", exc_info=(eType, eValue, eTraceback))


sys.excepthook = handle_exception


if __name__ == '__main__':
    app.setupApplication(AppProperties({
        'name': 'baram-snappy',
        'fullName': QApplication.translate('Main', 'Baram-snappy'),
        'iconResource': 'baram.ico',
        'logoResource': 'baram.ico',
    }))

    logger = logging.getLogger()
    formatter = logging.Formatter("[%(asctime)s][%(name)s] ==> %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    os.environ["QT_SCALE_FACTOR"] = app.settings.getScale()

    application = QApplication(sys.argv)

    loop = qasync.QEventLoop(application)
    asyncio.set_event_loop(loop)

    app.applyLanguage()

    app.window = MainWindow()

    background_tasks = set()
    task = asyncio.create_task(app.window.start())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    with loop:
        loop.run_forever()

    loop.close()
