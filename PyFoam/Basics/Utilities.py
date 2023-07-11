#  ICE Revision: $Id$
""" Utility functions

Can be used via a class or as functions"""

import sys
from PyFoam.ThirdParty.six import print_
from PyFoam.Error import warning,error
import subprocess
import os,fnmatch

if sys.version_info<(2,6):
    from popen2 import popen4
else:
    from subprocess import Popen,PIPE,STDOUT
from os import listdir,path,remove as removeFile

import re

try:
    import shutil
except ImportError:
    # this is an old python-version without it. We'll try to work around it
    pass

class Utilities(object):
    """Class with utility methods

    Can be inherited without side effects by classes that need these
    methods"""

    def __init__(self):
        pass

    def execute(self,
                cmd,
                debug=False,
                workdir=None,
                echo=None,
                outfile=None,
                getReturnCode=False):
        """Execute the command cmd. If specified change the working directory

        Currently no error-handling is done
        :return: A list with all the output-lines of the execution"""
        if debug:
            print_(cmd)

        oldDir=None
        if workdir:
            oldDir=os.getcwd()
            os.chdir(workdir)

        if type(cmd)==list:
            fpath=cmd[0]
        else:
            fpath=cmd.split(" ")[0]

        # Check if the file is there. Then we assume that this is a script
        if os.path.exists(fpath):
            # Script seems to be unexecutable
            if not os.access(fpath, os.X_OK):
                error("The script file",fpath,"is not executable")

        if sys.version_info<(2,6):
            raus,rein = popen4(cmd)
        else:
            p = Popen(cmd, shell=True,
                      stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True,
                      universal_newlines=True)
            (rein,raus)=(p.stdin,p.stdout)
        if (echo is not None) or (outfile is not None):
            tmp=[]
            while p.poll()==None:
                l=raus.readline()
                if echo is not None:
                    print_(echo,l,end="")
                if outfile is not None:
                    outfile.write(l)
                else:
                    tmp.append(l)
        else:
            tmp=raus.readlines()
        # line=raus.readline()
        # while line!="":
        #     print line
        #     line=raus.readline()

        if oldDir:
            os.chdir(oldDir)

        if getReturnCode:
            return p.returncode,tmp
        else:
            return tmp

    def remove(self,f):
        """Remove a file if it exists."""
        if path.exists(f):
            removeFile(f)

    def rmtree(self,dst,ignore_errors=False):
        """Encapsulates the shutil rmtree and provides an alternative for
        old Python-version"""
        try:
            if path.isdir(dst):
                shutil.rmtree(dst,ignore_errors=ignore_errors)
            elif path.exists(dst):
                os.remove(dst)
        except NameError:
            self.execute("rm -rf "+dst)

    def copytree(self,src,dst,
                 symlinks=False,force=False):
        """Encapsulates the shutil copytree and provides an alternative for
        old Python-version"""
        if force and path.exists(dst):
            if path.isdir(dst):
                self.rmtree(dst)
            else:
                os.remove(dst)
        try:
            if path.isdir(dst):
                dst=path.join(dst,path.basename(path.abspath(src)))

            if path.islink(src) and symlinks:
                os.symlink(path.realpath(src),dst)
            elif path.isdir(src):
                shutil.copytree(src,dst,
                                symlinks=symlinks)
            else:
                self.copyfile(src,dst)
        except NameError:
            cpOptions="-R"
            if not symlinks:
                cpOptions+=" -L"
            self.execute("cp "+cpOptions+" "+src+" "+dst)

    def copyfile(self,src,dst):
        """Encapsulates the shutil copyfile and provides an alternative for
        old Python-version"""
        try:
            if path.isdir(dst):
                dst=path.join(dst,path.basename(path.abspath(src)))
            shutil.copyfile(src,dst)
            shutil.copymode(src,dst)
        except NameError:
            self.execute("cp "+src+" "+dst)

    def writeDictionaryHeader(self,f):
        """Writes a dummy header so OpenFOAM accepts the file as a dictionary
        :param f: The file to write to
        :type f: file"""

        f.write("""
// * * * * * * * * * //
FoamFile
{
	version 0.5;
	format ascii;
	root "ROOT";
	case "CASE";
	class dictionary;
	object nix;
}
""")

    excludeNames=["^.svn$" , "~$"]

    def findFileInDir(self,dName,fName):
        """Find file in a directory (search recursively)
        :param dName: name of the directory
        :param fName: name of the file to look force
        :return: the complete path. Directory and path joined if nothing
        is found"""
        def lookFor(dName,fName):
            if path.exists(path.join(dName,fName)):
                return path.join(dName,fName)
            else:
                for f in listdir(dName):
                    if path.isdir(path.join(dName,f)):
                        result=lookFor(path.join(dName,f),fName)
                        if result:
                            return result
                return None
        result=lookFor(dName,fName)

        if result:
            return result
        else:
            return path.join(dName,fName)

    def listDirectory(self,d):
        """Lists the files in a directory, but excludes certain names
        and files with certain endings
        :param d: The directory to list
        :return: List of the found files and directories"""

        result=[]

        excludes=[re.compile(e) for e in self.excludeNames]

        for n in listdir(d):
            ok=True

            for e in excludes:
                if e.search(n):
                    ok=False
                    break

            if ok:
                result.append(n)

        return result

    def which(self,progname):
        """Get the full path. Return None if not found"""
        try:
            return shutil.which(progname)
        except AttributeError:
            # shutil has no which
            pipe = subprocess.Popen('which '+progname,
                                    shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)

            (fullname, errout) = pipe.communicate(input=input)

            stat = pipe.returncode

            if stat:
                warning("which can not find a match for",progname)
                return None
            else:
                return fullname

    def find(self,pattern, path,directoriesToo=True):
        """Find all files whose names match
        :param pattern: glob-style pattern
        :param path: path under which this files are to be searched
        :param directoriesToo: also match directories?"""
        result = []
        for root, dirs, files in os.walk(path):
            for name in files:
                if fnmatch.fnmatch(name, pattern):
                    result.append(os.path.join(root, name))
            if directoriesToo:
                for name in dirs:
                    if fnmatch.fnmatch(name, pattern):
                        result.append(os.path.join(root, name))
        return result

    def humanReadableSize(self,num):
        """Lifted from http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
        Gets a number in bytes and returns a human readable string"""
        for x in ['bytes','KB','MB','GB']:
            if num < 1024.0 and num > -1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, 'TB')

    def humanReadableDuration(self,num):
        """Creates a string that prints a duration in an easily readable form.
        Easily readable means that the two highest non-zero values will be printed"""
        intervals=[60*60*24*365,
                   60*60*24,
                   60*60,
                   60]
        names=["%dy",
               "%dd",
               "%dh",
               "%dmin",
               "%fs"]
        vals=[]
        for i in intervals:
            if num<i:
                vals.append(0)
            else:
                v=int(num/i)
                num-=v*i
                vals.append(v)
        result=None
        for v,s in zip(vals,names):
            if v>0:
                if result is None:
                    result=s%v
                else:
                    result+=" "+s%v
                    break
        if result is None:
            return " 0s"
        else:
            return result

    def diskUsage(self,fpath):
        """Calculate the disk space used at the specified path in bytes"""
        try:
            return int(
                subprocess.Popen(
                    ["du","-sb",fpath],
                    stdout=subprocess.PIPE,
                    stderr=open(os.devnull,"w")
                ).communicate()[0].split()[0])
        except IndexError:
            # assume that this du does not support -b
            return int(
                subprocess.Popen(
                    ["du","-sk",fpath],
                    stdout=subprocess.PIPE
                ).communicate()[0].split()[0])*1024

