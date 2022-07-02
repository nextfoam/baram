# Support for blink(1)-devices

import requests

import sys
import time

from PyFoam import configuration as conf
from PyFoam.Error import PyFoamException

class Blink1(object):
    """Actual class to connect to a blink-device"""

    def __init__(self,
                 ticColor=None):
        """Constructs the object. Tests for blink-device only in the beginning.
        If none is found an exception is thrown"""
        self.__baseURL=conf().get("Blink1","baseurl")
        self.__timeout=conf().getfloat("Blink1","allowedtimeout")
        try:
            response=self.__sendCommand("id")
        except requests.ConnectionError:
            e=sys.exc_info()[1]
            raise PyFoamException("No blink(1) at",self.__baseURL,":",e)
        if len(response["blink1_serialnums"])<1:
            raise PyFoamException("Seems that no blink(1) is plugged in")
        self.reloadPatterns()
        self.__threads=[]
        self.__tictocColor=ticColor if ticColor else conf().get("Blink1","tictoccolor")
        self.__lastTicTime=-1
        self.__ticToc=True

    @property
    def patterns(self):
        return self.__patterns

    def ticToc(self,color=None):
        """Alternate color between upper and lower side of the blink. Transition
        time depends on the times between calls"""
        color=self.__tictocColor if color is None else color
        now=time.time()
        if self.__lastTicTime<0:
            self.fadeToRGB(color,time=1,ledn=1)
        else:
            if self.__ticToc:
                ledIn,ledOut=2,1
            else:
                ledIn,ledOut=1,2
            self.__ticToc=not self.__ticToc
            # print(color,now-self.__lastTicTime,ledIn,ledOut)
            self.fadeToRGB(color,time=now-self.__lastTicTime,ledn=ledIn)
            self.fadeToRGB("#000000",time=now-self.__lastTicTime,ledn=ledOut)
        self.__lastTicTime=now

    def reloadPatterns(self):
        self.__patterns={}

        for p in self.__sendCommand("patterns")["patterns"]:
            pl=p["pattern"].split(",")
            repeat=int(pl[0])
            lngth=sum(float(v) for v in pl[2::3])
            self.__patterns[p["name"]]=repeat*lngth
        #        print (self.__patterns)

    def __sendCommand(self,command,**params):
        """Sends a command"""
        try:
            r=requests.get(self.__baseURL+"/"+command,
                           params=params,
                           timeout=self.__timeout)
        except requests.exceptions.ReadTimeout:
            return None
        except requests.exceptions.ConnectionError:
            return None
        if r.status_code==requests.codes.ok:
            json=r.json()
            if "status" not in json:
                return None
            elif json["status"]!="unknown command":
                return json
            else:
                return None
        else:
            return None

    def fadeToRGB(self,colorString,time=1,ledn=0):
        self.__sendCommand("fadeToRGB",rgb=colorString,time=time,ledn=ledn)

    def play(self,patternName):
        """Plays a defined pattern"""
        if patternName not in self.patterns:
            self.reloadPatterns()
            if patternName not in self.patterns:
                raise PyFoamException("blink(1) pattern",patternName,
                                      "unknown. Available:",
                                      ", ".join(self.patterns))
        response=self.__sendCommand("pattern/play",pname=patternName)

    def playRepeated(self,patternName,interval):
        """Plays a pattern at regular intervals (starts a new thread and returns
        the handle)"""

        import threading

        e=threading.Event()
        e.set()

        interval+=self.__patterns[patternName]

        def playPattern():
            # print("Starting",patternName)
            while e.is_set():
                self.play(patternName)
                # print("Playing",patternName)
                time.sleep(interval)
            # print("Stopping",patternName)
            self.fadeToRGB("#000000")

        t=threading.Thread(target=playPattern)
        t.start()
        self.__threads.append((t,e))
        return t

    def nrRepeats(self):
        """Number of running threads"""
        return len(self.__threads)

    def stop(self):
        """Completely reset. Stop all threads and fade to black"""
        self.stopAllPlays()
        # self.__sendCommand("pattern/stop")
        self.__sendCommand("off")

    def stopAllPlays(self):
        """Stop all threads that repeatedly play patterns"""
        threads=[t for t,e in self.__threads]
        for t in threads:
            self.stopPlay(t)

    def stopPlay(self,thread):
        """Using a thread handle stop a thread"""
        this,event=None,None
        for t,e in self.__threads:
            if t==thread:
                this,event=t,e
                break
        if this:
            event.clear()
            self.__threads.remove((this,event))
