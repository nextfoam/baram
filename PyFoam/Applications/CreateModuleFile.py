"""
Application-class that implements pyFoamCreateModuleFile.py

Generate a Modules modulefile for OpenFOAM using differences in environment
variables before and after sourcing the main OpenFOAM configuration file

For more information on Modules, visit the Environment  Modules Project:
http://modules.sourceforge.net

Usage : pyFoamCreateModuleFile.py OpenFOAM_CfgFile moduleFile

        For example: pyFoamCreateModuleFile.py ./bashrc /tmp/module

Warning #1: This command will not work if your OpenFOAM environment variabales are already
            initialized.

Warning #2: This command will not work if you are using the superuser account (aka: root)

Author:
  Martin Beaudoin, Hydro-Quebec, 2012.  All rights reserved

"""

import os
import string
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication
from PyFoam.Basics.Utilities import execute
from sets import Set
from os import path

from PyFoam.ThirdParty.six import print_

class CreateModuleFile(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""
Create a Modules modulefile for OpenFOAM. Input parameter 'OpenFOAM configuration file': bashrc or cshrc file for OpenFOAM; usually $WM_PROJECT_DIR/etc/bashrc or $WM_PROJECT_DIR/etc/cshrc. Output parameter 'modulefile': the resulting module file. For more information on Modules,  visit the Environment  Modules Project:  http://http://modules.sourceforge.net
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog OpenFOAM_cfgFile modulefile",
                                   interspersed=True,
                                   changeVersion=False,
                                   nr=2,
                                   **kwargs)

    def addOptions(self):
        module=OptionGroup(self.parser,
                           "Module",
                           "Options specific for the module-utility")
        self.parser.add_option_group(module)

        module.add_option("--csh",
                          action="store_true",
                          dest="useCshell",
                          default=False,
                          help='Use csh instead of bash for activating the OpenFOAM configuration')
        module.add_option("--clear-environment",
                          action="store_true",
                          dest="clearEnvironment",
                          default=False,
                          help='Attempt to clear the environment of all traces of an OpenFOAM-installation before proceeding. This is no substitute to having a clean environment')


    def uniqifyPathEnvVar(self, pathEnvVar):
        """Remove all duplicates from PATH env var. Order preserving"""
        checked = []
        for e in pathEnvVar.split(':'):
            if e not in checked:
                checked.append(e)

        return ":".join(checked)

    def removeComponentWithSubstrFromPathEnvVar(self, pathEnvVar, removeSubStr):
        """Remove components from PATH env var where a substring is present. Order preserving"""
        keepComponents = []
        pathComponents = pathEnvVar.split(':')

        for e in pathComponents:
            if e.find(removeSubStr) < 0:
                keepComponents.append(e)

        return ":".join(keepComponents)

    def removeComponentFromPathEnvVar(self, pathEnvVar, removePathComponents):
        """Remove components from PATH env var. Order preserving"""
        keepComponents = []
        pathComponents = pathEnvVar.split(':')
        removeComponents = removePathComponents.split(':')

        for e in pathComponents:
            if e not in removeComponents:
                keepComponents.append(e)

        return ":".join(keepComponents)


    def writeModuleFileHeader(self, fid, version):
        """Write Modules file header"""
        fid.write("#%Module1.0\n")
        fid.write("\n")
        fid.write("proc ModulesHelp { } {\n")
        fid.write("    puts stderr \"OpenFOAM version " + version + "\"\n")
        fid.write("}\n")
        fid.write("\n")
        fid.write("module-whatis \"OpenFOAM version " + version + "\"\n")


    def writeModuleFileFooter(self, fid):
        """Write Modules file footer"""
        fid.write("\n")
        fid.write("#EOF\n")
        return

    def writeModuleEnvironmentEntry(self, fid, envVarDict, homeVar, userVar):
        """Write Modules file environment variables"""
        fid.write("\n")
        fid.write("set HOME \"$env(HOME)\"\n")
        fid.write("set USER \"$env(USER)\"\n")
        fid.write("\n")
        fid.write("# Environment variables\n")

        # Memorize PATH variables
        pathVars = {}

        #Sorting keys
        keylist = list(envVarDict.keys())
        keylist.sort()
        for k in keylist:
            value = envVarDict[k][0]

            # Remove expanded occurences of $HOME variable
            value = value.replace(homeVar, "$HOME")

            # Remove expanded occurences of $USER variable
            value = value.replace(userVar, "$USER")

            if k.find('PATH') > -1 and value != ":":
                pathVars[k] = value
            else:
                fid.write("setenv " + k + " " + "\"" + value + "\""+ "\n")

        # Prepend PATH variables
        fid.write("\n")
        fid.write("# Various PATH variables\n")
        for k in pathVars:
            value = pathVars[k]
            if len(value) > 0:
                fid.write("prepend-path " + k + " " + "\"" + pathVars[k] + "\""+ "\n")
                fid.write("\n")

        # Write TCL variables for the environment variables.
        # This is only necessary for module.
        # The aliases definitions will use this
        # We also need to pay attention to empty environment variables
        # for TCL. if [info exists env(VARNAME)] {set value $env(VARNAME)}
        #
        fid.write("# Temporary TCL variables for the environment variables\n")
        fid.write("# Module will need this for the aliases when parsing this file\n")
        for k in keylist:
            fid.write("if [info exists env(" + k + ")] {set " + k + ' \"$env(' + k + ')\"}\n')
        fid.write("\n")


    def writeModuleAliasEntry(self, fid, aliasesVarDict, homeVar, userVar):
        """Write Modules file aliases"""
        fid.write("# Aliases\n")

        #Sorting keys
        keylist = list(aliasesVarDict.keys())
        keylist.sort()
        for k in keylist:
            value = aliasesVarDict[k][0]

            # Remove expanded occurences of $HOME variable
            value = value.replace(homeVar, "$HOME")

            # Remove expanded occurences of $USER variable
            value = value.replace(userVar, "$USER")

            fid.write("set-alias " + k + " " + "\"" + value + "\""+ "\n")

    def run(self):
        cfgFile=self.parser.getArgs()[0]
        moduleFile=self.parser.getArgs()[1]
        useCsh = self.opts.useCshell

        if self.opts.clearEnvironment:
            self.warning("Clearing environment of variables that might come from an OpenFAOM-installation. Nevertheless it is preferable to use a clean environment")
            try:
                oldVersion=os.environ["WM_PROJECT_VERSION"]
            except KeyError:
                self.warning("Seems to be a clean environment anyway")
                oldVersion=None

            if oldVersion:
                for e in list(os.environ.keys()):
                    for p in ["WM_","FOAM_"]:
                        if e.find(p)==0:
                            del os.environ[e]
                            break
                for p in ["PATH","DYLD_LIBRARY_PATH","LD_LIBRARY_PATH","MANPATH","PV_PLUGIN_PATH"]:
                    if p in os.environ:
                        lst=os.environ[p].split(":")
                        os.environ[p]=":".join([l for l in lst if l.find(oldVersion)<0])

        if path.exists(cfgFile) and path.isfile(cfgFile) and os.access(cfgFile, os.R_OK):
            print_(" Using file " + cfgFile + " for loading the OpenFOAM environment")

            # Some more sanity check
            fileData = open(cfgFile).read()
            if not useCsh and "setenv" in fileData:
                self.error(" Error: Detecting 'setenv' instructions in this bash file. Please provide a configuration file compatible for bash, or use the --csh option.")
            elif useCsh and "export" in fileData:
                self.error(" Error: Detecting 'export' instructions in this csh file. Please provide a configuration file compatible for csh.")
            else:
                print_(" The configuration file seems ok")
        else:
            self.error(" Error: Cannot access file: " + cfgFile)

        # We choose not to run if the OpenFOAM environment is already loaded.
        # We obviously cannot diff from such an environment
        if os.getenv("WM_PROJECT") != None:
            self.error(""" Error: Cannot run with OpenFOAM environment variables already present
                       You need to run this script from a clean environment""")

        # We choose not to run under the user 'root', simply because the HOME and USER environment
        # variables are usually very similar for this user, and this will cause problem later on
        # For instance, under Centos, for the super user:
        #     HOME=/root
        #     USER=root
        # Those two are very similar
        if os.getenv("USER") == "root":
            self.error(""" Error: You should not run this script from the 'root' account.
                       Please invoke this pyFoam command from a plain OpenFOAM user account.
                       Then, make the result file available to the super user (root) of the"
                       destination host in order to install the modules configuration files.""")

        # Grab environment + aliases before the activation of OpenFOAM
        # We start from a minimal environment using 'env -i'
        shellCmd = 'bash -c'
        sourceCmd = '.'

        if useCsh:
            shellCmd = 'csh -c'
            sourceCmd = 'source'

        oldEnv=Set(execute(shellCmd + ' "env|sort"'))
        oldAliases=Set(execute(shellCmd + ' "alias|sort"'))

        # Grab environment + aliases after the activation of OpenFOAM
        newEnv=Set(execute(shellCmd + ' \"' + sourceCmd + ' ' + cfgFile + '; env|sort"'))
        newAliases=Set(execute(shellCmd + ' \"' + sourceCmd + ' ' + cfgFile + '; alias|sort"'))

        # Handling of environment variables
        # Memorize all the PATH environment variables for later processing
        oldPath = {}
        newPath = {}
        homeVar = ""
        userVar = ""

        for v in oldEnv:
            if v.find('=') > -1:
                key, value = v.split('=', 1)

                # Memorize PATH variables
                if key.find('PATH') > -1:
                    oldPath[key] = value.replace('\n', '')

                    # We remove any reference to PyFOAM in the old PATH env. variable
                    # Since we run this script with PyFOAM, environment variables for PyFoam are
                    # present in oldPath. If the configuration file for OpenFOAM requires PyFoam too,
                    # we risk to lose these variables because they will be in common in both the
                    # 'before' and 'after'environment.
                    # This is ugly, but PyFOAM is just too useful to write this script with plain
                    # python.
                    # If you have installed PyFoam under a path where the string 'PyFoam' is not present,
                    # you will simply have to manually add the necessary PyFoam environment variables
                    # yourself in the module file. No biggie,
                    oldPath[key] = self.removeComponentWithSubstrFromPathEnvVar(oldPath[key], 'PyFoam')

                # Memorize HOME variable
                if key == 'HOME':
                    homeVar = value.replace('\n', '')

                # Memorize USER variable
                if key == 'USER':
                    userVar = value.replace('\n', '')

        # Using sets, it is trivial to remove common environment variables
        # and aliases between the two environments
        moduleEnv=newEnv - oldEnv
        moduleAliases=newAliases - oldAliases

        # Dictionary for environment variables
        envVar = {}

        # Dictionary for aliases
        aliasesVar = {}

        # Iterate through environment variables and store in dictionary
        for v in moduleEnv:
            if v.find('=') > -1:
                key, value = v.split('=', 1)

                # Minor cleanup
                value = value.replace('\n', '')

                # Memorize PATH variables for later processing
                if key.find('PATH') > -1:
                    newPath[key] = value
                else:
                    envVar.setdefault(key, []).append(value)

        # Handle the PATH variables
        for v in newPath:
            if v in oldPath:
                # Cleanup old PATH components
                newPath[v] = self.removeComponentFromPathEnvVar(newPath[v], oldPath[v])

            # Remove duplicate entries in PATH variable
            newPath[v] = self.uniqifyPathEnvVar(newPath[v])
            envVar.setdefault(v, []).append(newPath[v])

        # Iterate through aliases variables and store them in dictionary
        for v in moduleAliases:
            if v.find('=') > -1:
                key, value = v.split('=', 1)

                # Minor cleanup
                key = key.replace("alias ", "")
                value = value.replace('\n', "")
                value = value.replace('\'', "")
                aliasesVar.setdefault(key, []).append(value)

        # Generate module entries
        print_(" Generating modulefile: " , moduleFile)

        f = open(moduleFile, 'w')

        self.writeModuleFileHeader(f, envVar["WM_PROJECT_VERSION"][0])
        self.writeModuleEnvironmentEntry(f, envVar, homeVar, userVar)
        self.writeModuleAliasEntry(f, aliasesVar, homeVar, userVar)
        self.writeModuleFileFooter(f)

        f.close()
        print_(" Done\n")

# Should work with Python3 and Python2
