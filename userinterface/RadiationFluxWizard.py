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
#Ensure we use pyqt api 2 and consistency across python 2 and 3
from __future__ import unicode_literals,print_function
import sip
import tempfile

API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)

from PyQt5.Qt import QColor
from opencmiss.zinc.context import Context
from zincwidgets.sceneviewerwidget import SceneviewerWidget
import logging
from bodymodels.LoadOBJHumanModel import HumanModel
from support.ZincGraphicsElements import GenerateZincGraphicsElements
import numpy as np    
import sys
from PyQt5 import QtCore, QtGui, uic, QtWidgets
import os, json

class DummyCache(object):
    
    def __init__(self):
        pass
    
    def get(self,dx,default):
        return default
    
    def set(self,dx,val):
        pass

dir_path = os.path.dirname(os.path.realpath(sys.argv[0]))
if not hasattr(sys, 'frozen'): #For py2exe
    dir_path = os.path.join(dir_path,"..")
    
try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)

def tr(msg):
    return _translate("RadiationFluxWizard", msg, None)

class FloatDelegate(QtWidgets.QItemDelegate):
    def __init__(self, parent=None,decimals=2,angle=1e9):
        QtWidgets.QItemDelegate.__init__(self, parent=parent)
        self.nDecimals = decimals
        self.angle = angle

    def paint(self, painter, option, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        try:
            val = float(value)
            number = np.sign(val)*np.fmod(np.fabs(val),self.angle)
            
            painter.drawText(option.rect, QtCore.Qt.AlignVCenter, "{:.{}f}".format(number, self.nDecimals))
        except :
            painter.drawText(option.rect, QtCore.Qt.AlignVCenter, 'NaN')


uiFile = os.path.join(dir_path,"./uifiles/radiationfluxdesigner.ui")

form,base = uic.loadUiType(uiFile)

class RadiationDefinitionWidget(base, form):
    '''
    Define radiation exposure for each body part
    '''
    #Send a signal with the filename when an activity is saved.
    dataSaved = QtCore.pyqtSignal(object)
    colors  = [QColor(QtCore.Qt.red),QColor(QtCore.Qt.blue),QColor(QtCore.Qt.green)]
    modifyingTable = False
    activeSources = dict()
    sourceKey = 1
    meshLoaded = False
    centroidVisible = False
    lightsVisible = True
    computedFluxes = dict()
    
    def __init__(self,title='Radiation Definition',parent=None):
        super(base,self).__init__(parent)
        self.setupUi(self)  
        self.setupZinc()
        lightFile = os.path.join(dir_path,"./uifiles/images/idea.png")
        self.showLights.setIcon(QtGui.QIcon(lightFile))
        addFile = os.path.join(dir_path,"./uifiles/images/add.png")
        self.addSourceButton.setIcon(QtGui.QIcon(addFile))
        self.removeSourceButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogCloseButton))
        self.viewAllMesh.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogHelpButton))
        axisFile = os.path.join(dir_path,"./uifiles/images/axis.png")
        self.showCentroid.setIcon(QtGui.QIcon(axisFile))
        self._setConnections()
        headers = list(map(tr,['Name','Flux (kW/m^2)','Distance (m)','Latitude','Longitude','Light Color','key']))
        self.sourceTable.setColumnCount(len(headers))
        self.sourceTable.setHorizontalHeaderLabels(headers)
        self.sourceTable.horizontalHeader().setToolTip("Source beyond 10 times the mesh extant are clipped for visualization purposes")
        self.sourceTable.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        for i in [1,2]:
            self.sourceTable.horizontalHeader().resizeSection(i,100)
            self.sourceTable.setItemDelegateForColumn(i,FloatDelegate(self))
        self.sourceTable.horizontalHeader().resizeSection(3,100)
        self.sourceTable.setItemDelegateForColumn(3,FloatDelegate(self,angle=180.0))
        self.sourceTable.horizontalHeader().resizeSection(4,100)
        self.sourceTable.setItemDelegateForColumn(4,FloatDelegate(self,angle=360.0))
            
        self.sourceTable.horizontalHeader().resizeSection(5,75)
        self.sourceTable.setColumnHidden(6,True)
        self.sourceTable.itemChanged.connect(self.itemChanged)
        #To not cause QTimer error at close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)      
        self.cache = DummyCache()
        self.setWindowTitle(tr(title))
    
    def setupZinc(self):
        self.zincContext = Context(str('Radiation'))
        #Zinc viewer setup
        self.mvLayout = QtWidgets.QVBoxLayout(self.graphicsHost)
        self.mvLayout.setSpacing(0)
        self.mvLayout.setContentsMargins(0,0,0,0)
        self.mvLayout.setObjectName("mvLayout")
        self.meshWindow = SceneviewerWidget(self.graphicsHost)
        self.meshWindow.setContext(self.zincContext)
        self.mvLayout.addWidget(self.meshWindow)
        self.meshWindow.graphicsInitialized.connect(self.setBackgroundColor)
        
    def setBackgroundColor(self):
        self.meshWindow.setBackgroundColor([1,1,1])
    
    def setCache(self,cache):
        self.cache = cache
    
    def _setConnections(self):
        self.viewAllMesh.clicked.connect(self._viewAllMesh)
        self.showCentroid.clicked.connect(self._showCentroid)
        self.addSourceButton.clicked.connect(self._addSource)
        self.removeSourceButton.clicked.connect(self._removeSource)
        self.loadScene.clicked.connect(self._loadSceneDefinition)
        self.loadMesh.clicked.connect(self._loadMeshGUI)
        self.saveFlux.clicked.connect(self._saveRadiationModel)
        self.saveDefinition.clicked.connect(self._saveSceneDefinition)
        self.showLights.clicked.connect(self._showHideLights)

    def clearMesh(self):
        try:
            self.centroidVisible = False
            defaultRegion = self.zincContext.getDefaultRegion()
            if hasattr(self, 'zincGraphics'):
                self.zincGraphics.destroyGraphicsElements()
            region = defaultRegion.getFirstChild()
            while region.isValid():
                tmp = region
                region = region.getNextSibling()
                defaultRegion.removeChild(tmp)
                self.setZincTitleBarString(tr("No Mesh Loaded"))

            self.currentMeshData = None
            self.meshLoaded = False
            self.resetMeshScaling.setEnabled(False)
        except:
            logging.debug("Failed to clear mesh")

        
    def _viewAllMesh(self):
        self.meshWindow.viewAll()
    
    def _showCentroid(self):
        self.centroidVisible = not self.centroidVisible
        self.centroidGraphics.setVisibilityFlag(self.centroidVisible) 
    
    def _showHideLights(self):
        if hasattr(self.zincGraphics,'lights'):
            self.lightsVisible = not self.lightsVisible
            for lt,v in self.zincGraphics.lights.items():
                v[1].setVisibilityFlag(self.lightsVisible)
    
    def _addSource(self):
        self.modifyingTable = True        
        rc = self.sourceTable.rowCount()
        self.sourceTable.insertRow(rc)
        dbutton = QtWidgets.QToolButton()
        dbutton.setText('')
        qss = "background-color: %s" % self.colors[rc%3].name()
        dbutton.setStyleSheet(qss)        
        dbutton.clicked.connect(self.changeColor)
        self.sourceTable.setItem(rc,0,QtWidgets.QTableWidgetItem('Source%d'%self.sourceKey))
        self.sourceTable.setItem(rc,6,QtWidgets.QTableWidgetItem('%d'%self.sourceKey))
        self.sourceKey +=1
        for i in range(1,5):
            self.sourceTable.setItem(rc,i,QtWidgets.QTableWidgetItem('0.0'))
        self.sourceTable.setCellWidget(rc,5,dbutton)
        self.modifyingTable = False
        
    def insertSource(self,itemV):
        self.modifyingTable = True        
        rc = self.sourceTable.rowCount()
        self.sourceTable.insertRow(rc)
        dbutton = QtWidgets.QToolButton()
        dbutton.setText('')
        dbutton.clicked.connect(self.changeColor)
        self.sourceTable.setItem(rc,0,QtWidgets.QTableWidgetItem(itemV[0]))
        ikey = int(itemV[-1])
        self.sourceTable.setItem(rc,6,QtWidgets.QTableWidgetItem('%d'%ikey))
        if self.sourceKey < ikey:
            self.sourceKey = ikey + 1
        for i in range(1,5):
            self.sourceTable.setItem(rc,i,QtWidgets.QTableWidgetItem(itemV[i]))
        qss = "background-color: %s" % itemV[5]
        dbutton.setStyleSheet(qss)        
        self.sourceTable.setCellWidget(rc,5,dbutton)
        self.modifyingTable = False
        
        
    def itemChanged(self,itm):
        if not self.modifyingTable:
            self.update()

    def update(self,colorChanged=False):
        '''
        Update lights and flux
        '''
        if not self.modifyingTable and self.meshLoaded:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                self.modifyingTable = True
                itms = dict()
                for r in range(self.sourceTable.rowCount()):
                    uset = []
                    for c in range(5):
                        itm = self.sourceTable.item( r, c )
                        if itm is not None:
                            uset.append(itm.text())
                        else:
                            uset.append('')
                    itm = self.sourceTable.cellWidget( r, 5 )
                    col = itm.palette().color(QtGui.QPalette.Button)
                    uset.append([col.redF(),col.greenF(),col.blueF()])
                    itm = self.sourceTable.item( r, 6)
                    uset.append(itm.text())
                    rad = float(uset[2])
                    lat = float(uset[3])
                    lon = float(uset[4])
                    
                    x = rad*np.sin(lat)*np.cos(lon)
                    y = rad*np.sin(lat)*np.sin(lon)
                    z = rad*np.cos(lat)
                    uset[2]=x
                    uset[3]=y
                    uset[4]=z
                    
                    itms[uset[-1]]=uset
                rfluxes = []
                for itm in self.activeSources:
                    if itm not in itms:
                        rfluxes.append(itm)
                  
                #Check if item has changed
                nfluxes = []
                for itm,v in itms.items():
                    if itm in self.activeSources:
                        if v==self.activeSources[itm]:
                            continue
                    self.activeSources[itm]=v
                    nfluxes.append(itm)
                
                for itm in rfluxes:
                    self.removeLightSource(itm)
                    if itm in self.computedFluxes:
                        del self.computedFluxes[itm]
                    if itm in self.activeSources:
                        del self.activeSources[itm]
                    
                if not colorChanged:
                    totalFlux = np.zeros((len(self.humanParam.faces),1))
                    
                    for itm in nfluxes:
                        self.updateLightSource(self.activeSources[itm])
                        v = self.activeSources[itm]
                        flx = self.humanParam.computeIncidantFlux(float(v[1]), v[2:5])
                        self.computedFluxes[v[-1]] = flx*1000 #Since the input is in kilo Watt
                    if len(self.computedFluxes)>0:
                        for flx in self.computedFluxes.values():
                            totalFlux += flx
                        totalFlux /= (len(self.computedFluxes))
                    self.zincGraphics.updateRadiationFluxField(totalFlux)
                    self.radiationFlux = totalFlux
                    self.zincGraphics.setColorBarFontColor()
                else:
                    for itm in nfluxes:
                        self.updateLightSource(self.activeSources[itm])
                    
            except Exception as e:
                QtWidgets.QMessageBox.critical(None,tr('Failed to update fluxes'),'%s %s'%(tr('Flux update failed'),str(e)))
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()
                self.modifyingTable = False
            
    def updateLightSource(self,des):
        self.zincGraphics.createLightSource(des[-1], des[2:5], des[5], float(des[1]))
        
    def removeLightSource(self,ky):
        self.zincGraphics.removeLightSource(ky)
        
    def changeColor(self):
        but = self.sender()
        #index = self.table.indexAt(but.pos())
        color = QtWidgets.QColorDialog.getColor(but.palette().color(1))
        if color.isValid():
            qss = "background-color: %s" % color.name()
            but.setStyleSheet(qss)
            self.update(True)        
    
    def _removeSource(self):
        self.modifyingTable = True
        selectedItems = self.sourceTable.selectedItems()
        rows = set()
        for itm in selectedItems:        
            rows.add(itm.row())
        for r in rows:
            self.sourceTable.removeRow(r)
        self.modifyingTable = False
        if len(rows)>0:
            self.update()
        
        
    def _loadSceneDefinition(self):
        direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QtWidgets.QFileDialog.getOpenFileName(None, tr('Scene file'),direc,"Json (*.json)")
        try:
            if not filename is None and len(filename[0].strip()) > 0:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                with open(filename[0],'r') as ser:
                    result = json.load(ser)
                    meshData = result['mesh']
                    tfile = tempfile.NamedTemporaryFile(suffix=".obj",delete=False)
                    with open(tfile.name,'w') as ser:
                        ser.write(meshData)                        
                    self.computedFluxes = dict()
                    self.sourceTable.setRowCount(0)
                    self.activeSources.clear()        
                    self._loadMesh([tfile.name])
                    sources = result['sources']
                    for s,v in sources.items():
                        self.insertSource(v)
                    self.zincGraphics.setColorBarFontColor(str('black'))
                    self.update()
                    tfile.close()
                    os.remove(tfile.name)
        except Exception as e:
            QtWidgets.QMessageBox.critical(None,tr("Failed to Save"),"%s %s"%(tr("Saving failed with error"),str(e)))
            self.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "Failed to load file", str(e))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            
    def _saveRadiationModel(self):
        if hasattr(self, 'radiationFlux'):
            direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
            filename = QtWidgets.QFileDialog.getSaveFileName(None, tr('Radiation filename'),direc,"Json (*.json)")
            if not filename is None and len(filename[0].strip()) > 0:
                with open(filename[0],'w') as ser:
                    json.dump(self.radiationFlux.tolist(),ser)
                self.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))

    def _loadMeshGUI(self):
        self._loadMesh()

    def _loadMeshData(self,mshData):
        tmpfile = tempfile.NamedTemporaryFile(suffix='.obj', delete=False)
        with open(tmpfile.name,'w') as ser:
            print(mshData,file=ser)
        self.humanParam = HumanModel(tmpfile.name,2/3.0,True)
        self.humanParam.generateMesh(self.zincContext,zeroCenter=True) #Re-create with more time values when the simulation is completed
        self.zincGraphics = GenerateZincGraphicsElements(self.zincContext,'manequin')
        self.zincGraphics.createGraphicsElements()
        lengths = self.humanParam.bbox[0]-self.humanParam.bbox[1]
        self.centroidGraphics = self.zincGraphics.createCentroidGlyph(self.humanParam.centroid*0,lengths)
        self.zincGraphics.hideColorBar()
        self.centroidVisible = False
        self.computedFluxes = dict() 
        self.meshLoaded = True
        self.currentMeshData = mshData
        self.update()

        tmpfile.close()
        os.remove(tmpfile.name)

    def _loadMesh(self,filename=None):
        if filename is None:
            direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
            filename = QtWidgets.QFileDialog.getOpenFileName(None, tr('Load Mesh OBJ file'),direc,"OBJ (*.obj)")
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            QtWidgets.QApplication.processEvents()
            self.clearMesh()
            if not filename is None and len(filename[0].strip()) > 0:
                self.humanParam = HumanModel(filename[0],2/3.0,True)
                self.humanParam.generateMesh(self.zincContext,zeroCenter=True) #Re-create with more time values when the simulation is completed
                self.zincGraphics = GenerateZincGraphicsElements(self.zincContext,'manequin')
                self.zincGraphics.createGraphicsElements()
                lengths = self.humanParam.bbox[0]-self.humanParam.bbox[1]
                self.centroidGraphics = self.zincGraphics.createCentroidGlyph(self.humanParam.centroid*0,lengths)
                self.zincGraphics.hideColorBar()
                self.centroidVisible = False
                self.computedFluxes = dict()   
                self.meshLoaded = True
                with open(filename[0],'rb') as ld:
                    self.currentMeshData = ld.read()
                self.update()
                self.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))
                self.meshWindow.viewAll()   
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "Failed to load file", str(e))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
    
    def _saveSceneDefinition(self):
        if self.meshLoaded:
            result = dict()
            result['mesh'] = self.currentMeshData
            itms = dict()
            for r in range(self.sourceTable.rowCount()):
                uset = []
                for c in range(5):
                    itm = self.sourceTable.item( r, c )
                    if itm is not None:
                        uset.append(itm.text())
                    else:
                        uset.append('')
                itm = self.sourceTable.cellWidget( r, 5 )
                col = itm.palette().color(QtGui.QPalette.Button)
                uset.append(col.name())
                itm = self.sourceTable.item( r, 6)
                uset.append(itm.text())
                itms[uset[-1]]=uset
            result['sources'] = itms
            direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
            filename = QtWidgets.QFileDialog.getSaveFileName(None, tr('Save scene definition'),direc,"JSON (*.json)")
            try:
                if not filename is None and len(filename[0].strip()) > 0:
                    with open(filename[0],'w') as ser:
                        json.dump(result,ser)
            except Exception as e:
                QtWidgets.QMessageBox.critical(None,tr("Failed to Save"),"%s %s"%(tr("Saving failed with error"),str(e)))


        
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    obj = RadiationDefinitionWidget()
    obj.show()
    sys.exit(app.exec_())      