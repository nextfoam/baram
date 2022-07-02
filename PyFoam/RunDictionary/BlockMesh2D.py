"""Manipulate a 2 Dimensional C{blockMeshDict}"""

import re,os
import copy
import math
from PyFoam.Basics.LineReader import LineReader
from PyFoam.RunDictionary.FileBasis import FileBasisBackup
from PyFoam.RunDictionary.BlockMesh import BlockMesh
from PyFoam.RunDictionary.ParsedBlockMeshDict import ParsedBlockMeshDict
from PyFoam.Basics.DataStructures import *
from PyFoam.Basics.BlockMeshComponents import *
from math import ceil
from PyFoam.Error import error

class BlockMesh2D(FileBasisBackup):
    def __init__(self,
                 name,
                 extensionType,
                 frontbacktype,
                 frontvalue=0,
                 backvalue=0,
                 ncells=1,
                 backup=False):
        """:param name: The name of the parameter file
           :param backup: create a backup-copy of the file
        """
        FileBasisBackup.__init__(self,name,backup=backup)
        self.parsedBlockMesh=ParsedBlockMeshDict(name)
        self.vertexNum=len(self.parsedBlockMesh["vertices"])
        self.extensionType=extensionType
        self.frontvalue=frontvalue
        self.backvalue=backvalue
        self.ncells=ncells
        self.minBound=self.getBounds()
        self.frontBackType=frontbacktype

    def convert2DBlockMesh(self):
        newMesh=self._get2DMesh()
        newMesh=self.convertVertices(newMesh)
        newMesh=self.convertBlocks(newMesh)
        newMesh=self.convertEdges(newMesh)
        newMesh=self.convertBoundaries(newMesh)
        return self.__endProcess(newMesh,True)

    def _get2DMesh(self):
        mesh=""
        l=self.__startProcess()
        while l.read(self.fh):
            mesh+=l.line+'\n'
        return mesh

    def _getVertexes(self):
        try:
            from collections import OrderedDict
            result=OrderedDict()
        except ImportError:
            error("This python-version doesn't have OrderedDict in library collections. Can't go on''")

        startPattern=re.compile("^\s*vertices")
        endPattern=re.compile("^\s*\);")
        vertexPattern=re.compile("^\s*\(\s*(\S+)\s+(\S+)\s+(\S+)\s*\).*$")

        inVertex=False
        l=self.__startProcess()

        cnt=0
        while l.read(self.fh):
            if not inVertex:
                if startPattern.match(l.line):
                    inVertex=True
            elif endPattern.match(l.line):
                inVertex=False
            else:
                m=vertexPattern.match(l.line)
                if m!=None:
                    result[m.groups()]=(cnt,l.line)
                    cnt+=1

        return result

    def _get3DVertexes(self):
        verticeslist=self._get2DVertexes()

        vertices=copy.deepcopy(verticeslist)
        newvertices=list()
        for vertice in vertices:
            newvertices.append(BlockMeshVertex(self.minBound,vertice).extend(self.extensionType,self.frontvalue))
        for vertice in vertices:
            newvertices.append(BlockMeshVertex(self.minBound,vertice).extend(self.extensionType,self.backvalue))
        return newvertices

    def _get2DVertexes(self):
        return self.parsedBlockMesh["vertices"]

    def _get2DBlocks(self) :
        blocksRawList=self.parsedBlockMesh["blocks"]
        blocksList=list()
        for index, value in enumerate(blocksRawList):
            if value=='hex':
                blocksList.append(blocksRawList[index+1])
        return blocksList

    def _get2DEdges(self):
        edgesRawList=self.parsedBlockMesh["edges"]
        edgesList=list()
        for index,value in enumerate(edgesRawList):
            if value=='spline':
                newEdge=BlockMeshEdge(edgesRawList[index+1],edgesRawList[index+2],None,edgesRawList[index+3])
                edgesList.append(newEdge)
            elif value=='arc':
                newEdge=BlockMeshEdge(edgesRawList[index+1],edgesRawList[index+2],BlockMeshVertex(self.minBound,edgesRawList[index+3]),None)
                edgesList.append(newEdge)
        return edgesList

    def _get3DEdges(self):
        edgesList=self._get2DEdges()
        newEdgesList=list()
        for edge in edgesList:
            if edge.edgeType=='spline':
                pointsList=list()
                for edgepoint in edge.points:
                    pointsList.append(BlockMeshVertex(self.minBound,edgepoint).extend(self.extensionType,self.frontvalue))
                newEdgesList.append(BlockMeshEdge(edge.start,edge.end,edge.center,pointsList))
                pointsList=list()
                for edgepoint in edge.points:
                    pointsList.append(BlockMeshVertex(eself.minBound,dgepoint).extend(self.extensionType,self.backvalue))
                newEdgesList.append(BlockMeshEdge(edge.start+self.vertexNum,edge.end+self.vertexNum,edge.center,pointsList))
            if edge.edgeType=='arc':
                newEdgesList.append(BlockMeshEdge(edge.start,edge.end,edge.center.extend(self.extensionType,self.frontvalue),None))
                newEdgesList.append(BlockMeshEdge(edge.start+self.vertexNum,edge.end+self.vertexNum,edge.center.extend(self.extensionType,self.backvalue),None))
        return newEdgesList

    def _get2DBoundaries(self):
        boundariesRawList=self.parsedBlockMesh["boundary"]
        boundariesList=list()
        name=""
        faces=list()
        boundaryType=""
        for index, item in enumerate(boundariesRawList):
            if type(item) is str:
                name=item
                for key, value in  boundariesRawList[index+1].items():
                    if type(value) is list:
                        faces=value
                    elif type(value) is str:
                        boundaryType=value
                boundariesList.append(BlockMeshBoundary(name,boundaryType,faces))

        return boundariesList

    def _get3DBoundaries(self):
        boundariesList=self._get2DBoundaries()
        newBoundariesList=list()
        for boundary  in boundariesList:
            boundaryFaces=list()
            for face in boundary.faces:
                newFace=list()
                for point in reversed(face):
                    newFace.append(point+self.vertexNum)
                face=face+newFace
                boundaryFaces.append(face)

            newBoundariesList.append(BlockMeshBoundary(boundary.name,boundary.boundaryType,boundaryFaces))
        newBoundariesList.append(self._getFrontAndBackBoundaries())
        return newBoundariesList
    def convertBoundaries(self,mesh):
        boundariesList=self._get3DBoundaries()
        inBoundary=False
        inFace=False
        startPattern=re.compile("^\s*boundary")
        facestartPattern=re.compile("^\s*faces")
        endPattern=re.compile("^\s*\);")
        newMesh=""
        for line in  mesh.splitlines():
            toPrint=line
            if not inBoundary:
                if startPattern.match(line):
                    toPrint+="\n("
                    inBoundary=True
            else:
                toPrint=""
                if not inFace:
                    if facestartPattern.match(line):
                        inFace=True
                    if endPattern.match(line):
                        for boundary in reversed(boundariesList):
                           toPrint=str(boundary)+'\n' +toPrint
                        inBoundary=False
                        toPrint+='\n);'
                else:
                    if endPattern.match(line):
                            inFace=False
                    else:
                        newMesh=newMesh.rstrip()
            newMesh+=toPrint+"\n"
        return newMesh

    def convertEdges(self,mesh):
        newEdgesList=self._get3DEdges()
        inBlock=False
        startPattern=re.compile("^\s*edges")
        endPattern=re.compile("^\s*\);")
        edgePattern=re.compile("(^\s*edges)\s(\s*)(\);)",re.MULTILINE)
        newMesh=""
        for line in  mesh.splitlines():
            toPrint=line
            if not inBlock:
                if startPattern.match(line):
                    toPrint+="\n("
                    inBlock=True
            else:
                if endPattern.match(line):
                    toPrint='\n'+toPrint
                    for edge in reversed(newEdgesList):
                       toPrint='\n'+str(edge)+toPrint
                    toPrint="\n"+toPrint
                    inBlock=False
                else:
                    toPrint=""
                    newMesh=newMesh.rstrip()
            newMesh+=toPrint+"\n"
        return newMesh

    def convertBlocks(self,mesh):
        blocksList=self._get2DBlocks()
        tempBloksList=copy.deepcopy(blocksList)
        newBlocksList=list()
        for block in tempBloksList:
            tmpBlock=list()
            for point in block:
                tmpBlock.append(point+self.vertexNum)
            block=block+tmpBlock
            newBlocksList.append(block)
        startPattern=re.compile("^\s*blocks")
        endPattern=re.compile("^\s*\);")
        hexPattern=re.compile("^\s*(hex)\s*(\(.+\))\s+(\(\s*\d+\s+\d+\s*)(\)\s+simpleGrading\s*) (\(\s*\d+\s+\d+\s*)(\).*$)")
        hexblockPattern=re.compile("^\s*hex\s*(\(.+\))\s+\(\s*\d+\s+\d+\s+\d+\s*\).*$")
        inBlock=False
        l=self.__startProcess()
        newMesh=""
        count=0
        for line in  mesh.splitlines():
            toPrint=line
            if not inBlock:
                if startPattern.match(line):
                    inBlock=True
            else:
                if endPattern.match(line):
                    inBlock=False
                else:
                    m=hexPattern.match(line)
                    if m!=None:
                        g=m.groups()
                        toPrint="\t %s %s %s%s %s%s" % (g[0],"("+' '.join(map(str,newBlocksList[count]))+")",g[2]+" "+str(self.ncells),g[3],g[4]+" 1",g[5])
                        count=count+1
            newMesh+=toPrint+"\n"
        return self.__endProcess(newMesh)

    def convertVertices(self, mesh):
        startPattern=re.compile("^\s*vertices")
        endPattern=re.compile("^\s*\);")
        vertexPattern=re.compile("^(\s*\(\s*\S+\s+\S+\s*\)).*$")
        newvertices=self._get3DVertexes()
        inVertex=False
        newMesh=""
        stringVert=""
        count=0
        for line in  mesh.splitlines():
            toPrint=line
            if not inVertex:
                if startPattern.match(line):
                    inVertex=True
            elif endPattern.match(line):
                for vert in newvertices:
                    stringVert+="\t"+str(vert)+"\n"
                toPrint=stringVert+toPrint
                inVertex=False

            else:
                m=vertexPattern.match(line)
                if m!=None:
                    toPrint=""
                    newMesh=newMesh.rstrip()
            newMesh+=toPrint+"\n"

        return newMesh
    def _getFrontAndBackBoundaries(self):
        blocksList=self._get2DBlocks()
        derivedBlockList=deepcopy(blocksList)
        boundary=BlockMeshBoundary("frontAndBack",self.frontBackType,list())
        for block in blocksList:
            boundary.faces.append(block)
        for block in derivedBlockList:
            for index, vertex in enumerate(block):
                block[index]=vertex+self.vertexNum
            boundary.faces.append(block)
        return boundary

    def getBounds(self):
        v=self.parsedBlockMesh["vertices"]
        mi=[ 1e10, 1e10]
        ma=[-1e10,-1e10]
        for p in v:
            for i in range(2):
                mi[i]=min(p[i],mi[i])
                ma[i]=max(p[i],ma[i])
        return mi

    def __startProcess(self):
        l=LineReader(False)
        self.openFile()
        return l


    def __endProcess(self,newMesh,getContent=True):
        if getContent:
            self.content=newMesh
            return newMesh
        else:
            (fh,fn)=self.makeTemp()

            fh.write(newMesh)
            self.closeFile()
            fh.close()
            os.rename(fn,self.name)
