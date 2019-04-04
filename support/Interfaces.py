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
import json
from support.EffectiveResistances import ResistanceCalculator
import numpy as np

class ClothingResistanceModel(object):
    '''
    Create an interface to compute clothing resistance
    '''

    anatomyKeys = ['Head','Chest','Back','Pelvis','L-shoulder','R-shoulder','L-arm','R-arm','L-hand','R-hand','L-thigh','R-thigh','L-leg','R-leg','L-foot','R-foot']

    def __init__(self,):
        '''
        Constructor
        '''
        self.rc = ResistanceCalculator()
        self.velocityOfAir = 0.0
    
    def loadClothingModelFromFile(self,clothingModelFile):
        self.model = self.rc.loadClothingModel(clothingModelFile)
        self.thermalResistances = self.rc.getThermalResistances(self.model,self.velocityOfAir)
        self.evaporativeResistances = self.rc.getEvaporativeResistances(self.model,self.velocityOfAir)        
    
    def setVelocityOfAir(self,voa):
        self.velocityOfAir = voa
        self.thermalResistances = self.rc.getThermalResistances(self.model,self.velocityOfAir)
        self.evaporativeResistances = self.rc.getEvaporativeResistances(self.model,self.velocityOfAir) 

    def getHeatTransferCoefficient(self,anatomyIndex16Segment):
        return self.thermalResistances[self.anatomyKeys[anatomyIndex16Segment]]
    
    def getVapourTransferCoefficient(self,anatomyIndex16Segment):
        return self.evaporativeResistances[self.anatomyKeys[anatomyIndex16Segment]]




class RadiationModel(object):
    '''
    Interface for loading and serving a radiation model
    '''
    anatomyKeys = ['Head','Chest','Back','Pelvis','L-shoulder','R-shoulder','L-arm','R-arm','L-hand','R-hand','L-thigh','R-thigh','L-leg','R-leg','L-foot','R-foot']
    
    def __init__(self):
        self.radiationData = dict()
        for k in self.anatomyKeys:
            self.radiationData[k] = 0.0
        self.numIndices = len(self.anatomyKeys) 
        
    def getNumIndicies(self):
        return self.numIndices
              
    def loadRadiationDataFromFile(self,radiationDefinitionFile):
        symmetricKeys = ['Shoulder','Arm','Hand','Thigh','Leg','Foot']
        with open(radiationDefinitionFile,'r') as ser:
            model = json.load(ser)
            if isinstance(model,dict):
                for itm,value in model.items():
                    if itm in symmetricKeys:
                        ky = itm.lower()
                        self.radiationData['L-%s'%ky] = float(value)
                        self.radiationData['R-%s'%ky] = float(value)
                    else:
                        self.radiationData[itm] = float(value)
            elif isinstance(model,list):
                self.radiationData = np.array(model)
                self.numIndices = len(self.radiationData)
            else:
                raise ValueError("Unsupported format for radiation definition! File %s"%radiationDefinitionFile)

    def getFluxFor(self,anatomyIndex16Segment):
        return self.radiationData[self.anatomyKeys[anatomyIndex16Segment]]
    
    def getFluxes(self):
        return self.radiationData