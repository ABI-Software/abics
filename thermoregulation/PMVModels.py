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
import numpy as np
class ZhangModel(object):
    '''
    Implementation of dynamic Zhang model Based on A human thermal model for improved thermal comfort, PhD Thesis
    '''
    thermalSensationWeightingFactors = dict()
    thermalSensationWeightingFactors['Head']= 0.07
    thermalSensationWeightingFactors['Chest']= 0.35
    thermalSensationWeightingFactors['Lower arm']= 0.14
    thermalSensationWeightingFactors['Hand']= 0.05
    thermalSensationWeightingFactors['Thigh']= 0.19
    thermalSensationWeightingFactors['Lower leg']= 0.13
    thermalSensationWeightingFactors['Foot']= 0.07
        
    partSpecificRegressionCoefficients = dict()
    #C1, C1, K1, C2, C2, C3
    partSpecificRegressionCoefficients['Face']= [0.15, 0.70, 0.10,37, 105, -2289]
    partSpecificRegressionCoefficients['Head']= [0.38, 1.32, 0.18,543, 90, 0]
    partSpecificRegressionCoefficients['Neck']= [0.40, 1.25, 0.15,173, 217, 0]
    partSpecificRegressionCoefficients['Chest']= [0.35, 0.60, 0.10,39, 136, -2135]
    partSpecificRegressionCoefficients['Back']= [0.30, 0.70, 0.10,88, 192, -4054]
    partSpecificRegressionCoefficients['Pelvis']=[0.20, 0.40, 0.15,75, 137, -5053]
    partSpecificRegressionCoefficients['Upper arm']= [0.29, 0.40, 0.10,156, 167, 0]
    partSpecificRegressionCoefficients['Lower arm']=[0.30, 0.70, 0.10,144, 125, 0]
    partSpecificRegressionCoefficients['Hand']= [0.20, 0.45, 0.15,19, 46, 0]
    partSpecificRegressionCoefficients['Thigh']= [0.20, 0.29, 0.11,151, 263, 0]
    partSpecificRegressionCoefficients['Lower leg']= [0.29, 0.40, 0.10,206, 212, 0]
    partSpecificRegressionCoefficients['Foot']= [0.25, 0.26, 0.15,109, 162, 0 ]
    sixteenSegmentkeys = ['Head','Chest','Back','Pelvis','L-shoulder','R-shoulder','L-arm','R-arm','L-hand','R-hand','L-thigh','R-thigh','L-leg','R-leg','L-foot','R-foot']
    def __init__(self):
        '''
        Constructor
        '''
        calcKeys = dict()
        calcKeys['Head'] = ['Head']
        calcKeys['Chest'] = ['Chest','Back']
        calcKeys['Lower arm'] = ['L-arm','R-arm']
        calcKeys['Hand'] = ['L-hand','R-hand']
        calcKeys['Thigh'] = ['L-thigh','R-thigh']
        calcKeys['Lower leg'] = ['L-leg','R-leg']
        calcKeys['Foot'] = ['L-foot','R-foot']
        self.calcKeys = calcKeys
    
    
    def computePMV(self,sixteenSegmentSkinTempAndDt,sixteenSegmentCoreTempAndDt,setPointTemp,dt=None):
        '''
        Compute the sensation at either dynamic or steady state
        Steady state seems to provide more convincing values 
        '''
        calcValues = dict()
        dtd = 0.001
        if not dt is None:
            dtd = dt
        for k,v in self.calcKeys.items():
            tsum = np.array([0.0,0.0,0.0,0.0,0.0])
            for ky in v:
                ast = sixteenSegmentSkinTempAndDt[ky]
                act = sixteenSegmentCoreTempAndDt[ky]
                tset = setPointTemp[ky]
                tsum[0] += ast[0]
                tsum[1] += ast[1]/dtd
                tsum[2] += act[0]
                tsum[3] += act[1]/dtd
                tsum[4] += tset
            calcValues[k] = tsum/len(v)
        meanWholeBodySkinTemp = 0.0
        meanWholeBodySetTemp = 0.0
        
        for v in sixteenSegmentSkinTempAndDt.values():
            meanWholeBodySkinTemp += v[0]
        for v in setPointTemp.values():
            meanWholeBodySetTemp += v            
        meanWholeBodySkinTemp /= len(sixteenSegmentSkinTempAndDt)
        meanWholeBodySetTemp /= len(setPointTemp)
        
        localSensation = dict()
        for k,v in calcValues.items():
            slc = self.partSpecificRegressionCoefficients[k]
            C1 = slc[1]
            if v[0] < v[-1]: #tskin,local < tskin,local,set
                C1 = slc[0]
            C2 = slc[4]
            if v[1] < 0: #Dt < 0 - cooling
                C2 = slc[3]
            K1 = slc[2]
            C3 = slc[5]
            if not dt is None:
                slv = 4*(2.0/(1.0+np.exp(-C1*(v[0]-v[-1])-K1*(v[0]-meanWholeBodySkinTemp-v[-1]+meanWholeBodySetTemp)))-1) + C2*v[1] + C3*v[3]
            else:
                slv = 4*(2.0/(1.0+np.exp(-C1*(v[0]-v[-1])-K1*(v[0]-meanWholeBodySkinTemp-v[-1]+meanWholeBodySetTemp)))-1)
            localSensation[k] = slv
            #print k,v,slv
            
        Soverall = 0.0
        for lv,v in localSensation.items():
            Soverall += (v*self.thermalSensationWeightingFactors[lv])
            
        pmv = Soverall
        ppd = 100.0 - 95.0 * np.exp(-0.03353 * np.power(pmv, 4.0) - 0.2179 * np.power(pmv, 2.0))
        pmvr = int(np.ceil(pmv+np.sign(pmv)*0.1))
        feeling = 'error'
        if pmvr <= -4.0:
            feeling = 'Very Cold'
        elif pmvr == -3.0:
            feeling = 'Cold'
        elif pmvr == -2.0:
            feeling = 'Cool'
        elif pmvr == -1:
            feeling = 'Slightly Cool'
        elif pmvr == 0:
            feeling = 'Neutral'
        elif pmvr == 1:
            feeling = 'Slightly Warm'
        elif pmvr == 2:
            feeling = 'Warm'
        elif pmvr == 3:
            feeling = 'Hot'
        elif pmvr >= 4:
            feeling = 'Very Hot'
            
        return pmv,ppd,feeling

