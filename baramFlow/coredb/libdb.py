#!/usr/bin/env python
# -*- coding: utf-8 -*-

ns = 'http://www.baramcfd.org/baram'
nsmap = {'': ns}


def getElement(xpath, parent):
    return parent.find(xpath, namespaces=nsmap)


def getElements(xpath, parent):
    return parent.findall(xpath, namespaces=nsmap)


def getText(xpath, parent):
    return getElement(xpath, parent).text

