"""Execute an Application class through a different Python-interpreter

We need to create a temporary script because pvpython does not support
the usual -c optiont

"""

from PyFoam.Basics.Utilities import which
from PyFoam.ThirdParty.six import print_,PY3,u

if PY3:
    fopen=open
else:
    from io import open as fopen

# doDebug=True
doDebug=False

def printDebug(*args):
    if doDebug:
        print_(*args)

import sys
from os import environ as env
from os import path
import os
import stat
from subprocess import call

from tempfile import mkstemp

def changePython(pythonName,appClass,options=None):
    options=[] if options is None else options
    print_("Executing",appClass,"with",pythonName,"trough a proxy-script",
           "options:"," ".join(options))
    if path.exists(pythonName):
        pyInterpreter=pythonName
    else:
        pyInterpreter=which(pythonName)
    if pyInterpreter is None:
        print_("Error: No interpreter",pythonName,"found")
        sys.exit(-1)
    else:
        pyInterpreter=pyInterpreter.strip()

    printDebug("Using interpreter",pyInterpreter)
    pyFoamLocation=path.dirname(path.dirname(path.dirname(__file__)))
    printDebug("PyFoam location",pyFoamLocation,".")
    if "PYTHONPATH" in env:
        printDebug("PYTHONPATH:",env["PYTHONPATH"])
    else:
        printDebug("No PYTHONPATH")
    if "PYTHONPATH" not in env:
        env["PYTHONPATH"]=pyFoamLocation
    elif pyFoamLocation not in env["PYTHONPATH"].split(path.pathsep):
        env["PYTHONPATH"]=pyFoamLocation+path.pathsep+env["PYTHONPATH"]
    if "PYTHONPATH" in env:
        printDebug("PYTHONPATH:",env["PYTHONPATH"])
    else:
        printDebug("No PYTHONPATH")
    scriptFD,scriptName=mkstemp(suffix=".py",prefix="pyFoam"+appClass+"_",text=True)
    printDebug("Script file:",scriptName,"Handle",scriptFD)
    os.chmod(scriptName,stat.S_IXUSR | os.stat(scriptName).st_mode)
    fopen(scriptFD,"w").write(u("""#! %(pyInterpreter)s
from PyFoam.Applications.%(appClass)s import %(appClass)s

%(appClass)s()
""" % {'appClass':appClass,'pyInterpreter':" ".join([pyInterpreter]+options)}))

    ret=call([scriptName]+sys.argv[1:])
    printDebug("Return code:",ret)
    if ret:
        print_("Error: Return code ",ret,"executing",scriptName)
    else:
        os.unlink(scriptName)
