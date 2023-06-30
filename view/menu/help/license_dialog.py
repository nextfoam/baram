#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QLabel

from .license_dialog_ui import Ui_LicenseDialog


softwares = [
    ('PySide6', '6.5.1', 'https://pypi.org/project/PySide6/', 'Commercial, GPLv2, LGPLv3', 'https://pypi.org/project/PySide6/'),
    # ('Paraview', '', 'https://www.paraview.org/', 'permissive BSD', 'https://www.paraview.org/license/'),
    ('ionicons', '', 'https://ionic.io/ionicons', 'Completely open source, MIT licensed', 'https://ionic.io/ionicons'),
    # ('PyFoam', '', 'https://pypi.org/project/PyFoam', 'GPLv2+', 'https://pypi.org/project/PyFoam/'),
    ('h5py', '3.9.0', 'https://docs.h5py.org/en/stable/', 'h5py', 'https://docs.h5py.org/en/stable/licenses.html')
]

class LicenseDialog(QDialog):
    def __init__(self, widget):
        super().__init__(widget)
        self._ui = Ui_LicenseDialog()
        self._ui.setupUi(self)

        layout = self._ui.licenses.layout()
        row = 1
        for software, version, url, licence, licneceUrl in softwares:
            softwareLink = QLabel(f'<a href="{url}">{software}</a>')
            softwareLink.setOpenExternalLinks(True)
            layout.addWidget(softwareLink, row, 0)
            licenceLink = QLabel(f'<a href="{licneceUrl}">{licence}</a>')
            licenceLink.setOpenExternalLinks(True)
            layout.addWidget(licenceLink, row, 1)
            row += 1

        self._connectSignalsSlots()

    def _connectSignalsSlots(self):
        self._ui.close.clicked.connect(self.close)
