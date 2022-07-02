#  ICE Revision: $Id$
"""Plots a collection of timelines"""

from PyFoam.Error import warning,error

from PyFoam.Basics.CustomPlotInfo import readCustomPlotInfo,CustomPlotInfo

from .GeneralPlotTimelines import GeneralPlotTimelines

from platform import uname

from PyFoam.ThirdParty.six import print_

firstTimeImport=True
app=None


class QwtPlotTimelines(GeneralPlotTimelines):
    """This class opens a Qt-window and plots a timelines-collection in aQwt.Plot-widget"""

    figureNr=1

    def __init__(self,
                 timelines,
                 custom,
                 showWindow=True,
                 quiet=False,
                 registry=None):
        """:param timelines: The timelines object
        :type timelines: TimeLineCollection
        :param custom: A CustomplotInfo-object. Values in this object usually override the
        other options
        """

        try:
            global Qt,Qwt,app

            from PyQt4 import Qt
            import PyQt4.Qwt5 as Qwt

            if showWindow and app==None:
                app = Qt.QApplication([])
                #                app.thread()
        except ImportError:
            error("Could not import Qt4 or Qwt")

        GeneralPlotTimelines.__init__(self,timelines,custom,showWindow=showWindow,registry=registry)

        self.figNr=QwtPlotTimelines.figureNr
        QwtPlotTimelines.figureNr+=1

        self.figure=None
        self.title="no title"

        self.ylabel="no label"
        self.ylabel2="no label"
        try:
            if self.spec.ylabel:
                self.setYLabel(self.spec.ylabel)
        except AttributeError:
            pass
        try:
            if self.spec.y2label:
                self.setYLabel2(self.spec.y2label)
        except AttributeError:
            pass

        self.axis1=None
        self.axis2=None

        self.setTitle(self.spec.theTitle)

        self.with_=self.spec.with_
        if not self.with_ in ['lines']:
            warning("'with'-style",self.with_,"not implemented, using 'lines'")
            self.with_='lines'

        self.curves={}

        self.redo()

    def buildData(self,times,name,title,lastValid):
        """Build the implementation specific data
        :param times: The vector of times for which data exists
        :param name: the name under which the data is stored in the timeline
        :param title: the title under which this will be displayed"""

        if self.figure==None:
            return

        axis=self.axis1
        if self.testAlternate(name):
            a=self.axis2
        data=self.data.getValues(name)
        tm=times
        if len(tm)>0 and not lastValid:
            tm=tm[:-1]
            data=data[:-1]
        plotIt=True
        try:
            if self.spec.logscale and min(data)<=0:
                plotIt=False
        except AttributeError:
            pass

        if not plotIt:
            return

        if name not in self.curves:
            a=Qwt.QwtPlotCurve(title)
            print_("Plot",dir(a))
            a.attach(self.figure)
            a.setPen(Qt.QPen(Qt.Qt.red))
            self.curves[name]=a
            self.figure.update()

        a=self.curves[name]
        a.setData(tm,data)
        #        print "Figure",dir(self.figure)
        self.figure.replot()

##        drawstyle='default'
##        marker=''
##        linestyle='-'

##        if self.with_=='lines':
##            pass
##        elif self.with_=='steps':
##            drawstyle='steps'
##        elif self.with_=='points':
##            linestyle=''
##            marker='*'
##        elif self.with_=='dots':
##            linestyle=''
##            marker='.'
##        elif self.with_=='linespoints':
##            marker='*'
##        else:
##            warning("'with'-style",self.with_,"not implemented, using 'lines'")

