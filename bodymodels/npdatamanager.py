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
import pickle

class Tanabe16SegmentBodyData(object):
    '''
    Computes data that has been personalized
    '''
    
    standardData = dict()
    
    def __init__(self, gender='male',height=1.72,weight=74.43,age=35):
        '''
        Load the datafiles and compute the new values
        '''
        #set standard model's meta data
        self.height = height
        self.weight = weight 
        self.age = age
        self.gender = gender
        self.Metb_sexratio = 1.0 #ratio of a woman's metabolic rate and age to those of a man
        self.Metb_ratio = 1.0
    
    def loadParametersFromFiles(self,datadir= '../database'):
        #Temporary storage
        bodySurfaceArea = dict()
        bodyWeight = dict()
        heatCapacity = dict()
        metabolicRate = dict()
        basalBloodFlow = dict()
        thermalResitance = dict()
        setPointTemperature = dict()
        weightingAndDistributionCoefficients = dict()
        controlCoefficients = dict()

        
        data = np.genfromtxt('%s/table1.csv'%(datadir), delimiter=',', names=True,skip_header=0,dtype=None,encoding=None)        
        for row in data:
            bodySurfaceArea[int(row[0])] = row[2]
            bodyWeight[int(row[0])] = row[3]
        bsa = np.zeros(len(bodySurfaceArea.keys()))
        for i,val in bodySurfaceArea.items():
            bsa[i-1] = val
        bodySurfaceArea = bsa
        
        bsa = np.zeros(len(bodyWeight.keys()))
        for i,val in bodyWeight.items():
            bsa[i-1] = val
        bodyWeight = bsa  
        
        data = np.genfromtxt('%s/table2.csv'%(datadir), delimiter=',', names=True,skip_header=0,dtype=None,encoding=None)
        for row in data:
            #Core,Skin,Artery,Vein,SuperficialVein
            vals = np.zeros(4)
            vals[0] = row[2]
            vals[1] = row[3]
            vals[2] = row[4]
            vals[3] = row[5]
            heatCapacity[int(row[0])] = vals

        bsa = np.zeros((len(heatCapacity.keys()),4))
        for i,val in heatCapacity.items():
            bsa[i-1,:] = val
        heatCapacity = bsa  

        data = np.genfromtxt('%s/table3.csv'%(datadir), delimiter=',', names=True,skip_header=0,dtype=None,encoding=None)
        for row in data:
            #Metbj Core, Muscle, Fat, Skin,Metf(i)[-]
            vals = np.zeros(5)
            vals[0] = row[2]
            vals[1] = row[3]
            vals[2] = row[4]
            vals[3] = row[5]
            vals[4] = row[6]
            metabolicRate[int(row[0])] = vals
        
        bsa = np.zeros((len(metabolicRate.keys()),5))
        for i,val in metabolicRate.items():
            bsa[i-1,:] = val
        metabolicRate = bsa         
        
        
        data = np.genfromtxt('%s/table4.csv'%(datadir), delimiter=',', names=True,skip_header=0,dtype=None,encoding=None)
        for row in data:
            #Core,Muscle,Fat,Skin
            vals = np.zeros(4)
            vals[0] = row[2]
            vals[1] = row[3]
            vals[2] = row[4]
            vals[3] = row[5]
            basalBloodFlow[int(row[0])] = vals            

        bsa = np.zeros((len(basalBloodFlow.keys()),4))
        for i,val in basalBloodFlow.items():
            bsa[i-1,:] = val
        basalBloodFlow = bsa         

        
        data = np.genfromtxt('%s/table5.csv'%(datadir), delimiter=',', names=True,skip_header=0,dtype=None,encoding=None)
        for row in data:
            #Core,Muscle,Fat,Skin
            vals = np.zeros(3)
            vals[0] = row[2]
            vals[1] = row[3]
            vals[2] = row[4]
            thermalResitance[int(row[0])] = vals
        
        bsa = np.zeros((len(thermalResitance.keys()),3))
        for i,val in thermalResitance.items():
            bsa[i-1,:] = val
        thermalResitance = bsa
        
        
        data = np.genfromtxt('%s/table6.csv'%(datadir), delimiter=',', names=True,skip_header=0,dtype=None,encoding=None)
        for row in data:
            #Core,Muscle,Fat,Skin
            vals = np.zeros(4)
            vals[0] = row[2]
            vals[1] = row[3]
            vals[2] = row[4]
            vals[3] = row[5]
            setPointTemperature[int(row[0])] = vals  
        
        bsa = np.zeros((len(setPointTemperature.keys()),4))
        for i,val in setPointTemperature.items():
            bsa[i-1,:] = val
        setPointTemperature = bsa
                
        data = np.genfromtxt('%s/table7.csv'%(datadir), delimiter=',', names=True,skip_header=0,dtype=None,encoding=None)
        for row in data:
            #SKINR(i),SKINV(i),SKINC(i),Shivf(i),SKINS(i)Standing/sitting,SKINS(i)Spine,SKINS(i)Running
            vals = np.zeros(5)
            vals[0] = row[2]
            vals[1] = row[3]
            vals[2] = row[4]
            vals[3] = row[5]
            vals[4] = row[6]
            weightingAndDistributionCoefficients[int(row[0])] = vals 

        bsa = np.zeros((len(weightingAndDistributionCoefficients.keys()),5))
        for i,val in weightingAndDistributionCoefficients.items():
            bsa[i-1,:] = val
        weightingAndDistributionCoefficients = bsa
        
        
        data = np.genfromtxt('%s/table8.csv'%(datadir), delimiter=',', names=True,skip_header=0,dtype=None,encoding=None)
        for row in data:
            vals = dict()
            toks = row[1].split('=')
            controlCoefficients[toks[0].strip()] = float(toks[1])
            toks = row[2].split('=')
            controlCoefficients[toks[0].strip()] = float(toks[1])
            toks = row[3].split('=')
            controlCoefficients[toks[0].strip()] = float(toks[1])
        
        #Load heat conduction, convection and radiation coeffcients
        data = np.genfromtxt('%s/conductionconvectionradiationcoefficients.csv'%(datadir), delimiter=',', names=True,skip_header=2,dtype=None,encoding=None)
        heatExchangeCoefficients = dict()
        for row in data:
            #Hr,Hc,He
            vals = np.zeros(3)
            vals[0] = row[2]
            vals[1] = row[3]
            vals[2] = row[4]
            heatExchangeCoefficients[int(row[0])] = vals           

        bsa = np.zeros((len(heatExchangeCoefficients.keys()),3))
        for i,val in heatExchangeCoefficients.items():
            bsa[i-1,:] = val
        heatExchangeCoefficients = bsa

        data = np.genfromtxt('%s/StolwijkCoefficients.csv'%(datadir), delimiter=',', names=True,skip_header=0,dtype=None,encoding=None)
        heatProductionAndBasalEvaporation = dict()
        for row in data:
            #QB-C,M,F,S,EB
            vals = np.zeros(5)
            vals[0] = row[2]
            vals[1] = row[3]
            vals[2] = row[4]
            vals[3] = row[5]
            vals[4] = row[6]
            heatProductionAndBasalEvaporation[int(row[0])] = vals 

        bsa = np.zeros((len(heatProductionAndBasalEvaporation.keys()),5))
        for i,val in heatProductionAndBasalEvaporation.items():
            bsa[i-1,:] = val
        heatProductionAndBasalEvaporation = bsa
            

        data = np.genfromtxt('%s/radiationHeatFlux.csv'%(datadir), delimiter=',', names=True,skip_header=0,dtype=None)
        radiationHeatFlux = dict()
        for row in data:
            radiationHeatFlux [int(row[0])] = float(row[2]) 

        bsa = np.zeros((len(radiationHeatFlux .keys()),1))
        for i,val in radiationHeatFlux.items():
            bsa[i-1] = val
        radiationHeatFlux  = bsa
        
        #Load to standard data
        standardData = dict()
        standardData['bodySurfaceArea'] = bodySurfaceArea
        standardData['bodyWeight'] = bodyWeight
        standardData['heatCapacity'] = heatCapacity
        standardData['metabolicRate'] = metabolicRate
        standardData['basalBloodFlow'] = basalBloodFlow
        standardData['thermalResitance'] = thermalResitance
        standardData['setPointTemperature'] = setPointTemperature
        standardData['weightingAndDistributionCoefficients'] = weightingAndDistributionCoefficients
        standardData['controlCoefficients'] = controlCoefficients
        standardData['heatExchangeCoefficients'] = heatExchangeCoefficients
        standardData['heatProductionAndBasalEvaporation'] = heatProductionAndBasalEvaporation
        standardData['radiationHeatFlux'] = radiationHeatFlux  
        #Change the standard values to personalized ones
        self.standardData = standardData
        
    def saveAsPickle(self,filename):
       
        with open(filename,'wb+') as ser:
            pickle.dump(self.standardData,ser)
     
    
    def loadStandardData(self,filename):
        with open(filename,'rb+') as ser:
            try:
                self.standardData = pickle.load(ser)
            except UnicodeDecodeError:
                self.standardData = pickle.load(ser,encoding='latin1')
                
        
        
    def getParameters(self):
        return self.standardData
    
    def getMetbSexRatio(self):
        return self.Metb_sexratio
        

      
