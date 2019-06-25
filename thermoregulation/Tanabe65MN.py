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
#from numba import jit
import numpy as np
from thermoregulation.PMVModels import ZhangModel
from scipy.integrate._ode import ode
canUsePersonalizedModel = True
try:
    from bodymodels.LoadOBJHumanModel import HumanModel
except:
    canUsePersonalizedModel = False
from bodymodels.StandardT65Setup import Tanabe17segmentModel,\
    PersonalizedTanabe17SegmentModel
import pickle

class Tanabe65MNModel(object):
    '''
    Implementation of Tanabe 65 MN model based on S.-i. Tanabe et al, Energy and Buildings 34 (2002) 637-646
    '''
    relativeHumdity = 0.6
    alpha = 1.0
    rhoC  = 1.067
    nDofs = 0
    met = 0.8
    hr = 4.9 # W/m^2
    zhangComfortModel = ZhangModel()
    eswScaleFactor = 1.04921477
    emaxFactor = 19.7289316
    
    def __init__(self, humanModel):
        '''
        Constructor
        '''
        self.humanModel = humanModel
        self.nDofs = humanModel.numberOfFaces
        parameters = humanModel.getPersonalizedParameters()
        self.headDofs = humanModel.dofIndexes[0]
        self.chestDofs = humanModel.dofIndexes[1]
        self.Qb = humanModel.getQb() #Qb is obtained from the sum of basal metabolic rate of all nodes, 0.778 met.
        self.Ta = np.zeros(self.nDofs)
        self.Qij = np.zeros((self.nDofs,4))
        self.W  = np.zeros(self.Qij.shape)
        self.Ch  = np.zeros(self.Qij.shape)
        self.temperature = np.zeros((self.nDofs,4))
        self.dT = np.zeros((self.nDofs,4))
        self.dtc = np.zeros(self.nDofs*4+1)
        self.cbcTemp = 0.0
        #Convert to face dofs
        self.bodySurfaceArea = np.zeros((self.nDofs,1))
        self.heatCapacity = np.zeros((self.nDofs,4))
        self.metabolicRate = np.zeros((self.nDofs,4))
        self.setPointTemperature = np.zeros((self.nDofs,4))
        self.cbcSetPointTemperature = parameters['setPointTemperature'][16,-1]
        self.cbcheatCapacity = parameters['heatCapacity'][16,-1]
        self.basalBloodFlow = np.zeros((self.nDofs,4))
        self.thermalConductance = np.zeros((self.nDofs,3))
        self.radiationHeatFlux = np.zeros((self.nDofs,1))
        self.chit = np.zeros(self.nDofs)
        self.metf = np.zeros(self.nDofs)
        self.SKINC = np.zeros(self.nDofs)
        self.SKINR_norm = np.zeros(self.nDofs)
        self.SKINS = np.zeros(self.nDofs)
        self.SKINV = np.zeros(self.nDofs)
        self.bodySurfaceArea = humanModel.surfaceFaceAreas
        surfaceFactors = humanModel.surfaceFactors
        if hasattr(humanModel, 'getFaceIndexes'):
            self.faceIndexes = humanModel.getFaceIndexes()[:,0]
        else:
            self.faceIndexes = np.zeros(1,dtype='bool')
        self.headSurfaceFactors = surfaceFactors[self.headDofs]
        self.chestSurfaceFactors = surfaceFactors[humanModel.dofIndexes[1]]
        self.hc = np.zeros(self.nDofs)
        self.lhm = np.zeros(self.nDofs)
        
        for i in range(16):
            indexes = humanModel.dofIndexes[i]
            self.bodySurfaceArea[indexes] = parameters['bodySurfaceArea'][i]
            self.heatCapacity[indexes,:] = parameters['heatCapacity'][i,:]  
            self.metabolicRate[indexes,:] = parameters['metabolicRate'][i,0:4]*surfaceFactors[indexes,np.newaxis]
            self.setPointTemperature[indexes,:] = parameters['setPointTemperature'][i,:]  
            self.basalBloodFlow[indexes,:] = parameters['basalBloodFlow'][i,:]*surfaceFactors[indexes,np.newaxis]
            self.thermalConductance[indexes,:] = parameters['thermalResitance'][i,:]*surfaceFactors[indexes,np.newaxis]  
            #self.radiationHeatFlux[indexes,0] = parameters['radiationHeatFlux'][i]*surfaceFactors[indexes]
            self.chit[indexes] = parameters['weightingAndDistributionCoefficients'][i,4]
            self.metf[indexes] = parameters['metabolicRate'][i,4]
            self.SKINC[indexes] = parameters['weightingAndDistributionCoefficients'][i,3]*surfaceFactors[indexes]
            self.SKINV[indexes] = parameters['weightingAndDistributionCoefficients'][i,2]*surfaceFactors[indexes]
            self.SKINS[indexes] = parameters['weightingAndDistributionCoefficients'][i,1]*surfaceFactors[indexes]
            self.SKINR_norm[indexes] = parameters['weightingAndDistributionCoefficients'][i,0]*surfaceFactors[indexes]
            
        self.SKINR_head = parameters['weightingAndDistributionCoefficients'][0,0]*surfaceFactors[self.headDofs]
            
        self.Cch = parameters['controlCoefficients']['Cch']
        self.Sch = parameters['controlCoefficients']['Sch']
        self.Pch = parameters['controlCoefficients']['Pch']
        self.Csw = parameters['controlCoefficients']['Csw']
        self.Ssw = parameters['controlCoefficients']['Ssw']
        self.Psw = parameters['controlCoefficients']['Psw']
        self.Cdl = parameters['controlCoefficients']['Cdl']
        self.Sdl = parameters['controlCoefficients']['Sdl']
        self.Pdl = parameters['controlCoefficients']['Pdl']
        self.Cst = parameters['controlCoefficients']['Cst']
        self.Sst = parameters['controlCoefficients']['Sst']
        self.Pst = parameters['controlCoefficients']['Pst']
            

    def getDofIndexes(self):
        return self.humanModel.dofIndexes

    def getNumberOfDofs(self):
        return self.nDofs

    def getBodySurfaceArea(self):
        return self.bodySurfaceArea

    def setTa(self,Ta):
        '''
        Ambient air temperature
        '''
        self.Ta.fill(Ta)
        #Calculate Operative temperature
        self.Tr = Ta + self.radiationHeatFlux[:,0]/4.184/(self.heatCapacity[:,3]*3600.0)  
        self.To = (self.hr*self.Tr + self.hc*self.Ta)/(self.hr + self.hc)
        
            
    def setRadiationFlux(self,radiationFluxModel):
        if radiationFluxModel.getNumIndicies()==16:
            for i in range(16):
                indexes = self.humanModel.dofIndexes[i]
                self.radiationHeatFlux[indexes,0] = radiationFluxModel.getFluxFor(i)*self.humanModel.surfaceFactors[indexes]
        elif radiationFluxModel.getNumIndicies()==self.radiationHeatFlux.shape[0]:
            self.radiationHeatFlux[:,0] = np.multiply(radiationFluxModel.getFluxes()[:,0],self.humanModel.surfaceFactors)
        elif radiationFluxModel.getNumIndicies()>self.radiationHeatFlux.shape[0] and self.radiationHeatFlux.shape[0]==16:
            weightedFluxes = np.multiply(radiationFluxModel.getFluxes()[:,0],self.mySurfaceFaceAreas)
            for i in range(16):
                indexes = self.myDofIndexes[i]
                self.radiationHeatFlux[i,0] = np.sum(weightedFluxes[indexes])            
        else:
            print("Number of faces in radiation flux model does not match!")
            raise ValueError("Number of faces in radiation flux model does not match!")
        #Calculate Operative temperature
        #1 Watt = 1J/s, 1 cal = 4.184 Joules - 1 cal the energy need to raise temp by 1 C
        #Specific heat is the measure of calories needed to raise energy by 1 C
        #Tanabe units are in Wh/C = 1 Wh/ Kg/K = 3600 J/Kg/K
        self.Tr = self.Ta + self.radiationHeatFlux[:,0]/4.184/(self.heatCapacity[:,3]*3600.0)  
        self.To = (self.hr*self.Tr + self.hc*self.Ta)/(self.hr + self.hc)
    
    def setClothingModel(self,clothingModel):
        self.clothingModel = clothingModel
        for i in range(16):
            indexes = self.humanModel.dofIndexes[i]
            self.hc[indexes] = clothingModel.getHeatTransferCoefficient(i)
            self.lhm[indexes] = clothingModel.getVapourTransferCoefficient(i)
        
        #Set the face coefficients to exposed values, the projected 16 segment model does not distinguish
        if np.any(self.faceIndexes):
            self.hc[self.faceIndexes] = 7.752798575994982
            self.lhm[self.faceIndexes] = 0.3789018620063181
        
        
    def setRelativeHumidity(self,rh):
        self.relativeHumdity = rh

    def setMet(self,m):
        self.met = m
                
    def getW(self):
        W = 58.2*(self.met-self.Qb)*self.bodySurfaceArea*self.metf
        W[W<0] = 0.0
        self.W[:,1] = W
        
    def getQ(self):
        self.Qij = self.metabolicRate + self.W + self.Ch
        return self.Qij
    
    def getInitialConditions(self):
        ic = np.zeros(self.dtc.shape)
        ic[0:-1] = np.reshape(self.setPointTemperature,(-1,1))[:,0]
        ic[-1] = self.cbcSetPointTemperature
        return ic
    
    def setInitialConditions(self,temp):
        self.temperature = np.reshape(temp[0:-1], (-1,4))
        self.cbcTemp = temp[-1]
    
