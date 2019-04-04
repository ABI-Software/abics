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
API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)

import logging
import traceback,sys
from PyQt5 import QtCore
from PyQt5.Qt import pyqtSignal
import numpy as np
import os
from thermoregulation.Tanabe65MN import Tanabe65MNProjectedToStandard16,\
    Tanabe65MNModel
from support.Interfaces import ClothingResistanceModel, RadiationModel


class SimulationData(object):
    
    def __init__(self,tanabeModel,numberOfTimeSamples):
        self.dofIndexes= tanabeModel.getDofIndexes()
        self.bodySurfaceArea=tanabeModel.getBodySurfaceArea()
        self.nDofs = tanabeModel.getNumberOfDofs()
        self.numberOfTimeSamples = numberOfTimeSamples
        timeSamples = self.numberOfTimeSamples
        self.timeValue = np.zeros(timeSamples)
        self.pmv = np.zeros(timeSamples)
        self.ppd = np.zeros(timeSamples)
        self.sensation = [None]*timeSamples
        self.meanSkinTemperature = np.zeros(timeSamples)
        self.meanCoreTemperature = np.zeros(timeSamples)
        self.rectalTemperature   = np.zeros(timeSamples)
        self.meanThermalResistance= np.zeros(timeSamples)
        self.meanEvaporativeResistance= np.zeros(timeSamples)
        self.skinTemperature = np.zeros((self.nDofs,timeSamples))
        self.coreTemperature = np.zeros((self.nDofs,timeSamples))
        self.skinWettedness = np.zeros((self.nDofs,timeSamples))
        self.thermalResistance= np.zeros((self.nDofs,timeSamples))
        self.evaporativeResistance= np.zeros((self.nDofs,timeSamples))

    def getMeanSegmentCoreTemperature(self,i):
        indexes = self.dofIndexes[i]
        psa = self.bodySurfaceArea[indexes]
        tcr = self.coreTemperature[indexes,:]*psa[:, np.newaxis]
        return np.sum(tcr,axis=0)/np.sum(psa)
    
    def getMeanSegmentSkinTemperature(self,i):
        indexes = self.dofIndexes[i]
        psa = self.bodySurfaceArea[indexes]
        tcr = self.skinTemperature[indexes,:]*psa[:, np.newaxis]
        return np.sum(tcr,axis=0)/np.sum(psa)

    
