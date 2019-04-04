'''
   Version: Apache License  Version 2.0
 
   The contents of this file are subject to the Apache License Version 2.0 ; 
   you may not use this file except in
   compliance with the License. You may obtain a copy of the License at
   http://www.apache.org/licenses/
 
   Software distributed under the License is distributed on an "AS IS"
   basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
   License for the specific language governing rights and limitations
   under the License.
 
   The Original Code is ABI Comfort Simulator
 
   The Initial Developer of the Original Code is University of Auckland,
   Auckland, New Zealand.
   Copyright (C) 2007-2018 by the University of Auckland.
   All Rights Reserved.
 
   Contributor(s): Jagir R. Hussan
 
   Alternatively, the contents of this file may be used under the terms of
   either the GNU General Public License Version 2 or later (the "GPL"), or
   the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
   in which case the provisions of the GPL or the LGPL are applicable instead
   of those above. If you wish to allow use of your version of this file only
   under the terms of either the GPL or the LGPL, and not to allow others to
   use your version of this file under the terms of the MPL, indicate your
   decision by deleting the provisions above and replace them with the notice
   and other provisions required by the GPL or the LGPL. If you do not delete
   the provisions above, a recipient may use your version of this file under
   the terms of any one of the MPL, the GPL or the LGPL.
 
  "2019"
 '''
from __future__ import print_function, unicode_literals
import sip
#Ensure we use pyqt api 2 and consistency across python 2 and 3
API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)


import logging
from userinterface.RadiationFluxWizard import RadiationDefinitionWidget
from userinterface.ClothingWizard import ClothingDefinitionWidget
from support.client import SimulationRemoteProcessManager, ListServerTasks
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtGui import QColor
from zincwidgets.sceneviewerwidget import SceneviewerWidget
from opencmiss.zinc.context import Context
import pyqtgraph as pg
import numpy as np
import sys,os
import json
import pickle
import traceback
import tempfile
from userinterface.ActivityWizard import ActivityDefinitionWidget
from bodymodels.LoadOBJHumanModel import HumanModel
from support.ZincGraphicsElements import GenerateZincGraphicsElements,\
    createZincTitleBar
from support.Simulations import SimulationProcessManager, Simulator
from copy import deepcopy
from PyQt5.Qt import QApplication, QTimer, QColorDialog, QStyle, QMessageBox,\
    qApp, QFileDialog

from CacheManagement import WorkspaceCache


try:
    _encoding = QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)

def tr(msg):
    return _translate("MainWindow", msg, None)

dir_path = os.path.dirname(os.path.realpath(sys.argv[0]))
if not hasattr(sys, 'frozen'): #For py2exe
    dir_path = os.path.join(dir_path,"..")

   
meshUifilepath = os.path.join(dir_path,'./uifiles/personalization.ui')                                   
Ui_meshWidget, mhQtBaseClass = uic.loadUiType(meshUifilepath)
class LoadMeshWidget(QtWidgets.QDialog, Ui_meshWidget):
    meshSelected = QtCore.pyqtSignal(object)
    
    def __init__(self,title="Load target avatar"):
        QtWidgets.QDialog.__init__(self)
        Ui_meshWidget.__init__(self)
        self.setupUi(self)
        self.setWindowTitle(tr(title))
        self.loadMesh.clicked.connect(self.meshloaded)
        def canceled():
            self.close()
        self.cancelSelect.clicked.connect(canceled)
        self.selectFile.clicked.connect(self.meshFileSelected)

    def meshloaded(self):
        meshfile = str(self.meshFileName.text()).strip()
        if len(meshfile)>0:
            result = dict()
            result['file'] = meshfile
            result['age'] = self.age.value()
            result['height'] = self.height.value()
            result['weight'] = self.weight.value()
            result['CI'] = self.cardiacIndex.value()
            result['Rage'] = self.cardiacAgingRatio.value()
            result['Metb_sexratio'] = self.Metb_sexratio.value()
            result['male'] = self.maleButton.isChecked()
            self.meshSelected.emit(result)
            self.close()
        else:
            QtWidgets.QMessageBox.critical(None, "Missing data", "No mesh file selected")
    
    def meshFileSelected(self):
        direc = WorkspaceCache.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QFileDialog.getOpenFileName(None, tr('Load Mesh OBJ file'),direc,"OBJ (*.obj)")
        if not filename is None:
            self.meshFileName.setText(filename[0])