#    @jit
    def computeErrCldsWrms(self,temperature):
        self.Err = temperature - self.setPointTemperature
        self.Wrm = np.array(self.Err,copy=True)
        self.Cld = -np.array(self.Err,copy=True)
        self.Wrm[self.Err<0] = 0
        self.Cld[self.Err>0] = 0
        
        self.Wrms = np.sum(self.SKINR_norm*self.Wrm[:,3])
        self.Clds = np.sum(self.SKINR_norm*self.Cld[:,3])
        
        e11 = np.sum(self.Err[self.headDofs,0]*self.headSurfaceFactors)
        self.Err11 = e11

        Wrm11 = e11
        if Wrm11 < 0:
            Wrm11 = 0
        Cld11 = -e11
        if Cld11 < 0:
            Cld11 = 0
        self.Ch.fill(0.0)
        self.Ch[:,1] = (-self.Cch*e11-self.Sch*(self.Wrms-self.Clds) + self.Pch*Cld11*self.Clds)*self.chit
        self.Ch[self.Ch<0] = 0
            
        self.DL = self.Cdl*e11+self.Sdl*(self.Wrms-self.Clds) + self.Pdl*Wrm11*self.Wrms
        if self.DL<0:
            self.DL = 0
        self.ST = -self.Cst*e11-self.Sst*(self.Wrms-self.Clds) + self.Pst*Cld11*self.Clds
        if self.ST<0:
            self.ST = 0
        self.km = np.power(2.0,self.Err[:,3]/10)
        
        self.Esw = (self.Csw*e11 + self.Ssw*(self.Wrms-self.Clds) + self.Psw*Wrm11*self.Wrms)*self.SKINS*self.km

    
    #Following eq 21 of X. Wan, J. Fan, J. Therm Biol, 33, 2008, 87-97
    def getEmax(self,temperature):
        #Using Tetens eq
        Psk = 0.61078*np.exp(17.625*temperature[:,3]/(temperature[:,3]+237.3)) #Units kpa 
        #Require vapour pressure so RH is involved
        Pa  = self.relativeHumdity*0.61078*np.exp(17.625*self.Ta/(self.Ta+237.3)) #Units kpa 
        v = self.emaxFactor*(Psk-Pa)*self.bodySurfaceArea/self.lhm #Formula in Pa, Note that the bodysurface area factor is applied to handle nonstandard body area, according to Eq 14 of Tanabe 2002
        v[v<0] = 0.0
        return v
    
    #Following eq 20 of X. Wan, J. Fan, J. Therm Biol, 33, 2008, 87-97
