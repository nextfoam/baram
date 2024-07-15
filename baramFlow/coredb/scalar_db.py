#!/usr/bin/env python
# -*- coding: utf-8 -*-

import baramFlow.coredb.libdb as xml
from baramFlow.coredb.configuraitions import ConfigurationException
from baramFlow.coredb.material_db import MaterialObserver, MaterialDB


USER_DEFINED_SCALAR_XPATH = 'models/userDefinedScalars/scalar'


class _MaterialObserver(MaterialObserver):
    def materialRemoving(self, db, mid: int):
        scalars = [xml.getText(e, 'fieldName') for e in db.getElements(f'{USER_DEFINED_SCALAR_XPATH}[material="{mid}"]')]
        if scalars:
            raise ConfigurationException(
                self.tr('{} is referenced by user-defined scalars {}').format(
                    MaterialDB.getName(mid), ' '.join(scalars)))


MaterialDB.registerObserver(_MaterialObserver())
