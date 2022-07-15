#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import shutil


class Settings:
    _workingDirectory = None
    _settingsDirectory = None

    @classmethod
    def setWorkingDirectory(cls, directory):
        cls._workingDirectory = directory
        cls._settingsDirectory = os.path.join(directory, '.baram')

        if os.path.isdir(cls._settingsDirectory):
            shutil.rmtree(cls._settingsDirectory)
        os.mkdir(cls._settingsDirectory)

    @classmethod
    def workingDirectory(cls):
        return cls._workingDirectory

    @classmethod
    def settingsDirectory(cls):
        return cls._settingsDirectory
