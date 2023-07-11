#  ICE Revision: $Id$
"""Watches the output of Foam-run"""

from os import path
import stat
import os
import gzip
from time import sleep

from PyFoam.Basics.LineReader import LineReader
from PyFoam import configuration as config

from PyFoam.ThirdParty.six import print_

class BasicWatcher(object):
    """Base class for watching the output of commands

    Works like the UNIX-command 'tail -f <file>': the last lines of the file are output.
    If the file grows then these lines are output as they arrive"""

    def __init__(self,filenames,
                 silent=False,
                 tailLength=1000,
                 sleep=0.1,
                 endTime=None,
                 follow=True):
        """:param filename: name of the logfile to watch
        :param silent: if True no output is sent to stdout
        :param tailLength: number of bytes at the end of the fail that should be output.
        :param follow: if the end of the file is reached wait for further input
        Because data is output on a per-line-basis
        :param sleep: interval to sleep if no line is returned"""

        if type(filenames) is list:
            meshTimes=[]
            createMesh="Create mesh for time = "
            for fName in filenames:
                meshTime=None
                with open(fName) as f:
                    for l in f.readlines()[:100]:
                        if l.find(createMesh)==0:
                            meshTime=float(l[len(createMesh):])
                            break
                meshTimes.append((fName,meshTime))
            meshTimes.sort(key=lambda x:1e50 if x[1] is None else x[1])
            filenames=[m[0] for m in meshTimes]
            self.filename=filenames[0]
            self.nextFiles=filenames[1:]
            self.changeTimes=[m[1] for m in meshTimes[1:]]
        else:
            self.filename=filenames
            self.nextFiles=[]
            self.changeTimes=[]

        self._changeFileHooks=[]

        self.silent=silent
        self.tail=tailLength
        self.sleep=sleep
        self.follow=follow
        self.endTime=endTime
        self.isTailing=False

        if not path.exists(self.filename):
            print_("Error: Logfile ",self.filename,"does not exist")

        self.reader=LineReader(config().getboolean("SolverOutput","stripSpaces"))

    def getSize(self,filename):
        """:return: the current size (in bytes) of the file"""
        return os.stat(filename)[stat.ST_SIZE]

    def addChangeFileHook(self,func):
        self._changeFileHooks.append(func)

    def changeFile(self,filename):
        currSize=self.getSize(filename)

        fn,ext=path.splitext(filename)
        if ext=='.gz':
            fh=gzip.open(filename)
        else:
            fh=open(filename)

        for f in self._changeFileHooks:
            f()

        return fh,currSize

    def start(self):
        """Reads the file and does the processing"""

        fh,currSize=self.changeFile(self.filename)
        switchTime=None if len(self.changeTimes)==0 else self.changeTimes[0]
        self.changeTimes=self.changeTimes[1:]

        self.startHandle()

        while self.follow or currSize>self.reader.bytesRead() or len(self.nextFiles)>0:
            if self.endTime is not None:
                if self.analyzer.isPastTime(self.endTime):
                    print_("Reached end-time. If you want to keep the plot windows specify the --persisten option",self.endTime)
                    break
            if not currSize>self.reader.bytesRead() or self.analyzer.isPastTime(switchTime):
                if len(self.nextFiles)>0:
                    print_("\n\nSwitching from logfile",self.filename,
                           "to",self.nextFiles[0],"\n\n")
                    self.filename=self.nextFiles[0]
                    self.nextFiles=self.nextFiles[1:]
                    fh,currSize=self.changeFile(self.filename)
                    switchTime=None if len(self.changeTimes)==0 else self.changeTimes[0]
                    self.changeTimes=self.changeTimes[1:]
                    self.reader.reset()
                    self.analyzer.resetFile()
                    if currSize==0:
                        continue
                else:
                    if not self.follow:
                        break
            try:
                status=self.reader.read(fh)
                if status:
                    line=self.reader.line
                    if (currSize-self.reader.bytesRead())<=self.tail:
                        if not self.isTailing:
                            self.isTailing=True
                            self.timeHandle()
                            self.tailingHandle()

                        if not self.silent:
                            print_(line)

                    self.lineHandle(line)
                else:
                    if self.reader.userSaidStop():
                        break
                    sleep(self.sleep)
            except KeyboardInterrupt:
                print_("Watcher: Keyboard interrupt")
                import threading
                threads=threading.enumerate()
                if len(threads)!=1:
                    print_("More than one thread alive:",threads,"possible deadlock")
                break

        self.stopHandle()

        fh.close()

    def startHandle(self):
        """to be called before the program is started"""
        pass

    def stopHandle(self):
        """called after the program has stopped"""
        pass

    def tailingHandle(self):
        """called when the first line is output"""
        pass

    def lineHandle(self,line):
        """called every time a new line is read"""
        pass

# Should work with Python3 and Python2
