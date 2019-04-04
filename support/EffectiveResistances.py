from __future__ import unicode_literals,print_function
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
'''
Compute the effective thermal and vapour resistance based on number of layers
Based on Predicting the effect of relative humidity on skin temperature and skin wettedness, Journal of Thermal Biology 31 (2006) 442-452
'''


import json
import numpy as np
from collections import OrderedDict


class ResistanceCalculator(object):
    '''
    A support class to determine the effective thermal and vapour resistance based on the number of layers  
    '''
    k = 24e-3 # m W/m^2/C
    Real_a = 0.0334 #m2 kPa/W
    Real_b = 15e-3 #m
    
    def __init__(self, hr = 5.0, anatomybreadth=None):
        '''
        Constructor
        '''
        self.hr = hr
        self.breadth = anatomybreadth
        if anatomybreadth is None:
            self.breadth = {'Head': 0.142, 'Chest': 0.167, 'Back': 0.167, 'Pelvis': 0.147, 'L-shoulder': 0.117,
                            'R-shoulder': 0.117, 'L-arm' : 0.112, 'R-arm' : 0.112, 'L-hand': 0.052, 'R-hand': 0.0524,
                            'L-thigh': 0.120, 'R-thigh' : 0.118, 'L-leg': 0.082 ,'R-leg': 0.082, 'L-foot': 0.078, 'R-foot' : 0.078}


    def loadClothingModel(self,filename):
        with open(filename,'r') as ser:
            model = json.load(ser)
            values = model['LAYERS']

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

        return dataValues
        
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
            
    def getThermalResistances(self,anatomicalClothingModel,velocityOfAir=0.0):
        '''
        Compute the effective resistance for each anatomical region
        anatomicalClothingModel (dataValues) - is either a 10 segment (symmetric) or 16 segment anatomy model
        '''
        symmetricKeys = ['Shoulder','Arm','Hand','Thigh','Leg','Foot']
        #anatomyKeys = ['Head','Chest','Back','Pelvis','L-shoulder','R-shoulder','L-arm','R-arm','L-hand','R-hand','L-thigh','R-thigh','L-leg','R-leg','L-foot','R-foot']
        
        def computeResistances(itm,thickness,resistance):
            mitm = itm
            if itm in symmetricKeys:
                mitm = 'L-%s'%(itm.lower())
            br = self.breadth[mitm]
            radius = np.cumsum(thickness + br)
            rt = resistance[0]
            for i in range(1,radius.shape[0]):
                ral = 1.0/(self.hr+self.k/thickness[i])*radius[0]/radius[i-1]
                rf  = resistance[i]*radius[0]/radius[i]
                rt = rt + ral + rf
            return mitm,rt
        
        resistanceValue = dict()
        for itm in anatomicalClothingModel:
            ivalues = anatomicalClothingModel[itm]
            sortedValues = [None]*len(ivalues)
            for v in ivalues:
                sortedValues[int(v['INDEX'])] = v
            thickness = np.zeros(len(ivalues))
            resistance = np.zeros(len(ivalues))
            for i,v in enumerate(sortedValues):
                thickness[i] = v['THICKNESS']
                resistance[i]= v ['Ret']
            _,resistance[0] = self.computeNudeCoefficients(velocityOfAir)
            mitm,ret = computeResistances(itm, thickness, resistance)
            resistanceValue[mitm] = ret
            if itm != mitm:
                resistanceValue['R-%s' % itm.lower()] = ret
            
            
        return resistanceValue
    

    def getEvaporativeResistances(self,anatomicalClothingModel,velocityOfAir=0.0):
        '''
        Compute the effective evaporative resistance for each anatomical region
        anatomicalClothingModel (dataValues) - is either a 10 segment (symmetric) or 16 segment anatomy model
        '''
        symmetricKeys = ['Shoulder','Arm','Hand','Thigh','Leg','Foot']
        #anatomyKeys = ['Head','Chest','Back','Pelvis','L-shoulder','R-shoulder','L-arm','R-arm','L-hand','R-hand','L-thigh','R-thigh','L-leg','R-leg','L-foot','R-foot']
        
        def computeResistances(itm,thickness,resistance):
            mitm = itm
            if itm in symmetricKeys:
                mitm = 'L-%s'%(itm.lower())
            br = self.breadth[mitm]
            radius = np.cumsum(thickness + br)
            rt = resistance[0]
            for i in range(1,radius.shape[0]):
                rea = self.Real_a*(1.0-np.exp(-thickness[i]/self.Real_b))*radius[0]/radius[i-1]
                rf  = resistance[i]*radius[0]/radius[i]
                rt = rt + rea + rf
            return mitm,rt
        
        resistanceValue = dict()
        for itm in anatomicalClothingModel:
            ivalues = anatomicalClothingModel[itm]
            sortedValues = [None]*len(ivalues)
            for v in ivalues:
                sortedValues[int(v['INDEX'])] = v
            thickness = np.zeros(len(ivalues))
            resistance = np.zeros(len(ivalues))
            for i,v in enumerate(sortedValues):
                thickness[i] = v['THICKNESS']
                resistance[i]= v ['Rea']
            resistance[0],_ = self.computeNudeCoefficients(velocityOfAir)
            mitm,ret = computeResistances(itm, thickness, resistance)
            resistanceValue[mitm] = ret
            if itm != mitm:
                resistanceValue['R-%s' % itm.lower()] = ret
            
        return resistanceValue
    
if __name__ == '__main__':
    obj = ResistanceCalculator()
    #model = obj.loadClothingModel(r'D:\Jagir_Hussan\Research\Wool\ModelCode\ABIComfortSimulator\userinterface\clothing.json')
    #print(obj.getThermalResistances(model))
    #print(obj.getEvaporativeResistances(model))