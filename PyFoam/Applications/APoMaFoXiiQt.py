"""
Application-class that implements pyFoamAPoMaFoX.py (A Poor Man's FoamX)
"""
from os import path
import sys

from PyFoam.Applications.PyFoamApplication import PyFoamApplication
from PyFoam.Applications.CaseBuilderBackend import CaseBuilderFile,CaseBuilderDescriptionList
from PyFoam.Applications.CommonCaseBuilder import CommonCaseBuilder
from PyFoam import configuration as config

from PyFoam.Error import error,warning

from PyFoam.ThirdParty.six import print_

try:
    import PyQt4
except ImportError:
    error("This application needs an installed PyQt4-library")

from PyQt4 import QtCore, QtGui

class APoMaFoXiiQt(PyFoamApplication,
               CommonCaseBuilder):
    def __init__(self,args=None):
        description="""\
APoMaFoX is "A Poor Mans FoamX".

A small text interface to the CaseBuilder-Functionality
"""
        PyFoamApplication.__init__(self,
                                   args=args,
                                   description=description,
                                   usage="%prog <caseBuilderFile>",
                                   interspersed=True,
                                   nr=0,
                                   exactNr=False)

    def addOptions(self):
        CommonCaseBuilder.addOptions(self)

    def run(self):
        if self.pathInfo():
            return

        app = QtGui.QApplication(self.parser.getArgs())

        fName=None
        if len(self.parser.getArgs())==0:
            dialog=CaseBuilderBrowser()
            if len(dialog.descriptions)==1:
                fName=dialog.descriptions[0][1]
                self.warning("Automatically choosing the only description",fName)
        elif len(self.parser.getArgs())==1:
            fName=self.searchDescriptionFile(self.parser.getArgs()[0])

            if not path.exists(fName):
                error("The description file",fName,"does not exist")
        else:
            error("Too many arguments")

        if fName!=None:
            dialog=CaseBuilderDialog(fName)

        dialog.show()
        sys.exit(app.exec_())

class ComboWrapper(QtGui.QComboBox):
    def __init__(self):
        super(ComboWrapper,self).__init__()

    def text(self):
        return str(self.currentText())

class FilenameWrapper(QtGui.QWidget):
    def __init__(self,parent=None):
        super(FilenameWrapper,self).__init__(parent)
        layout=QtGui.QHBoxLayout()
        self.name=QtGui.QLineEdit()
        layout.addWidget(self.name)
        button=QtGui.QPushButton("File ...")
        layout.addWidget(button)
        self.connect(button,QtCore.SIGNAL("clicked()"),self.pushed)
        self.setLayout(layout)

    def pushed(self):
        try:
            theDir=path.dirname(self.text())
        except AttributeError:
            theDir=path.abspath(path.curdir)

        fName=QtGui.QFileDialog.getOpenFileName(self, # parent
                                                "Select File", # caption
                                                theDir)
        if fName!="":
            self.setText(str(fName))

        return False

    def setText(self,txt):
        self.name.setText(txt)

    def text(self):
        return path.abspath(str(self.name.text()))

class CaseBuilderQt(QtGui.QDialog):
    """The common denominator for the windows"""
    def __init__(self,parent=None):
        super(CaseBuilderQt,self).__init__(parent)
        self.status=None

    def setStatus(self,text):
        print_(text)
        if not self.status:
            self.status=QtGui.QStatusBar(self)
            self.layout().addWidget(self.status)

        self.status.showMessage(text)

class CaseBuilderBrowser(CaseBuilderQt):
    """A browser of all the available descriptions"""
    def __init__(self):
        CaseBuilderQt.__init__(self)

        self.descriptions=CaseBuilderDescriptionList()
        if len(self.descriptions)==0:
            error("No description-files (.pfcb) found in path",config().get("CaseBuilder","descriptionpath"))

        mainLayout = QtGui.QVBoxLayout()
        self.setLayout(mainLayout)

        self.descriptsList = QtGui.QListWidget()
        self.descriptsList.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        mainLayout.addWidget(self.descriptsList)

        self.itemlist=[]
        for d in self.descriptions:
            item=QtGui.QListWidgetItem(d[2])
            item.setToolTip(d[3])
            self.descriptsList.addItem(item)
            self.itemlist.append((item,d))

        buttons=QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)
        mainLayout.addWidget(buttons)
        selectButton=QtGui.QPushButton("Select")
        selectButton.setToolTip("Select the case description that we want to work with")
        buttons.addButton(selectButton,QtGui.QDialogButtonBox.AcceptRole)
        try:
            buttons.accepted.connect(self.selectPressed)
            buttons.rejected.connect(self.reject)
        except AttributeError:
            warning("Old QT-version where QDialogButtonBox doesn't have the accepted/rejected-attributes")
            self.connect(buttons,QtCore.SIGNAL("accepted()"),self.selectPressed)
            self.connect(buttons,QtCore.SIGNAL("rejected()"),self.reject)

    def selectPressed(self):
        self.setStatus("Pressed selected")
        selected=self.descriptsList.selectedItems()
        if len(selected)!=1:
            self.setStatus("Nothing selected")
            return

        desc=None
        for it,d in self.itemlist:
            if it==selected[0]:
                desc=d
                break

        if desc==None:
            self.setStatus("Did not find the selection")
            return

        self.setStatus("")
        sub=CaseBuilderDialog(desc[1],parent=self)
        sub.show()

