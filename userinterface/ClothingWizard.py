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
import tempfile

API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)
import logging
import sys
from PyQt5 import QtCore, QtWidgets, uic, QtGui
import os, json
import numpy as np
from collections import OrderedDict
from copy import deepcopy
from zincwidgets.sceneviewerwidget import SceneviewerWidget
from opencmiss.zinc.context import Context
from userinterface.LoadOBJClothingModel import ClothingMeshModel

try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)

def tr(msg):
    return _translate("ClothingWizard", msg, None)


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



uiFile = os.path.join(dir_path,"./uifiles/clothingdesigner.ui")

form,base = uic.loadUiType(uiFile)


class FabricList(QtWidgets.QWidget):
    '''
    List the fabrics in the local fabrics database
    '''
    database = os.path.join(dir_path,"./database/fabrics.json")
    
    selection = QtCore.pyqtSignal(object)
    
    def __init__(self,parent=None):
        super(QtWidgets.QWidget,self).__init__(parent)
        fabrics = []
        try:
            with open(self.database,'r') as ser:
                fabrics = json.load(ser)
        except:
            logging.error("Unable to load fabrics database")
        model = QtGui.QStandardItemModel(len(fabrics), 4)
        self.dataModel = model
        model.setHorizontalHeaderLabels([tr('Name'), tr('Thickness'), tr('Thermal Resistance'),tr('Evaporative Resistance')])
        for row, arr in enumerate(fabrics):
            for col , text in enumerate(arr):
                item = QStandardItemWithHash(text)
                model.setItem(row, col, item)
        
        # filter proxy model
        filter_proxy_model = QtCore.QSortFilterProxyModel()
        filter_proxy_model.setSourceModel(model)
        filter_proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        filter_proxy_model.setFilterKeyColumn(0) # first column
        
        # line edit for filtering
        layout = QtWidgets.QVBoxLayout(self)
        line_edit = QtWidgets.QLineEdit()
        line_edit.textChanged.connect(filter_proxy_model.setFilterRegExp)
        layout.addWidget(line_edit)
        
        # table view
        self.tableView = QtWidgets.QTableView()
        self.tableView.setModel(filter_proxy_model)
        self.tableView.resizeColumnsToContents()
        self.tableView.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.tableView)  
        
        self.numFabrics = len(fabrics)    

        self.tableView.doubleClicked.connect(self.reportSelection)
        #To not cause QTimer error at close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        
    def reportSelection(self,index):
        item = self.tableView.selectedIndexes()[0]
        #Map from proxy to model
        mindex = item.model().mapToSource(index)
        row = mindex.row()
        fir=list(map(str,[self.dataModel.item(row,0).text(),self.dataModel.item(row,1).text(),self.dataModel.item(row,2).text(),self.dataModel.item(row,3).text()]))          
        self.selection.emit(fir) 

    def reload(self):
        self.dataModel.clear()
        self.dataModel.setHorizontalHeaderLabels([tr('Name'), tr('Thickness'), tr('Thermal Resistance'),tr('Evaporative Resistance')])
        fabrics = []
        try:
            with open(self.database,'r') as ser:
                fabrics = json.load(ser)
        except:
            logging.error(tr("Failed to load fabrics"))
        for row, arr in enumerate(fabrics):
            for col , text in enumerate(arr):
                item = QStandardItemWithHash(text)
                self.dataModel.setItem(row, col, item)
        self.numFabrics = len(fabrics)

    def addItem(self,arr):
        rItems = []
        for text in arr:
            item = QStandardItemWithHash(text)
            rItems.append(item)
            
        self.dataModel.appendRow(rItems)
        fabrics = []
        try:
            with open(self.database,'r') as ser:
                fabrics = json.load(ser)
        except:
            logging.error(tr("Failed to load fabrics"))
        appendData = True
        for i,fa in enumerate(fabrics):
            if fa[0] == arr[0]:
                msgBox = QtWidgets.QMessageBox.question(self, tr("Fabric Exists"),tr("Fabric %s already exists! Overwrite?") % arr[0], QtWidgets.QMessageBox.Yes , QtWidgets.QMessageBox.No)
                result = msgBox.exec_()
                if result == QtWidgets.QMessageBox.Yes:
                    fabrics[i] = arr
                appendData = False
                break
        if appendData:
            fabrics.append(arr)   
        self.numFabrics = len(fabrics)        
        try:
            with open(self.database,'w+') as ser:
                json.dump(fabrics, ser)
        except:
            QtWidgets.QMessageBox.critical(self, tr("Failed"), tr("Unable to update permanent store!"))
            logging.error(tr("Failed to update permanent store"))
        self.reload()


