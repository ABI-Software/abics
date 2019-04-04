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
import sip
import zmq
import uuid
import pickle
from support.Simulations import Simulator
from PyQt5 import QtWidgets
from userinterface.CacheManagement import WorkspaceCache

API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)


try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)

def tr(msg):
    return _translate("ABICSClient", msg, None)

class SimulationRemoteProcessManager(object):
    '''
    Instance that runs simulations based on Activity and target human mesh data
    '''
    
    def __init__(self,serveruri='tcp://localhost',serverport=5570):
        super(SimulationRemoteProcessManager,self).__init__()
        self.context = zmq.Context()
        self.serverURI = serveruri
        self.serverPORT = serverport
        
    def createRemoteTask(self,identity=str(uuid.uuid1())):
        socket = self.context.socket(zmq.DEALER)
        socket.identity = identity.encode('ascii')
        socket.connect('%s:%d'%(self.serverURI,self.serverPORT))
        poll = zmq.Poller()
        poll.register(socket, zmq.POLLIN)
        return RemoteTask(socket,poll)

class RemoteTask(object):
    
    def __init__(self,socket,poll):
        super(RemoteTask,self).__init__()
        self.socket = socket
        self.poll = poll
    
    def getIdentity(self):
        return self.socket.identity
    
    def setup(self, activities,humanModel,projectedSimulation=True,numberOfSubSteps=10):
        '''
        activities - list of activities with clothing, velocity Of Air, radiation Data
        humanModel - target human model based on which simulations should be setup
        projectedSimulation - Use the standard 16 segment anatomy model
        numberOfSubSteps - number of sub steps to be simulated per duration (number of samples along time)
        '''
        self.simulator = Simulator()        
        self.simulator.setup(activities, humanModel, projectedSimulation, numberOfSubSteps)

    def setupSimulator(self,simulator):
        self.simulator = simulator
                
    def submit(self):
        self.socket.send_pyobj({'comm':'start','simulationdef':self.simulator})
        res = self.socket.recv_pyobj()
        return res
    
    def query(self,identity=None):
        '''
        identity should be an array of task identifiers
        '''
        idn = self.socket.identity
        if identity is not None:
            self.socket.send_pyobj({'comm':'getstatus','identity':identity})
        else:
            self.socket.send_pyobj({'comm':'getstatus','identity':[idn]})
        QtWidgets.QApplication.processEvents()
        res = self.socket.recv_pyobj()

        return res
    
    def getResults(self,identity=None):
        idn = self.socket.identity
        if identity is not None:
            idn = identity
        self.socket.send_pyobj({'comm':'getresults','identity':idn})
        res = self.socket.recv_pyobj()
        return res
        
    def remove(self,identify=None):
        idn = self.socket.identity
        if identify is not None:
            idn = identify
        self.socket.send_pyobj({'comm':'remove','identity':idn})
        res = self.socket.recv_pyobj()
        return res
    

