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
from bodymodels.npdatamanager import Tanabe16SegmentBodyData,\
    PersonalizedTanabe16SegmentBodyData
import os

class Tanabe17segmentModel(object):
    '''
    Standard 16 segment model's interface
    '''
    numberOfFaces = 16
    surfaceFactors = np.ones(numberOfFaces)
    surfaceFaceAreas= np.zeros(numberOfFaces)


    def __init__(self):
        '''
        Constructor
        '''
        self.dofIndexes = dict()
        for i in range(16):
            self.dofIndexes[i] = np.zeros(self.numberOfFaces,dtype='bool')
            self.dofIndexes[i][i] = True
            
    def getQb(self):
        return 0.778
    
    def getMetabolicFactor(self):
        return 1.0            
        
    def getSurfaceFactors(self):
        return self.surfaceFactors
    
    def getPersonalizedParameters(self):
        if not hasattr(self, 'personalizedParameters'):
            self.personalizeParameters()
        return self.personalizedParameters
        
    def personalizeParameters(self):
        parameters = Tanabe16SegmentBodyData()
        dataDir = os.path.dirname(os.path.realpath(__file__))
        parameters.loadStandardData(os.path.join(dataDir,'../database/standardData.pickle'))        
        personalizedParameters = parameters.getParameters()
        for i in range(16):
            self.surfaceFaceAreas[i] = personalizedParameters['bodySurfaceArea'][i]
        self.personalizedParameters = personalizedParameters
        #Used when creating project simulations
        self.bodyDataModel = parameters
        self.bodyDataModel.CI = 2.5847058823529414
        self.bodyDataModel.Rage = 1.0
        self.bodyDataModel.Metb_sexratio = 1.0


class PersonalizedTanabe17SegmentModel(Tanabe17segmentModel):
    
    Qb = 0.778
    
    def __init__(self,gender='male',height=1.72,weight=74.43,age=35,**kwargs):
        super(PersonalizedTanabe17SegmentModel,self).__init__()
        parameters = PersonalizedTanabe16SegmentBodyData(gender,height,weight,age)
        dataDir = os.path.dirname(os.path.realpath(__file__))
        parameters.loadStandardData(os.path.join(dataDir,'../database/standardData.pickle'))
        for k,v in kwargs.items():
            if k == 'CardiacIndex':
                parameters.setCardiacIndex(v)
            elif k == 'AgingCoeffientForBlood':
                parameters.setAgingCoeffientForBlood(v)
            elif k =='SexBasedMetabolicRatio':
                parameters.setMetbSexRatio(v)
        self.Qb *= parameters.Metb_sexratio
        parameters.personalize()
        personalizedParameters = parameters.getParameters()
        for i in range(16):
            self.surfaceFaceAreas[i] = personalizedParameters['bodySurfaceArea'][i]
        self.personalizedParameters = personalizedParameters 
        
    def updateToParameterModel(self,parameters,updateSurfaceAreas=False):
        self.Qb *= parameters.Metb_sexratio
        parameters.personalize()
        personalizedParameters = parameters.getParameters()
        if updateSurfaceAreas:
            for i in range(16):
                self.surfaceFaceAreas[i] = personalizedParameters['bodySurfaceArea'][i]
        self.personalizedParameters = personalizedParameters         
    
    def getQb(self):
        return self.Qb
        
    def getSurfaceFactors(self):
        return self.surfaceFactors
    
    def getPersonalizedParameters(self):
        return self.personalizedParameters
        
    def personalizeParameters(self):
        return        