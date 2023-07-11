"""Implements a little curses wrapper that makes the output of
PyFoam-applications more flashy"""

try:
    import curses
    hasCurses=True
except ImportError:
    hasCurses=False

import re
from collections import deque
import sys
import PyFoam.ThirdParty.six as six
from os import path
from PyFoam import configuration as config

from threading import Thread

rexpr=[]

def addExpr(e):
    if isinstance(e,six.string_types):
        r=re.compile(e)
    else:
        r=e
    if r not in rexpr:
        rexpr.append(r)

for e in [r'^Time = ([^\s]+)$',
          r'PyFoam WARNING',
          r"^End$"]:
    addExpr(e)

class CWindow:
    REGULAR_COLOR = 2
    HEADER_COLOR  = 1
    REGEX_COLOR   = 3
    GROUP_COLOR   = 4

    def __init__(self,wind,app,
                 bufflen=100,
                 powerline=False,
                 handleKeyboard=True):
        self.app=app
        self.wind=wind
        self.powerline=powerline and ("UTF-8" in sys.stdout.encoding) and six.PY3

        validColors=["red","white","blue","black","green","cyan","magenta","yellow"]
        def colorCode(name):
            return eval("curses.COLOR_%s" % name.upper())

        fgHeader=colorCode(config().getchoice("Curses","headerTextColor",
                                              validColors))
        bgHeader=colorCode(config().getchoice("Curses","headerBackgroundColor",
                                              validColors))
        bgText=colorCode(config().getchoice("Curses","textBackgroundColor",
                                              validColors))
        fgText=colorCode(config().getchoice("Curses","textColor",
                                              validColors))
        fgMatch=colorCode(config().getchoice("Curses","textMatchColor",
                                              validColors))
        fgGroup=colorCode(config().getchoice("Curses","textGroupColor",
                                              validColors))

        curses.init_pair(self.HEADER_COLOR, fgHeader, bgHeader)
        curses.init_pair(self.REGULAR_COLOR, fgText, bgText)
        curses.init_pair(self.REGEX_COLOR, fgMatch, bgText)
        curses.init_pair(self.GROUP_COLOR, fgGroup, bgText)
        # self.wind.nodelay(True)
        self.lineBuffer=deque(maxlen=bufflen)
        self.footerText=[]
        self.headerText=[]
        self.oldTOutHeight=0
        self._update()
        self.oldStdout=sys.stdout
        self.encoding=sys.stdout.encoding
        self.errors=sys.stdout.errors
        self.oldStderr=sys.stderr
        sys.stdout=self
        sys.stderr=self
        self.skipNext=False
        self.lineCount=0
        self.stopOutput=False

        self.handleKeyboard=handleKeyboard
        if self.handleKeyboard:
            self.keyThread=Thread(target=self.keyHandler)
            self.keyThread.daemon=True
            self.keyThread.start()

        self.keyMessage=None

        self.__staticBuffer=False
        self.__staticOffset=0

    def incrOffset(self,incr):
        my,mx=self.tout.getmaxyx()
        buffLen=len(self.lineBuffer)
        self.__staticOffset=max(0,
                                min(
                                    buffLen-my,
                                    self.__staticOffset+incr))

    @property
    def staticOffset(self):
        my,mx=self.tout.getmaxyx()
        buffLen=len(self.lineBuffer)
        # Cut off in case there was a resize in the meantime
        self.__staticOffset=max(0,
                               min(
                                   buffLen-my,
                                   self.__staticOffset))
        return self.__staticOffset

    def isStatic(self):
        return self.__staticBuffer

    def keyHandler(self):
        while True:
            c=self.wind.getch()
            msg=None
            repaint=False
            try:
                if c>=0:
                    if c==curses.KEY_RESIZE:
                        repaint=True
                    else:
                        repaint,k=self.handleKey(c)
                        if k:
                            msg="Unhandled key {}".format(curses.keyname(k))
                else:
                    msg="No key"
            except:
                msg="Key Handler Problem"
            self.keyMessage=msg
            if repaint or msg:
                self.update(resize=True)

    def updateFooterText(self):
        self.footerText=["Lines: {}".format(self.lineCount)]
        return True

    def updateHeaderText(self):
        if len(self.headerText)==0:
            from PyFoam import FoamInformation as FI
            self.headerText=[(path.basename(sys.argv[0]),
                              self.app.getApplication(),
                              "{} v{}".format(FI.foamFork(),FI.foamVersionString()))]

            offsetMessage=None
            my,mx=self.tout.getmaxyx()
            buffLen=len(self.lineBuffer)

            if self.isStatic() and my<buffLen:
                bottom=buffLen-self.staticOffset
                offsetMessage="Show lines {}-{} of {}".format(1+bottom-my,bottom,buffLen)
            if self.keyMessage or self.stopOutput or offsetMessage:
                self.headerText.append((self.keyMessage,
                                        "Output stopped" if self.stopOutput else None,
                                        offsetMessage))

            return True

        return False

    def restore(self):
        if sys.stdout is self:
            sys.stdout=self.oldStdout
        if sys.stderr is self:
            sys.stderr=self.oldStderr

    def _update(self):
        self.maxy,self.maxx=self.wind.getmaxyx()
        self.wind.clear()
        headerLen=max(0,min(len(self.headerText),self.maxy-2))
        footerLen=max(0,min(len(self.footerText),self.maxy-headerLen-2))
        self.textLength=self.maxy-headerLen-footerLen
        if headerLen>0:
            self.header=self.wind.subwin(headerLen,self.maxx,0,0)
            self.header.bkgd(" ",curses.A_REVERSE|curses.color_pair(self.HEADER_COLOR))
            self.header.attrset(curses.A_REVERSE|curses.color_pair(self.HEADER_COLOR))
        else:
            self.header=None
        # self.header.addstr(sys.argv[1][-(self.maxx-3):])
        # self.header.refresh()
        if self.textLength>1:
            self.tout=self.wind.subwin(self.textLength,self.maxx,headerLen,0)
            self.tout.bkgd(" ",curses.color_pair(self.REGULAR_COLOR))
            self.tout.attrset(curses.color_pair(self.REGULAR_COLOR))
            self.tout.idlok(1)
            self.tout.scrollok(1)
        else:
            self.tout=None
        if footerLen:
            self.footer=self.wind.subwin(footerLen,self.maxx,self.maxy-footerLen,0)
            self.footer.bkgd(" ",curses.A_REVERSE|curses.color_pair(self.HEADER_COLOR))
            self.footer.attrset(curses.A_REVERSE|curses.color_pair(self.HEADER_COLOR))
        else:
            self.footer=None

    def update(self,resize=False,onlyHeader=False):
        self._update()
        if resize:
            self._checkHeaders(force=True)

        self._reprint()

    def _reprint(self):
        if self.tout is None:
            return
        self.tout.erase()
        my,mx=self.tout.getmaxyx()

        off=self.staticOffset

        for i in reversed(range(min(my,len(self.lineBuffer)))):
            self._writeLine(self.lineBuffer[-(i+1+off)])

        self.tout.refresh()

    def drawHeadFoot(self,subwin,textIn):
        text=[t for t in textIn if t is not None]

        if subwin is None:
            return
        subwin.erase()
        maxy,maxx=subwin.getmaxyx()

        if self.powerline:
            rightSep="\ue0b0"
            leftSep="\ue0b2"
            filler=" "
        else:
            rightSep=">"
            leftSep="<"
            filler="-"

        def seperator(length):
            if length<=1:
                return (0,0)," "*length
            elif length==2:
                return (0,2),rightSep+leftSep
            elif length==3:
                return (0,3),rightSep+filler+leftSep
            else:
                result=" "+rightSep
                result+=filler*(length-4)
                result+=leftSep+" "
                return (1,length-2),result

        for i in range(len(text)):
            seperatorLoc=[]
            if i>maxy:
                break
            t=text[i]
            if isinstance(t,six.string_types):
                t=[t]
            t=[tt for tt in t if tt is not None]
            totalLen=sum([len(s) for s in t])+(len(t))
            if totalLen>=self.maxx:
                goodLen=(self.maxx-(len(t)-1))//len(t)
                if goodLen<3:
                    break  # doesn't make sense to print anything
                raw=list(enumerate(t))
                ok=[r for r in raw if len(r[1])<goodLen]
                usedLen=sum([len(r[1]) for r in ok])+(len(t)-1)
                availLen=self.maxx-usedLen
                bad=[r for r in raw if r not in ok]
                fixed=[]
                # all those that need less than their share are not clipped
                for j in range(len(bad)):
                    if len(bad[j][1])<=(availLen//len(bad)):
                        fixed.append(bad[j])
                bad=[b for b in bad if b not in fixed]
                ok=ok+fixed
                usedLen=sum([len(r[1]) for r in ok])+(len(t)-1)
                excessLength=max(0,sum([len(r[1]) for r in bad])-(self.maxx-usedLen))
                if len(bad)>0:
                    clipLen=excessLength//len(bad)+1
                    for k,v in bad:
                        ok.append((k,v[:(len(v)-clipLen)]))

                tNew=[s[1] for s in sorted(ok,key=lambda x:x[0])]
            else:
                tNew=t
            totalLen=sum([len(s) for s in tNew])
            if len(tNew)>0:
                out=tNew[0]
            else:
                out=""
            for j in range(1,len(tNew)-1):
                (off,length),string=seperator((self.maxx-totalLen)//(len(tNew)-1))
                seperatorLoc.append((len(out)+off,length))
                out+=string
                out+=tNew[j]
            if len(tNew)>1:
                (off,length),string=seperator(self.maxx-len(out)-len(tNew[-1])-1)
                seperatorLoc.append((len(out)+off,length))
                out+=string
                out+=tNew[-1]
            if len(tNew)==1:
                (off,length),string=seperator(self.maxx-len(out)+1)
                if length>1:
                    seperatorLoc.append((len(out)+off,length))
                out+=string[:-2]
            if len(out)>=self.maxx:
                errText="Error calculating output %d / %d" % (len(out),self.maxx)
                if len(errText)<self.maxx:
                    subwin.addstr(i,0,errText)
            else:
                try:
                    subwin.addstr(i,0,out)
                    # invert everything that is not data
                    for start,length in seperatorLoc:
                        for j in range(start,start+length):
                            if j<self.maxx:
                                subwin.chgat(i,j,1,
                                             curses.A_NORMAL|curses.color_pair(self.HEADER_COLOR))
                except:
                    pass

        subwin.refresh()

    def _ensureSize(self):
        maxy,maxx=self.wind.getmaxyx()
        if maxx!=self.maxx or maxy!=self.maxy:
            self._update()

    def _checkHeaders(self,force=False):
        self._ensureSize()

        oldHeaderLenght=len(self.headerText)
        oldFooterLenght=len(self.footerText)

        newHeaderText=self.updateHeaderText()
        newFooterText=self.updateFooterText()

        if (oldHeaderLenght!=len(self.headerText) or oldFooterLenght!=len(self.footerText)):
            self._update()
            self._reprint()

        if newHeaderText or force:
            self.drawHeadFoot(self.header,self.headerText)
        if newFooterText or force:
            self.drawHeadFoot(self.footer,self.footerText)

    def handleKey(self,key):
        if key==ord(" ") and not self.isStatic():
            self.stopOutput=not self.stopOutput
            return True,None
#            if not self.stopOutput:
#                self.update()
        elif self.isStatic() and key in [curses.KEY_UP,curses.KEY_DOWN,
                                         curses.KEY_HOME,curses.KEY_END,
                                         curses.KEY_NPAGE,curses.KEY_PPAGE]:
            if key==curses.KEY_UP:
                self.incrOffset(1)
            elif key==curses.KEY_DOWN:
                self.incrOffset(-1)
            elif key==curses.KEY_PPAGE:
                self.incrOffset(self.tout.getmaxyx()[0])
            elif key==curses.KEY_NPAGE:
                self.incrOffset(-self.tout.getmaxyx()[0])
            elif key==curses.KEY_HOME:
                self.incrOffset(len(self.lineBuffer))
            elif key==curses.KEY_END:
                self.incrOffset(-len(self.lineBuffer))
            return True,None
        else:
            return False,key

    def writeLine(self,l):
        # c=self.wind.getch()
        # if c>=0:
        #     if c==curses.KEY_RESIZE:
        #         self.update(resize=True)
        #     else:
        #         self.handleKey(c)

        self._ensureSize()

        parts=l.split("\n")

        if len(self.lineBuffer)==0 or (len(self.lineBuffer[-1]) and self.lineBuffer[-1][-1]=="\n"):
            self.lineBuffer.append(parts[0])
        else:
            self.lineBuffer[-1]+=parts[0]
        if len(parts)>1:
            self.lineBuffer[-1]+="\n"
            # self._writeLine(self.lineBuffer[-1])
            self.lineCount+=1
            for p in parts[1:-1]:
                self.lineBuffer.append(p+"\n")
                # self._writeLine(self.lineBuffer[-1])
                self.lineCount+=1
            self.lineBuffer.append(parts[-1])

        self._checkHeaders()

        if not self.stopOutput:
            self._writeLine(l)

    def flush():
        self.tout.refresh()

    def write(self,txt):
        self.writeLine(txt)
        if self.tout:
            self.tout.refresh()

    def _writeLine(self,l):
        if self.tout is None:
            return

        y,x=self.tout.getyx()
        found=False
        for e in rexpr:
            m=e.search(l)
            if m:
                found=True
                self.tout.addstr(l[:m.start()])
                pre=m.start()
                for x1,x2 in m.regs[1:]:
                    self.tout.addstr(l[pre:x1],curses.color_pair(self.REGEX_COLOR))
                    self.tout.addstr(l[x1:x2],curses.color_pair(self.GROUP_COLOR))
                    pre=x2
                self.tout.addstr(l[pre:m.end()],curses.color_pair(self.REGEX_COLOR))
                self.tout.addstr(l[m.end():])
                break
        if not found:
            self.tout.addstr(l)

    def buffer(self):
        return "".join(self.lineBuffer)

class CWindowAnalyzed(CWindow):
    def __init__(self,wind,app,bufflen=100,powerline=False):
        CWindow.__init__(self,wind,app,bufflen=bufflen,powerline=powerline)
        self.__contentGenerators=[]
        self.currTime=0
        self.nSteps=0
        self.analyzer=None
        self.progressString=None
        self.firstTime=True

        self.runner=None

        self.restartCount=0
        self._reset()

    def isStatic(self):
        return len(self.__contentGenerators)>0 or CWindow.isStatic(self)

    def addGenerator(self,gen):
        self.__contentGenerators.append(gen)

    def setAnalyzer(self,ana):
        self.analyzer=ana
        self._reset()

    def setRunner(self,runner):
        self.runner=runner
        self._reset()

    def _reset(self):
        self.currTime=0
        if self.nSteps>0:
            self.restartCount+=1
        self.nSteps=0
        self.firstTime=True

        self.startTime=None
        self.endTime=None
        self.clockTime=None

        self.caseName=None
        self.execName=None
        self.headerChanged=False

    def timeChanged(self):
        self.nSteps+=1
        self.currTime=self.analyzer.time
        self.progressString=self.analyzer.progressOut.lastProgress()

        if self.analyzer.hasAnalyzer("Execution"):
            self.clockTime=self.analyzer.getAnalyzer("Execution").clockTotal()

        if self.startTime is None:
            if self.runner:
                self.startTime=self.runner.createTime
            else:
                self.startTime=self.analyzer.getAnalyzer("Time").createTime()

        if self.endTime is None:
            sol=None
            if self.runner:
                sol=self.runner.getSolutionDirectory()
            else:
                if self.analyzer.hasAnalyzer("ExecName"):
                    caseName=self.analyzer.getAnalyzer("ExecName").caseName
                    if caseName and path.isdir(caseName):
                        from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
                        sol=SolutionDirectory(caseName,paraviewLink=False)
            if sol:
                from PyFoam.RunDictionary.ParameterFile import ParameterFile
                control=ParameterFile(sol.controlDict())
                try:
                    self.endTime=float(control.readParameter("endTime"))
                except ValueError:
                    self.endTime=-1

        if self.caseName is None or self.execName is None:
            if self.analyzer.hasAnalyzer("ExecName"):
                self.caseName=self.analyzer.getAnalyzer("ExecName").caseName
                self.execName=self.analyzer.getAnalyzer("ExecName").execName
                self.headerChanged=True

        from PyFoam.LogAnalysis.LogLineAnalyzer import LogLineAnalyzer
        for e in LogLineAnalyzer.allRegexp:
            addExpr(e)

        if self.firstTime:
            self.update(resize=True)
            self.firstTime=False
        else:
            self._checkHeaders(force=True)

        if len(self.__contentGenerators):
            content="".join([g(col=self.maxx-1) for g in self.__contentGenerators]).strip()
            self.lineBuffer=deque([c+"\n" for c in content.split("\n")])
            self.lineCount=len(self.lineBuffer)
            self.update(resize=True)

    def updateHeaderText(self):
        if self.headerChanged:
            self.headerText=[]
        update=CWindow.updateHeaderText(self)

        if self.caseName is not None and self.execName is not None and self.headerChanged:
            self.headerText.append([self.execName,
                                    ("Restarts: %d"%self.restartCount) if self.restartCount>0 else None,
                                    "Case: "+path.basename(self.caseName)])
            update=True

        return update

    def updateFooterText(self):
        from PyFoam.LogAnalysis.LogLineAnalyzer import LogLineAnalyzer

        self.footerText=[["Lines: {}".format(self.lineCount)+"/{}".format(self.analyzer.analyzedLines) if self.analyzer else "",
                          "Time {} to {}".format(self.startTime,self.endTime) if self.startTime is not None else None,
                          'Steps: {}'.format(self.nSteps)]]

        if self.progressString:
            self.footerText.append([self.progressString])

        if self.startTime is not None:
            elapsed=max(1e-7,self.currTime-self.startTime)
            endTime=self.endTime
            if endTime is None:
                endTime=self.startTime+2*elapsed
            whole=endTime-self.startTime
            steps=int(whole/(elapsed/max(1,self.nSteps)))

#            self.footerText.append(["Started at %s" % self.startTime,
#                                    "Ending: %f" % self.endTime,
#                                    "Now: %f" % self.currTime,
#                                    "Clock: %f" % self.clockTime ])

            from PyFoam.ThirdParty.tqdm import tqdm
            targetLen=self.maxx-1
            progString=tqdm.format_meter(self.nSteps,
                                         total=max(steps,self.nSteps),
                                         elapsed=self.clockTime,
                                         ncols=targetLen,
                                         ascii=not self.powerline,
                                         unit="it")
            if len(progString)>targetLen:
                progString=progString[:targetLen]
            self.footerText.append([progString])

        return True

def cursesWrap(app,bufflen=1000,endSleepTime=0,powerline=False):

    def main(wind):
        w=app.CWindowType(wind,app,bufflen=bufflen,powerline=powerline)
        app.cursesWindow=w

        cnt=0

        try:
            result=app.run()
            w.restore()
            import time
            time.sleep(endSleepTime)
            return result,w.buffer()
        except:
            w.restore()
            import traceback
            # e=sys.exc_info()[0]
            return None,w.buffer()+traceback.format_exc()

    result,output=curses.wrapper(main)
    print(output)
    return result
