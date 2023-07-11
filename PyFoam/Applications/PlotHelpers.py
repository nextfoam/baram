#  ICE Revision: $Id$
"""
Helper-functions for the plots
"""
from os import path

def cleanFilename(orig):
    """
    Clean the filename in such a way that it is suitable for use in
    HTML and LaTeX-documents
    """
    dName,fName=path.split(orig)
    fName,ext=path.splitext(fName)

    # HTML doesn't like spaces
    fName=fName.replace(' ','space')
    # LaTeX doesn't like dots
    fName=fName.replace('.','dot')
    result=path.join(dName,fName)+ext

    return result