def diskUsage(fpath):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().diskUsage(fpath)

def humanReadableSize(num):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().humanReadableSize(num)

def humanReadableDuration(num):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().humanReadableDuration(num)

def which(prog):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().which(prog)

def execute(cmd,
            debug=False,
            workdir=None,
            echo=None,
            outfile=None,
            getReturnCode=False):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().execute(cmd,
                               debug=debug,
                               workdir=workdir,
                               echo=echo,
                               outfile=outfile,
                               getReturnCode=getReturnCode)

def writeDictionaryHeader(f):
    """Calls the method of the same name from the Utilites class"""
    Utilities().writeDictionaryHeader(f)

def listDirectory(d):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().listDirectory(d)

def findFileInDir(d,f):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().findFileInDir(d,f)

def rmtree(path,ignore_errors=False):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().rmtree(path,ignore_errors=ignore_errors)

def copytree(src,dest,symlinks=False,force=False):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().copytree(src,dest,symlinks=symlinks,force=force)

def remove(f):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().remove(f)

def copyfile(src,dest):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().copyfile(src,dest)

def find(pattern,path,directoriesToo=True):
    """Calls the method of the same name from the Utilites class"""
    return Utilities().find(pattern,path,directoriesToo=directoriesToo)

# Should work with Python3 and Python2
