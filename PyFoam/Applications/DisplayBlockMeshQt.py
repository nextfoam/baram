"""
New implementation of DisplayBlockMesh using PyQT4
"""

from PyFoam.RunDictionary.ParsedBlockMeshDict import ParsedBlockMeshDict
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Applications.PyFoamApplicationQt4 import PyFoamApplicationQt4
from PyFoam.Error import error,warning
from PyFoam.RunDictionary.SolutionDirectory import NoTouchSolutionDirectory
from PyFoam.Execution.BasicRunner import BasicRunner
from PyFoam.Basics.TemplateFile import TemplateFile

from .CommonTemplateFormat import CommonTemplateFormat

from os import path
from optparse import OptionGroup

from PyFoam.ThirdParty.six import print_,PY3

import sys

def doImports():
    if not PY3:
        error("This utility does not support Python 2.x")
    try:
        global QtGui,QtCore
        from PyQt4 import QtGui,QtCore
        global vtk

        global usedVTK

        try:
            import vtk
            usedVTK="Using system-VTK"
        except ImportError:
            usedVTK="Trying VTK implementation from Paraview"
            from paraview import vtk

        global vtkVersion
        vtkVersion=vtk.VTK_MAJOR_VERSION
        print_("VTK version",vtkVersion)
        if vtkVersion==7:
            # currently the only supported VTK
            pass
        elif vtkVersion<5:
            error("Need at least VTK 5")
        else:
            warning("VTK version",vtkVersion,"currently unsupported (tested with VTK7)")

        global QVTKRenderWindowInteractor
        from vtk.qt4 import QVTKRenderWindowInteractor
    except ImportError:
        e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
        error("Error while importing modules:",e)

doImports()

class ReportToThreadRunner(BasicRunner):
    def __init__(self,
                 argv,
                 thread):
        BasicRunner.__init__(self,
                             argv=argv,
                             noLog=True,
                             silent=True)
        self.thread=thread

    def lineHandle(self,line):
        self.thread.append(line)

class UtilityThread(QtCore.QThread):
    def __init__(self,
                 argv,
                 parent):
        super(UtilityThread,self).__init__(parent)
        self.argv=argv
        self.status=""
    def run(self):
        try:
            runner=ReportToThreadRunner(argv=self.argv,
                                        thread=self)
            runner.start()
            if not runner.runOK():
                self.status=" - Problem"

        except IOError:
            self.status=" - OS Problem"

    def append(self,line):
        self.emit(QtCore.SIGNAL("newLine(QString)"),line)

