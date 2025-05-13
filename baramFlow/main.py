#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import sys

import qasync
from PySide6.QtCore import QFile, QTextStream, QIODevice
from PySide6.QtWidgets import QApplication, QMessageBox

# To render SVG files.
# noinspection PyUnresolvedReferences
import PySide6.QtSvg
from vtkmodules.vtkCommonCore import vtkOutputWindow, vtkSMPTools, vtkStringOutputWindow
from vtkmodules.vtkParallelCore import vtkDummyController, vtkMultiProcessController

# To use ".qrc" QT Resource files
# noinspection PyUnresolvedReferences
import resource_rc

from libbaram.mpi import checkMPI, MPIStatus
from libbaram.process import getAvailablePhysicalCores

from baramFlow.app import app
from baramFlow.app_properties import AppProperties
from baramFlow.app_plug_in import AppPlugIn
from baramFlow.base.graphic.color_scheme import initializeBaramPresetColorSchemes
from baramFlow.view.main_window.start_window import Baram
from baramFlow.coredb.app_settings import AppSettings

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


sys.excepthook = handle_exception


def loop_exception(loop, context):
    print("exception handling: ", context["exception"])
    loop.stop()


def main():
    application = QApplication(sys.argv)

    if mpiStatus := checkMPI():
        if mpiStatus == MPIStatus.NOT_FOUND:
            message = QApplication.translate('main', 'MPI package NOT available in the system.')
        elif mpiStatus == MPIStatus.LOW_VERSION:
            message = QApplication.translate('main', 'MPI package version low. Recent version required.')

        QMessageBox.information(None, QApplication.translate('main', 'Check MPI'), message)
        return

    app.setupApplication(AppProperties({
        'name': 'BaramFlow',
        'fullName': QApplication.translate('Main', 'BaramFlow'),
        'iconResource': 'baramFlow.ico',
        'logoResource': 'baramFlow.ico',
    }))
    app.setPlug(AppPlugIn())

    os.environ['LC_NUMERIC'] = 'C'
    os.environ["QT_SCALE_FACTOR"] = AppSettings.getUiScaling()

    errOut = vtkStringOutputWindow()
    vtkOutputWindow.SetInstance(errOut)

    # Leave 1 core for users
    numCores = getAvailablePhysicalCores() - 1

    smp = vtkSMPTools()
    smp.Initialize(numCores)
    smp.SetBackend('STDThread')

    # "vtkProbeLineFilter" runs only on parallel
    controller = vtkDummyController()
    vtkMultiProcessController.SetGlobalController(controller)

    application.setQuitOnLastWindowClosed(False)

    app.qApplication = application

    loop = qasync.QEventLoop(application)
    asyncio.set_event_loop(loop)

    loop.set_exception_handler(loop_exception)

    file = QFile(u":/ElegantDark.qss")
    file.open(QIODevice.ReadOnly | QIODevice.Text)
    stream = QTextStream(file)

    #app.setStyleSheet(app.styleSheet() + '\n' + stream.readAll())

    initializeBaramPresetColorSchemes()

    app.setLanguage(AppSettings.getLanguage())
    background_tasks = set()

    baram = Baram()
    task = loop.create_task(baram.start())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    with loop:
        loop.run_forever()

    loop.close()


if __name__ == '__main__':
    main()
