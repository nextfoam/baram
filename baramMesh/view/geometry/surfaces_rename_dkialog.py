#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

import qasync
from PySide6.QtWidgets import QDialog, QWidget

from widgets.async_message_box import AsyncMessageBox

from baramMesh.app import app
from .surfaces_rename_dkialog_ui import Ui_SurfacesRenameDialog


class SurfacesRenameDialog(QDialog):
    def __init__(self, parent: QWidget, surfaces: list[tuple[str, str]]):
        super().__init__(parent)
        self._ui = Ui_SurfacesRenameDialog()
        self._ui.setupUi(self)

        self._gIds: list[str] = [gId for gId, name in surfaces]

        if len(surfaces) == 1:
            self._ui.newName.setText(surfaces[0][1])

        self._connectSignalsSlots()

    def gIds(self):
        return self._gIds

    def _connectSignalsSlots(self):
        self._ui.ok.clicked.connect(self._accept)

    @qasync.asyncSlot()
    async def _accept(self):
        suffix = self._ui.newName.text()
        if re.fullmatch(r'^\w+$', suffix, flags=re.ASCII) is None:
            await AsyncMessageBox().information(
                self, self.tr('Input Error'),
                self.tr('Only letters, numbers, and underscores (_) are allowed.'))
            return

        db = app.db.checkout()
        if len(self._gIds) == 1:
            if db.getElements('geometry', lambda i, e: e['name'] == suffix):
                await AsyncMessageBox().information(
                    self, self.tr('Input Error'),
                    self.tr('New name is already in use.'))
                return
            else:
                db.setValue(f'geometry/{self._gIds[0]}/name', suffix)
        else:
            names = [e.value('name') for e in db.getElements('geometry', lambda i, e: e['name'].startswith(suffix + '_')).values()]

            no = 1
            for gId in self._gIds:
                while f'{suffix}_{no}' in names:
                    no += 1

                db.setValue(f'geometry/{gId}/name', f'{suffix}_{no}')
                no += 1

        app.db.commit(db)

        self.accept()
