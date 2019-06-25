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
from PyQt5 import QtWidgets,QtCore, uic
from PyQt5.QtGui import QColor, QPixmap, QIcon
import pyqtgraph as pg
import numpy as np
import os
import json
from PyQt5.Qt import pyqtSignal, QMessageBox, QFileDialog, QApplication

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

class FloatDelegate(QtWidgets.QItemDelegate):
    def __init__(self, parent=None,decimals=3):
        QtWidgets.QItemDelegate.__init__(self, parent=parent)
        self.nDecimals = decimals

    def paint(self, painter, option, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        try:
            val = float(value)            
            painter.drawText(option.rect, QtCore.Qt.AlignVCenter, "{:.{}f}".format(val, self.nDecimals))
        except :
            painter.drawText(option.rect, QtCore.Qt.AlignVCenter, 'NaN')


uiFile = os.path.join(dir_path,"./uifiles/activitydesignerv2.ui")

form,base = uic.loadUiType(uiFile)

class ActivityDefinitionWidget(base, form):
    currentActivityId = -1
    numberOfActivities = 0
    activities = dict()
    #Send a signal with the filename when an activity is saved.
    dataSaved = pyqtSignal(object)
    modifyingTable = False
    hite = ['description','duration','rh','Tab','velocityOfAir','metabolicActivity','clothingFile','radiationFluxFile']
    
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
        addFile = os.path.join(dir_path,"./uifiles/images/add.png")
        self.addActivity.setIcon(QIcon(addFile))
        self.deleteActivity.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogCloseButton))
        self.moveUpButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowUp))
        self.moveDownButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowDown))
        
        headers = list(map(tr,['Description','Duration (min)','RH %','Temp','Vel. of Air (m/s)','Met','Clothing File','Radiation File']))
        self.activityTable.setColumnCount(len(headers))
        self.activityTable.setHorizontalHeaderLabels(headers)
        self.activityTable.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.activityTable.horizontalHeader().resizeSection(0,65)
        self.activityTable.horizontalHeader().resizeSection(1,95)
        for i in range(2,6):
            self.activityTable.horizontalHeader().resizeSection(i,65)
            self.activityTable.setItemDelegateForColumn(i,FloatDelegate(self))
        self.activityTable.horizontalHeader().resizeSection(4,95)
        self.setObjectName('ActivityWizard')
        #Create the plots for individual electrode selection
        self.createSignalPlots()
        
        #Established signals and slot maps
        self._setConnections()
        self.setWindowTitle(tr(title))
        self.deleteActivity.setDisabled(True)
        self.saveActivityButton.setDisabled(True)
        self.retranslateUi(self)
        
        #To not cause QTimer error at close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.cache = DummyCache()
        self.activityName.setText(tr("Unnamed"))
        self.setWindowTitle(tr(title))
        self.activityTable.cellDoubleClicked.connect(self.activityTableDoubleClicked)
        self.activityTable.itemChanged.connect(self.updateCurrentActivity)

    def loadingClothingFileName(self):
        direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QFileDialog.getOpenFileName(None, tr('Load Clothing Description file'),direc,"JSON (*.json)")
        if not filename is None and len(filename[0].strip())>0:
            #self.clothingFile.setText(os.path.abspath(filename[0]))
            self.activityTable.setItem(self.currentActivityId,6,QtWidgets.QTableWidgetItem(os.path.abspath(filename[0])))

    def loadingRadiationFileName(self):
        direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QFileDialog.getOpenFileName(None, tr('Load Radiation Description file'),direc,"JSON (*.json)")
        if not filename is None and len(filename[0].strip())>0:
            #self.radiationFluxFile.setText(os.path.abspath(filename[0]))
            self.activityTable.setItem(self.currentActivityId,7,QtWidgets.QTableWidgetItem(os.path.abspath(filename[0])))

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
        plt.setTitle(tr('Velocity of Air'),bold=True,color='#ffffff')
        self.velocityOfAirPlot = plt
        plt = self.selectElectrodesPlot.addPlot(3,0) 
        #plt.hideAxis('left')
        #plt.hideAxis('bottom')
        plt.setTitle(tr('Metabolic Activity'),bold=True,color='#ffffff')
        self.metabolicActivityPlot = plt

        
    def _setConnections(self):
        self.addActivity.clicked.connect(self.addCurrentActivity)
        self.deleteActivity.clicked.connect(self.deleteCurrentActivity)
        self.saveActivityButton.clicked.connect(self.saveActivity)
        self.loadActivity.clicked.connect(self._loadActivity)
        self.moveUpButton.clicked.connect(self.moveUp)
        self.moveDownButton.clicked.connect(self.moveDown)

    def activityTableDoubleClicked(self,row,col):
        self.currentActivityId = row
        if col==6: #This should be clothing mesh
            self.loadingClothingFileName()
        elif col==7:
            self.loadingRadiationFileName()
        
    def addCurrentActivity(self):
        self.modifyingTable = True        
        rc = self.activityTable.rowCount()
        self.activityTable.insertRow(rc)
        self.currentActivityId = rc
        mdl = self.activityTable.model()
        self.activityTable.setItem(rc,0,QtWidgets.QTableWidgetItem('Activity %d'%rc))
        if rc==0:
            self.activityTable.setItem(rc,1,QtWidgets.QTableWidgetItem('1.0'))
            self.activityTable.setItem(rc,2,QtWidgets.QTableWidgetItem('40.0'))
            self.activityTable.setItem(rc,3,QtWidgets.QTableWidgetItem('21.0'))
            self.activityTable.setItem(rc,4,QtWidgets.QTableWidgetItem('1.0'))
            self.activityTable.setItem(rc,5,QtWidgets.QTableWidgetItem('0.0'))
            self.activityTable.setItem(rc,6,QtWidgets.QTableWidgetItem(''))
            self.activityTable.setItem(rc,7,QtWidgets.QTableWidgetItem(''))
        else:
            clone = rc-1
            selectedItems = self.activityTable.selectedItems()
            rows = set()
            for itm in selectedItems:        
                rows.add(itm.row())
            if len(rows)>0:
                clone = rows.pop()
                
            for i in range(1,8):
                self.activityTable.setItem(rc,i,QtWidgets.QTableWidgetItem(mdl.index(clone,i).data()))
        self.deleteActivity.setEnabled(True)
        self.saveActivityButton.setEnabled(True)
        #Updates activities and graph
        act = dict()
        act['id'] = rc
        for j,v in enumerate(self.hite):
            if j>0 and j<6:
                act[v] = float(mdl.index(rc,j).data())
            else:
                act[v] = mdl.index(rc,j).data()
        self.activities[rc] = act
        self.refreshGraph()        
        self.modifyingTable = False 
    
    
    def updateCurrentActivity(self,item=None):
        if not self.modifyingTable:   
            self.activities = dict()
            mdl = self.activityTable.model()
            
            for i in range(self.activityTable.rowCount()):
                act = dict()
                act['id'] = i
                for j,v in enumerate(self.hite):
                    if j>0 and j<6:
                        act[v] = float(mdl.index(i,j).data())
                    else:
                        act[v] = mdl.index(i,j).data()
                self.activities[i] = act
            if item is not None:
                col = item.column()
                if col > 0 and col < 6:          
                    self.refreshGraph() 
            else:
                self.refreshGraph()

        
    def deleteCurrentActivity(self):
        selectedItems = self.activityTable.selectedItems()
        rows = set()
        for itm in selectedItems:        
            rows.add(itm.row())
        for r in rows:
            self.activityTable.removeRow(r)
            del self.activities[r]
        if self.activityTable.rowCount()==0:
            self.deleteActivity.setDisabled(True)
            self.saveActivityButton.setDisabled(True)
        self.refreshGraph()  
    
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
                self.loadActivityFromDict(activities,filename)
                
    def loadActivityFromDict(self,activities,filename='.'):                
        #Remove buttons and recreate them
        try:
            self.modifyingTable = True
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
            for rc,ak in enumerate(ix):
                self.activityTable.insertRow(rc)
                self.currentActivityId = rc
                activity = activities[actKeys[ak]]
                self.activityTable.setItem(rc,0,QtWidgets.QTableWidgetItem(activity['description']))
                self.activityTable.setItem(rc,1,QtWidgets.QTableWidgetItem(str(activity['duration'])))
                self.activityTable.setItem(rc,2,QtWidgets.QTableWidgetItem(str(activity['rh'])))
                self.activityTable.setItem(rc,3,QtWidgets.QTableWidgetItem(str(activity['Tab'])))
                self.activityTable.setItem(rc,4,QtWidgets.QTableWidgetItem(str(activity['velocityOfAir'])))
                self.activityTable.setItem(rc,5,QtWidgets.QTableWidgetItem(str(activity['metabolicActivity'])))
                self.activityTable.setItem(rc,6,QtWidgets.QTableWidgetItem(activity['clothingFile']))
                self.activityTable.setItem(rc,7,QtWidgets.QTableWidgetItem(activity['radiationFluxFile']))            
                          
            self.deleteActivity.setEnabled(True)
            self.saveActivityButton.setEnabled(True)
            self.modifyingTable = False
            self.updateCurrentActivity()
        except:
            import traceback
            traceback.print_exc(file=sys.stdout)
        finally:
            self.modifyingTable = False

    def moveDown(self):
        self.modifyingTable = True 
        row = self.activityTable.currentRow()
        column = self.activityTable.currentColumn();
        if row < self.activityTable.rowCount()-1:
            self.activityTable.insertRow(row+2)
            for i in range(self.activityTable.columnCount()):
                self.activityTable.setItem(row+2,i,self.activityTable.takeItem(row,i))
                self.activityTable.setCurrentCell(row+2,column)
            self.activityTable.removeRow(row)     
        self.modifyingTable = False    
        self.updateCurrentActivity()


    def moveUp(self):    
        self.modifyingTable = True 
        row = self.activityTable.currentRow()
        column = self.activityTable.currentColumn()
        if row > 0:
            self.activityTable.insertRow(row-1)
            for i in range(self.activityTable.columnCount()):
                self.activityTable.setItem(row-1,i,self.activityTable.takeItem(row+1,i))
                self.activityTable.setCurrentCell(row-1,column)
            self.activityTable.removeRow(row+1) 
        self.modifyingTable = False 
        self.updateCurrentActivity()
                
    def saveActivity(self):
        self.updateCurrentActivity()
        if len(self.activities) > 0:
            direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
            filename = QFileDialog.getSaveFileName(None, 'Save file',direc,"JSON (*.json)")
            if not filename is None and len(filename[0].strip()) > 0:
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
                    if self.activities['activityname']=='Unnamed':
                        self.activities['activityname']=os.path.splitext(os.path.basename(filename[0]))[0]
                        self.activityName.setText(self.activities['activityname'])
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