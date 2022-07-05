#  ICE Revision: $Id$
"""Getting Information about the Foam-Installation (like the installation directory)"""

from os import environ,path,listdir
import sys

if sys.version_info<(2,6):
    from popen2 import popen4
else:
    from subprocess import Popen,PIPE,STDOUT

import re

from PyFoam.Error import error,warning

from PyFoam import configuration as config

def getPathFromEnviron(name):
    """Gets a path from an environment variable
    :return: the path
    :rtype: string
    :param name: the name of the environment variable"""

    tmp=""
    if name in environ:
        tmp=path.normpath(environ[name])

    return tmp

def foamTutorials():
    """:return: directory in which the tutorials reside"""

    return getPathFromEnviron("FOAM_TUTORIALS")

def foamEtc():
    """:return: the etc-directory of the distro"""

    return path.join(getPathFromEnviron("WM_PROJECT_DIR"),"etc")

def foamCaseDicts():
    """:return: the caseDicts-directory of the distro"""

    return path.join(foamEtc(),"caseDicts")

def foamPostProcessing():
    """:return: the caseDicts/postProcessing-directory of the distro"""

    return path.join(foamCaseDicts(),"postProcessing")

def foamMPI():
    """:return: the used MPI-Implementation"""
    if "WM_MPLIB" not in environ:
        return ()
    else:
        vStr=environ["WM_MPLIB"]
        return vStr

def foamVersionString(useConfigurationIfNoInstallation=False):
    """:return: string for the  Foam-version as found
    in $WM_PROJECT_VERSION"""

    if "WM_PROJECT_VERSION" not in environ and not useConfigurationIfNoInstallation:
        return ""
    else:
        if "WM_PROJECT_VERSION" in environ:
            vStr=environ["WM_PROJECT_VERSION"]
        else:
            vStr=""

        if vStr=="" and  useConfigurationIfNoInstallation:
            vStr=config().get("OpenFOAM","Version")

    return vStr

class VersionTuple(tuple):
    """Wrapper around the regular tuple that is printed in a way that
    can be parsed as a tuple in a OF-dictionary

    """

    # Python3 doesn't like this. But it was only here out of courtesy
#    def __init__(self,data):
#        tuple.__init__(self,data)

    def __str__(self):
        return ".".join([str(e) for e in self])

def foamVersion(useConfigurationIfNoInstallation=False):
    """:return: tuple that represents the Foam-version as found
    in $WM_PROJECT_VERSION"""

    vStr=foamVersionString(useConfigurationIfNoInstallation=useConfigurationIfNoInstallation)

    if len(vStr)>0 and vStr[0]=="v":
        vStr=vStr[1:]
        if vStr[-1]=="+":
            vStr=vStr[:-1]
    if vStr=="":
        return ()
    else:
        res=[]

        for el in vStr.split("."):
            for e in el.split("-"):
                try:
                    res.append(int(e))
                except:
                    res.append(e)

        return VersionTuple(res)

def foamVersionNumber(useConfigurationIfNoInstallation=False):
    """:return: tuple that represents the Foam-Version-Number (without
    strings"""

    ver=foamVersion(useConfigurationIfNoInstallation=useConfigurationIfNoInstallation)

    if ver==("dev",) or ver==("plus",):
        return VersionTuple((9,9,9))
    nr=[]

    for e in ver:
        if type(e)==int:
            nr.append(e)
        else:
            break

    return VersionTuple(nr)

def oldAppConvention():
    """Returns true if the version of OpenFOAM is older than 1.5 and
    it therefor uses the 'old' convention to call utilities ("dot, case")
    """
    return foamVersionNumber()>() and foamVersionNumber()<(1,5)

def oldTutorialStructure():
    """Returns true if the version of OpenFOAM is older than 1.6 and
    it therefor uses the 'old' (flat) structure for the tutorials
    """
    return foamVersionNumber()>() and foamVersionNumber()<(1,6)

def installationPath():
    """Path to the installation"""
    return path.abspath(environ["WM_PROJECT_DIR"])

def findInstalledVersions(basedir,valid,forkName="openfoam"):
    versions={}

    basedir=path.abspath(basedir)

    try:
        candidates=listdir(basedir)
    except OSError:
        return versions

    for f in candidates:
        m=valid.match(f)
        if m:
            dname=path.join(basedir,f)
            if path.isdir(dname):
                name=m.groups(1)[0]
                dotDir=path.join(dname,".OpenFOAM-"+name)
                etcDir=path.join(dname,"etc")
                if path.isdir(etcDir) and path.exists(path.join(etcDir,"bashrc")):
                    versions[(forkName,m.groups(1)[0])]=dname
                elif path.isdir(dotDir) and path.exists(path.join(dotDir,"bashrc")):
                    versions[(forkName,m.groups(1)[0])]=dname

    return versions

__foamInstallations=None