class ListServerTasks(QtWidgets.QWidget):
    
    def __init__(self,title="Remote simulations",cache=WorkspaceCache.cache):
        super(ListServerTasks, self).__init__()
        self.setWindowTitle(title)
        self.cache = cache
        self.serveruri  = self.cache.get("serveruri",default='tcp://localhost')
        self.serverport = int(self.cache.get("serverport",default=5570))
        self.tc = SimulationRemoteProcessManager(self.serveruri,self.serverport)
        
        mainlayout = QtWidgets.QVBoxLayout(self)
        l1 = QtWidgets.QLabel("%s :\t%s:%d"%(tr("Remote server connection"),self.serveruri,self.serverport))
        mainlayout.addWidget(l1)
        self.table = QtWidgets.QTableWidget()
        mainlayout.addWidget(self.table)
        controlsLayout = QtWidgets.QHBoxLayout()
        spitem = QtWidgets.QSpacerItem(150, 10, QtWidgets.QSizePolicy.Expanding)
        self.refresh = QtWidgets.QPushButton("Refresh")
        controlsLayout.addItem(spitem)
        controlsLayout.addWidget(self.refresh)
        controlsLayout.setStretch(0,1)
        mainlayout.addLayout(controlsLayout)
        mainlayout.setStretch(1,1)
        self.resize(500,300)
        self.refresh.clicked.connect(self.loadTaskStatus)
        
    def loadTaskStatus(self):
        self.remoteProcessIds = self.cache.get(r'remoteProcessIds%s:%d'%(self.serveruri,self.serverport),default=dict())
        tids = list(self.remoteProcessIds.keys())
        rtask = self.tc.createRemoteTask()
        if len(tids)>0:
            result = rtask.query(tids)
            #result = completions
            #QTableWidget needs number of rows and columns details for custom widgets to work
            tableEntries = dict()
            for tid in tids:
                name = self.remoteProcessIds[tid][0]
            
                try:
                    if result[tid] != 'Not found':
                        prog = float(result[tid])*100.0
                        tableEntries[tid] = [name,prog]
                except:
                    del self.remoteProcessIds[tid]
                    self.cache.set(r'remoteProcessIds%s:%d'%(self.serveruri,self.serverport),self.remoteProcessIds)
            
            self.table.clear()
            self.table.verticalHeader().hide()
            
            self.table.setRowCount(len(tableEntries))
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels([tr("Activity Name"),tr("Progress"),"",""])
            self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
            self.table.horizontalHeader().resizeSection(1,150)
            self.table.horizontalHeader().resizeSection(2,50)
            self.table.horizontalHeader().resizeSection(3,50)
            rc = 0
            for tid,v in tableEntries.items():
                self.table.setItem(rc,0,QtWidgets.QTableWidgetItem(v[0]))
                pbar = QtWidgets.QProgressBar()
                pbar.setMinimum(0)
                pbar.setMaximum(100)
                pbar.setValue(v[1])
                pbar.setTextVisible(True)
                self.table.setCellWidget(rc,1,pbar)
                dbutton = QtWidgets.QToolButton()
                dbutton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowDown))
                dbutton.setProperty('tid',tid)
                dbutton.clicked.connect(self.downloadResults)
                self.table.setCellWidget(rc,2,dbutton)
                rbutton = QtWidgets.QToolButton()
                rbutton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton))
                rbutton.setProperty('tid',tid)
                rbutton.clicked.connect(self.removeSimulation)
                self.table.setCellWidget(rc,3,rbutton)
                rc +=1

            
    def downloadResults(self):
        but = self.sender()
        tid = but.property('tid')
        rtask = self.tc.createRemoteTask()
        res = rtask.getResults(tid)
        projectinfo = self.remoteProcessIds[tid]
        if not 'status' in res:
            if 'error' in res:
                result = QtWidgets.QMessageBox.question(self,tr("Simulation error"),"Error %s.\nContinue?"%res['error'], QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
                if result == QtWidgets.QMessageBox.No:
                    return
            direc = self.cache.get('LASTSUCCESSFULWORKSPACE',default='.')
            filename = QtWidgets.QFileDialog.getSaveFileName(None, tr('Save project'),direc,"Pickle (*.pkl)")
            if not filename is None and len(filename[0].strip()) > 0:
                with open(filename[0],'wb+') as ser:                  
                    projectData = [projectinfo[1],projectinfo[2],res['data'],projectinfo[3],projectinfo[4],projectinfo[5],projectinfo[6]]
                    pickle.dump(projectData,ser)
        else:
            QtWidgets.QMessageBox.critical(None, tr("Failed to download "), res['message'])
            
    
    def removeSimulation(self):
        but = self.sender()
        index = self.table.indexAt(but.pos())
        currentRow = index.row()        
        tid = but.property('tid')
        rtask = self.tc.createRemoteTask()
        res = rtask.remove(tid)
        if res['status']=='success':
            del self.remoteProcessIds[tid]
            self.cache.set(r'remoteProcessIds%s:%d'%(self.serveruri,self.serverport),self.remoteProcessIds)
            self.table.removeRow(currentRow)
        else:
            QtWidgets.QMessageBox.critical(None, "Failed", "Failed to remove simulation and results.\n %s"%res['message'])

import sys
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    diskCacheLocation = r'D:\Temp\ABICS'
    WorkspaceCache.createDefaultCache(str(diskCacheLocation))   
    qw = ListServerTasks(cache=WorkspaceCache.cache)
    qw.show()
    qw.loadTaskStatus()
    sys.exit(app.exec_())
