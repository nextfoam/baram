#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import sys

import qasync
from PySide6.QtWidgets import QApplication, QMessageBox

# To render SVG files.
# noinspection PyUnresolvedReferences
import PySide6.QtSvg
from vtkmodules.vtkCommonCore import vtkSMPTools

# To use ".qrc" QT Resource files
# noinspection PyUnresolvedReferences
import resource_rc

from app_properties import meshAppProperties
from libbaram.mpi import checkMPI, MPIStatus, MPI_PREFIX
from libbaram.process import getAvailablePhysicalCores

from analytics import Analytics
from analytics.events import EVENT_LOOP_ERROR

from baramMesh.app import app
from baramMesh.view.main_window.main_window import MainWindow

logger = logging.getLogger()
formatter = logging.Formatter("[%(asctime)s][%(name)s] ==> %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def handle_exception(eType, eValue, eTraceback):
    if issubclass(eType, KeyboardInterrupt):
        sys.__excepthook__(eType, eValue, eTraceback)
        return

    logger.critical("Uncaught exception", exc_info=(eType, eValue, eTraceback))
    Analytics().captureException(eValue)


sys.excepthook = handle_exception


def loop_exception(loop, context):
    exception = context.get('exception')
    print("exception handling: ", exception if exception is not None else context.get('message', ''))
    if exception is not None:
        Analytics().captureException(exception, {'source': 'event_loop'})
    else:
        Analytics().capture(EVENT_LOOP_ERROR, {'message': context.get('message', '')})
    loop.stop()


def main():
    application = QApplication(sys.argv)

    if mpiStatus := asyncio.run(checkMPI()):
        if mpiStatus == MPIStatus.NOT_FOUND:
            message = QApplication.translate('main', 'MPI package NOT available in the system.')
        elif mpiStatus == MPIStatus.LOW_VERSION:
            message = QApplication.translate('main', 'MPI package version low. Recent version required.')
        elif mpiStatus == MPIStatus.INVALID_PREFIX:
            message = QApplication.translate(
                'main', f'Incorrect "$BARAM_MPI_PREFIX" environment variable.<br/>'
                        f'"{MPI_PREFIX}/mpirun" does NOT exist.')

        QMessageBox.information(None, QApplication.translate('main', 'Check MPI'), message)
        return

    app.setupApplication(meshAppProperties)

    Analytics().configure(
        app_name=meshAppProperties.name,
        app_version=meshAppProperties.version,
        config_dir=app.settings.settingsPath())

    os.environ['LC_NUMERIC'] = 'C'
    os.environ["QT_SCALE_FACTOR"] = app.settings.getScale()

    # Leave 1 core for users
    numCores = getAvailablePhysicalCores() - 1

    smp = vtkSMPTools()
    smp.Initialize(numCores)
    smp.SetBackend('STDThread')

    app.qApplication = application

    loop = qasync.QEventLoop(application)
    asyncio.set_event_loop(loop)

    loop.set_exception_handler(loop_exception)

    app.applyLanguage()

    if Analytics().ensureConsent():
        Analytics().init()

    app.window = MainWindow()

    background_tasks = set()
    task = loop.create_task(app.window.start())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    with loop:
        loop.run_forever()

    loop.close()
    Analytics().shutdown(final=True)


if __name__ == '__main__':
    main()