class PersonalizedTanabe16SegmentBodyData(Tanabe16SegmentBodyData):     
    '''
    Personalize parameters based on total- height, -weight and body part weight and height 
    '''
    def __init__(self,gender='male',height=1.72,weight=74.43,age=35): 
        super(PersonalizedTanabe16SegmentBodyData,self).__init__(gender,height,weight,age)
        self.AduST = 1.870
        self.WtST  = 74.43
        self.CI = 2.5847058823529414 #cardiac index (cardiac output [L/min]/body surface area [m2]) 
        self.Rage = 1.0 #Aging coefficient
        self.BFBall_st = 290.004 #L/h
        self.Metab_st_whole = 84.652 #W 
        
    def setHeight(self,height):
        self.height = height
        
    def setWeight(self,weight):
        self.weight = weight
         
    def setAge(self,age):
        self.age = age

    def setCardiacIndex(self,CI):
        self.CI = CI
        
    def setAgingCoeffientForBlood(self,Rage):
        self.Rage = Rage

    def setMetbSexRatio(self,Metabsr):
        self.Metb_sexratio = Metabsr
    
    def setGender(self,gender):
        self.gender = gender

    def personalize(self):
        #Round of to second decimal as height in standard units is upto 2 decimals
        #When small variation around the height is present there is a large change in surface aread and related properties
        self.Adu = np.around(0.202*np.power(self.weight,0.425)*np.power(self.height,0.725),decimals=2) 
        self.AduRa = self.Adu/self.AduST
        self.WtRa = np.around(self.weight,decimals=2)/self.WtST
        
        bodySurfaceArea = self.standardData['bodySurfaceArea']
        for k,v in enumerate(bodySurfaceArea):
            bodySurfaceArea[k] = v*self.AduRa
                
        bodyWeight = self.standardData['bodyWeight']
        for k,v in enumerate(bodyWeight):
            bodyWeight[k] = v*self.WtRa

        heatCapacity = self.standardData['heatCapacity'] 
        for k,val in enumerate(heatCapacity):
            heatCapacity[k] = val*self.WtRa # Eq 14
        
        self.BFBall = self.CI*60.0*self.Adu*self.Rage
        #Check if the rates are right
        self.BFBall_ra = self.BFBall/self.BFBall_st
        #Heat capacity of blood pool is different
        heatCapacity[16][-1] = heatCapacity[k][-1]*self.BFBall_ra/self.WtRa
        
        basalBloodFlow = self.standardData['basalBloodFlow']
        for k,val in enumerate(basalBloodFlow):
            basalBloodFlow[k] = val*self.BFBall_ra
        
        #Metab_ra is calculated based on the change of surface area and metabsra
        self.Metab_ra = self.AduRa*self.Metb_sexratio
        
        metabolicRate = self.standardData['metabolicRate']
        for k,v in enumerate(metabolicRate):
            metabolicRate[k] = self.Metab_ra*v
            
if __name__ == '__main__':
    obj = Tanabe16SegmentBodyData()
    obj.loadParametersFromFiles()
    obj.saveAsPickle('standardData.pickle')
    obj.loadStandardData('standardData.pickle')