#    @jit
    def getQti(self,temperature):
        return (temperature[:,3]-self.To)*self.hc*self.bodySurfaceArea
    
#    @jit
    def RES(self):
        #Using part of the head and chest to calculate Respiratory exchange
        #ta = np.sum(self.Ta[self.headDofs]*self.headSurfaceFactors)*0.3
        #ta = ta + np.sum(self.Ta[self.chestDofs]*self.chestSurfaceFactors)
        ta = np.sum(self.Ta[self.headDofs]*self.bodySurfaceArea[self.headDofs])/np.sum(self.bodySurfaceArea[self.headDofs])
        ta = 0.5*( ta + np.sum(self.Ta[self.chestDofs]*self.bodySurfaceArea[self.chestDofs])/np.sum(self.bodySurfaceArea[self.chestDofs]))
        #Since vapour pressure is of interest
        pa  = self.relativeHumdity*0.61078*np.exp(17.625*ta/(ta+237.3)) #Units kpa
        #return (0.0014*(34-ta)+0.017*(5.867-pa))*(np.sum(np.sum(self.Qij)))*self.chestSurfaceFactors
        return (0.0014*(34-ta)+0.017*(5.867-pa))*(np.sum(np.sum(self.Qij)))
                
    def dTbydt(self,temp):
        temperature = np.reshape(temp[0:-1], (-1,4))
        cbcTemp = temp[-1]
        #self.getW() Needs to be computed only once
        self.computeErrCldsWrms(temperature)
        self.getQ()
        
        BFS = (self.basalBloodFlow +(self.W + self.Ch)/1.16)
        #Compute BF For skin
        BFS[:,3] = self.km*(self.basalBloodFlow[:,3] + self.SKINV*self.DL)/(1.0+self.SKINC*self.ST)
        BF = self.alpha*self.rhoC*BFS*(temperature - cbcTemp)
        D  = self.thermalConductance*(temperature[:,0:3]-temperature[:,1:])

        Qt = self.getQti(temperature)
        Emax  = self.getEmax(temperature)
        Esw = self.Esw
        Esw[Esw<0] = 0.0
        Eb = self.eswScaleFactor*(Emax-Esw)
        E =  Eb + Esw
        ix = E>Esw
        E[ix] = Esw[ix]
        self.dT[:,0] = self.Qij[:,0] - BF[:,0] - D[:,0]
        self.dT[:,1] = self.Qij[:,1] - BF[:,1] + D[:,0] - D[:,1]
        self.dT[:,2] = self.Qij[:,2] - BF[:,2] + D[:,1] - D[:,2]
        #The manner in which Qt and E are computed impacts the temperature change
        #if this DT is zero, the temperatures are near the initial temperature
        self.dT[:,3] = self.Qij[:,3] - BF[:,3] + D[:,2] - Qt - E + self.radiationHeatFlux[:,0]
        #Do RES for chest

        self.dT[self.chestDofs,0] -= self.RES()
        #dT = np.divide(self.dT,self.heatCapacity)
        dT = self.dT/self.heatCapacity
        dcbc = np.sum(np.sum(BF))/self.cbcheatCapacity
         
        self.dtc[0:-1] = np.reshape(dT,(-1,1))[:,0]
        self.dtc[-1] = dcbc
        return self.dtc
     
    def solve(self,targetT):
        temperature = np.zeros(self.nDofs*4+1)
        temperature[0:-1] = np.reshape(self.temperature, (-1,1))[:,0]
        temperature[-1] = self.cbcTemp
        
        def dTbydt(time,temp,obj):
            return obj.dTbydt(temp)
        
        def JacdTbydt(time,temp,obj):
            #The argument is passed to jac function too 
            return self.dt2bydt2(temp)
        
        tl = [0, targetT]
        if isinstance(targetT,np.ndarray):
            tl = list(targetT)
        elif isinstance(targetT,list):
            tl = targetT

        r = ode(dTbydt).set_integrator('vode',method='bdf')
        #r = ode(dTbydt).set_integrator('dopri5')
        r.set_initial_value(temperature, tl[0]).set_f_params(self).set_jac_params(self)
        ts = 1
        if tl[-1]>1:
            ts = np.ceil(tl[-1]/1)

        dt = float(tl[-1])/ts
        while r.successful() and r.t < tl[-1]:
            temperature = r.integrate(r.t+dt)                
            self.temperature = np.reshape(temperature[:-1], (-1,4))
            self.cbcTemp = temperature[-1]
        if r.t < tl[-1]:
            temperature = r.integrate(tl[-1])                
            self.temperature = np.reshape(temperature[:-1], (-1,4))
            self.cbcTemp = temperature[-1]
                    
        #Compute the wettedness based on the final value
        Emax = self.getEmax(self.temperature)
        Emax[Emax==0] = 1.0 #Avoid divide by zero
        Esw = self.Esw
        Esw[Esw<0] = 0.0        
        self.wettedness = 0.06 + 0.94*Esw/Emax #Using formula 14 of Journal of Atmaca and Yigit, Thermal Biology 31 (2006) 442-452 
        

    def getSkinWettedness(self):
        return self.wettedness

    def getMeanSkinTemperature(self):
        tsk = self.temperature[:,3]*self.bodySurfaceArea
        return np.sum(tsk)/np.sum(self.bodySurfaceArea)

    def getMeanCoreTemperature(self):
        tcr = self.temperature[:,0]*self.bodySurfaceArea
        return np.sum(tcr)/np.sum(self.bodySurfaceArea)    
    
    def printSegmentTemperatures(self):
        self.segmentTemp = np.zeros((16,4))
        wTemps = self.temperature*self.humanModel.surfaceFactors[:,np.newaxis]
        for i in range(16):
            indexes = self.humanModel.dofIndexes[i]
            self.segmentTemp[i,:] = np.sum(wTemps[indexes,:],axis=0)
        
        def getSegmentTemperatures(j):
            stemp = self.segmentTemp[:,j] 
            return stemp
        
        def getSkinTemperatures():
            skinj = 3
            return getSegmentTemperatures(skinj)

        def getCoreTemperatures():
            corej = 0 
            return getSegmentTemperatures(corej)
    
        def getMuscleTemperatures():
            musclej = 0
            return getSegmentTemperatures(musclej)
    
        def getFatTemperatures():
            fatj = 2
            return getSegmentTemperatures(fatj)
    
        print(getSkinTemperatures())
        print(getFatTemperatures())
        print(getMuscleTemperatures())
        print(getCoreTemperatures())
        print(self.cbcTemp)

    def getMeanSegmentCoreTemperature(self,i):
        indexes = self.humanModel.dofIndexes[i]
        psa = self.bodySurfaceArea[indexes]
        tcr = self.temperature[indexes,0]*psa
        return np.sum(tcr)/np.sum(psa)
    
    def getMeanSegmentSkinTemperature(self,i):
        indexes = self.humanModel.dofIndexes[i]
        psa = self.bodySurfaceArea[indexes]
        tcr = self.temperature[indexes,3]*psa
        return np.sum(tcr)/np.sum(psa)

    def getSegmentCoreTemperature(self,i):
        indexes = self.humanModel.dofIndexes[i]
        return self.temperature[indexes,0]
    
    def getSegmentSkinTemperature(self,i):
        indexes = self.humanModel.dofIndexes[i]
        return self.temperature[indexes,3]
    
    def getSegmentSkinWettedness(self,i):    
        indexes = self.humanModel.dofIndexes[i]
        return self.wettedness[indexes]
    
    def getTemperature(self):
        return self.temperature
    
    def getEffectiveEvaporativeResistance(self):
        return self.lhm
    
    def getEffectiveThermalResistance(self):
        return self.hc
    
    def getMeanThermalResistance(self):
        return np.mean(self.hc)
    
    def getMeanEvaporativelResistance(self):
        return np.mean(self.lhm)

    
    def getRectalTemperature(self):
        #Defined as i=4,j=1 by X. Wan, J.Fan
        #Here we use pelvis core
        psa = self.bodySurfaceArea[self.humanModel.dofIndexes[3]]
        tcr = self.temperature[self.humanModel.dofIndexes[3],0]*psa
        return np.sum(tcr)/np.sum(psa)    


    def FangerPMV(self,vel = 0.0,wme=0):
        pa = self.relativeHumdity * 10 * np.exp(16.6536 - 4030.183 / (self.Ta[0] + 235));
        #icl = np.sum(self.hc*self.bodySurfaceArea)/np.sum(self.bodySurfaceArea) #thermal insulation of the clothing in M2K/W
        icl = 0.10
        m = self.met * 58.15 #metabolic rate in W/M2
        w = wme * 58.15 #external work in W/M2
        mw = m - w #internal heat production in the human body
        if icl <= 0.078:
            fcl = 1 + (1.29 * icl)
        else:
            fcl = 1.05 + (0.645 * icl)

        #heat transf. coeff. by forced convection
        hcf = 12.1 * np.sqrt(vel)
        taa = self.Ta[0] + 273
        tra = np.mean(self.Tr) + 273
        tcla = taa + (35.5 - self.Ta[0]) / (3.5 * icl + 0.1)

        p1 = icl * fcl
        p2 = p1 * 3.96
        p3 = p1 * 100
        p4 = p1 * taa
        p5 = 308.7 - 0.028 * mw + p2 * pow(tra / 100, 4)
        xn = tcla / 100
        xf = tcla / 50
        eps = 0.00015

        n = 0
        while (abs(xn - xf) > eps) :
            xf = (xf + xn) / 2
            hcn = 2.38 * pow(abs(100.0 * xf - taa), 0.25);
            if (hcf > hcn):
                hc = hcf
            else:
                hc = hcn
            xn = (p5 + p4 * hc - p2 * pow(xf, 4)) / (100 + p3 * hc)
            n = n + 1
            if (n > 150) :
                print('Max iterations exceeded')
                return 1

        tcl = 100 * xn - 273

        #heat loss diff. through skin
        hl1 = 3.05 * 0.001 * (5733 - (6.99 * mw) - pa);
        #heat loss by sweating
        if (mw > 58.15):
            hl2 = 0.42 * (mw - 58.15)
        else:
            hl2 = 0
        #latent respiration heat loss
        hl3 = 1.7 * 0.00001 * m * (5867 - pa)
        #dry respiration heat loss
        hl4 = 0.0014 * m * (34 - self.Ta[0])
        #heat loss by radiation
        hl5 = 3.96 * fcl * (pow(xn, 4) - pow(tra / 100, 4))
        #heat loss by convection
        hl6 = fcl * hc * (tcl - self.Ta[0])

        ts = 0.303 * np.exp(-0.036 * m) + 0.028;
        pmv = ts * (mw - hl1 - hl2 - hl3 - hl4 - hl5 - hl6)
        ppd = 100.0 - 95.0 * np.exp(-0.03353 * pow(pmv, 4.0) - 0.2179 * pow(pmv, 2.0))

        return pmv,ppd
    
    def save(self,filename):
        with open(filename,'w') as ser:
            pickle.dump([self.temperature,self.dT,self.humanModel.dofIndexes],ser)
           
            
    def ZhangPMVPPD(self):
        '''
        Based on A human thermal model for improved thermal comfort, PhD Thesis
        '''        
        keys = ['Head','Chest','Back','Pelvis','L-shoulder','R-shoulder','L-arm','R-arm','L-hand','R-hand','L-thigh','R-thigh','L-leg','R-leg','L-foot','R-foot']
        
        sixteenSegmentSkinTempAndDt = dict()
        sixteenSegmentCoreTempAndDt = dict()
        setPointTemperature = dict()
        for i in range(16):
            ast = np.mean(self.temperature[self.humanModel.dofIndexes[i],3])
            asdt =np.mean(self.dT[self.humanModel.dofIndexes[i],3]/self.heatCapacity[self.humanModel.dofIndexes[i],3])
            act = np.mean(self.temperature[self.humanModel.dofIndexes[i],0])
            acdt =np.mean(self.dT[self.humanModel.dofIndexes[i],0]/self.heatCapacity[self.humanModel.dofIndexes[i],0])
            sixteenSegmentSkinTempAndDt[keys[i]] = [ast,asdt]
            sixteenSegmentCoreTempAndDt[keys[i]] = [act,acdt]
            setPointTemperature[keys[i]] = self.setPointTemperature[self.humanModel.dofIndexes[i]][0,3]

        return self.zhangComfortModel.computePMV(sixteenSegmentSkinTempAndDt,sixteenSegmentCoreTempAndDt,setPointTemperature)
        