def findInstallationDir(newVersion):
    installed=foamInstalledVersions()
    found=[]

    for fork,version in installed.keys():
        if newVersion==version:
            found.append((fork,version))
        elif newVersion==(fork+"-"+version):
            found.append((fork,version))

    if len(found)==0:
        error("Can't find basedir for OpenFOAM-version", newVersion, "in",
              ", ".join([ a[0]+"-"+a[1] for a in installed.keys() ]))
    elif len(found)==1:
        return found[0][0],found[0][1],installed[found[0]]
    else:
        error("Requested version:",newVersion,"Matches found:",
              ", ".join([ a[0]+"-"+a[1] for a in found ]))


def findThirdPartyDir(newVersion):
    if isinstance(newVersion,tuple):
        newVersion = "{}-{}".format(*newVersion)

    fork, version, installation = findInstallationDir(newVersion)

    thirdPartyDir = path.join(installation,
                              path.pardir,
                              "ThirdParty-{}".format(version))

    if path.isdir(thirdPartyDir):
        return thirdPartyDir
    else:
        return None


def foamInstalledVersions():
    """:return: A list with the installed versions of OpenFOAM"""
    global __foamInstallations

    if __foamInstallations:
        return __foamInstallations

    __foamInstallations={}

    forks=config().getList("OpenFOAM","Forks")

    for fork in forks:
        currentFork=foamFork()

        if "WM_PROJECT_INST_DIR" in environ and currentFork==fork:
            basedir=environ["WM_PROJECT_INST_DIR"]
        else:
            basedir=path.expanduser(config().get("OpenFOAM","Installation-"+fork))

        if not path.exists(basedir) or not path.isdir(basedir):
            warning("Basedir",basedir,"for fork",fork,"does not exist or is not a directory")
            # continue

        for bdir in [basedir]+config().getList("OpenFOAM","AdditionalInstallation-"+fork):
            for val in [re.compile(s) for s in config().getList("OpenFOAM","DirPatterns-"+fork)]:
                __foamInstallations.update(findInstalledVersions(bdir,val,fork))

    return __foamInstallations

def foamFork():
    """The currently used fork of OpenFOAM/Foam"""
    try:
        return environ["WM_FORK"]
    except KeyError:
        vStr=foamVersionString()
        if len(vStr)>1 and vStr[0]=="v":
            return "openfoamplus"
        else:
            return "openfoam"

def ensureDynamicLibraries():
    """Ensure that the dynamic library path is set for systems where it
    was erased for security rasons (for instance Mac OS X 10.11)"""

    def makeLdPath():
        pth=[environ[p] for p in ["FOAM_LIBBIN",
                                  "FOAM_USER_LIBBIN",
                                  "FOAM_SITE_LIBBIN"] if p in environ]

        if "FOAM_MPI" in environ and "FOAM_LIBBIN" in environ:
            pth=[path.join(environ["FOAM_LIBBIN"],environ["FOAM_MPI"])]+pth

        return pth

    if sys.platform in ["darwin"]:
        if "DYLD_LIBRARY_PATH" not in environ:
            environ["DYLD_LIBRARY_PATH"]=":".join(makeLdPath())

    if "LD_LIBRARY_PATH" not in environ:
        environ["LD_LIBRARY_PATH"]=":".join(makeLdPath())


def shellExecutionPrefix(ensureDynamic=True,asList=False):
    """Stuff to prefix to a call that is passed to the shell. Main
    application is currently to work around a security feature of Mac OS X
    10.11 that doesn't pass the load paths for the dynamic libraries to a
    shell"""
    if ensureDynamic:
        ensureDynamicLibraries()
    prefix=[]
    if sys.platform in ["darwin"]:
        for v in ["LD_LIBRARY_PATH","DYLD_LIBRARY_PATH"]:
            if v in environ:
                prefix.append("export "+v+"="+environ[v]+"; ")

    if asList:
        return prefix
    else:
        return "".join(prefix)

def changeFoamVersion(new,
                      force64=False,
                      force32=False,
                      compileOption=None,
                      foamCompiler=None,
                      wmCompiler=None):
    """Changes the used FoamVersion. Only valid during the runtime of
    the interpreter (the script or the Python session)
    :param new: The new Version
    :param force64: Forces the 64-bit-version to be chosen
    :param force32: Forces the 32-bit-version to be chosen
    :param compileOption: Forces Debug or Opt
    :param wmCompiler: Force new value for WM_COMPILER
    :param foamCompiler: Force system or OpenFOAM-Compiler"""

    newFork,newVersion,basedir=findInstallationDir(new)

    old=None
    oldFork=foamFork()
    if "WM_PROJECT_VERSION" in environ:
        old=environ["WM_PROJECT_VERSION"]
        if newVersion==old and newFork==oldFork:
            warning(old+"-"+foamFork(),"is already being used")
    else:
        warning("No OpenFOAM-Version installed")

    if path.exists(path.join(basedir,"etc")):
        script=path.join(basedir,"etc","bashrc")
    else:
        script=path.join(basedir,".OpenFOAM-"+new,"bashrc")

    forceArchOption=None
    if force64:
       forceArchOption="64"
    elif force32:
       forceArchOption="32"

    injectVariables(script,
                    forceArchOption=forceArchOption,
                    compileOption=compileOption,
                    foamCompiler=foamCompiler,
                    wmCompiler=wmCompiler)

    try:
        if old==environ["WM_PROJECT_VERSION"] and oldFork==foamFork():
            warning("Problem while changing to version",new,"old version still used:",foamFork()+"-"+environ["WM_PROJECT_VERSION"])
    except KeyError:
        pass

