#  ICE Revision: $Id$
"""Hardcoded values"""

from os import path,makedirs,environ
from PyFoam.ThirdParty.six import PY3

_pyFoamDirName="pyFoam"

_pyFoamConfigName="pyfoamrc"

pyFoamSiteVar="PYFOAM_SITE_DIR"

def globalDirectory():
    """:return: the global directory"""
    return path.join("/etc",_pyFoamDirName)

def globalConfigFile():
    """:return: The name of the global configuration File"""
    return path.join(globalDirectory(),_pyFoamConfigName)

def globalConfigDir():
    """:return: The name of the global configuration directory where .cfg-files can be placed"""
    return globalConfigFile()+".d"

def siteDirectory():
    """:return: the site directory"""
    if pyFoamSiteVar in environ:
        return path.join(environ[pyFoamSiteVar],"etc")
    else:
        return None

def siteConfigFile():
    """:return: The name of the site configuration File"""
    if pyFoamSiteVar in environ:
        return path.join(siteDirectory(),_pyFoamConfigName)
    else:
        return None

def siteConfigDir():
    """:return: The name of the site configuration directory where .cfg-files can be placed"""
    if pyFoamSiteVar in environ:
        return siteConfigFile()+".d"
    else:
        return None

def userDirectory():
    """:return: the user directory"""
    return path.expanduser(path.join("~","."+_pyFoamDirName))

def userConfigFile():
    """:return: The name of the user configuration File"""
    return path.join(userDirectory(),_pyFoamConfigName)

def userConfigDir():
    """:return: The name of the user configuration directory where .cfg-files can be placed"""
    return userConfigFile()+".d"

def userName():
    """:return: name of the current user"""
    user=""
    if "USER" in environ:
        user=environ["USER"]
    return user

def logDirectory():
    """Path to the log directory that this user may write to.
    /var/log/pyFoam for root, ~/.pyFoam/log for all others
    :return: path to the log directory."""
    if userName()=="root":
        return path.join("/var/log","pyFoam")
    else:
        return path.join(userDirectory(),"log")

def authDirectory():
    """Path to the directory with authentication data"""
    return path.join(userDirectory(),"auth")

def assertDirectory(name,dirMode=None):
    """Makes sure that the directory exists
    :param name: the directory
    :param dirMode: string to set mode of the directory"""
    if path.exists(name):
        return
    else:
        if PY3:
            perm=eval("0o755")
        else:
            perm=eval("0755")

        makedirs(name,mode=perm)
    if dirMode is not None:
        if PY3:
            perm=eval("0o"+dirMode)
        else:
            perm=eval("0"+dirMode)
        from os import chmod
        chmod(name,perm)

# Should work with Python3 and Python2