class Tanabe65MNProjectedToStandard16(Tanabe65MNModel):
    '''
    An interface to the Tanabe16MN model that solves the system on the standard body and projects the results to
    the given mesh
    '''

    def __init__(self,humanModel):
        #humanParam = Tanabe17segmentModel()
        bm = humanModel.bodyDataModel
        #The following uses standard surface areas
        humanParam = PersonalizedTanabe17SegmentModel(gender=bm.gender,height=bm.height,\
                                                      weight=bm.weight,age=bm.age,\
                                                      CardiacIndex=bm.CI,\
                                                      AgingCoeffientForBlood=bm.Rage,\
                                                      SexBasedMetabolicRatio=bm.Metb_sexratio)
        parameters = humanParam.getPersonalizedParameters()
        parameters['controlCoefficients'] = humanModel.getPersonalizedParameters()['controlCoefficients']
        #The following will use the mesh surface areas instead of standard surface areas
        #humanParam.updateToParameterModel(humanModel.bodyDataModel)
        super(Tanabe65MNProjectedToStandard16, self).__init__(humanParam)
        self.myDofIndexes = humanModel.dofIndexes
        self.mySurfaceFaceAreas = humanModel.surfaceFaceAreas
        self.myDofs = humanModel.numberOfFaces
        self.projectTemperature = np.zeros((self.myDofs,4))

    def getDofIndexes(self):
        return self.myDofIndexes

    def getNumberOfDofs(self):
        return self.myDofs
    
    def getBodySurfaceArea(self):
        rvals = np.zeros(self.myDofs)
        for i in range(16):
            rvals[self.myDofIndexes[i]] = self.bodySurfaceArea[i]
        return rvals            
        
    def getSegmentCoreTemperature(self,i):
        indexes = self.myDofIndexes[i]
        return self.temperature[i,0]*np.ones(indexes.shape[0])
    
    def getSegmentSkinTemperature(self,i):
        indexes = self.myDofIndexes[i]
        return self.temperature[i,3]*np.ones(indexes.shape[0])
    
    def getSegmentSkinWettedness(self,i):    
        indexes = self.myDofIndexes[i]
        return self.wettedness[i]*np.ones(indexes.shape[0])
    
    def getSkinWettedness(self):
        rvals = np.zeros(self.myDofs)
        for i in range(16):
            rvals[self.myDofIndexes[i]] = self.wettedness[i]
        return rvals
        
    def getTemperature(self):
        for i in range(16):
            self.projectTemperature[self.myDofIndexes[i],:] = self.temperature[i,:]
        return self.projectTemperature
    
    def getEffectiveThermalResistance(self):
        rvals = np.zeros(self.myDofs)
        for i in range(16):
            rvals[self.myDofIndexes[i]] = self.hc[i]
        return rvals
            
    def getEffectiveEvaporativeResistance(self):
        rvals = np.zeros(self.myDofs)
        for i in range(16):
            rvals[self.myDofIndexes[i]] = self.lhm[i]
        return rvals