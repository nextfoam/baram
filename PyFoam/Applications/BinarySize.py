"""
Application-class that implements pyFoamBinarySize.py
"""
from optparse import OptionGroup

from .PyFoamApplication import PyFoamApplication

from PyFoam.ThirdParty.six import print_
from PyFoam.ThirdParty.tqdm import tqdm

from PyFoam.Basics.Utilities import diskUsage,humanReadableSize

import PyFoam.FoamInformation as FI

from os import listdir,path

class BinarySize(PyFoamApplication):
    def __init__(self,
                 args=None,
                 **kwargs):
        description="""\
Goes through the OpenFOAM-installation and records the size of all the binary
files (linked as well as object files) and reports them for each compiliation
option separately (Debug/Opt, compilers)

This should provide the user with an overview how much disk space each variation
of the binaries needs.

The reported OpenfOAM-installation can be selected using the usual Foam-version
switching.
"""
        examples="""\
%prog

  List the disk space used by the current OpenFOAM-installation

%prog --foamVersion=1.7.x

  List the disk space used by binaries in OpenFOAM-1.7.x

%prog --all-installations

  List the disk space used by all the available installations

%prog --all-installations --follow-symlinked-installations

  Also follow symlinked installations (this may count binaries twice)"""

        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   examples=examples,
                                   usage="%prog <caseDirectory>",
                                   interspersed=True,
                                   changeVersion=True,
                                   nr=0,
                                   exactNr=True,
                                   **kwargs)

    def addOptions(self):
        what=OptionGroup(self.parser,
                         "What",
                         "What should be reported")
        self.parser.add_option_group(what)

        what.add_option("--all-installations",
                        action="store_true",
                        dest="allInstallations",
                        default=False,
                        help="Report the disk usage for all installations (this may take quite a while)")
        what.add_option("--follow-symlinked-installations",
                        action="store_true",
                        dest="symlinkInstallations",
                        default=False,
                        help="Also count the installation if it is a symlink (otherwise only report the original installation and skip it)")
        what.add_option("--no-documentation",
                        action="store_false",
                        dest="doDocumentation",
                        default=True,
                        help="Do not process the amount of memory needed by the documentation")

        what.add_option("--no-third-party",
                        action="store_false",
                        dest="doThirdParty",
                        default=True,
                        help="Do not process the amount of memory needed by the Third-party directory")

        display=OptionGroup(self.parser,
                            "Display",
                            "Output on the screen")
        self.parser.add_option_group(display)
        display.add_option("--progress-maximum-depth",
                           action="store",
                           type=int,
                           dest="maximumProgressDepth",
                           default=2,
                           help="Maximum level of recursion depth for which the progress should be reported. Default: %default")
        display.add_option("--no-progress-bar",
                           action="store_const",
                           const=0,
                           dest="maximumProgressDepth",
                           help="Switch off the progress bars")

    def output(self,*args):
        if self.opts.maximumProgressDepth>0:
            self.out+=" ".join(str(a) for a in args)+"\n"
        else:
            print_(*args)

    def scanDir(self, dPath, usages, depth=1, thirdParty=False):
        dName=path.basename(dPath)
        dirs= ["Make","platform","bin","platforms","build"]
        if self.opts.doDocumentation:
            dirs+=["Doxygen"]
        if dName[0]==".":
            return
        elif dName in ["lnInclude"]:
            return
        elif dName in dirs:
            for f in tqdm(listdir(dPath),
                          desc=path.basename(dPath),
                          disable=depth>self.opts.maximumProgressDepth,
                          unit="files"):
                if f[0]==".":
                    continue
                nPath=path.join(dPath,f)
                if path.isdir(nPath):
                    isBin=False
                    for end in ["Opt","Debug","Prof"]:
                        if f.find(end)>0 and (f.find(end)+len(end))==len(f):
                            isBin=True
                    if f in ["html"] and self.opts.doDocumentation:
                        isBin=True
                    if thirdParty:
                        for c in ["Gcc", "Clang", "linux"]:
                            if f.find(c)>=0:
                                isBin = True
                    if isBin:
                        sz=diskUsage(nPath)
                        try:
                            usages[f]+=sz
                        except KeyError:
                            usages[f]=sz
                           # self.output("Found architecture",f,"in",dPath)
        else:
            try:
                for f in tqdm(listdir(dPath),
                              unit="files",
                              disable=depth>self.opts.maximumProgressDepth,
                              desc=path.basename(dPath)):
                    nPath=path.join(dPath,f)
                    if path.isdir(nPath) and not path.islink(nPath):
                        self.scanDir(nPath,usages,depth=depth+1, thirdParty=thirdParty)
            except OSError:
                self.warning("Can't process",dPath)

    def reportInstallation(self, fName, thirdParty=False):
        """Report the usages of a OpenFOAM-installation"""
        self.output("\nScanning",fName)
        totalSize = diskUsage(fName)
        self.output("  Total size:",humanReadableSize(totalSize))
        if path.islink(fName):
            self.output("Symlinked to",path.realpath(fName))
            if not self.opts.symlinkInstallations:
                self.output("Skipping symlinked installation")
                return 0
        usages={}
        self.scanDir(fName, usages, thirdParty=thirdParty)
        if len(usages)>0:
            nameLength=max([len(k) for k in usages.keys()])
            sizeLength=max([len(str(k)) for k in usages.values()])
            formatString="    %%%ds - %%%dd (%%s)" % (nameLength,sizeLength)
            total=0
            for k in sorted(usages.keys()):
                v=usages[k]
                total+=v
                self.output(formatString % (k,v,humanReadableSize(v)))
            self.output("Sum of binaries",humanReadableSize(total))
            return total, totalSize
        else:
            self.output("    No binaries found")
            return 0, totalSize

    def run(self):
        self.out=""
        if self.opts.allInstallations:
            installed=FI.foamInstalledVersions()
            total, size = 0, 0
            for k in tqdm(sorted(installed.keys()),
                          desc="Distro",
                          unit="distro"):
                instPath=installed[k]
                t, s = self.reportInstallation(instPath)
                total += t
                size += s
                if self.opts.doThirdParty:
                    thirdPartyDir = FI.findThirdPartyDir(k)
                    if thirdPartyDir is not None:
                        t, s = self.reportInstallation(thirdPartyDir, thirdParty=True)
                        total += t
                        size += s

            self.output("\nTotal disk space used by binaries: {} (Complete size: {})".format(
                humanReadableSize(total),
                humanReadableSize(size)))
        else:
            try:
                self.reportInstallation(FI.installationPath())
                if self.opts.doThirdParty:
                    installed = FI.foamInstalledVersions()
                    version = None
                    for k in installed:
                        if installed[k] == FI.installationPath():
                            version = k
                            break
                    if k is not None:
                        self.reportInstallation(FI.findThirdPartyDir(version), thirdParty=True)

            except KeyError:
                self.error("No Foam-installation active. Specify one")
        if len(self.out)>0:
            print_("\n")
            print_(self.out)