class Simulator(object):
    '''
    Instance that runs simulations based on Activity and target human mesh data
    '''

    numberOfSubSteps = 10
    setupError = None
    def __init__(self):
        super(Simulator,self).__init__()
        
    def setup(self, activities,humanModel,projectedSimulation=True,numberOfSubSteps=10):
        '''
        activities - list of activities with clothing, velocity Of Air, radiation Data
        humanModel - target human model based on which simulations should be setup
        projectedSimulation - Use the standard 16 segment anatomy model
        numberOfSubSteps - number of sub steps to be simulated per duration (number of samples along time)
        '''        
        self.numberOfSubSteps = numberOfSubSteps
        self.activities = activities
        self.humanModel = humanModel
        self.projectedSimulation = projectedSimulation
        self.currentTimeIndex = 0
        self.setupActivities()
        
    def setupActivities(self):
        self.numActivities = len(self.activities)-1
        self.timeValues = np.zeros(self.numActivities)
        self.temps = np.zeros(self.numActivities)
        self.mets = np.zeros(self.numActivities)
        self.rh = np.zeros(self.numActivities)
        self.voa = np.zeros(self.numActivities)
        self.clothingData = []
        self.radiationData  = []
        i = 0
        for act in self.activities.values():
            if isinstance(act,dict):
                self.timeValues[i] = act['duration']
                self.rh[i] = act['rh']/100.0 #Convert from %
                self.temps[i] = act['Tab']
                self.voa[i] = act['velocityOfAir']
                self.mets[i] = act['metabolicActivity']
                cfile =  os.path.abspath(act['clothingFile'])
                if 'definitionDirectory' in act:
                    bdir = act['definitionDirectory']
                    if not os.path.exists(cfile):
                        cfile = os.path.abspath(os.path.join(bdir,act['clothingFile']))
                        
                if os.path.exists(cfile):
                    #self.clothingData.append(cfile)
                    cm = ClothingResistanceModel()
                    cm.loadClothingModelFromFile(cfile)
                    self.clothingData.append(cm)
                else:
                    estr = 'Clothing Data file %s does not exist!'%act['clothingFile']
                    logging.critical(estr)
                    raise ValueError(estr)
                cfile =  os.path.abspath(act['radiationFluxFile'])
                if 'definitionDirectory' in act:
                    bdir = act['definitionDirectory']
                    if not os.path.exists(cfile):
                        cfile = os.path.abspath(os.path.join(bdir,act['radiationFluxFile']))                
                if os.path.exists(cfile) and os.path.isfile(cfile):
                    #self.radiationData.append(cfile)
                    rm = RadiationModel()
                    rm.loadRadiationDataFromFile(cfile)                
                    self.radiationData.append(rm)
                else:
                    self.radiationData.append(None)
                i +=1
            
        self.timeValues = self.timeValues*60.0 #Convert from minutes to seconds
        if self.projectedSimulation:
            self.trModel = Tanabe65MNProjectedToStandard16(self.humanModel)
        else:
            self.trModel = Tanabe65MNModel(self.humanModel)
    
        self.simulationData = SimulationData(self.trModel,self.numActivities*self.numberOfSubSteps)        
    
    def getCurrentStatus(self):
        result = dict()
        result['type'] = 'simulationdata'
        result['data'] = self.simulationData
        result['numberoftimesamples'] = self.simulationData.pmv.shape[0]
        result['currenttimeindex'] = self.currentTimeIndex
        result['timevalues'] = self.timeValues
        return result
    
    def getSimulationResults(self):
        return self.simulationData
    
    def getNumberOfTimeSamples(self):
        return self.simulationData.pmv.shape[0]
    
    def pause(self):
        self.pauseProcessing = True
    
    def stop(self):
        self.currentTimeIndex = 0
        self.timeValue.fill(0.0)
            
    def getSolvedTimeIndex(self):
        return self.currentTimeIndex
        
    def run(self):
        self.setupError=None
        try:
            t = self.timeValues[self.currentTimeIndex]
            #cm = ClothingResistanceModel()
            #cm.loadClothingModelFromFile(self.clothingData[self.currentTimeIndex])
            cm = self.clothingData[self.currentTimeIndex]
            cm.setVelocityOfAir(self.voa[self.currentTimeIndex])           
            self.trModel.setClothingModel(cm)
            if not self.radiationData[self.currentTimeIndex] is None:
                #rm = RadiationModel()
                #rm.loadRadiationDataFromFile(self.radiationData[self.currentTimeIndex])
                rm = self.radiationData[self.currentTimeIndex]
                self.trModel.setRadiationFlux(rm)
            self.trModel.setTa(self.temps[self.currentTimeIndex])
            self.trModel.setRelativeHumidity(self.rh[self.currentTimeIndex])
            if self.currentTimeIndex==0:
                temp = self.trModel.getInitialConditions()
                self.trModel.setInitialConditions(temp)
            self.trModel.setMet(self.mets[self.currentTimeIndex])
            self.trModel.getW()
            
            tms = t/self.numberOfSubSteps
            for i in range(self.numberOfSubSteps):
                self.trModel.solve(tms)
                pmv,ppd,sens = self.trModel.ZhangPMVPPD()
                tidx = self.currentTimeIndex*self.numberOfSubSteps+i
                self.simulationData.timeValue[tidx] = self.simulationData.timeValue[tidx-1] + tms # 
                self.simulationData.pmv[tidx] = pmv  
                self.simulationData.ppd[tidx] = ppd
                self.simulationData.sensation[tidx] = sens
                self.simulationData.meanCoreTemperature[tidx] = self.trModel.getMeanCoreTemperature()
                self.simulationData.meanSkinTemperature[tidx] = self.trModel.getMeanSkinTemperature()
                self.simulationData.rectalTemperature[tidx]   = self.trModel.getRectalTemperature()
                self.simulationData.meanThermalResistance[tidx] = self.trModel.getMeanThermalResistance()
                self.simulationData.meanEvaporativeResistance[tidx] = self.trModel.getMeanEvaporativelResistance()
                
                sTemp = self.trModel.getTemperature()
                self.simulationData.skinTemperature[:,tidx] = sTemp[:,3]
                self.simulationData.coreTemperature[:,tidx] = sTemp[:,0]
                self.simulationData.skinWettedness[:,tidx] = self.trModel.getSkinWettedness()
                self.simulationData.evaporativeResistance[:,tidx] = self.trModel.getEffectiveEvaporativeResistance()
                self.simulationData.thermalResistance[:,tidx] = self.trModel.getEffectiveThermalResistance()
        except IndexError as ie:
            self.setupError = ie
            logging.error("Current time index is incorrect")
            traceback.print_exc(file=sys.stdout)
        except Exception as e:
            self.setupError = e
            traceback.print_exc(file=sys.stdout)


