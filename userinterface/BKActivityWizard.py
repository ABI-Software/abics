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

from __future__ import unicode_literals,print_function
#Ensure we use pyqt api 2 and consistency across python 2 and 3
import sip

API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)

import sys
from PyQt5 import QtCore, uic
from PyQt5.QtGui import QColor, QPixmap, QIcon
import pyqtgraph as pg
import numpy as np
import os
import json
from collections import OrderedDict
from PyQt5.Qt import pyqtSignal, QMessageBox, QFileDialog, QApplication,\
    QPushButton

try:
    _encoding = QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)

def tr(msg):
    return _translate("ActivityWizard", msg, None)

dir_path = os.path.dirname(os.path.realpath(sys.argv[0]))
if not hasattr(sys, 'frozen'): #For py2exe
    dir_path = os.path.join(dir_path,"..")

class DummyCache(object):
    
    def __init__(self):
        pass
    
    def get(self,dx,default):
        return default
    
    def set(self,dx,val):
        pass


uiFile = os.path.join(dir_path,"./uifiles/activitydesigner.ui")

form,base = uic.loadUiType(uiFile)

class ActivityDefinitionWidget(base, form):
    currentActivityId = -1
    numberOfActivities = 0
    activities = OrderedDict()
    activityButtons = dict()
    #Send a signal with the filename when an activity is saved.
    dataSaved = pyqtSignal(object)
    
    def __init__(self,title='Activity Definition',parent=None):
        super(base,self).__init__(parent)
        #Setup colors
        graphColors = [18,4,12,11,10,8,9,7] #Based on Qt.GlobalColor
        #Create color objects
        self.graphColors = [QColor(QtCore.Qt.GlobalColor(x)) for x in graphColors]
        #Map control names to color indexes
        self.cindexMap = {'a18Color':0,'b18Color':1,'c18Color':2,'d18Color':3,'e18Color':4,'f18Color':5,'g18Color':6,'h18Color':7}
        #Setup the ui
        self.setupUi(self)
        
        self.setObjectName('ActivityWizard')
        #Create the plots for individual electrode selection
        self.createSignalPlots()
        
        #Established signals and slot maps
        self._setConnections()
        ICON = QIcon(QPixmap(os.path.join(dir_path,'./uifiles/images/pwave.png')))
        self.setWindowTitle(tr(title))
        self.setWindowIcon(ICON)
        self.deleteActivity.setDisabled(True)
        self.cloneActivity.setDisabled(True)
        self.updateActivity.setDisabled(True)
        self.save.setDisabled(True)
        self.loadingClothingFile.clicked.connect(self.loadingClothingFileName)
        self.loadingRadiationFile.clicked.connect(self.loadingRadiationFileName)
        self.retranslateUi(self)
        #To not cause QTimer error at close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.cache = DummyCache()
        self.activityName.setText(tr("Unnamed"))
        self.setWindowTitle(tr(title))

    def loadingClothingFileName(self):
        direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QFileDialog.getOpenFileName(None, tr('Load Clothing Description file'),direc,"JSON (*.json)")
        if not filename is None and len(filename[0].strip())>0:
            self.clothingFile.setText(os.path.abspath(filename[0]))

    def loadingRadiationFileName(self):
        direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QFileDialog.getOpenFileName(None, tr('Load Radiation Description file'),direc,"JSON (*.json)")
        if not filename is None and len(filename[0].strip())>0:
            self.radiationFluxFile.setText(os.path.abspath(filename[0]))


    def setCache(self,cache):
        self.cache = cache

    def refreshGraph(self):
        numActivities = len(self.activities)
        if 'activityname' in self.activities:
            numActivities -=1
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
                i +=1
        timeValues = np.r_[0,np.cumsum(timeValues)]
                
        self.temperaturePlot.clear()
        self.metabolicActivityPlot.clear()
        self.velocityOfAirPlot.clear()
        self.relativeHumidityPlot.clear()
        if numActivities > 0:
            temps[0] = temps[1]
            mets[0] = mets[1]
            voa[0] = voa[1]
            rh[0] = rh[1]
            #timeValues[0] = timeValues[1]-0.01
            citem = pg.PlotCurveItem(timeValues,temps,stepMode=True)
            citem.setPen(pg.mkPen(self.graphColors[0],width=2, cosmetic=True))
            self.temperaturePlot.addItem(citem)
    
            citem = pg.PlotCurveItem(timeValues,mets,stepMode=True)
            citem.setPen(pg.mkPen(self.graphColors[1],width=2, cosmetic=True))
            self.metabolicActivityPlot.addItem(citem)

            citem = pg.PlotCurveItem(timeValues,voa,stepMode=True)
            citem.setPen(pg.mkPen(self.graphColors[2],width=2, cosmetic=True))
            self.velocityOfAirPlot.addItem(citem)
    
            citem = pg.PlotCurveItem(timeValues,rh,stepMode=True)
            citem.setPen(pg.mkPen(self.graphColors[3],width=2, cosmetic=True))
            self.relativeHumidityPlot.addItem(citem)


    def createSignalPlots(self):
        plt = self.selectElectrodesPlot.addPlot(0,0) 
        #plt.hideAxis('left')
        #plt.hideAxis('bottom')
        plt.setTitle(tr('Ambient Temperature'),bold=True,color='#ffffff')
        self.temperaturePlot = plt
        plt = self.selectElectrodesPlot.addPlot(1,0) 
        #plt.hideAxis('left')
        #plt.hideAxis('bottom')
        plt.setTitle(tr('Ambient Relative Humidity'),bold=True,color='#ffffff')
        self.relativeHumidityPlot = plt
        plt = self.selectElectrodesPlot.addPlot(2,0) 
        #plt.hideAxis('left')
        #plt.hideAxis('bottom')
        plt.setTitle(tr('Velcity of Air'),bold=True,color='#ffffff')
        self.velocityOfAirPlot = plt
        plt = self.selectElectrodesPlot.addPlot(3,0) 
        #plt.hideAxis('left')
        #plt.hideAxis('bottom')
        plt.setTitle(tr('Metabolic Activity'),bold=True,color='#ffffff')
        self.metabolicActivityPlot = plt

        
    def _setConnections(self):
        self.addActivity.clicked.connect(self.addCurrentActivity)
        self.updateActivity.clicked.connect(self.updateCurrentActivity)
        self.deleteActivity.clicked.connect(self.deleteCurrentActivity)
        self.cloneActivity.clicked.connect(self.cloneCurrentActivity)
        self.save.clicked.connect(self.saveActivity)
        self.loadActivity.clicked.connect(self._loadActivity)
        
    def addCurrentActivity(self):
        desc     = str(self.activityDescription.text())
        duration = float(str(self.eventDuration.text()))
        rh       = float(str(self.relativeHumidity.text()))
        Tab      = float(str(self.ambientTemperature.text()))
        velOfAir = float(str(self.velocityOfAir.text()))
        metabolicActivity =str(self.metabolicActivity.text())
        clothingFile = str(self.clothingFile.text())
        radiationFluxFile = str(self.radiationFluxFile.text())
        activity = dict()
        activity['description'] = desc
        activity['duration'] = duration
        activity['rh'] = rh
        activity['Tab'] = Tab
        activity['velocityOfAir'] = velOfAir
        activity['metabolicActivity'] = metabolicActivity
        activity['clothingFile'] = clothingFile
        activity['radiationFluxFile'] = radiationFluxFile
        if self.currentActivityId==-1:
            try:
                self.currentActivityId = max(self.activities.keys()) + 1
            except ValueError:
                self.currentActivityId = 0
            self.numberOfActivities = self.currentActivityId + 1
        else:
            self.numberOfActivities +=1
            self.currentActivityId = self.numberOfActivities
            
        activity['id'] = self.currentActivityId
        self.activities[self.currentActivityId] = activity
        
        self.deleteActivity.setEnabled(True)
        self.cloneActivity.setEnabled(True)
        self.save.setEnabled(True)
        self.updateActivity.setDisabled(False)

        
        pb = QPushButton('%s' % desc,self)
        pb.setObjectName('%d' % activity['id'])
        pb.clicked.connect(self.setupActivity)
        self.currentActivities.addWidget(pb)
        self.activityButtons[activity['id']] = pb
        self.refreshGraph()
        #print activity
    
    def updateCurrentActivity(self):
        if self.currentActivityId==-1:
            QMessageBox.critical(self, tr('Missing target'), tr('Current record is not associated with any existing record! Click Add or select Activity Record.\nSelecting an activity record will reset current values'))
            return
        desc     = str(self.activityDescription.text())
        duration = float(str(self.eventDuration.text()))
        rh       = float(str(self.relativeHumidity.text()))
        Tab      = float(str(self.ambientTemperature.text()))
        velOfAir = float(str(self.velocityOfAir.text()))
        metabolicActivity =str(self.metabolicActivity.text())
        clothingFile = str(self.clothingFile.text())
        radiationFluxFile = str(self.radiationFluxFile.text())
        activity = dict()
        activity['description'] = desc
        activity['duration'] = duration
        activity['rh'] = rh
        activity['Tab'] = Tab
        activity['velocityOfAir'] = velOfAir
        activity['metabolicActivity'] = metabolicActivity
        activity['clothingFile'] = clothingFile
        activity['radiationFluxFile'] = radiationFluxFile
        activity['id'] = self.currentActivityId  
        self.activities[self.currentActivityId] = activity
        self.activityButtons[self.currentActivityId].setText(desc)
        self.refreshGraph()  
    
    def setupActivity(self):
        pb = self.sender()
        self.currentActivityId = int(pb.objectName())
        activity = self.activities[self.currentActivityId]
        self.activityDescription.setText(activity['description'])
        self.eventDuration.setText(str(activity['duration']))
        self.relativeHumidity.setText(str(activity['rh']))
        self.ambientTemperature.setText(str(activity['Tab']))
        self.velocityOfAir.setText(str(activity['velocityOfAir']))
        self.metabolicActivity.setText(activity['metabolicActivity'])
        self.clothingFile.setText(activity['clothingFile'])
        self.radiationFluxFile.setText(activity['radiationFluxFile'])    
        self.updateActivity.setDisabled(False)
        self.deleteActivity.setDisabled(False) 

        
    def deleteCurrentActivity(self):
        try:
            del self.activities[self.currentActivityId]
            pb = self.activityButtons[self.currentActivityId]
            pb.hide()
            self.currentActivities.removeWidget(pb)
            del self.activityButtons[self.currentActivityId]
            self.numberOfActivities -= 1
        except:
            QMessageBox.information(self, tr("In correct usage"), tr("Only Activities that have been added will be deleted. If you have cloned an activity, it has not been added yet. Select an activity by clicking on its name in the activity bar."))

        self.currentActivityId = -1
        self.refreshGraph()
        if len(self.activities)==0:
            self.deleteActivity.setDisabled(True)
            self.cloneActivity.setDisabled(True)
            self.save.setDisabled(True)
        self.updateActivity.setDisabled(True)
        self.deleteActivity.setDisabled(True)

    
    def cloneCurrentActivity(self):
        self.numberOfActivities +=1
        self.currentActivityId = max(self.activities.keys()) + 1
        self.activityDescription.setText('%s Clone ' % self.activityDescription.text())
        self.updateActivity.setDisabled(True)
    
    def _loadActivity(self):
        direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QFileDialog.getOpenFileName(None, 'Load file',direc,"JSON (*.json)")
        if not filename is None and len(filename[0].strip())>0:
            self.loadActivityFromFile(filename[0])
            self.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))
    
    def loadActivityFromFile(self,filename):
        if not filename is None and len(filename.strip()) > 0:                  
            with open(filename,'r') as ser:
                activities = json.load(ser)
                #self.currentActivityId = len(activities)
                self.loadActivityFromDict(activities,filename)
                
    def loadActivityFromDict(self,activities,filename='.'):                
        #Remove buttons and recreate them
        try:
            for i,pb in self.activityButtons.items():
                pb.hide()
                self.currentActivities.removeWidget(pb)
                del self.activityButtons[i]
            self.activityButtons.clear()
            self.activities.clear()
            self.activities.update(activities)
            #Activities should be ordered by id, json does not conserve orders
            actKeys = []
            if 'activityname' in activities:
                self.activityName.setText(activities['activityname'])
            else:
                self.activityName.setText(os.path.basename(filename))
            actOrder = []
            for k,activity in activities.items():
                #utf2str converts integers to string
                if isinstance(activity,dict):
                    actKeys.append(k)
                    actOrder.append(int(activity['id']))
            ix = np.argsort(actOrder)
            for ak in ix:
                activity = activities[actKeys[ak]]
                pb = QPushButton( activity['description'],self)
                pb.setObjectName('%d' % activity['id'])
                pb.clicked.connect(self.setupActivity)
                self.currentActivities.addWidget(pb)
                self.activityButtons[activity['id']] = pb
                self.activities[activity['id']] = activity
            activity = self.activities[actKeys[ix[0]]]
            self.currentActivityId = activity['id']
            self.activityDescription.setText(activity['description'])
            self.eventDuration.setText(str(activity['duration']))
            self.relativeHumidity.setText(str(activity['rh']))
            self.ambientTemperature.setText(str(activity['Tab']))
            self.velocityOfAir.setText(str(activity['velocityOfAir']))
            self.metabolicActivity.setText(activity['metabolicActivity'])
            self.clothingFile.setText(activity['clothingFile'])
            self.radiationFluxFile.setText(activity['radiationFluxFile'])                 
            self.deleteActivity.setEnabled(True)
            self.cloneActivity.setEnabled(True)
            self.save.setEnabled(True)
            self.refreshGraph()
        except:
            import traceback
            traceback.print_exc(file=sys.stdout)
                
    def saveActivity(self):
        if len(self.activities) > 0:
            direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
            filename = QFileDialog.getSaveFileName(None, 'Save file',direc,"JSON (*.json)")
            if not filename is None and len(filename[0].strip()) > 0:
                print(json.dumps(self.activities))
                #Update filenames to be relative to this file
                bdir = os.path.dirname(filename[0])
                for aid in self.activities:
                    activity = self.activities[aid]
                    if isinstance(activity,dict):
                        cf = activity['clothingFile']
                        cp = os.path.abspath(cf)
                        activity['clothingFile'] = str(os.path.relpath(cp, bdir))
                        rf = activity['radiationFluxFile']
                        if len(rf.strip())>0:
                            rp = os.path.abspath(rf)
                            activity['radiationFluxFile'] = str(os.path.relpath(rp, bdir))
                with open(filename[0],'w') as ser:
                    self.activities['activityname']=self.activityName.text()
                    json.dump(self.activities,ser)
                    self.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))
                self.dataSaved.emit(filename[0])
        else:
            QMessageBox.information(self, tr("In correct usage"), tr("No activities defined. Did you forget to click add!"))
    

if __name__ == '__main__':
    app = QApplication(sys.argv)
    obj = ActivityDefinitionWidget()
    obj.show()
    sys.exit(app.exec_())    