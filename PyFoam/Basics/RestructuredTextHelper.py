#  ICE Revision: $Id$
"""Helps formatting output for restructured text"""

import os

from PyFoam.Error import error
from PyFoam.ThirdParty.six import iteritems

class RestructuredTextHelper(object):
    """Helper class that formats stuff for restructured text"""

    LevelPart           = 0
    LevelChapter        = 1
    LevelSection        = 2
    LevelSubSection     = 3
    LevelSubSubSection  = 4
    LevelParagraph      = 5

    def __init__(self,defaultHeading=LevelSection):
        self.defaultHeading=defaultHeading

    def buildHeading(self,*text,**keywords):
        """General method to build a heading
        :param text: list of items that build the heading text
        :param level: The level of the heading"""

        level=RestructuredTextHelper.LevelSection
        if "level" in keywords:
            level=keywords["level"]

        header=None
        for t in text:
            if header==None:
                header=""
            else:
                header+=" "
            header+=str(t)
        overline=False
        if level==RestructuredTextHelper.LevelPart:
            c="#"
            overline=True
        elif level==RestructuredTextHelper.LevelChapter:
            c="*"
            overline=True
        elif level==RestructuredTextHelper.LevelSection:
            c="="
        elif level==RestructuredTextHelper.LevelSubSection:
            c="-"
        elif level==RestructuredTextHelper.LevelSubSubSection:
            c="^"
        elif level==RestructuredTextHelper.LevelParagraph:
            c='"'
        else:
            error("Unknown level",level,"for headers")

        underline=c*len(header)

        result="\n"

        if overline:
            result+=underline+"\n"

        result+=header+"\n"
        result+=underline+"\n"

        return result

    def heading(self,*text):
        """Build a heading on the default level"""

        keys={"level":self.defaultHeading}

        return self.buildHeading(*text,**keys)

    def table(self,labeled=False):
        """Creates a new ReSTTable-object"""
        if labeled:
            return LabledReSTTable()
        else:
            return ReSTTable()

    def __markup(self,limiter,*txt):
        return limiter+" ".join(str(t) for t in txt)+limiter

    def emphasis(self,*txt):
        return self.__markup("*",*txt)

    def strong(self,*txt):
        return self.__markup("**",*txt)

    def literal(self,*txt):
        return self.__markup("``",*txt)

    def bulletList(self,data,bullet="-"):
        """Generate a bullet list from the data"""
        return "\n".join(bullet+" "+str(d) for d in data)+"\n"

    def enumerateList(self,data,first=1):
        """Generate an enumerated list from the data. First number can be chosen
        and determines the format"""
        if len(data)==0:
            return "\n"
        else:
            return str(first)+". "+str(data[0])+"\n"+"\n".join("#. "+str(d) for d in data[1:])+"\n"

    def definitionList(self,data):
        """Generate a definiton list from the data."""
        return "\n\n".join(str(k)+"\n  "+str(v) for k,v in iteritems(data))+"\n"

    def code(self,code,language="python"):
        """@param code: string to be typeset as a program code
        @param language: programming language to be used"""
        return "\n.. code:: "+language+"\n" + \
               "\n".join("  "+l for l in code.split("\n"))+"\n\n"

class ReSTTable(object):
    """Class that administrates a two-dimensional table and prints it as
    a restructured text-table when asked"""

    def __init__(self):
        self.data=[[]]
        self.lines=set()
        self.head=-1;

    def addLine(self,val=None,head=False):
        """Add a line after that row
        :param val: the row after which to add. If None a line will be added after the
        current last row"""
        if val==None:
            now=len(self.data)-1
        else:
            now=int(val)
        self.lines.add(now)
        if head:
            self.head=now

    def __str__(self):
        """Output the actual table"""
        widths=[1]*len(self.data[0])
        for r in self.data:
            for i,v in enumerate(r):
                try:
                    widths[i]=max(widths[i],len(v))
                except TypeError:
                    if i==0:
                        widths[i]=max(widths[i],2)
                    else:
                        widths[i]=max(widths[i],1)

        head=None
        for w in widths:
            if head==None:
                head=""
            else:
                head+=" "
            head+="="*w

        inter=head.replace("=","-")

        txt=head+"\n"

        for i,r in enumerate(self.data):
            line=""
            for j,v in enumerate(r):
                if v==None or v=="":
                    if j==0:
                        t=".."
                    else:
                        t=""
                else:
                    t=v
                if j>0:
                    line+=" "
                line+=t+" "*(widths[j]-len(t))
            txt+=line+"\n"
            if i==(len(self.data)-1):
                txt+=head+"\n"
            elif i in self.lines:
                if i==self.head:
                    txt+=head+"\n"
                else:
                    txt+=inter+"\n"

        return "\n"+txt

    def __setitem__(self,index,value):
        """Sets an item of the table
        :param index: a tuple with a row and a column. If it is a single integer then the
        row is assumed
        :param value: the value to set. If only the row was specified it is a list with the column
        values"""

        try:
            row,col=index
            self.setElement(row,col,value)
        except TypeError:
            row=index
            for col,v in enumerate(value):
                self.setElement(row,col,v)

    def setElement(self,row,col,value):
        """Sets a specific element
        :param row: the row
        :param col: column
        :param value: the used value"""

        if len(self.data)<=row:
            self.data+=[[None]*len(self.data[0])]*(row-len(self.data)+1)
        if len(self.data[row])<=col:
            for r in self.data:
                r+=[None]*(col-len(r)+1)

        self.data[row][col]=str(value)

class LabledReSTTable(ReSTTable):
    """A ReSTTable that has rownames in the first column and column-names in the first row"""
    def __init__(self):
        ReSTTable.__init__(self)
        self.data[0].append("")
        self.addLine(head=True)

    def addRow(self,rowName):
        newRow=[None]*len(self.data[0])
        newRow[0]=rowName
        self.data.append(newRow)

    def addItem(self,column,value,row=None):
        if row==None:
            rowIndex=-1
            if len(self.data)==1:
                self.data.append([])
        else:
            rowIndex=-1
            for i in range(1,len(self.data)):
                if len(self.data[i])>=1:
                    if self.data[i][0]==row:
                        rowIndex=i
                        break
            if rowIndex<0:
                rowIndex=len(self.data)
                newRow=[None]*len(self.data[0])
                newRow[0]=row
                self.data.append(newRow)

        colIndex=-1
        for i in range(1,len(self.data[0])):
            if column==self.data[0][i]:
                colIndex=i
        if colIndex<0:
            colIndex=len(self.data[0])
            self.data[0].append(column)
            for i in range(1,len(self.data)):
                self.data[i]+=[None]*(len(self.data[0])-len(self.data[i]))

        self.data[rowIndex][colIndex]=str(value)