from multiprocessing import Process, Queue

def simulationProcess(simulator,parentQ,childQ):
    stopProcessing = False

    maxSteps = simulator.timeValues.shape[0]
    stepFactor = 100.0/float(maxSteps)
    if stepFactor>1:
        stepFactor = 1.0/float(maxSteps)
    childQ.put_nowait({'type':'status','progress':0.25})
    try:
        while simulator.currentTimeIndex < maxSteps:
            if not parentQ.empty():
                res = parentQ.get_nowait()
                if isinstance(res,dict):
                    if 'comm' in res and res['comm']=='stop':
                        stopProcessing = True
                    elif 'comm' in res and res['comm']=='status':
                        childQ.put_nowait(simulator.getCurrentStatus())
            if not stopProcessing:
                simulator.run()
                if simulator.setupError is not None:
                    childQ.put_nowait({'type':'status','error':str(simulator.setupError),'simulationResults':simulator.getCurrentStatus()})
                    break
                #print(simulator.currentTimeIndex,stepFactor,0.25+0.75*simulator.currentTimeIndex*stepFactor)
                childQ.put_nowait({'type':'status','progress':0.25+0.75*simulator.currentTimeIndex*stepFactor})
                simulator.currentTimeIndex +=1
            else:
                break
        childQ.put_nowait(simulator.getCurrentStatus())    
    except Exception as e:
        childQ.put_nowait({'type':'status','error':str(e),'simulationResults':simulator.getCurrentStatus()})
    finally:
        childQ.put_nowait({'type':'status','completed':True,'simulationResults':simulator.getCurrentStatus()})
        childQ.close()

class SimulationProcessManager(QtCore.QThread):
    '''
    Instance that runs simulations based on Activity and target human mesh data
    '''
    completed = pyqtSignal(object)
    progress  = pyqtSignal(float)
    pauseProcessing = False
    stopProcessing  = False
    numberOfSubSteps = 10
    
    def __init__(self,parent=None):
        super(SimulationProcessManager,self).__init__(parent)
        
        
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
    
    def getSimulationResults(self):
        if not hasattr(self, 'simulationResults'):
            self.parent_conn.put({'comm':'status'})
            res = self.child_conn.get()
            while res['type'] != 'simulationdata':
                if res['type']=='status':
                    if not (self.stopProcessing or self.pauseProcessing):
                        self.progress.emit(float(res['progress']))
                res = self.child_conn.get()
            self.simulationResults = res
        return self.simulationResults['data']
    
    def getNumberOfTimeSamples(self):
        if not hasattr(self, 'simulationResults'):
            self.parent_conn.put({'comm':'status'})
            res = self.child_conn.get()
            while res['type'] != 'simulationdata':
                if res['type']=='status':
                    if not (self.stopProcessing or self.pauseProcessing):
                        self.progress.emit(float(res['progress']))
                res = self.child_conn.get()
            self.simulationResults = res
        return self.simulationResults['numberoftimesamples']
    
    def pause(self):
        self.pauseProcessing = True

    def stop(self):
        self.stopProcessing = True
        self.child_conn.send({'comm':'stop'})
        
    def getSolvedTimeIndex(self):
        return self.simulator.currentTimeIndex
        
    def run(self):
        self.parent_conn = Queue()
        self.child_conn = Queue()
        self.jp = Process(target=simulationProcess, args=(self.simulator,self.parent_conn,self.child_conn,))
        self.jp.start()
        self.error = None
        while True:
            res = self.child_conn.get()
            if isinstance(res,dict):
                if res['type']=='status':
                    if 'progress' in res:
                        if not (self.stopProcessing or self.pauseProcessing):
                            self.progress.emit(float(res['progress']))
                    elif 'error' in res:
                        self.error = res['error']
                        self.simulationResults = res['simulationResults']
                        self.completed.emit(self.simulationResults)
                        break
                    elif 'completed' in res:
                        self.simulationResults = res['simulationResults']
                        self.completed.emit(self.simulationResults)
                        break
                    else:
                        logging.info("Unexpected result from process",res)
                elif res['type'] == 'simulationdata':
                    self.simulationResults = res
        self.jp.join()        