def injectVariables(script,
                    forceArchOption=None,
                    compileOption=None,
                    foamCompiler=None,
                    wmCompiler=None):
    """Executes a script in a subshell and changes the current
    environment with the enivironment after the execution
    :param script: the script that is executed
    :param forceArchOption: To which architecture Option should be forced
    :param compileOption: to which value the WM_COMPILE_OPTION should be forced
    :param wmCompiler: Force new value for WM_COMPILER
    :param foamCompiler: Force system or OpenFOAM-Compiler"""

    # Certan bashrc-s fail if these are set
    for v in ["FOAM_INST_DIR",
              "WM_THIRD_PARTY_DIR",
              "WM_PROJECT_USER_DIR",
              "OPAL_PREFIX"]:
        try:
            del environ[v]
        except KeyError:
            pass

    if not path.exists(script):
        error("Can not execute",script,"it does not exist")

    try:
        if "SHELL" in environ:
            shell=environ["SHELL"]

        if(path.basename(shell).find("python")==0):
            # this assumes that the 'shell' is a PyFoam-Script on a cluster
            shell=config().get("Paths","bash")
            environ["SHELL"]=shell

        allowedShells = [ "bash", "zsh", "sh", "dash"]
        if not path.basename(shell) in allowedShells:
            error("Currently only implemented for the shells",allowedShells,", not for",shell)

        cmd=""
        postCmd=""
        if forceArchOption!=None:
            cmd+="export WM_ARCH_OPTION="+forceArchOption+"; "
            postCmd+=" WM_ARCH_OPTION="+forceArchOption
        if compileOption!=None:
            cmd+="export WM_COMPILE_OPTION="+compileOption+"; "
            postCmd+=" WM_COMPILE_OPTION="+compileOption
        if foamCompiler!=None:
            cmd+="export foamCompiler="+foamCompiler+"; "
            postCmd+=" foamCompiler="+foamCompiler
        if wmCompiler!=None:
            cmd+="export WM_COMPILER="+wmCompiler+"; "
            postCmd+=" WM_COMPILER="+wmCompiler
        cmd+=" . "+script+postCmd+'; echo "Starting The Dump Of Variables"; export'
    except KeyError:
        # Instead of 'KeyError as name'. This is compatible with 2.4-3.2
        # http://docs.pythonsprints.com/python3_porting/py-porting.html#handling-exceptions
        name = sys.exc_info()[1]
        error("Can't do it, because shell variable",name,"is undefined")

    if sys.version_info<(2,6):
        raus,rein = popen4(cmd)
    else:
        p = Popen("bash -c '"+cmd+"'", shell=True,
                  stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        (rein,raus)=(p.stdin,p.stdout)
    lines=[l.strip().decode() for l in raus.readlines()]
    rein.close()
    raus.close()

    # clumsy but avoids more complicated expressions
    exp=re.compile('export (.+)="(.*)"$')
    exp2=re.compile("export (.+)='(.*)'$")
    exp3=re.compile('declare -x (.+)="(.*)"$')

    cnt=0

    for l in lines:
        m=exp.match(str(l))
        if not m:
            m=exp2.match(str(l))
        if not m:
            m=exp3.match(str(l))
        if m:
            cnt+=1
            environ[m.groups()[0]]=m.groups()[1]

def getUserName():
    """Get the current username"""
    import getpass
    return getpass.getuser()

def getPublicKey():
    from PyFoam.Infrastructure.Authentication import myPublicKeyText,ensureKeyPair
    ensureKeyPair()
    return myPublicKeyText()

def getAuthenticatedKeys():
    from PyFoam.Infrastructure.Authentication import authenticatedKeys,ensureKeyPair
    ensureKeyPair()
    return authenticatedKeys()

def getUserTempDir():
    """Return path to a user-specific private directory. Create directory if not existing"""
    from os import path
    import tempfile,os

    tempDir=path.join(tempfile.gettempdir(),
                      "PyFoam_"+getUserName())
    if not path.isdir(tempDir):
        try:
            os.mkdir(tempDir)
        except OSError:
            tempDir=tempfile.gettempdir()
    return tempDir

# Should work with Python3 and Python2