workspaceUifilepath = os.path.join(dir_path,'./uifiles/workspace.ui')                                   
Ui_workspaceWidget, wsQtBaseClass = uic.loadUiType(workspaceUifilepath)
class WorkspaceWidget(QtWidgets.QDialog, Ui_workspaceWidget):
    diskSpaceSelected = QtCore.pyqtSignal(str)
    def __init__(self):
        QtWidgets.QDialog.__init__(self)
        Ui_workspaceWidget.__init__(self)
        self.setupUi(self)
        settings = QtCore.QSettings("ABIComfortSimulator","workspaces")
        numWorkSpaces = settings.beginReadArray("CacheLocations")
        listOfWorkSpaces = []
        for i in range(numWorkSpaces):
            settings.setArrayIndex(i)
            listOfWorkSpaces.append(str(settings.value("directory")))
        settings.endArray()
    
        self.lastWorkSpace = settings.value("LastCacheLocation")
        if self.lastWorkSpace is None:
            self.lastWorkSpace = ''
        
        self.workspace.clear()
        for ws in listOfWorkSpaces:
            self.workspace.addItem(ws)
        if not self.lastWorkSpace in listOfWorkSpaces and self.lastWorkSpace != '':
            self.workspace.addItem(self.lastWorkSpace)
        if self.lastWorkSpace != '':
            index = self.workspace.findText(self.lastWorkSpace)
            if index != -1: 
                self.workspace.setCurrentIndex(index)
        self.browse.clicked.connect(self.allowSelection)
        self.launch.clicked.connect(self.launchWorkspace)
        self.cancel.clicked.connect(self.handleCancel)
        
        
    #Handle keypress event
    def keyPressEvent(self,evt):
        if evt.key() == QtCore.Qt.Key_Enter or  evt.key() == QtCore.Qt.Key_Return:
            self.launchWorkspace()
            
    def handleCancel(self):
        self.done(0)
            
    def launchWorkspace(self):
        diskCacheLocation = str(self.workspace.currentText())
        if len(diskCacheLocation.strip()) > 0:
            AllItems = [self.workspace.itemText(i) for i in range(self.workspace.count())]
            settings = QtCore.QSettings("ABIComfortSimulator","workspaces")
            settings.beginWriteArray("CacheLocations")
            for i,itm in enumerate(AllItems):
                if len(str(itm).strip()) > 0:
                    settings.setArrayIndex(i)
                    settings.setValue("directory",str(itm))
            settings.endArray()
            settings.setValue("LastCacheLocation",diskCacheLocation)
            self.diskSpaceSelected.emit(diskCacheLocation)
        self.done(0)    
        
            
    def allowSelection(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(None,"Select cache location",self.lastWorkSpace)
        if directory is None or str(directory) == '':     
            return
        index = self.workspace.findText(str(directory))
        if index == -1: 
            self.workspace.addItem(str(directory))
        index = self.workspace.findText(str(directory))
        self.workspace.setCurrentIndex(index)
        self.workspace.setFocus()


prefUifilepath = os.path.join(dir_path,'./uifiles/preferences.ui')                                   
Ui_prefWidget, pfQtBaseClass = uic.loadUiType(prefUifilepath)
class PreferencesWidget(QtWidgets.QDialog, Ui_prefWidget):
    serverPreferencesChanged = pyqtSignal()
    def __init__(self,title="Set preferences"):
        QtWidgets.QDialog.__init__(self)
        Ui_prefWidget.__init__(self)
        self.setupUi(self)
        self.setWindowTitle(tr(title))
        self.setPreferences.clicked.connect(self.updatePreferences)
        server = WorkspaceCache.cache.get('useServer')
        self.serverDataBox.setChecked(server)
        if server:
            self.serveruri.setText(WorkspaceCache.cache.get('serveruri'))
            self.serverport.setText(WorkspaceCache.cache.get('serverport'))
        self.timeoutInterval.setValue(WorkspaceCache.cache.get('animationinterval',default=100))
        self.numberOfTimeSamples.setValue(WorkspaceCache.cache.get('numberofsubsteps',default=100))
        
    def updatePreferences(self):
        changed = WorkspaceCache.cache.get('useServer')!= self.serverDataBox.isChecked()
        WorkspaceCache.cache.set('useServer',self.serverDataBox.isChecked())
        WorkspaceCache.cache.set('serveruri',self.serveruri.text())
        WorkspaceCache.cache.set('serverport',self.serverport.text())
        WorkspaceCache.cache.set('animationinterval',self.timeoutInterval.value())
        WorkspaceCache.cache.set('numberofsubsteps',self.numberOfTimeSamples.value())

        if changed:
            self.serverPreferencesChanged.emit()
        self.close()


class ProjectMetaDataDialog(QtWidgets.QDialog):
    metaDataUpdated = pyqtSignal(str)
    
    def __init__(self,parent=None):
        super(ProjectMetaDataDialog,self).__init__(parent)
        self.setModal(True)
        self.setFixedWidth(600)
        self.setFixedHeight(450)
        self.setWindowTitle(tr("Project Metadata"))

        layout = QtWidgets.QVBoxLayout(self)
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addItem(QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.agreeButton = QtWidgets.QPushButton(self)
        self.agreeButton.setText(tr("Ok"))
        hlayout.addWidget(self.agreeButton)
        hlayout.setStretch(0,10)
        
        self.textWidgetC = QtWidgets.QTextEdit()
        layout.addWidget(self.textWidgetC)
        layout.addLayout(hlayout)
        layout.setStretch(0,10)
        self.agreeButton.clicked.connect(self.updateMetaData)
        
    def setMetaData(self,mdata):
        self.textWidgetC.setPlainText(mdata)
        
    def updateMetaData(self):
        mdata = self.textWidgetC.toPlainText()
        self.metaDataUpdated.emit(mdata)
        self.close()
        
class AboutDialog(QtWidgets.QDialog):
    credits = '''<h1>ABI Comfort Simulator</h1>
<p>Version <span style="color: #ff0000;">1.0 </span></p>
<h3>Contributor:</h3>
<ul style="list-style-type: circle;">
<li style="padding-left: 30px;">Dr. Jagir R. Hussan, Auckland Bioengineering Institute, University of Auckland, New Zealand.</li>
</ul>
<h3>Credits:</h3>
<ul style="list-style-type: circle;">
<li style="padding-left: 30px;">Prof. Peter J. Hunter, Auckland Bioengineering Institute, University of Auckland, New Zealand.</li>
<li style="padding-left: 30px;">Mr. Alan Wu, Auckland Bioengineering Institute, University of Auckland, New Zealand.</li>
<li style="padding-left: 30px;">Dr. Richard Christie, Auckland Bioengineering Institute, University of Auckland, New Zealand.</li>
</ul>
<h3>Funding:</h3>
<ul style="list-style-type: circle;">
<li style="padding-left: 30px;">The Aotearoa Foundation, New Zealand.</li>
</ul>
<p><strong>Permanent Location:</strong> https://github.com/ABI-Software/ABICS</p>
'''
    
    
    def __init__(self,parent=None):
        super(AboutDialog,self).__init__(parent)
        self.setModal(True)
        self.setFixedWidth(600)
        self.setFixedHeight(450)
        self.setWindowTitle(_translate("AboutDialog","About",None))
        layout = QtWidgets.QVBoxLayout(self)
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addItem(QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        self.agreeButton = QtWidgets.QPushButton(self)
        self.agreeButton.setText(_translate("AboutDialog","Ok",None))
        hlayout.addWidget(self.agreeButton)
        hlayout.setStretch(0,10)
        
        textWidgetC = QtWidgets.QTextBrowser()
        textWidgetC.setHtml(_translate("AboutDialog",self.credits,None))
        layout.addWidget(textWidgetC)
        layout.addLayout(hlayout)
        layout.setStretch(0,10)
        self.agreeButton.clicked.connect(self.close)



uiFile = os.path.join(dir_path,"./uifiles/simulationWindow.ui")

form,base = uic.loadUiType(uiFile)

class SimulationMainWindow(base, form):
    windowReady = pyqtSignal()
    currentSimulationData = None
    currentMeshData = None
    projectMetaData = ''
    anatomyKeys = ['Head','Chest','Back','Pelvis','L-shoulder','R-shoulder','L-arm','R-arm','L-hand','R-hand','L-thigh','R-thigh','L-leg','R-leg','L-foot','R-foot']
    def __init__(self,title='ABI comfort simulator',parent=None):
        super(base,self).__init__(parent)
        self.zincContext = Context(str('ClothingModel'))
        #Handle to all timeIndicators
        self.timeIndicators = []
        self.playing = False
        self.currentTime = 0
        self.maxTime = 0
        self.timeoutInMilliSeconds = 100
        self.computeUsingProjection = True
        self.currentMeshFile = None
        self.activities = dict()
        self.humanParam = None
        self.numberOfSubSteps = 30 #Number of samples per duration
        self.debugMode = False #If true simulation thread is run serially
        #Setup colors
        graphColors = [7,8,9,10,11,12,3] #Based on Qt.GlobalColor
        #Create color objects
        self.graphColors = [QColor(QtCore.Qt.GlobalColor(x)) for x in graphColors]        
        #Setup the ui
        self.setupUi(self)
        self.actionOpen_Mesh.setShortcut(tr("Ctrl+M"))
        #using maximum size for each child so that they get equal spacing
        self.splitter.setSizes([16777215,16777215])
        self.tsplitter.setSizes([16777215,16777215])
        
        self.simulationProgressBar.hide()        
        
        #Zinc viewer setup
        self.mvLayout = QtWidgets.QVBoxLayout(self.modelView)
        self.mvLayout.setSpacing(0)
        self.mvLayout.setContentsMargins(0,0,0,0)
        self.mvLayout.setObjectName("mvLayout")
        self.meshWindow = SceneviewerWidget(self.modelView)
        self.meshWindow.setContext(self.zincContext)
        #Add child widget to display Field information
        self.mvLayout.addWidget(self.meshWindow)
        #Set icons
        self.playPause.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_MediaPlay')))
        
        #load default options
        self._loadDefaults()
        #Graphs
        self.createTemperaturePlots()
        self.createComfortLevelPlot()
        self.createActivitySignalPlots()
        #Create timer
        self.animationTimer = QTimer()
        #Established signals and slot maps
        self._setConnections()
        #Handle internationalization 
        self.retranslateUi(self)
        self.resetMeshScaling.setEnabled(False)
        self.projectMetaDataDialog = ProjectMetaDataDialog()
        def updateProjectMetadata(mdata):
            self.projectMetaData = mdata
            
        self.projectMetaDataDialog.metaDataUpdated.connect(updateProjectMetadata)
        self.setWindowTitle(tr(title))
        self.menuRecent_projects.hide()
        self.windowReady.emit()
        
    def _setConnections(self):
        #self.hideShowControls.clicked.connect(self._toggleControlView)
        self.resetMeshScaling.clicked.connect(self.meshWindow.viewAll)
        self.timeSlider.valueChanged.connect(self.timeChanged)
        self.playPause.clicked.connect(self.playPauseToggle)
        self.animationTimer.timeout.connect(self.incrementTimeSlider)
        self.meshWindow.graphicsInitialized.connect(self.zincInitialized)
        #Plot Color controls
        self.plotColor.clicked.connect(self.changeBodyPlotColor)
        self.meanSkinTemperatureColor.clicked.connect(self.changeMeanSkinTemperatureColor)
        self.meanCoreTemperatureColor.clicked.connect(self.changeMeanCoreTemperatureColor)
        self.rectalTemperatureColor.clicked.connect(self.changeRectalTemperatureColor)
        self.meanThermalResistanceColor.clicked.connect(self.changeMeanThermalResistanceColor)
        self.meanEvaporativeResistanceColor.clicked.connect(self.changeMeanEvaporativeResistanceColor)
        self.addBodyPlot.clicked.connect(self.currentBodySegmentChanged)
        self.pmvColor.clicked.connect(self.changePMVComfortFactorColor)
        self.ppdColor.clicked.connect(self.changePPDComfortFactorColor)
        
        #Combox box signals
        self.bodySegment.currentIndexChanged.connect(self.currentBodySegmentChanged)
        self.layerBox.currentIndexChanged.connect(self.currentBodySegmentChanged) 
        #Radio buttons
        self.showSkinTemperature.toggled.connect(self.showSkinTemperature_clicked)
        self.showCoreTemperature.toggled.connect(self.showCoreTemperature_clicked)
        self.showSkinWettedness.toggled.connect(self.showSkinWettedness_clicked)
        self.showThermalResistance.toggled.connect(self.showThermalResistance_clicked)
        self.showEvaporativeResistance.toggled.connect(self.showEvaporativeResistance_clicked)
        #Checkboxes
        self.meanSkinTemperature.stateChanged.connect(self.meanSkinTemperature_toggled)
        self.meanCoreTemperature.stateChanged.connect(self.meanCoreTemperature_toggled)
        self.rectalTemperature.stateChanged.connect(self.rectalTemperature_toggled)
        self.meanThermalResistance.stateChanged.connect(self.meanThermalResistance_toggled)
        self.meanEvaporativeResistance.stateChanged.connect(self.meanEvaporativeResistance_toggled)
        self.pmvVisible.stateChanged.connect(self.comfortLevelPMV_toggled)
        self.ppdVisible.stateChanged.connect(self.comfortLevelPPD_toggled)
                
        #Menu connections
        self.actionNew_project.triggered.connect(self.createNewProject)
        self.actionSave_project.triggered.connect(self.saveProject)
        self.actionOpen_project.triggered.connect(self.openProject)
        self.actionExit.triggered.connect(self.closeWindow)
        self.actionOpen_Activity.triggered.connect(self.showActivity)
        self.actionCreate_New_Activity.triggered.connect(self.showActivityWizard)
        self.actionEdit_Activity.triggered.connect(self.showEditActivityWizard)
        self.actionOpen_Mesh.triggered.connect(self.loadMesh)
        self.actionStart.triggered.connect(self.startSimulation)
        self.actionPause.triggered.connect(self.pauseSimulation)
        self.actionStop.triggered.connect(self.stopSimulation)
        self.actionSubmit_to_Server.triggered.connect(self.startSimulation)
        self.actionProject_To_Standard_Model.triggered.connect(self.toggleComputeUsingProjection)
        self.actionQuery_Server.triggered.connect(self.loadSimulationResults)
        self.actionSave_simulation.triggered.connect(self.saveSimulationData)
        
        self.actionCreate_New_Radiation_Profile.triggered.connect(self.showRadiationWizard)        
        self.actionCreate_New_Fabric_Profile.triggered.connect(self.showClothingWizard)
        self.actionEdit_Fabric_Profile.triggered.connect(self.showEditClothingWizard)
        self.actionLoad_simulation.triggered.connect(self.loadSimulationResultsAskFile)
        self.actionAbout.triggered.connect(self.showAbout)
        self.actionPreferences.triggered.connect(self.showPreferences)
        self.actionEdit_Project_Metadata.triggered.connect(self.editProjectMetaData)


    def closeWindow(self):
        QApplication.instance().closeAllWindows

    def reconfigure(self,diskCache=None):
        '''
        Reconfigure based on workspace settings
        '''
        if diskCache is not None:
            WorkspaceCache.cache = diskCache
        self.computeUsingProjection = WorkspaceCache.cache.get('computeUsingProjection',default=True)
        self.actionProject_To_Standard_Model.setChecked(self.computeUsingProjection)
        
        self.debugMode = WorkspaceCache.cache.get("debugMode",default=False)
        useServer = WorkspaceCache.cache.get('useServer')
        if useServer is None:
            WorkspaceCache.cache.set('useServer',False)
            useServer = False
            
        self.numberOfSubSteps = WorkspaceCache.cache.get('numberofsubsteps',default=30)
        self.computeUsingProjection = WorkspaceCache.cache.get('computeUsingProjection',default=True)
        self.actionProject_To_Standard_Model.setChecked(self.computeUsingProjection)
        self.actionQuery_Server.setVisible(useServer)
        self.actionSubmit_to_Server.setVisible(useServer)
        self.actionStart.setVisible(not useServer)
        self.actionPause.setVisible(not useServer)
        self.actionStop.setVisible(not useServer)
        self.updateRecentFiles()
        
    def playPauseToggle(self):
        if self.playing:
            self.animationTimer.stop()
            self.playPause.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_MediaPlay')))
        else:
            self.timeoutInMilliSeconds = WorkspaceCache.cache.get('animationinterval',default=100)            
            self.animationTimer.start(self.timeoutInMilliSeconds)            
            self.playPause.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_MediaPause')))
        self.playing = not self.playing

    def zincInitialized(self):
        self.meshWindow.viewAll()
        if not hasattr(self, 'titleBar'):
            self.titleGraphics, self.titleBar = createZincTitleBar(self.zincContext)        

    def setZincTitleBarString(self,label):
        if not hasattr(self, 'titleBar'):
            self.titleGraphics, self.titleBar = createZincTitleBar(self.zincContext)               
        self.titleBar.setLabelText(1,str(label))
        
    def incrementTimeSlider(self):
        self.timeSlider.setValue((self.timeSlider.value() + 1)%self.maxTime)

    def timeChanged(self,value):
        self.currentTime = value
        for ind in self.timeIndicators:
            ind.setValue(value)
        try:
            self.zincGraphics.setTime(int(value*self.simulationTimeConversionFactor))
        except:
            pass

        
    def changeBodyPlotColor(self):
        color = QColorDialog.getColor(self.plotColor.palette().color(1))
        if color.isValid():
            anatomy = self.bodySegment.currentText()
            layer   = self.layerBox.currentText()
            self.bodyTemperaturePlotHandles['%s_%s'%(anatomy,layer)].setPen(pg.mkPen(color,width=2, cosmetic=True))
            qss = "background-color: %s" % color.name()
            self.plotColor.setStyleSheet(qss)

    def changePPDComfortFactorColor(self):
        color = QColorDialog.getColor(self.ppdColor.palette().color(1))
        if color.isValid():
            self.ppdPlotItemHandle.setPen(pg.mkPen(color,width=2, cosmetic=True))
            self.comfortLevelsPlotHandle.getAxis('right').setPen(pg.mkPen(color,width=2, cosmetic=True))            
            qss = "background-color: %s" % color.name()
            self.ppdColor.setStyleSheet(qss)

    def changePMVComfortFactorColor(self):
        color = QColorDialog.getColor(self.pmvColor.palette().color(1))
        if color.isValid():
            self.pmvPlotItemHandle.setPen(pg.mkPen(color,width=2, cosmetic=True))
            self.comfortLevelsPlotHandle.getAxis('left').setPen(pg.mkPen(color,width=2, cosmetic=True))
            qss = "background-color: %s" % color.name()
            self.pmvColor.setStyleSheet(qss)        

    def showSkinTemperature_clicked(self,enabled):
        if enabled:
            self.zincGraphics.setDataField('Tskin')
            self.setZincTitleBarString(tr("Skin Temperature"))
            self.meshWindow.viewAll()        

    def showCoreTemperature_clicked(self,enabled):
        if enabled:
            self.zincGraphics.setDataField('Tcore')
            self.setZincTitleBarString(tr("Core Temperature"))
            self.meshWindow.viewAll()  
            
    def showSkinWettedness_clicked(self,enabled):
        if enabled:
            self.zincGraphics.setDataField('SkinWettedness') 
            self.setZincTitleBarString(tr("Skin Wettedness")) 
            self.meshWindow.viewAll()
            
    def showThermalResistance_clicked(self,enabled):
        if enabled:
            self.zincGraphics.setDataField('ThermalResistance')  
            self.setZincTitleBarString(tr("Effective Thermal Resistance"))
            self.meshWindow.viewAll()
            
    def showEvaporativeResistance_clicked(self,enabled):
        if enabled:
            self.zincGraphics.setDataField('EvaporativeResistance')  
            self.setZincTitleBarString(tr("Effective Evaporative Resistance"))
            self.meshWindow.viewAll()
            
    def meanSkinTemperature_toggled(self):
        if self.meanSkinTemperature.isChecked():
            self.bodyTemperaturePlotVisible['MeanSkin'] = True
            self.bodyTemperaturePlotHandles['MeanSkin'].show()
            self.alltemperaturesPlotHandle.show()            
        else:
            self.bodyTemperaturePlotHandles['MeanSkin'].hide()
            self.bodyTemperaturePlotVisible['MeanSkin'] = False
            
    def meanCoreTemperature_toggled(self):
        if self.meanCoreTemperature.isChecked():
            self.bodyTemperaturePlotVisible['MeanCore'] = True
            self.bodyTemperaturePlotHandles['MeanCore'].show()
            self.alltemperaturesPlotHandle.show()            
        else:
            self.bodyTemperaturePlotHandles['MeanCore'].hide()
            self.bodyTemperaturePlotVisible['MeanCore'] = False

    def rectalTemperature_toggled(self):
        if self.rectalTemperature.isChecked():
            self.bodyTemperaturePlotVisible['Rectal'] = True
            self.bodyTemperaturePlotHandles['Rectal'].show()
            self.alltemperaturesPlotHandle.show()
        else:
            self.bodyTemperaturePlotHandles['Rectal'].hide()
            self.bodyTemperaturePlotVisible['Rectal'] = False
    
    def meanThermalResistance_toggled(self):
        if self.meanThermalResistance.isChecked():
            self.meanThermalResistancePlotItemHandle.show()
            self.meanResistancePlotHandle.show()
            self.meanResistancePlotHandle.showAxis('left')
        else:
            self.meanThermalResistancePlotItemHandle.hide()
            self.meanResistancePlotHandle.hideAxis('left')
            if not self.meanEvaporativeResistance.isChecked():
                self.meanResistancePlotHandle.hide()
        self.meanResistancePlotHandle.informViewBoundsChanged()
            
    def meanEvaporativeResistance_toggled(self):
        if self.meanEvaporativeResistance.isChecked():
            self.meanEvaporativeResistancePlotItemHandle.show()
            self.meanResistancePlotHandle.show()
            self.meanResistancePlotHandle.showAxis('right')
        else:
            self.meanEvaporativeResistancePlotItemHandle.hide()
            self.meanResistancePlotHandle.hideAxis('right')
            if not self.meanThermalResistance.isChecked():
                self.meanResistancePlotHandle.hide()
        self.meanResistancePlotHandle.informViewBoundsChanged()

    def comfortLevelPPD_toggled(self):
        if self.ppdVisible.isChecked():
            self.ppdPlotItemHandle.show()
            self.comfortLevelsPlotHandle.show()
            self.comfortLevelsPlotHandle.showAxis('right')
        else:
            self.ppdPlotItemHandle.hide()
            self.comfortLevelsPlotHandle.hideAxis('right')
            if not self.pmvVisible.isChecked():
                self.comfortLevelsPlotHandle.hide()            
        self.comfortLevelsPlotHandle.informViewBoundsChanged()

    def comfortLevelPMV_toggled(self):
        if self.pmvVisible.isChecked():
            self.pmvPlotItemHandle.show()
            self.comfortLevelsPlotHandle.show()
            self.comfortLevelsPlotHandle.showAxis('left')
        else:
            self.pmvPlotItemHandle.hide()
            self.comfortLevelsPlotHandle.hideAxis('left')
            if not self.ppdVisible.isChecked():
                self.comfortLevelsPlotHandle.hide()
        self.comfortLevelsPlotHandle.informViewBoundsChanged()
        
        
    def _loadDefaults(self):
        self.actionStop.setEnabled(True)
        
        for i, an in enumerate(self.anatomyKeys):
            self.bodySegment.addItem(tr(an),i)
        self.layerBox.addItem(tr('Skin'),0)
        self.layerBox.addItem(tr('Core'),1)
        col = QColor(QtCore.Qt.white)
        qss = "background-color: %s" % col.name()
        self.plotColor.setStyleSheet(qss)
        self.addBodyPlot.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogApplyButton')))

        col = QColor(QtCore.Qt.red)
        qss = "background-color: %s" % col.name()
        self.pmvColor.setStyleSheet(qss)

        col = QColor(QtCore.Qt.green)
        qss = "background-color: %s" % col.name()
        self.ppdColor.setStyleSheet(qss)

    def showActivityWizard(self):
        if hasattr(self, 'aw'):
            del self.aw
        self.aw = ActivityDefinitionWidget()
        self.aw.setCache(WorkspaceCache.cache)
        self.aw.dataSaved.connect(self.loadActivityFromFile)
        self.aw.show()
    
    def showEditActivityWizard(self):
        self.aw = ActivityDefinitionWidget()
        self.aw.setCache(WorkspaceCache.cache)
        try:
            if hasattr(self, 'currentActivityFileName'):
                self.aw.loadActivityFromFile(self.currentActivityFileName)
            elif hasattr(self, 'activities'):
                self.aw.loadActivityFromDict(self.activities)
            else:
                raise ValueError('')
            self.aw.dataSaved.connect(self.loadActivityFromFile)
            self.aw.show()
        except:
            QMessageBox.warning(None, tr('Missing activity description', 'No activity file was loaded to be edited! Try Create New Activity Profile'))
            del self.aw

    def showRadiationWizard(self):
        if hasattr(self, 'radiationWizard'):
            del self.radiationWizard
        self.radiationWizard = RadiationDefinitionWidget()
        self.radiationWizard.setCache(WorkspaceCache.cache)
        #in case mesh is available, send it
        if self.currentMeshFile is not None:
            self.radiationWizard._loadMesh(self.currentMeshFile)
        elif self.currentMeshData is not None:
            self.radiationWizard._loadMeshData(self.currentMeshData)
        self.radiationWizard.show()       

    def showClothingWizard(self):
        if hasattr(self, 'clothingWizard'):
            del self.clothingWizard
        self.clothingWizard = ClothingDefinitionWidget()
        self.clothingWizard.setCache(WorkspaceCache.cache)
        self.clothingWizard.show()
    
    def showEditClothingWizard(self):
        if hasattr(self, 'clothingWizard'):
            del self.radiationWizard        
        self.clothingWizard = ClothingDefinitionWidget()
        self.clothingWizard.setCache(WorkspaceCache.cache)      
        self.clothingWizard._loadClothingModel()
        self.clothingWizard.show() 
        
    def currentBodySegmentChanged(self,index):
        anatomy = self.bodySegment.currentText()
        layer   = self.layerBox.currentText()
        key = '%s_%s'%(anatomy,layer)
        if not self.bodyTemperaturePlotVisible[key]:
            self.addBodyPlot.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogCancelButton')))
            self.bodyTemperaturePlotHandles[key].show()
            self.bodyTemperaturePlotVisible[key] = True
        else:
            self.addBodyPlot.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogApplyButton')))
            self.bodyTemperaturePlotHandles[key].hide()
            self.bodyTemperaturePlotVisible[key] = False
        color = self.bodyTemperaturePlotHandles[key].opts['pen'].color()
        qss = "background-color: %s" % color.name()
        self.plotColor.setStyleSheet(qss)

    def changePlotColor(self,pitem,button):
        '''
        Called to change the color of the plotCurveItem and UI button
        '''
        color = QColorDialog.getColor(button.palette().color(1))
        if color.isValid():            
            pitem.setPen(pg.mkPen(color,width=2, cosmetic=True))
            qss = "background-color: %s" % color.name()
            button.setStyleSheet(qss)    
            
    def changeMeanSkinTemperatureColor(self):
        self.changePlotColor(self.bodyTemperaturePlotHandles['MeanSkin'],self.meanSkinTemperatureColor)
        
    def changeMeanCoreTemperatureColor(self):
        self.changePlotColor(self.bodyTemperaturePlotHandles['MeanCore'],self.meanCoreTemperatureColor)

    def changeRectalTemperatureColor(self):
        self.changePlotColor(self.bodyTemperaturePlotHandles['Rectal'],self.rectalTemperatureColor)
        
    def changeMeanThermalResistanceColor(self):
        self.changePlotColor(self.meanThermalResistancePlotItemHandle,self.meanThermalResistanceColor)
        
    def changeMeanEvaporativeResistanceColor(self):
        self.changePlotColor(self.meanEvaporativeResistancePlotItemHandle,self.changeMeanEvaporativeResistanceColor)

    def refreshActivityGraph(self):
        numActivities = len(self.activities)-1
        timeValues = np.zeros(numActivities+1)
        temps = np.zeros(numActivities+1)
        mets = np.zeros(numActivities+1)
        rh = np.zeros(numActivities+1)
        voa = np.zeros(numActivities+1)
        i = 0
        for act in self.activities.values():
            if isinstance(act,dict):
                timeValues[i+1] = act['duration']
                rh[i+1] = act['rh']
                temps[i+1] = act['Tab']
                voa[i+1] = act['velocityOfAir']
                mets[i+1] = act['metabolicActivity']
                i = i + 1
        
        self.numberOfSubSteps = max(self.numberOfSubSteps,int(100/numActivities))
        timeValues = np.r_[0,np.cumsum(timeValues)]*60.0 #Convert from minutes to seconds
        
        if numActivities > 0:
            temps[0] = temps[1]
            mets[0] = mets[1]
            voa[0] = voa[1]
            rh[0] = rh[1]

            self.temperaturePlotPCI.setData(timeValues,temps,stepMode=True)
            self.metabolicActivityPlotPCI.setData(timeValues,mets,stepMode=True)
            self.velocityOfAirPlotPCI.setData(timeValues,voa,stepMode=True)
            self.relativeHumidityPlotPCI.setData(timeValues,rh,stepMode=True)
            #set the maximum time value for the timeslider
            self.maxTime = int(timeValues[-1]) + 1 # 1 is added to help with modulo arithmatic used in time increments 
            self.timeSlider.setMaximum(timeValues[-1])

        for tv in self.timeIndicators:
            tv.setValue(self.currentTime)
            
        self.temperaturePlot.show()
        self.metabolicActivityPlot.show()
        self.velocityOfAirPlot.show()
        self.relativeHumidityPlot.show()            
    
    def createActivitySignalPlots(self):
        self.aspLayout = QtWidgets.QVBoxLayout(self.activitiesPlotWindow)
        self.aspLayout.setSpacing(0)
        self.aspLayout.setContentsMargins(0,0,0,0)
        self.aspLayout.setObjectName("aspLayout")
        
        pw = pg.GraphicsLayoutWidget()
        pw.setContentsMargins(0, 0, 0, 20)
        self.aspLayout.addWidget(pw)
        plt = pw.addPlot(0,0)
        #plt.enableAutoRange(False, False)
        plt.setTitle(tr("Activity/Environment"),bold=True,color='#ffffff') 
        #plt.hideAxis('left')
        plt.hideAxis('bottom')
        plt.setLabel('left','<font>T<sub>a</sub></font>',bold=True,color=self.graphColors[0].name())
        self.temperaturePlot = plt
        timeIndicator = pg.InfiniteLine(pos=(0))
        plt.addItem(timeIndicator)
        self.timeIndicators.append(timeIndicator)
        
        plt = pw.addPlot(1,0) 
        #plt.enableAutoRange(False, False)
        #plt.hideAxis('left')
        plt.hideAxis('bottom')
        plt.setLabel('left','<font>RH%</font>',bold=True,color=self.graphColors[3].name())
        self.relativeHumidityPlot = plt
        timeIndicator = pg.InfiniteLine(pos=(0))
        plt.addItem(timeIndicator)
        self.timeIndicators.append(timeIndicator)
        
        plt = pw.addPlot(2,0)
        #plt.enableAutoRange(False, False) 
        #plt.hideAxis('left')
        plt.hideAxis('bottom')
        plt.setLabel('left','<font>v<sub>a</sub></font>',bold=True,color=self.graphColors[4].name())
        self.velocityOfAirPlot = plt
        timeIndicator = pg.InfiniteLine(pos=(0))
        plt.addItem(timeIndicator)
        self.timeIndicators.append(timeIndicator)
        
        plt = pw.addPlot(3,0) 
        #plt.enableAutoRange(False, False)
        #plt.hideAxis('bottom')
        plt.setLabel('left','<font>Met</font>',bold=True,color=self.graphColors[1].name())
        plt.setLabel('bottom','<font>Time (s) </font>',bold=True,color='#ffffff')
        self.metabolicActivityPlot = plt
        timeIndicator = pg.InfiniteLine(pos=(0))
        plt.addItem(timeIndicator)
        self.timeIndicators.append(timeIndicator)
        
        citem = pg.PlotCurveItem()
        citem.setPen(pg.mkPen(self.graphColors[0],width=2, cosmetic=True))
        self.temperaturePlotPCI = citem
        self.temperaturePlot.addItem(citem)
    
        citem = pg.PlotCurveItem()
        citem.setPen(pg.mkPen(self.graphColors[1],width=2, cosmetic=True))
        self.metabolicActivityPlotPCI = citem
        self.metabolicActivityPlot.addItem(citem)

        citem = pg.PlotCurveItem()
        citem.setPen(pg.mkPen(self.graphColors[4],width=2, cosmetic=True))
        self.velocityOfAirPlotPCI = citem
        self.velocityOfAirPlot.addItem(citem)
    
        citem = pg.PlotCurveItem()
        citem.setPen(pg.mkPen(self.graphColors[3],width=2, cosmetic=True))
        self.relativeHumidityPlotPCI = citem
        self.relativeHumidityPlot.addItem(citem)
        
        
        self.temperaturePlot.hide()
        self.metabolicActivityPlot.hide()
        self.velocityOfAirPlot.hide()
        self.relativeHumidityPlot.hide()

    def createComfortLevelPlot(self):
        self.clLayout = QtWidgets.QVBoxLayout(self.comfortLevelPlot)
        self.clLayout.setSpacing(0)
        self.clLayout.setContentsMargins(0,0,0,0)
        self.clLayout.setObjectName("clLayout")
        
        pw = pg.GraphicsLayoutWidget()
        pw.setContentsMargins(0, 0, 0, 20)
        self.comfortLevelsGLW = pw
        self.clLayout.addWidget(pw)
        
        #Create a plot with secondary Axis
        plt = pw.addPlot(0,0)
        plt.clear()
        plt.setTitle(tr("Comfort Factors"),bold=True,color='#ffffff')
        plt.setLabel('bottom',tr('Time (s)'))#,units ='s')
        plt.setLabels(left='PMV')
        
        ## create a new ViewBox, link the right axis to its coordinate system
        p2 = pg.ViewBox()
        plt.showAxis('right')
        plt.scene().addItem(p2)
        plt.getAxis('right').linkToView(p2)
        p2.setXLink(plt)
        plt.getAxis('right').setLabel('PPD %')

        self.comfortLevelsPlotHandle = plt
        self.comfortLevelsViewHandle = p2
        self.updateComfortLevelsViews()
        plt.vb.sigResized.connect(self.updateComfortLevelsViews)

        col = QColor(QtCore.Qt.red)
        citem = pg.PlotCurveItem()
        citem.setPen(pg.mkPen(col,width=2, cosmetic=True))
        plt.addItem(citem)
        citem.hide()
        plt.getAxis('left').setPen(pg.mkPen(col,width=2, cosmetic=True))
        self.pmvPlotItemHandle = citem
        qss = "background-color: %s" % col.name()
        self.pmvColor.setStyleSheet(qss)

        col = QColor(QtCore.Qt.green)
        citem = pg.PlotCurveItem()
        citem.setPen(pg.mkPen(col,width=2, cosmetic=True))
        p2.addItem(citem)
        citem.hide()
        plt.getAxis('right').setPen(pg.mkPen(col,width=2, cosmetic=True))
        self.ppdPlotItemHandle = citem
        qss = "background-color: %s" % col.name()
        self.ppdColor.setStyleSheet(qss)

        #Add time indicator
        self.comfortLevelsTimeIndicator = pg.InfiniteLine(pos=(0))
        plt.addItem(self.comfortLevelsTimeIndicator)     
        self.timeIndicators.append(self.comfortLevelsTimeIndicator)
                
        self.comfortLevelsPlotHandle.hideAxis('left')
        self.comfortLevelsPlotHandle.hideAxis('right')
        self.comfortLevelsPlotHandle.hide()
        
    def createTemperaturePlots(self):
        self.tpLayout = QtWidgets.QVBoxLayout(self.temperaturePlotWindow)
        self.tpLayout.setSpacing(0)
        self.tpLayout.setContentsMargins(0,0,0,0)
        self.tpLayout.setObjectName("tpLayout")
        
        pw = pg.GraphicsLayoutWidget()
        pw.setContentsMargins(0, 0, 0, 20)
        self.temperatureGLW = pw
        self.tpLayout.addWidget(pw)
        
        plt = pw.addPlot(0,0)
        plt.clear()
        plt.setTitle(tr("Temperature"),bold=True,color='#ffffff')
        #plt.enableAutoRange(False, False)
        plt.setLabel('left','<font>C</font>')
        plt.setLabel('bottom',tr('Time (s)'))#,units ='s')
        
        i = 0
        self.bodyTemperaturePlotHandles = dict()
        self.bodyTemperaturePlotVisible = dict()
        for an in self.anatomyKeys:
            col = self.graphColors[int(i%7)] 
            citem = pg.PlotCurveItem()
            citem.setPen(pg.mkPen(col,width=2, cosmetic=True))
            plt.addItem(citem)
            citem.hide()
            i += 1
            self.bodyTemperaturePlotHandles['%s_Skin'%an] = citem
            self.bodyTemperaturePlotVisible['%s_Skin'%an] = False
            col = self.graphColors[int(i%7)] 
            citem = pg.PlotCurveItem()
            citem.setPen(pg.mkPen(col,width=2, cosmetic=True))
            plt.addItem(citem)
            citem.hide()
            self.bodyTemperaturePlotHandles['%s_Core'%an] = citem
            self.bodyTemperaturePlotVisible['%s_Core'%an] = False
            i += 1
            #Allow other operations
            qApp.processEvents()

        meanTemperatures = ['MeanSkin','MeanCore','Rectal']
        colors  = [QColor(QtCore.Qt.red),QColor(QtCore.Qt.blue),QColor(QtCore.Qt.green)]
        buttons = [self.meanSkinTemperatureColor,self.meanCoreTemperatureColor,self.rectalTemperatureColor]
        for i, an in enumerate(meanTemperatures):
            col = colors[i]
            citem = pg.PlotCurveItem()
            citem.setPen(pg.mkPen(col,width=2, cosmetic=True))
            plt.addItem(citem)
            citem.hide()
            self.bodyTemperaturePlotHandles[an] = citem
            self.bodyTemperaturePlotVisible[an] = False
            qss = "background-color: %s" % col.name()
            buttons[i].setStyleSheet(qss)
            #Allow other operations
            qApp.processEvents()
            
        #plt.setXRange(0,self.numTimePoints*self.timeScale,padding=self.timeScale)
        #ax = plt.getAxis('bottom')
        #ax.setTickSpacing(0.05,1)
        #Add time indicator
        self.temperatureTimeIndicator = pg.InfiniteLine(pos=(0))
        plt.addItem(self.temperatureTimeIndicator)  
        plt.enableAutoRange(True, False)
        self.alltemperaturesPlotHandle = plt  
        
        self.timeIndicators.append(self.temperatureTimeIndicator) 
        
        #Create a plot with secondary Axis
        plt = pw.addPlot(1,0)
        plt.clear()
        plt.setTitle(tr("Mean Resistances"),bold=True,color='#ffffff')
        plt.setLabel('bottom',tr('Time (s)'))#,units ='s')
        plt.setLabels(left='Thermal <br> <font>W/m<sup>2</sup>K</font>')
        
        ## create a new ViewBox, link the right axis to its coordinate system
        p2 = pg.ViewBox()
        plt.showAxis('right')
        plt.scene().addItem(p2)
        plt.getAxis('right').linkToView(p2)
        p2.setXLink(plt)
        plt.getAxis('right').setLabel('Evaporative <br> <font>Pa.m<sup>2</sup>/W</font>')

        self.meanResistancePlotHandle = plt
        self.meanResistanceViewHandle = p2
        self.updateResistanceViews()
        plt.vb.sigResized.connect(self.updateResistanceViews)

        col = QColor(QtCore.Qt.magenta)
        citem = pg.PlotCurveItem()
        citem.setPen(pg.mkPen(col,width=2, cosmetic=True))
        plt.addItem(citem)
        citem.hide()
        plt.getAxis('left').setPen(pg.mkPen(col,width=2,cosmetic=True))
        self.meanThermalResistancePlotItemHandle = citem
        qss = "background-color: %s" % col.name()
        self.meanThermalResistanceColor.setStyleSheet(qss)

        col = QColor(QtCore.Qt.yellow)
        citem = pg.PlotCurveItem()
        citem.setPen(pg.mkPen(col,width=2, cosmetic=True))
        p2.addItem(citem)
        citem.hide()
        plt.getAxis('right').setPen(pg.mkPen(col,width=2,cosmetic=True))
        self.meanEvaporativeResistancePlotItemHandle = citem
        qss = "background-color: %s" % col.name()
        self.meanEvaporativeResistanceColor.setStyleSheet(qss)

        #Add time indicator
        self.meanResistanceTimeIndicator = pg.InfiniteLine(pos=(0))
        plt.addItem(self.meanResistanceTimeIndicator)     
        self.timeIndicators.append(self.meanResistanceTimeIndicator)
                
        self.meanResistancePlotHandle.hideAxis('left')
        self.meanResistancePlotHandle.hideAxis('right')
        self.meanResistancePlotHandle.hide()
        self.alltemperaturesPlotHandle.hide()

    def updateResistanceViews(self):
        '''
        Resize resistance views such that the plot and the view are aligned
        '''
        self.meanResistanceViewHandle.setGeometry(self.meanResistancePlotHandle.vb.sceneBoundingRect())
        ## need to re-update linked axes since this was called
        ## incorrectly while views had different shapes.
        ## (probably this should be handled in ViewBox.resizeEvent)
        self.meanResistanceViewHandle.linkedViewChanged(self.meanResistancePlotHandle.vb, self.meanResistanceViewHandle.XAxis)

    def updateComfortLevelsViews(self):
        '''
        Resize comfort level views such that the plot and the view are aligned
        '''
        self.comfortLevelsViewHandle.setGeometry(self.comfortLevelsPlotHandle.vb.sceneBoundingRect())
        ## need to re-update linked axes since this was called
        ## incorrectly while views had different shapes.
        ## (probably this should be handled in ViewBox.resizeEvent)
        self.comfortLevelsViewHandle.linkedViewChanged(self.comfortLevelsPlotHandle.vb, self.comfortLevelsViewHandle.XAxis)

    def showActivity(self):
        direc = WorkspaceCache.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QFileDialog.getOpenFileName(None, tr('Load Activity file'),direc,"JSON (*.json)")
        if not filename is None:
            self.loadActivityFromFile(filename[0])
            WorkspaceCache.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))
        
    def loadActivityFromFile(self,filename):
        if not filename is None and len(filename.strip()) > 0:
            QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            with open(filename,'r') as ser:
                self.simulationProgressBar.show()
                self.simulationProgressBar.setValue(10.0)
                activities = json.load(ser)
                if hasattr(self, 'activities'):
                    self.activities.clear()
                else:
                    self.activities = dict()
                if 'activityname' in activities:
                    self.activities['activityname'] = activities['activityname']
                else:
                    self.activities['activityname'] = os.path.basename(filename)                    
                for activity in list(activities.values()):
                    #utf2str converts integers to string
                    if isinstance(activity,dict):
                        activity['id'] = int(activity['id'])
                        activity['definitionDirectory'] = os.path.dirname(filename)#Store directory name resolve relative file names
                        self.activities[activity['id']] = activity
                        
                self.simulationProgressBar.setValue(50.0)
                self.refreshActivityGraph()
                self.simulationProgressBar.setValue(100.0)
                self.simulationProgressBar.hide()
                self.currentActivityFileName = filename
        QApplication.restoreOverrideCursor()

    def showProgress(self,value,close=False):
        self.simulationProgressBar.setValue(value)
        self.simulationProgressBar.show()
        if close:
            self.simulationProgressBar.hide()
        qApp.processEvents()

    def clearMesh(self):
        try:
            defaultRegion = self.zincContext.getDefaultRegion()
            if hasattr(self, 'zincGraphics'):
                self.zincGraphics.destroyGraphicsElements()
            region = defaultRegion.getFirstChild()
            while region.isValid():
                tmp = region
                region = region.getNextSibling()
                defaultRegion.removeChild(tmp)
                self.setZincTitleBarString(tr("No Mesh Loaded"))
            self.currentMeshFile = None
            self.currentMeshData = None
            self.resetMeshScaling.setEnabled(False)
        except:
            logging.debug("Failed to clear mesh")
            
    def renderMesh(self):
        self.zincGraphics = GenerateZincGraphicsElements(self.zincContext,'manequin')
        self.zincGraphics.createGraphicsElements()          
        self.showProgress(0,True)
        
    def loadMesh(self):
        dlg = LoadMeshWidget()
        def meshLoaded(res):
            self.humanBodyParameters = res
            self.currentMeshFile = res['file']
            self.loadMeshFromFile(res['file'])
            
        dlg.meshSelected.connect(meshLoaded)
        dlg.show()
        self.loadMeshWidget = dlg
        
    def loadMeshFromFile(self,filename):
        if not filename is None and len(filename.strip()) > 0:
            QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                self.showProgress(0)
                self.humanParam = HumanModel(filename,2/3.0,True)
                #Create a copy that uses the same surfaceArea as the standard model
                #This is used for projectedCalculations
                self.humanParam2 = deepcopy(self.humanParam)
                self.humanParam2.totalSurfaceArea = self.humanParam2.basemodelSurfaceArea 
                gender = 'male'
                if not self.humanBodyParameters['male']:
                    gender = 'female'
                self.humanParam.personalizeParameters(gender,self.humanBodyParameters['height'],self.humanBodyParameters['weight'],\
                                                      self.humanBodyParameters['age'],\
                                                      CardiacIndex=self.humanBodyParameters['CI'],\
                                                      AgingCoeffientForBlood=self.humanBodyParameters['Rage'],\
                                                      SexBasedMetabolicRatio=self.humanBodyParameters['Metb_sexratio'])
                self.humanParam2.personalizeParameters(gender,self.humanBodyParameters['height'],self.humanBodyParameters['weight'],\
                                                      self.humanBodyParameters['age'],\
                                                      CardiacIndex=self.humanBodyParameters['CI'],\
                                                      AgingCoeffientForBlood=self.humanBodyParameters['Rage'],\
                                                      SexBasedMetabolicRatio=self.humanBodyParameters['Metb_sexratio'])
                
                self.showProgress(25)
                self.humanParam.generateMesh(self.zincContext,None) #Re-create with more time values when the simulation is completed
                self.showProgress(50)
                self.renderMesh()
                self.setZincTitleBarString("Skin Temperature")
                self.resetMeshScaling.setEnabled(True)
                self.meshWindow.viewAll()
            except:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, tr("Incorrect file"), tr("File %s is not a recognized mesh file" % filename))
                #Remove any elements created
                try:
                    self.clearMesh()
                except:
                    pass
                self.setZincTitleBarString(tr("No Mesh Loaded"))
                self.humanParam = None
                traceback.print_exc(file=sys.stdout)
        else:
            self.humanParam = None
        QApplication.restoreOverrideCursor()
            
    def toggleComputeUsingProjection(self):
        self.computeUsingProjection = self.actionProject_To_Standard_Model.isChecked()
        WorkspaceCache.cache.set('computeUsingProjection',self.computeUsingProjection)
        
    def editProjectMetaData(self):
        self.projectMetaDataDialog.setMetaData(self.projectMetaData)
        self.projectMetaDataDialog.show()

    def createNewProject(self):
        self.clearMesh()
        self.meanResistancePlotHandle.hide()
        self.meanResistanceViewHandle.hide()
        self.alltemperaturesPlotHandle.hide()
        self.pmvPlotItemHandle.hide()
        self.ppdPlotItemHandle.hide()
        self.comfortLevelsPlotHandle.hide()   
        self.temperaturePlot.hide()
        self.metabolicActivityPlot.hide()
        self.velocityOfAirPlot.hide()
        self.relativeHumidityPlot.hide()           
        self.currentTime = 0
        self.currentActivityFileName = None
        self.currentSimulationData = None
        self.currentMeshFile = None
        self.currentMeshData = None
        self.humanBodyParameters = None
        for tv in self.timeIndicators:
            tv.setValue(0)
        self.activities.clear()
        self.projectMetaData = ''
        self.editProjectMetaData()
        
    def saveProject(self):
        if self.currentMeshFile is not None or len(self.activities)>0:
            direc = WorkspaceCache.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
            filename = QFileDialog.getSaveFileName(None, tr('Save project file'),direc,"Pickle (*.pkl)")
            if not filename is None and len(filename[0].strip())>0:
                try:
                    if self.currentMeshFile is not None:
                        with open(self.currentMeshFile,'rb') as msh:
                            mshData = msh.read()
                    elif hasattr(self, 'currentMeshData'):
                        mshData = self.currentMeshData
                    else:
                        mshData = None
                        
                    with open(filename[0],'wb+') as ser:
                        pickle.dump([mshData,self.humanBodyParameters, self.currentSimulationData,\
                                      self.activities,self.computeUsingProjection, self.numberOfSubSteps,self.projectMetaData],ser)
                    QtWidgets.QMessageBox.information(None, "Success", "Project successfully saved")
                except:
                    traceback.print_exc(file=sys.stdout)
                    QtWidgets.QMessageBox.critical(None, "Failed", "Failed to save project")
        else:
            QtWidgets.QMessageBox.critical(None, "Failed", "No mesh or activity data is available!")
            
    
    def openProject(self):
        direc = WorkspaceCache.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QFileDialog.getOpenFileName(None, tr('Open project file'),direc,"Pickle (*.pkl)")
        self.openProjectFromFile(filename)
    
    def openProjectFromFile(self,filename):
        if not filename is None and len(filename[0].strip())>0:
            try:
                QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                with open(filename[0],'rb+') as ser:
                    try:
                        mshData, self.humanBodyParameters, self.currentSimulationData,\
                                self.activities,self.computeUsingProjection, \
                                self.numberOfSubSteps, self.projectMetaData = pickle.load(ser)
                    except UnicodeDecodeError:
                        QtWidgets.QMessageBox.critical(None,tr("Unsupported pickle format"),tr("The project was saved using python 2 and cannot be loaded in a simulator instance running on python 3"))
                        return

                tfile = tempfile.NamedTemporaryFile(suffix=".obj",delete=False)
                with open(tfile.name,'w') as ser:
                    ser.write(mshData)

                self.currentMeshData = mshData
                self.loadMeshFromFile(tfile.name)
                self.meshWindow.viewAll()
                self.refreshActivityGraph()
                if self.currentSimulationData is not None:
                    self.setZincTitleBarString("Skin Temperature")
                    self.showProgress(50)
                    self.renderSimulationData(self.currentSimulationData)     
                    self.meshWindow.viewAll()
                
                self.showProgress(0,close=True)
                QApplication.restoreOverrideCursor()
                QtWidgets.QMessageBox.information(None, "Success", "Project successfully loaded")
                tfile.close()
                os.remove(tfile.name)
                self.updateRecentFiles(filename[0])
            except:
                traceback.print_exc( file=sys.stdout)
                QApplication.restoreOverrideCursor()
                QtWidgets.QMessageBox.critical(None, "Failed", "Failed to load project")


    def updateRecentFiles(self,project=None):
        recentFiles = WorkspaceCache.cache.get('RECENTFILES',default=[])
        
        if project is not None:
            af = set(recentFiles)
            if project not in af:
                recentFiles.append(project)
            else:
                return
            if len(recentFiles)>10:
                recentFiles.pop(0)
            WorkspaceCache.cache.set('RECENTFILES',recentFiles)
        self.menuRecent_projects.hide()
        self.menuRecent_projects.clear()
        for i,v in enumerate(recentFiles):
            act = QtWidgets.QAction(self, visible=False,triggered=self.openRecentProjectFile)
            text = "&%d %s" % (i + 1, os.path.basename(v))
            act.setText(text)
            act.setData(v)
            self.menuRecent_projects.addAction(act)
        if len(recentFiles)>0:
            self.menuRecent_projects.show()
            

    def openRecentProjectFile(self):
        action = self.sender()
        self.openProjectFromFile([action.data()])

    def startSimulation(self):
        '''
        Start the simulation after checking if all the required data i.e. Activity, Human Object are defined
        Simulation is run using a separate object
        '''
        if len(self.activities) > 0 and not self.humanParam is None:
            
            if self.computeUsingProjection:
                result = QMessageBox.question(self,tr("Simulation Accuracy"),tr("You have chosen to simulate on a reduced 16 segment model which will not have much correspondence to the mesh. \nUse of this method is suggested only for initial setup and testing.\nContinue?"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if result == QMessageBox.No:
                    return
            else:
                result = QMessageBox.question(self,tr("Simulation Accuracy"),tr("You have chosen to simulate on a full mesh which might requires fews minutes to hours!!\nContinue?"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if result == QMessageBox.No:
                    return
            QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            useServer = WorkspaceCache.cache.get('useServer')
            if not useServer:
                self.simulationThread = SimulationProcessManager(self)
                if self.computeUsingProjection:
                    self.simulationThread.setup(self.activities,self.humanParam2,self.computeUsingProjection,self.numberOfSubSteps)
                else:
                    self.simulationThread.setup(self.activities,self.humanParam,self.computeUsingProjection,self.numberOfSubSteps)
                self.simulationThread.progress.connect(self.showProgress)
                self.simulationThread.finished.connect(self.simulationCompleted)
                if self.debugMode:
                    self.simulationThread.run()
                    self.simulationCompleted() #As event will not be triggered
                else:
                    self.simulationThread.start()
                
                self.actionPause.setEnabled(True)
                self.actionStop.setEnabled(True)                      
            else:
                simulator = Simulator()
                if self.computeUsingProjection:
                    simulator.setup(self.activities,self.humanParam2,self.computeUsingProjection,self.numberOfSubSteps)
                else:
                    simulator.setup(self.activities,self.humanParam,self.computeUsingProjection,self.numberOfSubSteps)
                serveruri  = WorkspaceCache.cache.get("serveruri",default='tcp://localhost')
                serverport = int(WorkspaceCache.cache.get("serverport",default=5570))
                    
                if not hasattr(self, "remoteProcessManager"):
                    self.remoteProcessManager = SimulationRemoteProcessManager(serveruri=serveruri,serverport=serverport)
                else:
                    #If constants have changed than recreate
                    if self.remoteProcessManager.serverURI!=serveruri or self.remoteProcessManager.serverPORT != serverport:
                        self.remoteProcessManager = SimulationRemoteProcessManager(serveruri=serveruri,serverport=serverport)
                
                self.remoteProcessIds = WorkspaceCache.cache.get(r'remoteProcessIds%s:%d'%(serveruri,serverport),default=dict())
                         
                rtask = self.remoteProcessManager.createRemoteTask()
                idn = rtask.getIdentity()
                rtask.setupSimulator(simulator)
                res = rtask.submit()
                QApplication.restoreOverrideCursor()
                if res['status']=='success':                
                    #self.remoteProcessIds[idn] = self.activities['activityname']
                    #Store basic project related details
                    if self.currentMeshData is None:
                        with open(self.currentMeshFile,'rb') as msh:
                            self.currentMeshData = msh.read()
                        
                    self.remoteProcessIds[idn] = [self.activities['activityname'],self.currentMeshData,self.humanBodyParameters, self.activities,self.computeUsingProjection, self.numberOfSubSteps,self.projectMetaData]
                    WorkspaceCache.cache.set(r'remoteProcessIds%s:%d'%(serveruri,serverport),self.remoteProcessIds)
                    QtWidgets.QMessageBox.information(None, "Success", "Job successfully submitted to server")
                elif res['status']=='failed':
                    QtWidgets.QMessageBox.critical(None, "Failed", res['message'])
                    return
        else:
            QMessageBox.information(self, tr("Missing information"), tr("Activity description and target mesh should be provided."))
        
    def simulationCompleted(self):
        self.showProgress(50) #Start loading
        simulationData = self.simulationThread.getSimulationResults()
        self.renderSimulationData(simulationData)
        QApplication.restoreOverrideCursor()

    def loadSimulationResults(self):
        useServer = WorkspaceCache.cache.get('useServer')
        if useServer:
            QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            if hasattr(self, 'qwListServerTasks'):
                del self.qwListServerTasks      
            #Launch current simulations view
            self.qwListServerTasks = ListServerTasks(cache=WorkspaceCache.cache)
            self.qwListServerTasks.show()
            self.qwListServerTasks.loadTaskStatus()
        QApplication.restoreOverrideCursor()        
    
    def loadSimulationResultsAskFile(self):
        direc = WorkspaceCache.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QFileDialog.getOpenFileName(None, tr('Load Activity file'),direc,"Pickle (*.pkl);; All (*.*)")
        if not filename is None:
            QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.loadSimulationResultsFromFile(filename[0])
            WorkspaceCache.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))
        QApplication.restoreOverrideCursor()
            
    def loadSimulationResultsFromFile(self,filename):
        if not filename is None and len(filename.strip()) > 0:
            self.showProgress(0)
            try:
                with open(filename,'rb') as ser:
                    simulationData = pickle.load(ser)
                    if isinstance(simulationData,dict):
                        self.renderSimulationData(simulationData)
                    else:
                        QApplication.restoreOverrideCursor()
                        QtWidgets.QMessageBox.critical(None, tr("Incorrect file format"), tr("Selected file cannot be loaded!\nDid you choose a project file or a file downloaded from server, if so use load project."))
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QtWidgets.QMessageBox.critical(None, tr("Unable to load"), '%s%s'%(tr("Selected file cannot be loaded!\nError "),str(e)))
                traceback.print_exc(file=sys.stdout)

            
    def renderSimulationData(self,simulationData):        
        self.humanParam.generateMesh(self.zincContext,simulationData)
        self.showProgress(60)
        maxPotentials = dict()
        minPotentials = dict()
        maxPotentials['Tskin'] = simulationData.skinTemperature.max()
        minPotentials['Tskin'] = simulationData.skinTemperature.min()
        maxPotentials['Tcore'] = simulationData.coreTemperature.max()
        minPotentials['Tcore'] = simulationData.coreTemperature.min()
        maxPotentials['SkinWettedness'] = simulationData.skinWettedness.max()
        minPotentials['SkinWettedness'] = simulationData.skinWettedness.min()
        maxPotentials['ThermalResistance'] = simulationData.thermalResistance.max()
        minPotentials['ThermalResistance'] = simulationData.thermalResistance.min()
        maxPotentials['EvaporativeResistance'] = simulationData.evaporativeResistance.max()
        minPotentials['EvaporativeResistance'] = simulationData.evaporativeResistance.min()

        self.showProgress(75) #Start loading
        self.simulationTimeConversionFactor = float(simulationData.numberOfTimeSamples)/self.maxTime
        self.zincGraphics.createGraphicsElements(maxPotentials, minPotentials)
        #update graph items
        tvals = simulationData.timeValue

        self.meanThermalResistancePlotItemHandle.setData(tvals,simulationData.meanThermalResistance)
        #self.meanThermalResistancePlotHandle.setXRange(0,tvals[-1])
        self.meanEvaporativeResistancePlotItemHandle.setData(tvals,simulationData.meanEvaporativeResistance)
        #self.meanEvaporativeResistancePlotHandle.setXRange(0,tvals[-1])
 
        for plt in list(self.bodyTemperaturePlotHandles.values()):
            plt.clear()

        for i,an in enumerate(self.anatomyKeys):
            self.bodyTemperaturePlotHandles['%s_Skin'%an].setData(tvals,simulationData.getMeanSegmentSkinTemperature(i))
            self.bodyTemperaturePlotHandles['%s_Core'%an].setData(tvals,simulationData.getMeanSegmentCoreTemperature(i))

        self.alltemperaturesPlotHandle.setYRange(min(minPotentials['Tskin'],minPotentials['Tcore'],simulationData.rectalTemperature.min())-1,\
                                                 max(maxPotentials['Tskin'],maxPotentials['Tcore'],simulationData.rectalTemperature.max())+1)
        self.showProgress(90) #
        self.bodyTemperaturePlotHandles['MeanSkin'].setData(tvals,simulationData.meanSkinTemperature)
        self.bodyTemperaturePlotHandles['MeanCore'].setData(tvals,simulationData.meanCoreTemperature)
        self.bodyTemperaturePlotHandles['Rectal'].setData(tvals,simulationData.rectalTemperature)

        #Comfort levels
        self.pmvPlotItemHandle.setData(tvals,simulationData.pmv)
        self.ppdPlotItemHandle.setData(tvals,simulationData.ppd)
        self.pmvPlotItemHandle.show()
        self.ppdPlotItemHandle.show()
        self.comfortLevelsPlotHandle.showAxis('left')
        self.comfortLevelsPlotHandle.showAxis('right')
        self.comfortLevelsPlotHandle.show()
        self.updateComfortLevelsViews()
        
        #Show mean temperature so that the axis and graph location is shown
        self.meanSkinTemperature.setChecked(True)
        self.alltemperaturesPlotHandle.show()
        self.actionPause.setEnabled(False)
        self.actionStop.setEnabled(False)
        self.showProgress(0,True)                
        self.currentSimulationData = simulationData
        #Resize temperature plot viewport else it is minimized until the window is changed
        gscene = self.temperatureGLW.scene() 
        tp = gscene.sceneRect()
        self.temperatureGLW.viewport().resize(tp.width(),tp.height())
        
    def saveSimulationData(self):
        if hasattr(self,'currentSimulationData'):            
            direc = WorkspaceCache.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
            filename = QtWidgets.QFileDialog.getSaveFileName(None, 'Simulation filename',direc,"Pickle (*.pkl);; All Files (*,*)")
            if not filename is None and len(filename[0].strip()) > 0:
                QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                try:
                    with open(filename[0],'wb+') as ser:
                        pickle.dump(self.currentSimulationData,ser)
                    WorkspaceCache.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))
                    QtWidgets.QMessageBox.information(None, "Success","Simulation data saved successfully!")
                except Exception as e:
                    QtWidgets.QMessageBox.critical(None, "Failed","Failed to save simulation data!\n%s"%str(e))
                QApplication.restoreOverrideCursor()
                
    def pauseSimulation(self):
        useServer = WorkspaceCache.cache.get('useServer')
        if not useServer:
            try:
                self.simulationThread.pause()
            except:
                pass
    
    def stopSimulation(self):
        useServer = WorkspaceCache.cache.get('useServer')
        if not useServer:            
            try:
                self.simulationThread.stop()
            except:
                pass
        else:
            print("Not implemented Simulator 1130")        
        
    def showAbout(self):
        #print('showAbout')
        if not hasattr(self, 'aboutDialog'):
            self.aboutDialog = AboutDialog()
        self.aboutDialog.show()
        
    def showPreferences(self):
        try:
            if not hasattr(self, 'preferencesDialog'):
                self.preferencesDialog = PreferencesWidget()
                self.preferencesDialog.serverPreferencesChanged.connect(self.reconfigure)   
            self.preferencesDialog.show()
        except:
            traceback.print_exc(file=sys.stdout)