class DisplayBlockMeshDialog(QtGui.QMainWindow):
    def __init__(self,
                 fName,
                 valuesFile=None,
                 opts=None):
        super(DisplayBlockMeshDialog,self).__init__(None)
        self.fName=fName
        self.vName=valuesFile

        # dirty. Gives us access to the command line opts
        self.opts=opts

        self.numberScale=2
        self.pointScale=1
        self.axisLabelScale=1
        self.axisTubeScale=0.5

        titleString="%s[*] - DisplayBlockMesh" % fName

        if self.vName:
            titleString+="(Values: %s)" % path.basename(self.vName)

        self.setWindowTitle(titleString)

        self.caseDir=None
        try:
            components=path.abspath(fName).split(path.sep)
            if components[-2]=="polyMesh":
                # old scheme with blockMeshDict in constant/polyMesh
                components=components[:-3]
            else:
                # new scheme with blockMeshDict in system
                components=components[:-2]

            caseDir=path.sep+path.join(*components)
            isOK=NoTouchSolutionDirectory(caseDir)
            if isOK:
                self.caseDir=caseDir
                self.setWindowTitle("Case %s[*] - DisplayBlockMesh" % caseDir.split(path.sep)[-1])
        except:
            pass

        central = QtGui.QWidget()
        self.setCentralWidget(central)

        layout = QtGui.QVBoxLayout()
        central.setLayout(layout)
        self.renInteractor=QVTKRenderWindowInteractor.QVTKRenderWindowInteractor(central)
        #        self.renInteractor.Initialize() # this creates a segfault for old PyQt
        #        self.renInteractor.Start()  # segfault

        layout.addWidget(self.renInteractor)

        mainDock=QtGui.QDockWidget("Main controls",
                                   self)
        mainDock.setObjectName("MainControlsDock")
        mainDock.setFeatures(QtGui.QDockWidget.DockWidgetFloatable | QtGui.QDockWidget.DockWidgetMovable)
        mainDock.setAllowedAreas(QtCore.Qt.TopDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
        mainDockWidget=QtGui.QWidget()
        mainDock.setWidget(mainDockWidget)

        subLayout=QtGui.QGridLayout()
        mainDockWidget.setLayout(subLayout)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, mainDock)

        self.renInteractor.show()
        self.renWin = self.renInteractor.GetRenderWindow()
        self.ren = vtk.vtkRenderer()
        self.renWin.AddRenderer(self.ren)
        self.renWin.SetSize(600, 600)
        self.ren.SetBackground(0.7, 0.7, 0.7)
        self.ren.ResetCamera()
        self.cam = self.ren.GetActiveCamera()
        self.axes = vtk.vtkCubeAxesActor2D()
        self.axes.SetCamera(self.ren.GetActiveCamera())

        self.undefinedActor=vtk.vtkTextActor()
        self.undefinedActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
        self.undefinedActor.GetPositionCoordinate().SetValue(0.05,0.2)
        self.undefinedActor.GetTextProperty().SetColor(1.,0.,0.)
        self.undefinedActor.SetInput("")

        self.rereadAction=QtGui.QAction("&Reread",
                                        self)
        self.rereadAction.setShortcut("Ctrl+R")
        self.rereadAction.setToolTip("Reread the blockMesh-file")
        self.connect(self.rereadAction,
                     QtCore.SIGNAL("triggered()"),
                     self.reread)

        self.blockMeshAction=QtGui.QAction("&BlockMesh",
                                        self)
        self.blockMeshAction.setShortcut("Ctrl+B")
        self.blockMeshAction.setToolTip("Execute blockMesh-Utility")
        self.connect(self.blockMeshAction,
                     QtCore.SIGNAL("triggered()"),
                     self.blockMesh)

        self.checkMeshAction=QtGui.QAction("Chec&kMesh",
                                        self)
        self.checkMeshAction.setShortcut("Ctrl+K")
        self.checkMeshAction.setToolTip("Execute checkMesh-Utility")
        self.connect(self.checkMeshAction,
                     QtCore.SIGNAL("triggered()"),
                     self.checkMesh)
        if self.caseDir==None:
            self.blockMeshAction.setEnabled(False)
            self.checkMeshAction.setEnabled(False)

        self.quitAction=QtGui.QAction("&Quit",
                                      self)

        self.quitAction.setShortcut("Ctrl+Q")
        self.quitAction.setToolTip("Quit this program")
        self.connect(self.quitAction,
                     QtCore.SIGNAL("triggered()"),
                     self.close)

        self.saveAction=QtGui.QAction("&Save",
                                      self)

        self.saveAction.setShortcut(QtGui.QKeySequence.Save)
        self.saveAction.setToolTip("Save the blockmesh from the editor")
        self.connect(self.saveAction,
                     QtCore.SIGNAL("triggered()"),
                     self.saveBlockMesh)
        self.saveAction.setEnabled(False)

        self.fileMenu=self.menuBar().addMenu("&Blockmesh file")
        self.fileMenu.addAction(self.rereadAction)
        self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAction)

        editTitle="Edit blockMesh"
        if self.vName:
            editTitle+=" - template"

        self.editorDock=QtGui.QDockWidget(editTitle,
                                          self)
        self.editorDock.setObjectName("EditorDock")
        self.editorDock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)

        try:
            self.editor=QtGui.QPlainTextEdit()
            self.editor.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
            self.editor.textChanged.connect(self.blockMeshWasModified)
            self.alwaysSave=False
        except AttributeError:
            warning("Old PyQT4-version. Editing might not work as expected")
            self.editor=QtGui.QTextEdit()
            self.alwaysSave=True
            self.saveAction.setEnabled(True)

        self.editor.setFont(QtGui.QFont("Courier"))

        self.editorDock.setWidget(self.editor)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea,self.editorDock)
        self.editorDock.hide()

        if self.vName:
            self.vEditorDock=QtGui.QDockWidget("Values file",
                                               self)
            self.vEditorDock.setObjectName("VEditorDock")
            self.vEditorDock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)

            try:
                self.vEditor=QtGui.QPlainTextEdit()
                self.vEditor.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
                self.vEditor.textChanged.connect(self.blockMeshWasModified)
            except AttributeError:
                warning("Old PyQT4-version. Editing might not work as expected")
                self.vEditor=QtGui.QTextEdit()

            self.vEditor.setFont(QtGui.QFont("Courier"))

            self.vEditorDock.setWidget(self.vEditor)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea,self.vEditorDock)
            self.vEditorDock.hide()

        self.utilityDock=QtGui.QDockWidget("Utility output",
                                          self)
        self.utilityOutput=QtGui.QTextEdit()
        self.utilityOutput.setFont(QtGui.QFont("Courier"))
        self.utilityOutput.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.utilityOutput.setReadOnly(True)
        self.utilityDock.setWidget(self.utilityOutput)
        self.utilityDock.setObjectName("UtilityDock")
        self.utilityDock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea,self.utilityDock)
        self.utilityDock.hide()

        self.worker=None

        self.texteditorAction=self.editorDock.toggleViewAction()
        self.texteditorAction.setShortcut("Ctrl+E")

        if self.vName:
            self.textveditorAction=self.vEditorDock.toggleViewAction()
            self.textveditorAction.setShortcut("Ctrl+F")

        self.utilityAction=self.utilityDock.toggleViewAction()
        self.utilityAction.setShortcut("Ctrl+U")

        self.displayDock=QtGui.QDockWidget("Display Properties",
                                           self)
        self.displayDock.setObjectName("DisplayPropertiesDock")
        self.displayDock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)

        displayStuff=QtGui.QWidget()
        displayLayout=QtGui.QGridLayout()
        displayStuff.setLayout(displayLayout)
        displayLayout.addWidget(QtGui.QLabel("Number scale"),0,0)
        nrScale=QtGui.QDoubleSpinBox()
        nrScale.setValue(self.numberScale)
        nrScale.setMinimum(1e-2)
        nrScale.setSingleStep(0.1)
        self.connect(nrScale,QtCore.SIGNAL("valueChanged(double)"),self.numberScaleChanged)
        displayLayout.addWidget(nrScale,0,1)
        displayLayout.addWidget(QtGui.QLabel("Point scale"),1,0)
        ptScale=QtGui.QDoubleSpinBox()
        ptScale.setValue(self.pointScale)
        ptScale.setMinimum(1e-2)
        ptScale.setSingleStep(0.1)
        self.connect(ptScale,QtCore.SIGNAL("valueChanged(double)"),self.pointScaleChanged)
        displayLayout.addWidget(ptScale,1,1)
        displayLayout.addWidget(QtGui.QLabel("Axis label scale"),2,0)
        axisLScale=QtGui.QDoubleSpinBox()
        axisLScale.setValue(self.axisLabelScale)
        axisLScale.setMinimum(1e-2)
        axisLScale.setSingleStep(0.1)
        self.connect(axisLScale,QtCore.SIGNAL("valueChanged(double)"),self.axisLabelScaleChanged)
        displayLayout.addWidget(axisLScale,2,1)
        displayLayout.addWidget(QtGui.QLabel("Axis tube scale"),3,0)
        axisTScale=QtGui.QDoubleSpinBox()
        axisTScale.setValue(self.axisTubeScale)
        axisTScale.setMinimum(1e-2)
        axisTScale.setSingleStep(0.1)
        self.connect(axisTScale,QtCore.SIGNAL("valueChanged(double)"),self.axisTubeScaleChanged)
        displayLayout.addWidget(axisTScale,3,1)

        displayLayout.setRowStretch(4,10)

        self.displayDock.setWidget(displayStuff)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea,self.displayDock)
        self.displayDock.hide()

        self.displaypropertiesAction=self.displayDock.toggleViewAction()
        self.displaypropertiesAction.setShortcut("Ctrl+D")

        self.displayMenu=self.menuBar().addMenu("&Display")
        self.displayMenu.addAction(self.texteditorAction)
        self.displayMenu.addAction(self.displaypropertiesAction)
        self.displayMenu.addAction(self.utilityAction)
        if self.vName:
            self.displayMenu.addAction(self.textveditorAction)

        self.utilityMenu=self.menuBar().addMenu("&Utilities")
        self.utilityMenu.addAction(self.blockMeshAction)
        self.utilityMenu.addAction(self.checkMeshAction)

        self.rereadButton=QtGui.QPushButton("Reread blockMeshDict")

        try:
            self.readFile()
        except Exception:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'

            warning("While reading",self.fName,"this happened:",e)
            raise e

        self.ren.ResetCamera()

        self.oldBlock=-1
        self.blockActor=None
        self.blockTextActor=None
        self.blockAxisActor=None

        self.oldPatch=-1
        self.patchActor=None
        self.patchTextActor=vtk.vtkTextActor()
        self.patchTextActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
        self.patchTextActor.GetPositionCoordinate().SetValue(0.05,0.1)
        self.patchTextActor.GetTextProperty().SetColor(0.,0.,0.)
        self.patchTextActor.SetInput("Patch: <none>")

        label1=QtGui.QLabel("Block (-1 is none)")
        subLayout.addWidget(label1,0,0)
        self.scroll=QtGui.QSlider(QtCore.Qt.Horizontal)
        self.scroll.setRange(-1,len(self.blocks)-1)
        self.scroll.setValue(-1)
        self.scroll.setTickPosition(QtGui.QSlider.TicksBothSides)
        self.scroll.setTickInterval(1)
        self.scroll.setSingleStep(1)
        self.connect(self.scroll,QtCore.SIGNAL("valueChanged(int)"),self.colorBlock)
        subLayout.addWidget(self.scroll,0,1)

        label2=QtGui.QLabel("Patch (-1 is none)")
        subLayout.addWidget(label2,1,0)
        self.scroll2=QtGui.QSlider(QtCore.Qt.Horizontal)
        self.scroll2.setRange(-1,len(list(self.patches.keys()))-1)
        self.scroll2.setValue(-1)
        self.scroll2.setTickPosition(QtGui.QSlider.TicksBothSides)
        self.scroll2.setTickInterval(1)
        self.scroll2.setSingleStep(1)
        self.connect(self.scroll2,QtCore.SIGNAL("valueChanged(int)"),self.colorPatch)
        subLayout.addWidget(self.scroll2,1,1)

        buttonLayout=QtGui.QHBoxLayout()
        buttonLayout.addStretch()

        subLayout.addLayout(buttonLayout,2,0,1,2)
        buttonLayout.addWidget(self.rereadButton)
        self.connect(self.rereadButton,QtCore.SIGNAL("clicked()"),self.reread)
        b1=QtGui.QPushButton("Quit")
        buttonLayout.addWidget(b1)
        self.connect(b1,QtCore.SIGNAL("clicked()"),self.close)

        self.iren = self.renWin.GetInteractor()
        self.istyle = vtk.vtkInteractorStyleSwitch()

        self.iren.SetInteractorStyle(self.istyle)
        self.istyle.SetCurrentStyleToTrackballCamera()

        #        self.iren.Initialize() # Seems to be unnecessary and produces segfaults
        #        self.renWin.Render()
        self.iren.Start()

        self.addProps()

        self.setUnifiedTitleAndToolBarOnMac(True)

        self.setupBlockingGui()

        storedGeometry=QtCore.QSettings().value("geometry")
        if storedGeometry is not None:
            self.restoreGeometry(storedGeometry)
        else:
            print("No stored window geometry")

        storedState=QtCore.QSettings().value("state")
        if storedState is not None:
            self.restoreState(storedState)
        else:
            print("No stored state")

        self.setStatus()

        self.reread()

    def setupBlockingGui(self):
        """sets up the GUI to add the Blocking functions."""
        self.isBlocking = False
        self.isPatching = False
        self.tmpBlock = []
        self.redLineActors = []
        self.tmpBlockActor = None

        self.tmpPatch = []
        self.tmpPatchActor = None

        self.tmpGlyphActor = None

        self.renInteractor.GetPicker().AddObserver('PickEvent', self.PickEvent)

        self.blockingDock=QtGui.QDockWidget("GUI Blocking",
                                          self)
        self.blockingDock.setObjectName("BlockingDock")
        self.blockingDock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)

        displayStuff=QtGui.QWidget()
        displayLayout=QtGui.QGridLayout()
        displayStuff.setLayout(displayLayout)

        """Define Block"""
        self.defineBlockButton=QtGui.QPushButton("Define Block")
        displayLayout.addWidget(self.defineBlockButton,0,0)
        self.connect(self.defineBlockButton,QtCore.SIGNAL("clicked()"),self.defineBlock)

        """Insert Block"""
        self.insertBlockButton=QtGui.QPushButton("Insert Block")
        self.insertBlockButton.setEnabled(False)
        displayLayout.addWidget(self.insertBlockButton,0,1)
        self.connect(self.insertBlockButton,QtCore.SIGNAL("clicked()"),self.insertBlock)

        displayLayout.addWidget(QtGui.QLabel("Press 'p' to select vertices"),1,0,1,4,QtCore.Qt.AlignLeft)

        """Division Spin Box"""
        self.blockdivx = 1;
        self.blockdivy = 1;
        self.blockdivz = 1;


        self.blockDivSpinX=QtGui.QDoubleSpinBox()
        self.blockDivSpinX.setValue(self.blockdivx)
        self.blockDivSpinX.setMinimum(1)
        self.blockDivSpinX.setSingleStep(1)
        self.blockDivSpinX.setDecimals(0)


        self.blockDivSpinY=QtGui.QDoubleSpinBox()
        self.blockDivSpinY.setValue(self.blockdivy)
        self.blockDivSpinY.setMinimum(1)
        self.blockDivSpinY.setSingleStep(1)
        self.blockDivSpinY.setDecimals(0)


        self.blockDivSpinZ=QtGui.QDoubleSpinBox()
        self.blockDivSpinZ.setValue(self.blockdivz)
        self.blockDivSpinZ.setMinimum(1)
        self.blockDivSpinZ.setSingleStep(1)
        self.blockDivSpinZ.setDecimals(0)

        divLayout = QtGui.QHBoxLayout()
        divWidget = QtGui.QWidget()
        displayLayout.addWidget(QtGui.QLabel("Block Division"),2,0)
        divLayout.addWidget(self.blockDivSpinX)
        divLayout.addWidget(self.blockDivSpinY)
        divLayout.addWidget(self.blockDivSpinZ)
        divWidget.setLayout(divLayout)
        displayLayout.addWidget(divWidget,2,1,1,3)

        """Text Editor"""

        self.hexeditor=QtGui.QTextEdit()
        self.hexeditor.setFont(QtGui.QFont("Courier"))
        self.hexeditor.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.hexeditor.setReadOnly(True)
        #self.hexeditor.textChanged.connect(self.blockMeshWasModified)
        displayLayout.addWidget(self.hexeditor,3,0,1,4)

        """patch button"""
        self.definePatchButton=QtGui.QPushButton("Define Patch")
        displayLayout.addWidget(self.definePatchButton,4,0)
        self.connect(self.definePatchButton,QtCore.SIGNAL("clicked()"),self.definePatch)

        self.insertPatchButton=QtGui.QPushButton("Insert Patch")
        displayLayout.addWidget(self.insertPatchButton,5,0)
        self.connect(self.insertPatchButton,QtCore.SIGNAL("clicked()"),self.insertPatch)
        self.insertPatchButton.setEnabled(False)

        self.reverseNormalButton=QtGui.QPushButton("Reverse Normal")
        displayLayout.addWidget(self.reverseNormalButton,4,1)
        self.connect(self.reverseNormalButton,QtCore.SIGNAL("clicked()"),self.reverseNormal)
        self.reverseNormalButton.setEnabled(False)

        self.selectPatchBox=QtGui.QComboBox()
        displayLayout.addWidget(self.selectPatchBox,4,2,1,2)

        for str in self.patches.keys():
            self.selectPatchBox.addItem(str)

        self.blockingDock.setWidget(displayStuff)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea,self.blockingDock)
        self.blockingDock.hide()

        self.blockingGuiAction=self.blockingDock.toggleViewAction()
        self.blockingGuiAction.setShortcut("Ctrl+G")
        self.displayMenu.addAction(self.blockingGuiAction)
        self.blockingGuiAction.setEnabled(True)

    def AddBlockToDict(self):
        """Adds block to dict, using pyFoam functions"""
        msgBox = QtGui.QMessageBox()
        msgBox.setText("The document has been modified.")
        msgBox.setInformativeText("Do you want to save your changes?")
        msgBox.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
        ret = msgBox.exec_()

        if(ret==QtGui.QMessageBox.Ok):
            self.blockMesh["blocks"].append("hex")
            self.blockMesh["blocks"].append(self.tmpBlock)
            self.blockMesh["blocks"].append(self.getDivString())
            self.blockMesh["blocks"].append("simpleGrading")
            self.blockMesh["blocks"].append("(1 1 1)")
            self.blockMesh.writeFile()
            self.reread()

    def AddBlockToText(self):
        """Inserts block into opened dict"""
        msgBox = QtGui.QMessageBox()
        msgBox.setText("The document has been modified.")
        msgBox.setInformativeText("Do you want to save your changes?")
        msgBox.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
        ret = msgBox.exec_()

        if(ret==QtGui.QMessageBox.Ok):
            txt=str(self.editor.toPlainText())
            p1=txt.find("blocks")
            p2=txt.find("(",p1+1)
            if p1>=0 and p2>=0:
              txt=txt[:p2+1]+self.getTotalHexString()+txt[p2+1:]
              self.editor.setPlainText(txt)
              self.saveBlockMesh()

    def AddPatchToText(self):
        """Inserts patch into opened dict"""
        msgBox = QtGui.QMessageBox()
        msgBox.setText("The document has been modified.")
        msgBox.setInformativeText("Do you want to save your changes?")
        msgBox.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
        ret = msgBox.exec_()

        if(ret==QtGui.QMessageBox.Ok):
            txt=str(self.editor.toPlainText())
            patchname = self.selectPatchBox.currentText()
            self.setStatus("Adding to patch "+patchname)
            p1=txt.find(patchname)
            p2=txt.find("{",p1+1)
            p3=txt.find("(",p1+1)

            success=False

            if p1>=0 and p2>=0 and (p3<0 or p3>p2):
                p11=txt.find("faces",p2)
                p22=txt.find("(",p11+1)
                if p11>=0 and p22>=0:
                    success=True
                    txt=txt[:p22+1]+self.getTotalPatchString()+txt[p22+1:]
            elif p1>=0 and p3>=0:
                # old blockMeshFormat
                success=True
                txt=txt[:p3+1]+self.getTotalPatchString()+txt[p3+1:]

            if success:
                self.editor.setPlainText(txt)
                self.saveBlockMesh()
            else:
                self.setStatus("Could not insert into patch",patchname)

    def PickEvent(self, obj, evt):
        """Callback for picking event"""
        if(self.isBlocking):
            self.pickBlockVertice()
        if(self.isPatching):
            self.pickPatchVertice()
        return 1

    def pickBlockVertice(self):
        """pick a sphere and add point to block"""
        i=self.pickVertice()
        if(i==None):
            return

        if (len(self.tmpBlock)<=0 or self.tmpBlock[-1] != i):
            self.tmpBlock.append(i)
            self.hexeditor.moveCursor(QtGui.QTextCursor.End)
            self.hexeditor.insertPlainText(str(self.tmpBlock[-1]) + " ")
            n=len(self.tmpBlock)
            if(n>1):
                if(n==5):
                    self.addTmpBlockingLine(self.tmpBlock[n-5],self.tmpBlock[-1])
                    self.addTmpBlockingLine(self.tmpBlock[0],self.tmpBlock[3])
                elif(n>5):
                    self.addTmpBlockingLine(self.tmpBlock[n-5],self.tmpBlock[-1])
                    self.addTmpBlockingLine(self.tmpBlock[-2],self.tmpBlock[-1])
                else:
                    self.addTmpBlockingLine(self.tmpBlock[-2],self.tmpBlock[-1])

        if(len(self.tmpBlock)>=8):
            self.isBlocking=False
            self.hexeditor.moveCursor(QtGui.QTextCursor.End)
            self.hexeditor.insertPlainText(self.getEndHexString())
            self.setStatus("Block finished")
            self.showTmpBlock()
            #self.AddBlockToDict()
            self.insertBlockButton.setEnabled(True)

    def pickPatchVertice(self):
        """pick a sphere and add point to vertice"""
        i=self.pickVertice()
        if(i==None):
            return

        if (len(self.tmpPatch)<=0 or self.tmpPatch[-1] != i):
            self.tmpPatch.append(i)
            self.hexeditor.moveCursor(QtGui.QTextCursor.End)
            self.hexeditor.insertPlainText(str(self.tmpPatch[-1]) + " ")
            n=len(self.tmpPatch)
            if(n>1):
                if(n>3):
                    self.addTmpBlockingLine(self.tmpPatch[0],self.tmpPatch[-1])
                    self.addTmpBlockingLine(self.tmpPatch[-2],self.tmpPatch[-1])
                else:
                    self.addTmpBlockingLine(self.tmpPatch[-2],self.tmpPatch[-1])

        if(len(self.tmpPatch)>=4):
            self.isPatching=False
            self.hexeditor.moveCursor(QtGui.QTextCursor.End)
            self.hexeditor.insertPlainText(")")
            self.setStatus("Patch finished")
            self.showTmpPatch()
            self.insertPatchButton.setEnabled(True)
            self.reverseNormalButton.setEnabled(True)

    def pickVertice(self):
        """pick a vertice, returns Null if invalid"""
        picker = self.renInteractor.GetPicker()

        for i,v in enumerate(self.vActors):
            if v==picker.GetActor():
                return i

        return None

    def getEndHexString(self):
        """last part of hex string"""
        string =""
        divstring=self.getDivString()
        # + " " + str(self.blockDivSpinY.value()) + " " + str(self.blockDivSpinZ.value()) + " )"
        string = " ) "+ divstring +" simpleGrading (1 1 1)"
        return string

    def getTotalHexString(self):
        """total block hex string"""
        string ="\n    // added by pyFoam, DisplayBlockMesh\n"
        string =string + "    hex ( "
        for blk in self.tmpBlock:
            string += str(blk) + " "
        divstring=self.getDivString()
        string = string + self.getEndHexString()
        return string

    def getTotalPatchString(self):
        """total patch string"""
        string ="\n    // added by pyFoam, DisplayBlockMesh\n"
        string+=self.getPatchString()
        return string

    def getPatchString(self):
        string = "( "
        for patch in self.tmpPatch:
            string += str(patch) + " "
        string+= ")"
        return string

    def getDivString(self):
        """block division string"""
        divstring="(" + "{val:g}".format(val=self.blockDivSpinX.value())
        divstring=divstring + " {val:g}".format(val=self.blockDivSpinY.value())
        divstring=divstring + " {val:g})".format(val=self.blockDivSpinZ.value())
        return divstring

    def defineBlock(self):
        """callback for create block button"""
        self.isBlocking = not self.isBlocking
        if(self.isBlocking):
            self.startBlocking()
        else:
            self.resetBlocking()

    def definePatch(self):
        """Callback for create patch button"""
        self.isPatching = not self.isPatching
        if(self.isPatching):
            self.startPatch()
        else:
            self.resetPatch()

    def insertBlock(self):
        """inserts new block"""
        self.AddBlockToText()
        self.resetBlocking()

    def insertPatch(self):
        """inserts new patch"""
        self.AddPatchToText()
        self.resetPatch()

    def startBlocking(self):
        """start blocking"""
        self.resetBlocking()
        self.resetPatch()

        self.renInteractor.setFocus()
        self.isBlocking = True
        self.defineBlockButton.setText("Reset Block")
        self.hexeditor.append("hex ( ")
        self.setStatus("Start hex")

    def resetBlocking(self):
        """rest block"""
        self.isBlocking = False
        self.defineBlockButton.setText("Define Block")

        for act in self.redLineActors:
            self.ren.RemoveActor(act)
        self.redLineActors = []
        self.tmpBlock = []
        self.hexeditor.clear()
        self.insertBlockButton.setEnabled(False)
        self.ren.RemoveActor(self.tmpBlockActor)
        #cellpicker = vtk.vtkCellPicker()
        #picker = self.renInteractor.GetPicker()
        self.reread(False)

    def startPatch(self):
        """start define patch"""
        self.resetBlocking()
        self.resetPatch()

        self.renInteractor.setFocus()
        self.isPatching = True
        self.definePatchButton.setText("Reset Patch")
        self.hexeditor.append("( ")
        return

    def resetPatch(self):
        """rest patch"""
        self.isPatching = False
        self.definePatchButton.setText("Define Patch")
        self.tmpPatch = []
        for act in self.redLineActors:
            self.ren.RemoveActor(act)
        self.ren.RemoveActor(self.tmpGlyphActor)
        self.redLineActors = []
        self.hexeditor.clear()
        self.insertPatchButton.setEnabled(False)
        self.reverseNormalButton.setEnabled(False)
        self.ren.RemoveActor(self.tmpBlockActor)
        self.reread(False)
        return;

    def reverseNormal(self):
        self.tmpPatch.reverse()
        self.ren.RemoveActor(self.tmpGlyphActor)
        self.ren.RemoveActor(self.tmpBlockActor)
        self.showTmpPatch()
        self.hexeditor.clear()
        self.hexeditor.append(self.getPatchString())

    def addTmpBlockingLine(self,index1,index2):
        """Add a colored line to show blocking progress"""
        try:
            c1=self.vertices[index1]
            c2=self.vertices[index2]
        except:
            if index1>=len(self.vertices):
                self.addUndefined(index1)
            if index2>=len(self.vertices):
                self.addUndefined(index2)
            return None
        line=vtk.vtkLineSource()
        line.SetPoint1(c1)
        line.SetPoint2(c2)
        mapper=vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(line.GetOutputPort())

        property = vtk.vtkProperty();
        property.SetColor(0, 255, 50);

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.SetProperty(property);

        self.redLineActors.append(actor)

        self.ren.AddActor(actor)
        return actor

    def addInputToPolyData(self,appendPoly,data):
        """Helper version needed because of changed API in VTK6"""
        if vtkVersion>=6:
            appendPoly.AddInputData(data)
        else:
            appendPoly.AddInput(data)

    def showTmpBlock(self):
        """Add a colored block"""
        append=vtk.vtkAppendPolyData()
        b=self.tmpBlock
        self.addInputToPolyData(append,self.makeFace([b[0],b[1],b[2],b[3]]))
        self.addInputToPolyData(append,self.makeFace([b[4],b[5],b[6],b[7]]))
        self.addInputToPolyData(append,self.makeFace([b[0],b[1],b[5],b[4]]))
        self.addInputToPolyData(append,self.makeFace([b[3],b[2],b[6],b[7]]))
        self.addInputToPolyData(append,self.makeFace([b[0],b[3],b[7],b[4]]))
        self.addInputToPolyData(append,self.makeFace([b[1],b[2],b[6],b[5]]))
        mapper=vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(append.GetOutputPort())
        self.tmpBlockActor = vtk.vtkActor()
        self.tmpBlockActor.SetMapper(mapper)
        self.tmpBlockActor.GetProperty().SetColor(0.,1.,0.1)
        self.tmpBlockActor.GetProperty().SetOpacity(0.3)
        self.ren.AddActor(self.tmpBlockActor)

        self.renWin.Render()

    def showTmpPatch(self):
        """Add a colored patch"""
        append=vtk.vtkAppendPolyData()
        b=self.tmpPatch
        self.addInputToPolyData(append,self.makeFace([b[0],b[1],b[2],b[3]]))
        mapper=vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(append.GetOutputPort())
        self.tmpBlockActor = vtk.vtkActor()
        self.tmpBlockActor.SetMapper(mapper)
        self.tmpBlockActor.GetProperty().SetColor(0.,1.,0.1)
        self.tmpBlockActor.GetProperty().SetOpacity(0.3)
        self.ren.AddActor(self.tmpBlockActor)


        planeNormals = vtk.vtkPolyDataNormals()
        planeNormals.SetInputConnection(append.GetOutputPort())
        planeMapper = vtk.vtkDataSetMapper()
        planeMapper.SetInputConnection(planeNormals.GetOutputPort())

        arrowSource = vtk.vtkArrowSource()

        arrowGlyph = vtk.vtkGlyph3D()
        arrowGlyph.ScalingOn()
        arrowGlyph.SetScaleFactor(self.blockMesh.typicalLength()/4)
        arrowGlyph.SetVectorModeToUseNormal()
        arrowGlyph.SetScaleModeToScaleByVector()
        arrowGlyph.OrientOn()
        arrowGlyph.SetSourceConnection(arrowSource.GetOutputPort())
        arrowGlyph.SetInputConnection(planeNormals.GetOutputPort())

        """



        >>>
        >>> # Specify the shape of the glyph
        >>> vtkArrowSource arrowSource
        >>>
        >>> vtkGlyph3D arrowGlyph
        >>>  arrowGlyph ScalingOn
        >>>  arrowGlyph SetScaleFactor 0.7
        >>>  arrowGlyph SetVectorModeToUseNormal
        >>>  arrowGlyph SetScaleModeToScaleByVector
        >>>  arrowGlyph OrientOn
        >>>  arrowGlyph SetSourceConnection [arrowSource GetOutputPort]
        >>>  arrowGlyph SetInputConnection  [planeNormals GetOutputPort]
        >>>
        >>> vtkDataSetMapper arrowGlyphMapper
        >>>  arrowGlyphMapper SetInputConnection [arrowGlyph GetOutputPort]
        >>>
        >>> vtkActor glyphActor
        >>>  glyphActor SetMapper arrowGlyphMapper
        """
        #actor = vtk.vtkActor()
        #actor.SetMapper(planeMapper);
        #self.ren.AddActor(actor)

        glyphMapper = vtk.vtkPolyDataMapper()
        glyphMapper.SetInputConnection(arrowGlyph.GetOutputPort());

        self.tmpGlyphActor = vtk.vtkActor()
        self.tmpGlyphActor.SetMapper(glyphMapper);

        self.tmpGlyphActor.GetProperty().SetColor(0., 1., 0.)

        self.ren.AddActor(self.tmpGlyphActor)

        self.renWin.Render()

    def blockMesh(self):
        self.executeUtility("blockMesh")

    def checkMesh(self):
        self.executeUtility("checkMesh")

    def executeUtility(self,util):
        if self.worker!=None:
            self.error("There seems to be another worker")

        self.setStatus("Executing "+util)
        self.blockMeshAction.setEnabled(False)
        self.checkMeshAction.setEnabled(False)

        self.utilityOutput.clear()
        self.utilityOutput.append("Running "+util+" on case "+self.caseDir)
        self.utilityDock.show()

        self.worker=UtilityThread(argv=[util,
                                        "-case",
                                        self.caseDir],
                                  parent=self)
        self.connect(self.worker,QtCore.SIGNAL("finished()"),self.executionEnded)
        self.connect(self.worker,QtCore.SIGNAL("newLine(QString)"),self.utilityOutputAppend)
        self.worker.start()

    def utilityOutputAppend(self,line):
        self.utilityOutput.append(line)

    def executionEnded(self):
        self.blockMeshAction.setEnabled(True)
        self.checkMeshAction.setEnabled(True)
        self.setStatus("Execution of "+self.worker.argv[0]+" finished"+self.worker.status)
        self.worker=None

    def setStatus(self,message="Ready"):
        if self.isWindowModified():
            message="blockMesh modified - "+message
        print_("Status:",message)
        self.statusBar().showMessage(message)

    def blockMeshWasModified(self):
        if not self.saveAction.isEnabled():
            self.saveAction.setEnabled(True)
        if self.rereadAction.isEnabled():
            self.rereadAction.setEnabled(False)
            self.rereadButton.setEnabled(False)

        self.setWindowModified(True)
        self.setStatus()

    def readFile(self,resetText=True):
        if resetText:
            txt=open(self.fName).read()
            self.editor.setPlainText(txt)
            if self.vName:
                txt=open(self.vName).read()
                self.vEditor.setPlainText(txt)

        self.setWindowModified(False)
        if not self.alwaysSave:
            self.saveAction.setEnabled(False)
        self.rereadAction.setEnabled(True)
        self.rereadButton.setEnabled(True)

        bFile=self.fName
        if self.vName:
            print_("Evaluating template")
            bFile=path.splitext(self.fName)[0]
            template=TemplateFile(self.fName,
                                  expressionDelimiter=self.opts.expressionDelimiter,
                                  assignmentLineStart=self.opts.assignmentLineStart)

            if path.exists(self.vName):
                vals=ParsedParameterFile(self.vName,
                                         noHeader=True,
                                         doMacroExpansion=True).getValueDict()
            else:
                vals={}
            txt=template.getString(vals)
            open(bFile,"w").write(txt)

        self.blockMesh=ParsedBlockMeshDict(bFile,
                                           doMacroExpansion=True)

        self.vertices=self.blockMesh.vertices()
        self.vActors=[None]*len(self.vertices)
        self.tActors=[None]*len(self.vertices)
        self.spheres=[None]*len(self.vertices)

        self.blocks=self.blockMesh.blocks()
        self.patches=self.blockMesh.patches()

        self.vRadius=self.blockMesh.typicalLength()/50

        for i in range(len(self.vertices)):
            self.addVertex(i)

        self.setAxes()

        self.undefined=[]

        for i in range(len(self.blocks)):
            self.addBlock(i)

        for a in self.blockMesh.arcs():
            self.makeArc(a)

        if len(self.undefined)>0:
            self.undefinedActor.SetInput("Undefined vertices: "+str(self.undefined))
        else:
            self.undefinedActor.SetInput("")

        self.setStatus("Read file")

    def saveBlockMesh(self):
        txt=str(self.editor.toPlainText())
        open(self.fName,"w").write(txt)
        if self.vName:
            txt=str(self.vEditor.toPlainText())
            open(self.vName,"w").write(txt)

        self.reread(resetText=False)
        self.setStatus("Saved file")

    def addUndefined(self,i):
        if not i in self.undefined:
            self.undefined.append(i)

    def addProps(self):
        self.ren.AddViewProp(self.axes)
        self.ren.AddActor2D(self.patchTextActor)
        self.ren.AddActor2D(self.undefinedActor)

    def numberScaleChanged(self,scale):
        self.numberScale=scale
        for tActor in self.tActors:
            tActor.SetScale(self.numberScale*self.vRadius,self.numberScale*self.vRadius,self.numberScale*self.vRadius)
        self.renWin.Render()

    def pointScaleChanged(self,scale):
        self.pointScale=scale
        for sphere in self.spheres:
            sphere.SetRadius(self.vRadius*self.pointScale)
        self.renWin.Render()

    def axisLabelScaleChanged(self,scale):
        self.axisLabelScale=scale
        if self.blockTextActor:
            for t in self.blockTextActor:
                t.SetScale(self.axisLabelScale*self.vRadius,
                           self.axisLabelScale*self.vRadius,
                           self.axisLabelScale*self.vRadius)
            self.renWin.Render()

    def axisTubeScaleChanged(self,scale):
        self.axisTubeScale=scale
        if self.blockAxisActor:
            for t in self.blockAxisActor:
                t.SetRadius(self.vRadius*self.axisTubeScale)
            self.renWin.Render()

    def addPoint(self,coord,factor=1):
        sphere=vtk.vtkSphereSource()
        sphere.SetRadius(self.vRadius*factor*self.pointScale)
        sphere.SetCenter(coord)
        mapper=vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self.ren.AddActor(actor)

        return sphere,actor

    def addVertex(self,index):
        coord=self.vertices[index]
        self.spheres[index],self.vActors[index]=self.addPoint(coord)
        text=vtk.vtkVectorText()
        text.SetText(str(index))
        tMapper=vtk.vtkPolyDataMapper()
        tMapper.SetInputConnection(text.GetOutputPort())
        tActor = vtk.vtkFollower()
        tActor.SetMapper(tMapper)
        tActor.SetScale(self.numberScale*self.vRadius,self.numberScale*self.vRadius,self.numberScale*self.vRadius)
        tActor.AddPosition(coord[0]+self.vRadius,coord[1]+self.vRadius,coord[2]+self.vRadius)
        tActor.SetCamera(self.cam)
        tActor.GetProperty().SetColor(1.0,0.,0.)
        self.tActors[index]=tActor
        self.ren.AddActor(tActor)

    def addLine(self,index1,index2):
        try:
            c1=self.vertices[index1]
            c2=self.vertices[index2]
        except:
            if index1>=len(self.vertices):
                self.addUndefined(index1)
            if index2>=len(self.vertices):
                self.addUndefined(index2)
            return None
        line=vtk.vtkLineSource()
        line.SetPoint1(c1)
        line.SetPoint2(c2)
        mapper=vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(line.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self.ren.AddActor(actor)
        return actor

    def makeDirection(self,index1,index2,label):
        try:
            c1=self.vertices[index1]
            c2=self.vertices[index2]
        except:
            return None,None
        line=vtk.vtkLineSource()
        line.SetPoint1(c1)
        line.SetPoint2(c2)
        tube=vtk.vtkTubeFilter()
        tube.SetRadius(self.vRadius*self.axisTubeScale)
        tube.SetNumberOfSides(10)
        tube.SetInputConnection(line.GetOutputPort())
        text=vtk.vtkVectorText()
        text.SetText(label)
        tMapper=vtk.vtkPolyDataMapper()
        tMapper.SetInputConnection(text.GetOutputPort())
        tActor = vtk.vtkFollower()
        tActor.SetMapper(tMapper)
        tActor.SetScale(self.axisLabelScale*self.vRadius,
                        self.axisLabelScale*self.vRadius,
                        self.axisLabelScale*self.vRadius)
        tActor.AddPosition((c1[0]+c2[0])/2+self.vRadius,
                           (c1[1]+c2[1])/2+self.vRadius,
                           (c1[2]+c2[2])/2+self.vRadius)
        tActor.SetCamera(self.cam)
        tActor.GetProperty().SetColor(0.0,0.,0.)
        return tube,tActor

    def makeSpline(self,lst):
        points = vtk.vtkPoints()
        for i in range(len(lst)):
            v=lst[i]
            points.InsertPoint(i,v[0],v[1],v[2])
        spline=vtk.vtkParametricSpline()
        spline.SetPoints(points)
        spline.ClosedOff()
        splineSource=vtk.vtkParametricFunctionSource()
        splineSource.SetParametricFunction(spline)
        mapper=vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(splineSource.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self.ren.AddActor(actor)

    def makeArc(self,data):
        try:
            self.makeSpline([self.vertices[data[0]],data[1],self.vertices[data[2]]])
        except:
            if data[0]>=len(self.vertices):
                self.addUndefined(data[0])
            if data[2]>=len(self.vertices):
                self.addUndefined(data[2])

        self.addPoint(data[1],factor=0.5)

    def makeFace(self,lst):
        points = vtk.vtkPoints()
        side = vtk.vtkCellArray()
        side.InsertNextCell(len(lst))
        for i in range(len(lst)):
            try:
                v=self.vertices[lst[i]]
            except:
                self.addUndefined(lst[i])
                return None
            points.InsertPoint(i,v[0],v[1],v[2])
            side.InsertCellPoint(i)
        result=vtk.vtkPolyData()
        result.SetPoints(points)
        result.SetPolys(side)

        return result

    def addBlock(self,index):
        b=self.blocks[index]

        self.addLine(b[ 0],b[ 1])
        self.addLine(b[ 3],b[ 2])
        self.addLine(b[ 7],b[ 6])
        self.addLine(b[ 4],b[ 5])
        self.addLine(b[ 0],b[ 3])
        self.addLine(b[ 1],b[ 2])
        self.addLine(b[ 5],b[ 6])
        self.addLine(b[ 4],b[ 7])
        self.addLine(b[ 0],b[ 4])
        self.addLine(b[ 1],b[ 5])
        self.addLine(b[ 2],b[ 6])
        self.addLine(b[ 3],b[ 7])

    def setAxes(self):
        append=vtk.vtkAppendPolyData()
        for a in self.vActors:
            if a!=None:
                append.AddInputConnection(a.GetMapper().GetOutputPort())
        if vtkVersion>=6:
            self.axes.SetInputConnection(append.GetOutputPort())
        else:
            self.axes.SetInput(append.GetOutput())

    def reread(self,resetText=True):
        self.ren.RemoveAllViewProps()
        self.patchActor=None
        self.blockActor=None
        self.blockAxisActor=None
        self.blockTextActor=None
        self.addProps()
        try:
            self.readFile(resetText=resetText)

            tmpBlock=self.scroll.value()
            if not tmpBlock<len(self.blocks):
                tmpBlock=len(self.blocks)-1
            self.scroll.setRange(-1,len(self.blocks)-1)
            self.scroll.setValue(tmpBlock)
            self.colorBlock(tmpBlock)

            tmpPatch=self.scroll2.value()
            if not tmpPatch<len(list(self.patches.keys())):
                tmpPatch=len(list(self.patches.keys()))-1
            self.scroll2.setRange(-1,len(list(self.patches.keys()))-1)
            self.scroll2.setValue(tmpPatch)
            self.colorPatch(tmpPatch)

            self.renWin.Render()
        except Exception:
            e = sys.exc_info()[1] # Needed because python 2.5 does not support 'as e'
            print_("Problem rereading:",e)
            self.setStatus("Problem:"+str(e))
            raise e

    def colorBlock(self,value):
        newBlock=int(value)
        if self.oldBlock>=0 and self.blockActor!=None:
            self.ren.RemoveActor(self.blockActor)
            for ta in self.blockTextActor:
                self.ren.RemoveActor(ta)
            self.blockActor=None
            self.blockTextActor=None
            self.blockAxisActor=None
        if newBlock>=0:
            append=vtk.vtkAppendPolyData()
            b=self.blocks[newBlock]

            self.addInputToPolyData(append,self.makeFace([b[0],b[1],b[2],b[3]]))
            self.addInputToPolyData(append,self.makeFace([b[4],b[5],b[6],b[7]]))
            self.addInputToPolyData(append,self.makeFace([b[0],b[1],b[5],b[4]]))
            self.addInputToPolyData(append,self.makeFace([b[3],b[2],b[6],b[7]]))
            self.addInputToPolyData(append,self.makeFace([b[0],b[3],b[7],b[4]]))
            self.addInputToPolyData(append,self.makeFace([b[1],b[2],b[6],b[5]]))
            d1,t1=self.makeDirection(b[0],b[1],"x1")
            self.addInputToPolyData(append,d1.GetOutput())
            self.ren.AddActor(t1)
            d2,t2=self.makeDirection(b[0],b[3],"x2")
            self.addInputToPolyData(append,d2.GetOutput())
            self.ren.AddActor(t2)
            d3,t3=self.makeDirection(b[0],b[4],"x3")
            self.addInputToPolyData(append,d3.GetOutput())
            self.ren.AddActor(t3)
            self.blockTextActor=(t1,t2,t3)
            self.blockAxisActor=(d1,d2,d3)
            mapper=vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(append.GetOutputPort())
            self.blockActor = vtk.vtkActor()
            self.blockActor.SetMapper(mapper)
            self.blockActor.GetProperty().SetColor(0.,1.,0.)
            self.blockActor.GetProperty().SetOpacity(0.3)
            self.ren.AddActor(self.blockActor)

        self.oldBlock=newBlock
        self.renWin.Render()

    def colorPatch(self,value):
        newPatch=int(value)
        if self.oldPatch>=0 and self.patchActor!=None:
            self.ren.RemoveActor(self.patchActor)
            self.patchActor=None
            self.patchTextActor.SetInput("Patch: <none>")
        if newPatch>=0:
            name=list(self.patches.keys())[newPatch]
            subs=self.patches[name]
            append=vtk.vtkAppendPolyData()
            for s in subs:
                self.addInputToPolyData(append,self.makeFace(s))
            mapper=vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(append.GetOutputPort())
            self.patchActor = vtk.vtkActor()
            self.patchActor.SetMapper(mapper)
            self.patchActor.GetProperty().SetColor(0.,0.,1.)
            self.patchActor.GetProperty().SetOpacity(0.3)
            self.ren.AddActor(self.patchActor)
            self.patchTextActor.SetInput("Patch: "+name)

        self.oldPatch=newPatch
        self.renWin.Render()

    def closeEvent(self,event):
        print_("Closing and saving settings to",QtCore.QSettings().fileName())
        QtCore.QSettings().setValue("geometry",self.saveGeometry())
        QtCore.QSettings().setValue("state",self.saveState())

class DisplayBlockMesh(PyFoamApplicationQt4,
                       CommonTemplateFormat):
    def __init__(self):
        description="""\
Reads the contents of a blockMeshDict-file and displays the vertices
as spheres (with numbers). The blocks are sketched by lines. One block
can be seceted with a slider. It will be displayed as a green cube
with the local directions x1,x2 and x3. Also a patch that is selected
by a slider will be sketched by blue squares

This is a new version with a QT-GUI
        """

        super(DisplayBlockMesh,self).__init__(description=description,
                                              usage="%prog [options] <blockMeshDict>",
                                              interspersed=True,
                                              nr=1)

    def addOptions(self):
        template=OptionGroup(self.parser,
                             "Template mode",
                             "Additional input for template mode where the edited file is a template that can be processed with the pyFoamFromTemplate.py-utility")
        template.add_option("--values-file",
                            dest="valuesFile",
                            action="store",
                            default=None,
                            help="File with the values to be used in the template. If specified the application runs in template mode")

        self.parser.add_option_group(template)

        CommonTemplateFormat.addOptions(self)

    def setupGUI(self):
        print_(usedVTK)

        bmFile=self.parser.getArgs()[0]
        if not path.exists(bmFile):
            self.error(bmFile,"not found")

        if self.opts.valuesFile:
            print_("Running in template mode")
            if path.splitext(bmFile)[1]=="":
                self.error("Specified template file",bmFile,
                           "has no extension")
        try:
            self.dialog=DisplayBlockMeshDialog(bmFile,
                                               opts=self.opts,
                                               valuesFile=self.opts.valuesFile)
        except IOError:
            self.error("Problem with blockMesh file",bmFile)
        self.dialog.show()

# Should work with Python3