class QStandardItemWithHash(QtGui.QStandardItem):
    
    def __hash__(self, *args, **kwargs):
        return id(self)

class ClothingDefinitionWidget(base, form):
    '''
    Define clothing layer for thermoregulation simulations
    '''

    clothingMeshFile = None
    clothingMeshData = None
    def __init__(self,title='Clothing Definition',parent=None):
        super(base,self).__init__(parent)
        self.zincContext = Context(str('ClothingModel'))
        self.setupUi(self)
        self.viewAllScene.setEnabled(False)
        self.mvLayout = QtWidgets.QVBoxLayout(self.modelView)
        self.mvLayout.setSpacing(0)
        self.mvLayout.setContentsMargins(0,0,0,0)
        self.mvLayout.setObjectName("mvLayout")
        self.meshWindow = SceneviewerWidget(self.modelView)
        self.meshWindow.setContext(self.zincContext)
        self.mvLayout.addWidget(self.meshWindow)
                        
        self.dataModel = QtGui.QStandardItemModel(0,1)
        items = ['Head','Chest','Back','Pelvis','Shoulder','Arm','Hand','Thigh','Leg','Foot']
        self.rootItems = dict()
        self.itemChildren = dict()
        self.itemMetaData = dict()
        Rea,Rt = self.computeNudeCoefficients(0.0)
        skinparam = {'TYPE':'LAYER','INDEX':'0','NAME':'SKIN','THICKNESS':'0.0','Rea':Rea,'Ret':Rt,'Vel':0.0}
        self.settingdata = False
        for ix,itm in enumerate(items):
            nodeItem = QStandardItemWithHash(tr(itm))
            self.rootItems[itm] = nodeItem
            nodeItem.setEditable(False)
            self.itemMetaData[nodeItem] = {'TYPE':'ANATOMY','ITEM':itm,'INDEX':ix}
            nudeItem = QStandardItemWithHash('SKIN')
            nudeItem.setEditable(False)
            sm = deepcopy(skinparam)
            sm['ITEM'] = itm
            self.itemMetaData[nudeItem] = sm
            nodeItem.insertRow(0, [nudeItem])
            ic = OrderedDict()
            ic[0] = nudeItem
            self.itemChildren[itm] = ic 
            self.dataModel.appendRow(nodeItem)
        self.dataModel.setHorizontalHeaderLabels(['Body Part'])
        self.anatomyView.setModel(self.dataModel)
        self._setConnections()
        self.setUpLayerData(self.itemMetaData[self.itemChildren['Head'][0]])
        
        hsi = self.dataModel.indexFromItem(self.rootItems['Head'])
        self.anatomyView.expand(hsi)
        #Fabric database interface
        self.fdb = FabricList()
        self.fdb.selection.connect(self.setFabricValues)
        
        self.setObjectName('ClothingWizard')
        #To not cause QTimer error at close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.cache = DummyCache()
        self.setWindowTitle(tr(title))

    def setCache(self,cache):
        self.cache = cache

    def _setConnections(self):
        self.anatomyView.clicked.connect(self.setAnatomy)
        self.velocityOfAir.textChanged.connect(self.voaChanged)
        self.layer.valueChanged.connect(self.layerValueChanged)
        self.loadZincMesh.clicked.connect(self._loadZincMesh)
        self.loadFabricModel.clicked.connect(self._loadFabricModel)
        self.saveFabricModel.clicked.connect(self._saveFabricModel)
        self.setLayerModel.clicked.connect(self._setLayerModel)
        self.removeLayerModel.clicked.connect(self._removeLayerModel)
        self.loadClothingModel.clicked.connect(self._loadClothingModel)
        self.saveClothingModel.clicked.connect(self._saveClothingModel)
        self.viewAllScene.clicked.connect(self._viewAllScene)
        #Connect zinc graphics ready
        self.meshWindow.graphicsInitialized.connect(self.setMeshSceneFilter)
    
    def setMeshSceneFilter(self):
        '''
        Set the scene view filter if necessary
        '''
        pass
    
    def _viewAllScene(self):
        '''
        Show all the mesh contents
        '''
        self.viewAllScene.setEnabled(True)
    
    def _loadZincMeshFromFile(self,filename):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            clothingModel = ClothingMeshModel(filename)
            clothingModel.generateMesh(self.zincContext, 'clothing')
            #Render
            clothingModel.createSurfaceGraphics()
            self.meshWindow.viewAll()
            self.viewAllScene.setEnabled(True)
            self.clothingMeshFile = filename
            cfile = open(filename,'rb')
            self.clothingMeshData = cfile.read()
        except Exception as ex:
            self.clothingMeshData = None
            QtWidgets.QMessageBox.critical(self, tr("Error"), '%s %s\n%s %s'%(tr("Failed to load file"),filename, tr("Error"),str(ex)))
            logging.error('%s %s\n%s %s'%(tr("Failed to load file"),filename, tr("Error"),str(ex)))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

    def _loadZincMesh(self):
        '''
        Load a obj file for visualization
        '''
        direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QtWidgets.QFileDialog.getOpenFileName(None, tr('Obj file'),direc,'OBJ (*.obj)')
        self.clothingMeshFile = None
        if not filename is None and len(filename[0].strip()) > 0:
            self._loadZincMeshFromFile(filename[0])
            self.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))
            
    def setFabricValues(self,arr):
        '''
        Set the fabric form values from the array - called when set using values from fabric database
        '''
        self.fabricThickness.setText(arr[1])
        self.fabricThermalResistance.setText(arr[2])
        self.fabricEvaporativeResistance.setText(arr[3])
        self.fabricName.setText(arr[0])
        self.fdb.hide()
                
    def _loadFabricModel(self):
        '''
        Show the load fabric model dialog
        '''
        try:
            self.fdb.show()
        except RuntimeError:
            logging.error(tr("Failed to load fabric model"))
            self.fdb = FabricList()
            self.fdb.selection.connect(self.setFabricValues)
            self.fdb.show()

    def _saveFabricModel(self):
        '''
        Add current fabric form values to the fabrics database
        '''
        fric = list(map(str,[self.fabricName.text(),self.fabricThickness.text(), self.fabricThermalResistance.text(),self.fabricEvaporativeResistance.text()]))
        self.fdb.addItem(fric)

    def _removeLayerModel(self):
        '''
        Remove the current layer from the clothing list
        '''
        layer = int(self.layer.value())
        if layer==0:
            QtWidgets.QMessageBox.critical(self, tr("Invalid selection"), tr("Cannot remove skin layer"))
            return
        bpart = str(self.BodyPart.text())
        children = self.itemChildren[bpart]
        
        if layer in children:
            self.rootItems[bpart].takeRow(layer)
            del children[layer]
            self.itemChildren[bpart] = children
        ks = list(children.keys())[-1]
        self.layerValueChanged(ks)

    def loadClothingValues(self,values):
        self.dataModel.clear()
        #Clear clears the header too
        self.dataModel.setHorizontalHeaderLabels(['Body Part'])
        dataValues = dict()
        indexes = OrderedDict()
        for v in values:
            d = v
            if d['TYPE']=='ANATOMY':
                indexes[int(d['INDEX'])] = d['ITEM'] 
            elif d['TYPE']=='LAYER':
                if d['ITEM'] not in dataValues:
                    dataValues[d['ITEM']] = []
                dataValues[d['ITEM']].append(d)
                
        self.rootItems = dict()
        self.itemChildren = dict()
        self.itemMetaData = dict()

        self.settingdata = False
        self.dataModel.setRowCount(len(indexes))
        skeys = sorted(indexes.keys())
        for ix in skeys:
            itm = indexes[ix]
            nodeItem = QStandardItemWithHash(itm)
            self.rootItems[itm] = nodeItem
            nodeItem.setEditable(False)
            self.itemMetaData[nodeItem] = {'TYPE':'ANATOMY','ITEM':itm,'INDEX':ix}
            ivalues = dataValues[itm]
            sortedValues = [None]*len(ivalues)
            for v in ivalues:
                sortedValues[int(v['INDEX'])] = v
            ic = OrderedDict()
            for i,v in enumerate(sortedValues):
                if v is None:
                    continue
                nudeItem = QStandardItemWithHash(v['NAME'])
                nudeItem.setEditable(False)
                self.itemMetaData[nudeItem] = v
                nodeItem.insertRow(i, [nudeItem])
                ic[i] = nudeItem
            self.itemChildren[itm] = ic 
            self.dataModel.insertRow(ix,nodeItem)
        topItem = indexes[skeys[0]]
        #Get the furthest layer
        v = list(self.itemChildren[topItem].keys())
        self.setUpLayerData(self.itemMetaData[self.itemChildren[topItem][v[-1]]])
        hsi = self.dataModel.indexFromItem(self.rootItems[topItem])
        self.anatomyView.expand(hsi)

        

    def _loadClothingModel(self):
        direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QtWidgets.QFileDialog.getOpenFileName(None, tr('Clothing filename'),direc,"JSON (*.json)")
        if not filename is None and len(filename[0].strip()) > 0:
            with open(filename[0],'r') as ser:
                model = json.load(ser)
                if 'CLOTHINGMESHDATA' in model and model['CLOTHINGMESHDATA'] is not None:
                    self.clothingMeshData = model['CLOTHINGMESHDATA']
                    namedFile = tempfile.NamedTemporaryFile(mode='wb',suffix='.obj', delete=False)
                    namedFile.write(model['CLOTHINGMESHDATA'].encode('utf-8'))
                    namedFile.close()
                    self._loadZincMeshFromFile(namedFile.name)
                    os.remove(namedFile.name)
                self.loadClothingValues(model['LAYERS'])
                self.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))

                    

    def _saveClothingModel(self):
        direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
        filename = QtWidgets.QFileDialog.getSaveFileName(None, tr('Clothing filename'),direc,"JSON (*.json)")
        if not filename is None and len(filename[0].strip()) > 0:
            with open(filename[0],'w') as ser:
                if not self.clothingMeshData is None:
                    json.dump({'CLOTHINGMESHDATA':self.clothingMeshData.decode('utf-8'),'LAYERS':list(self.itemMetaData.values())}, ser)
                else:
                    json.dump({'LAYERS': list(self.itemMetaData.values())}, ser)
                self.cache.set('LASTSUCCESSFULWORKSPACE',os.path.dirname(filename[0]))

    def _setLayerModel(self):
        '''
        Set current fabric values to the current layer for the anatomy
        '''
        bpart = str(self.BodyPart.text())
        children = self.itemChildren[bpart]
        layer = int(self.layer.value())
        mdata = dict()
        mdata['TYPE'] = 'LAYER'
        mdata['INDEX'] = layer
        mdata['NAME'] = str(self.fabricName.text())
        mdata['ITEM'] = bpart
        mdata['Vel'] = 0.0
        if layer==0:
            try:
                mdata['Vel'] = float(self.velocityOfAir.text())
                if mdata['Vel'] < 0.0:
                    raise
            except:
                QtWidgets.QMessageBox.critical(self, tr("Invalid data"), tr("Velocity of Air is incorrect"))
                logging.error(tr('Velocity of Air is incorrect'))
                return
        
        try:
            mdata['THICKNESS'] = float(self.fabricThickness.text())
            if mdata['THICKNESS'] < 0.0:
                raise
        except:
            QtWidgets.QMessageBox.critical(self, tr("Invalid data"), tr("Thickness is incorrect"))
            logging.error(tr('Thickness is incorrect'))
            return
        try:    
            mdata['Rea'] = float(self.fabricEvaporativeResistance.text())
            if mdata['Rea'] < 0.0:
                raise
        except:
            QtWidgets.QMessageBox.critical(self, tr("Invalid data"), tr("Evaporative resistance value is incorrect"))
            logging.error(tr('Evaporative resistance is incorrect'))
            return
        try:
            mdata['Ret'] = float(self.fabricThermalResistance.text())
            if mdata['Ret'] < 0.0:
                raise
        except:
            QtWidgets.QMessageBox.critical(self, "Invalid data", "Thermal resistance is incorrect")
            logging.error('Thermal resistance is incorrect')
            return
        
        if layer not in children:
            newItem = QStandardItemWithHash(mdata['NAME'])
            newItem.setEditable(False)
            self.itemMetaData[newItem] = mdata
            self.rootItems[bpart].insertRow(layer, [newItem])
            self.itemChildren[bpart][layer] = layer
        self.itemMetaData[children[layer]] = mdata
                

    def layerValueChanged(self,ivl):
        '''
        Set the layer number related Values if data is already available else setup a clean slate
        '''
        if self.settingdata ==False:
            bpart = str(self.BodyPart.text())
            children = self.itemChildren[bpart]
            self.velocityOfAir.setVisible(False)
            self.velocityOfAirLabel.setVisible(False)
            self.removeLayerModel.setEnabled(True)
            if ivl==0:
                self.velocityOfAir.setVisible(True)  
                self.velocityOfAirLabel.setVisible(True)     
                self.removeLayerModel.setEnabled(False)     
            if ivl in children:
                idata = children[ivl]
                mdata = self.itemMetaData[idata]
                self.setUpLayerData(mdata)
            else:
                self.fabricName.setText('')
                self.fabricThickness.setText(' ')
                self.fabricEvaporativeResistance.setText(' ')
                self.fabricThermalResistance.setText(' ')
                self.velocityOfAir.setText(' ')      
                                  
    def voaChanged(self):
        '''
        Change Rea and Rt values for skin layer
        '''
        if not self.settingdata and self.layer.value() == 0:
            Rea,Rt = self.computeNudeCoefficients(float(str(self.velocityOfAir.text())))
            self.fabricEvaporativeResistance.setText(str(Rea))
            self.fabricThermalResistance.setText(str(Rt))
                
    def computeNudeCoefficients(self,velocityOfAir):
        '''
        Compute the value for Rt, Rea based on velocity of Air for SKIN
        '''
        #Calculate Rea and Ret 
        lam = 2257e3 #latent heat of evaporation of water in Jkg^-1
        #Based on X. Wan, J. Fan, J. Therm Biol, 33, 2008, 87-97
        Rea = lam/(2430e3/0.1353*np.sqrt(0.11+velocityOfAir))
        hr = 5.0 # Room temperature value for black radiators
        Rt = (hr+8.3*np.sqrt(0.11+velocityOfAir))
        return Rea,Rt       

    def setUpLayerData(self,mdata):
        '''
        Setup the layer data based on prior assignment for the anatomy
        '''
        self.settingdata = True
        layer = int(mdata['INDEX'])
        self.BodyPart.setText(mdata['ITEM'])
        self.layer.setValue(layer)
        self.velocityOfAir.setVisible(False)
        self.velocityOfAirLabel.setVisible(False)
        self.removeLayerModel.setEnabled(True)
        if layer==0:
            self.velocityOfAir.setVisible(True)
            self.velocityOfAirLabel.setVisible(True)
            self.removeLayerModel.setEnabled(False)
        self.fabricName.setText(mdata['NAME'])
        self.fabricThickness.setText(str(mdata['THICKNESS']))
        self.fabricEvaporativeResistance.setText(str(mdata['Rea']))
        self.fabricThermalResistance.setText(str(mdata['Ret']))
        self.velocityOfAir.setText(str(mdata['Vel']))
        self.settingdata = False
                
    def setAnatomy(self,index):
        '''
        Set the fabric values for the current anatomy - if multiple layers, show the outermost layer's fabric values
        '''
        item = self.anatomyView.selectedIndexes()[0]
        ditem = item.model().itemFromIndex(index)
        try:
            mdata = None
            idata = self.itemMetaData[ditem]
            if idata['TYPE'] == 'ANATOMY': #anatomy selected
                #Only show tree associated with this item
                self.anatomyView.collapseAll()
                hsi = self.dataModel.indexFromItem(self.rootItems[idata['ITEM']])
                self.anatomyView.expand(hsi)
                #Set the furthest child 
                children = self.itemChildren[idata['ITEM']]
                ks = list(children.keys())[-1]
                selected = children[ks]
                mdata = self.itemMetaData[selected]
            elif idata['TYPE'] == 'LAYER': 
                mdata = idata
            if not mdata is None:
                self.setUpLayerData(mdata)
        except:
            logging.error(tr("Failed to set anatomy"))
        
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    obj = ClothingDefinitionWidget()
    obj.show()
    sys.exit(app.exec_())  