class CaseBuilderDialog(CaseBuilderQt):
    """A dialog for a CaswBuilder-dialog"""
    def __init__(self,fName,parent=None):
        CaseBuilderQt.__init__(self,parent=parent)

        self.desc=CaseBuilderFile(fName)

        #        print_("Read case description",self.desc.name())

        mainLayout = QtGui.QVBoxLayout()
        self.setLayout(mainLayout)

        mainLayout.addWidget(QtGui.QLabel("Builder Template: "
                                        + self.desc.name()
                                        +"\n"+self.desc.description()))

        mainLayout.addWidget(QtGui.QLabel("Data Template: "
                                          + self.desc.templatePath()))

        try:
            caseLayout=QtGui.QFormLayout()
        except AttributeError:
            warning("Qt-version without QFormLayout")
            caseLayout=QtGui.QVBoxLayout()

        mainLayout.addLayout(caseLayout)

        self.caseName=QtGui.QLineEdit()
        self.caseName.setToolTip("The name under which the case will be saved")

        try:
            caseLayout.addRow("Case name",self.caseName)
        except AttributeError:
            caseLayout.addWidget(QtGui.QLabel("Case name"))
            caseLayout.addWidget(self.caseName)

        args=self.desc.arguments()
        mLen=max(*list(map(len,args)))
        aDesc=self.desc.argumentDescriptions()
        aDef=self.desc.argumentDefaults()
        allArgs=self.desc.argumentDict()

        self.argfields={}

        groups=[None]+self.desc.argumentGroups()
        gDesc=self.desc.argumentGroupDescription()

        theGroupTabs=QtGui.QTabWidget()
        mainLayout.addWidget(theGroupTabs)

        for g in groups:
            if g==None:
                name="Default"
                desc="All the arguments that did not fit into another group"
            else:
                name=g
                desc=gDesc[g]
            gWidget=QtGui.QWidget()
            try:
                gLayout=QtGui.QFormLayout()
            except AttributeError:
                gLayout=QtGui.QVBoxLayout()
            gWidget.setLayout(gLayout)
            idx=theGroupTabs.addTab(gWidget,name)
            theGroupTabs.setTabToolTip(idx,desc)

            for a in self.desc.groupArguments(g):
                theType=allArgs[a].type
                if theType=="file":
                    print_("File",a)
                    aWidget=FilenameWrapper(self)
                    aWidget.setText(aDef[a])
                elif theType=="selection":
                    aWidget=ComboWrapper()
                    aWidget.addItems(allArgs[a].values)
                    aWidget.setCurrentIndex(allArgs[a].values.index(aDef[a]))
                else:
                    aWidget=QtGui.QLineEdit()
                    aWidget.setText(aDef[a])
                aWidget.setToolTip(aDesc[a])
                self.argfields[a]=aWidget
                try:
                    gLayout.addRow(a,aWidget)
                except AttributeError:
                    gLayout.addWidget(QtGui.QLabel(a))
                    gLayout.addWidget(aWidget)

        bottomLayout=QtGui.QHBoxLayout()
        mainLayout.addLayout(bottomLayout)

        self.noClose=QtGui.QCheckBox("Don't close")
        self.noClose.setToolTip("Do not close after 'Generate'")
        bottomLayout.addWidget(self.noClose)

        buttons=QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)
        bottomLayout.addWidget(buttons)
        generateButton=QtGui.QPushButton("Generate")
        generateButton.setToolTip("Copy the template case and modify it according to the settings")
        buttons.addButton(generateButton,QtGui.QDialogButtonBox.AcceptRole)
        try:
            buttons.accepted.connect(self.generatePressed)
            buttons.rejected.connect(self.reject)
        except AttributeError:
            self.connect(buttons,QtCore.SIGNAL("accepted()"),self.generatePressed)
            self.connect(buttons,QtCore.SIGNAL("rejected()"),self.reject)

    def generatePressed(self):
        self.setStatus("Pressed generate")
        ok=False

        caseName=str(self.caseName.text())
        if len(caseName)==0:
            self.setStatus("Casename empty")
            return

        if path.exists(caseName):
            self.setStatus("Directory "+caseName+" already existing")
            return

        self.setStatus("Generating the case "+caseName)
        args={}
        for i,a in enumerate(self.desc.arguments()):
            args[a]=str(self.argfields[a].text())
            if len(args[a])==0:
                self.setStatus("No argument "+a+" was given")
                return

        msg=self.desc.verifyArguments(args)
        if msg:
            self.setStatus(msg)
            return

        self.setStatus("With the arguments "+str(args))

        self.desc.buildCase(caseName,args)
        ok=True
        if ok:
            self.setStatus("")
            if not self.noClose.isChecked():
                self.accept()
            else:
                self.setStatus("Generated "+caseName)

# Should work with Python3 and Python2