import pickle
if __name__ == '__main__':
    zm = ZhangModel()
    keys = ['Head','Chest','Back','Pelvis','L-shoulder','R-shoulder','L-arm','R-arm','L-hand','R-hand','L-thigh','R-thigh','L-leg','R-leg','L-foot','R-foot','cbp']    
    with open('../database/standardData.pickle','r') as ser:
        sd = pickle.load(ser)
        setPointTemperature = sd['setPointTemperature'] 
        thermalConductance = sd['heatCapacity']
        setPointTemp = dict()
        for k,v in enumerate(setPointTemperature):
            setPointTemp[keys[k]] = v[-1]
    for fi in range(1,5):
        with open('%d.pickle'%fi,'r') as ser:
            temperature,dT,dofIndexes = pickle.load(ser)        
            
            
            sixteenSegmentSkinTempAndDt = dict()
            sixteenSegmentCoreTempAndDt = dict()
            
            for i in range(16):
                ast = np.mean(temperature[dofIndexes[i],3])
                asdt =np.mean(dT[dofIndexes[i],3]/thermalConductance[i,3])
                act = np.mean(temperature[dofIndexes[i],0])
                acdt =np.mean(dT[dofIndexes[i],0]/thermalConductance[i,0])
                sixteenSegmentSkinTempAndDt[keys[i]] = [ast,asdt]
                sixteenSegmentCoreTempAndDt[keys[i]] = [act,acdt]
    
            print(fi,'__________________________')            
            print(sixteenSegmentCoreTempAndDt)
            print(sixteenSegmentSkinTempAndDt)
            print(zm.computePMV(sixteenSegmentSkinTempAndDt, sixteenSegmentCoreTempAndDt, setPointTemp))
            print(fi,'__________________________')
        