##        if plotIt:
##            a.plot(tm,
##                   data,
##                   label=title,
##                   drawstyle=drawstyle,
##                   marker=marker,
##                   linestyle=linestyle)

    def preparePlot(self):
        """Prepare the plotting window"""
        if self.figure:
            return
        self.figure=Qwt.QwtPlot()
        self.figure.setCanvasBackground(Qt.Qt.white)
        self.figure.canvas().setFrameStyle(Qt.QFrame.Box | Qt.QFrame.Plain)
        self.figure.canvas().setLineWidth(1)
        for i in range(Qwt.QwtPlot.axisCnt):
            scaleWidget = self.figure.axisWidget(i)
            if scaleWidget:
                scaleWidget.setMargin(0)
            scaleDraw = self.figure.axisScaleDraw(i)
            if scaleDraw:
                scaleDraw.enableComponent(
                    Qwt.QwtAbstractScaleDraw.Backbone, False)
        self.figure.setTitle("Figure: %d - %s" % (self.figNr,self.title))
        self.figure.insertLegend(Qwt.QwtLegend(), Qwt.QwtPlot.BottomLegend)

        self.figure.setAxisTitle(Qwt.QwtPlot.xBottom, "Time")
        self.figure.setAxisTitle(Qwt.QwtPlot.yLeft, self.ylabel)
        self.axis1=Qwt.QwtPlot.yLeft
        if len(self.alternate)>0:
            self.figure.enableAxis(Qwt.QwtPlot.yRight)
            self.figure.setAxisTitle(Qwt.QwtPlot.yRight, self.ylabel2)
            self.axis2=Qwt.QwtPlot.yRight

        if self.spec.logscale:
            self.figure.setAxisScaleEngine(Qwt.QwtPlot.yLeft,
                                           Qwt.QwtLog10ScaleEngine())
            if len(self.alternate)>0:
                self.figure.setAxisScaleEngine(Qwt.QwtPlot.yRight,
                                               Qwt.QwtLog10ScaleEngine())

        mY = Qwt.QwtPlotMarker()
        mY.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
        mY.setLineStyle(Qwt.QwtPlotMarker.HLine)
        mY.setYValue(0.0)
        mY.attach(self.figure)

        self.figure.resize(500,300)
        self.figure.show()

##        self.figure=plt.figure(self.figNr)
##        self.figure.clear()
##        # this is black magic that makes the legend work with two axes
##        if self.hasSubplotHost:
##            self.axis1=SubplotHost(self.figure,111)
##            self.figure.add_subplot(self.axis1)
##        else:
##            self.axis1=self.figure.add_subplot(111)
##        self.axis1.set_xlabel("Time")
##        self.axis1.set_ylabel(self.ylabel)
##        if self.spec.start or self.spec.end:
##            self.axis1.set_xbound(lower=self.spec.start,upper=self.spec.end)

##        if len(self.alternate)>0:
##            self.axis2=self.axis1.twinx()
##            self.axis2.set_ylabel(self.ylabel2)

##        try:
##            if self.spec.logscale:
##                self.axis1.set_yscale("log")
##                if self.axis2:
##                    self.axis2.set_yscale("log")
##        except AttributeError:
##            pass

    def doReplot(self):
        """Replot the whole data"""

        self.figure.replot()

##        if self.hasSubplotHost:
##            l=self.axis1.legend(fancybox=True)
##        else:
##            l=plt.legend(fancybox=True)
##        #         l.get_frame().set_fill(False)
##        if l:
##            l.get_frame().set_alpha(0.7)
##            l.get_texts()[0].set_size(10)
##        plt.suptitle(self.title)
##        plt.draw()

    def actualSetTitle(self,title):
        """Sets the title"""

        self.title=title

    def setYLabel(self,title):
        """Sets the label on the first Y-Axis"""

        self.ylabel=title

    def setYLabel2(self,title):
        """Sets the label on the second Y-Axis"""

        self.ylabel2=title

    def doHardcopy(self,filename,form,termOpts=None):
        """Write the contents of the plot to disk
        :param filename: Name of the file without type extension
        :param form: String describing the format"""

        Qt.QPixmap.grabWidget(self.figure).save(filename+"."+form.lower(),form)

# Should work with Python3 and Python2
