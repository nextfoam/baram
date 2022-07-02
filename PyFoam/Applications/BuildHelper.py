#  ICE Revision: $Id$
"""
Application class that implements pyFoamBuildHelper
"""

from .PyFoamApplication import PyFoamApplication
from PyFoam.Basics.GeneralVCSInterface import whichVCS,getVCS
from PyFoam.Error import FatalErrorPyFoamException

from optparse import OptionGroup
from os import environ,path
from platform import uname
import os,subprocess

from PyFoam.ThirdParty.six import print_

import sys

class BuildHelper(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
This application helps with updating a
project and the projects it depends on. A phase (or a desired output)
has to be specified with an options.

If no arguments are given then it assumes that the current directory
is the root directory of the project to be compiled and that the only
project it depends on is the OpenFOAM-installation (as found in the
WM_PROJECT_DIR-environment variable). Arguments are assumed to be
other projects that are injected between these two
        """

        PyFoamApplication.__init__(self,
                                   nr=0,
                                   exactNr=False,
                                   args=args,
                                   usage="%prog [options] <directories> [arguments]",
                                   description=description,
                                   interspersed=True,
                                   **kwargs)

    def addOptions(self):
        projects=OptionGroup(self.parser,
                             "Projects",
                             "Which projects should be automatically considered")
        self.parser.add_option_group(projects)

        projects.add_option("--no-openfoam",
                            dest="openfoam",
                            default=True,
                            action="store_false",
                            help="Do not consider the OpenFOAM-directory")
        projects.add_option("--no-current-directory",
                            dest="currentDir",
                            default=True,
                            action="store_false",
                            help="Do not consider the current directory")

        phases=OptionGroup(self.parser,
                             "Action",
                             "What to do")
        self.parser.add_option_group(phases)

        phases.add_option("--info",
                          dest="actions",
                          action="append_const",
                          const="info",
                          help="Only print the informations gathered")
        phases.add_option("--name-of-the-build",
                          dest="actions",
                          action="append_const",
                          const="name",
                          help="The unique name of the build to identify it in testing environments")
        phases.add_option("--update",
                          dest="actions",
                          action="append_const",
                          const="update",
                          help="Update the sources in all directories from their servers")
        phases.add_option("--build",
                          dest="actions",
                          action="append_const",
                          const="build",
                          help="Build all projects in the correct order")

        parameters=OptionGroup(self.parser,
                             "Parameters",
                             "Additional parameters")
        self.parser.add_option_group(parameters)
        parameters.add_option("--timeout",
                              dest="timeout",
                              action="store",
                              type="int",
                              default=None,
                              help="Default timeout (in seconds) for the update from the repositories. If none specified the default of the VCS in question is used. Only applicable if the VCS supports it")

    def run(self):
        if not self.opts.actions:
            self.error("No action defined")

        dirs=[]
        if self.opts.openfoam and "WM_PROJECT_DIR" in environ:
            dirs.append(environ["WM_PROJECT_DIR"])
        dirs+=self.parser.getArgs()
        if self.opts.currentDir:
            dirs.append(path.curdir)

        fullDirs=[]
        for d in dirs:
            if path.isdir(d):
                fullDirs.append(path.abspath(d))

        info=dict(list(zip(fullDirs,[{} for i in range(len(fullDirs))])))

        for d in fullDirs:
            info[d]["writable"]=os.access(d,os.W_OK)

            info[d]["isFoam"]=(d==fullDirs[0] and self.opts.openfoam)

            info[d]["vcs"]=whichVCS(d)

            if path.exists(path.join(d,"Allwmake")):
                info[d]["make"]="Allwmake"
            elif path.exists(path.join(d,"Makefile")):
                info[d]["make"]="make"
            else:
                info[d]["make"]="wmake"

            if info[d]["vcs"]=="":
                info[d]["branch"]="unknown"
            else:
                vcs=getVCS(info[d]["vcs"],
                           d,
                           tolerant=True)
                if vcs:
                    try:
                        info[d]["branch"]=vcs.branchName()
                    except FatalErrorPyFoamException:
                        info[d]["branch"]="notImplemented"

                    try:
                        info[d]["revision"]=vcs.getRevision()
                    except FatalErrorPyFoamException:
                        info[d]["revision"]="notImplemented"
                else:
                    info[d]["branch"]="noVCS"
                    info[d]["revision"]="noVCS"

        for action in self.opts.actions:
            if action=="info":
                print_("Project directories:\n")
                for i,d in enumerate(fullDirs):
                    print_("%2d.  %s" % (i+1,d))
                    print_("    ",info[d])
                    print_()

                self.setData({'order' : fullDirs,
                              'info'  : info})
            elif action=="name":
                name=""
                if self.opts.openfoam:
                    name+="%s-%s_%s_%s_%s" % (environ["WM_PROJECT"],
                                              environ["WM_PROJECT_VERSION"],
                                              environ["WM_ARCH"],
                                              environ["WM_OPTIONS"],
                                              environ["WM_MPLIB"])
                else:
                    name+="%s_%s" % (uname()[0],
                                     uname()[-1])
                name += "_branch-%s" % info[fullDirs[-1]]["branch"]

                print_(name)
                self.setData({'name'   : name,
                              'info'   : info,
                              'order'  : fullDirs})
            elif action=="update":
                success=True
                for d in fullDirs:
                    if info[d]["writable"]:
                        print_("Attempting to update",d)
                        print_()
                        vcs=getVCS(info[d]["vcs"],
                                   d,
                                   tolerant=True)
                        if vcs:
                            try:
                                if not vcs.update(timeout=self.opts.timeout):
                                    success=False
                            except FatalErrorPyFoamException:
                                e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
                                print_("Problem:",e)
                                success=False
                        else:
                            print_("Not under version control ... skipping")
                            success=False
                    else:
                        print_(d,"not writable .... skipping update")

                    print_()
                if not success:
                    self.error("Problem during updating")
            elif action=="build":
                success=True
                oldDir=os.getcwd()

                for d in fullDirs:
                    if info[d]["writable"]:
                        print_("Attempting to build",d)
                        print_()
                        makeCommand={"make"    :["make"],
                                     "wmake"   :["wmake"],
                                     "Allwmake":["./Allwmake"]}[info[d]["make"]]

                        print_("Changing to",d,"and executing"," ".join(makeCommand))
                        print_()
                        os.chdir(d)
                        erg=subprocess.call(makeCommand)
                        if erg:
                            print_()
                            print_("Result of build command:",erg)
                            success=False
                    else:
                        print_(d,"not writable .... skipping build")

                    print_()

                os.chdir(oldDir)

                if not success:
                    self.error("Problem during building")

            else:
                self.error("Unimplemented action",action)

# Should work with Python3 and Python2
