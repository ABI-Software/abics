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

from opencmiss.zinc.context import Context
from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.node import Node
from opencmiss.zinc.field import Field
import numpy as np
from bodymodels.npdatamanager import PersonalizedTanabe16SegmentBodyData
import os


zincDebug = False
cubicHermite = False

    
         
class AbstractHumanModel(object):
    '''
    Base model that holds the data
    '''
    
    def __init__(self):
        pass
    
    def getQb(self):
        return 0.778*np.power(self.totalSurfaceArea/self.basemodelSurfaceArea,self.metabolicScalingFactor)*self.Metb_sexratio
    
    def getMetabolicFactor(self):
        return np.power(self.totalSurfaceArea/self.basemodelSurfaceArea,self.metabolicScalingFactor)            
        
    def getSurfaceFactors(self):
        return self.surfaceFactors

    def getPersonalizedParameters(self):
        return self.personalizedParameters


class HumanModel(AbstractHumanModel):
    '''
    Converts obj file based on manuel bastoni to opencmiss zinc
    In order to get the part a face belong to export the mesh from blender in obj format
    In Export select
        polygroups
        Keep vertex order
    This will generate polygroups where faces belonging to a group are generated
    spine 03 is the upper chest and back
    spine 02 is the middle chest and back
    spine 02 is the lower back
    '''
    
    nodes = dict()
    nodeGroup = dict()
    faces = dict()
    nodeNormals = dict()
    faceNormals = dict()
    facegroup = dict()
    faceAreas = dict()
    centroid = np.zeros(3)
    Metb_sexratio = 1.0    
    basemodelHeight = 1.70
    basemodelSurfaceArea = 1.869 #Obtained by summing table 10
    effectiveRadiationArea = 1.282
    metabolicScalingFactor = 1.5
    
    def __init__(self, objfilename,metScaleFactor=1.5,filterFaces=False):
        '''
        Constructor
        '''
        super(HumanModel,self).__init__()
        self.metabolicScalingFactor = metScaleFactor
        ndctr = 0
        nnctr = 0
        fctr = 0
        lastpolygroup = 0
        gc = 10
        headValue = 0
        neckValue = 0
        chestValue = 1
        backValue  = 2
        pelvisValue = 3
        lshoulder = 4
        rshoulder = 5
        larm = 6
        rarm = 7
        lhand = 8
        rhand = 9
        lthigh = 10
        rthigh = 11
        lleg = 12
        rleg = 13
        lfoot = 14
        rfoot = 15
        abdomainValue = 16
        #Make human 1.0 group names
        bdtypes = {   "head" : headValue,
                      "calf_L": lleg,
                      "thigh_L": lthigh,
                      "index02_L": lhand,
                      "index03_L": lhand,
                      "index01_L": lhand,
                      "index00_L": lhand,
                      "ring01_L": lhand,
                      "ring00_L": lhand,
                      "pinky01_L": lhand,
                      "pinky00_L": lhand,
                      "middle01_L": lhand,
                      "thumb03_L": lhand,
                      "thumb02_L": lhand,
                      "thumb01_L": lhand,
                      "hand_L": lhand,
                      "middle00_L": lhand,
                      "neck": neckValue,
                      "clavicle_L": lshoulder, #Left Shoulder
                      "spine03": chestValue,   #Upper chest & Back
                      "upperarm_L": larm,
                      "upperarm_R": rarm,
                      "lowerarm_L": larm,
                      "clavicle_R": rshoulder, # Right Shoulder
                      "spine02": abdomainValue,   #Middle chest & Back
                      "middle02_L": lhand,
                      "middle03_L": lhand,
                      "ring02_L": lhand,
                      "ring03_L": lhand,
                      "pinky02_L": lhand,
                      "pinky03_L": lhand,
                      "toes_L": lfoot,
                      "foot_L": lfoot,
                      "pelvis": pelvisValue,
                      "spine01": abdomainValue,  #Lower Back and gonoid
                      "calf_R": rleg,
                      "thigh_R": rthigh,
                      "index02_R": rhand,
                      "index03_R": rhand,
                      "index01_R": rhand,
                      "index00_R": rhand,
                      "ring01_R": rhand,
                      "ring00_R": rhand,
                      "pinky01_R": rhand,
                      "pinky00_R": rhand,
                      "middle01_R": rhand,
                      "thumb03_R": rhand,
                      "thumb02_R": rhand,
                      "thumb01_R": rhand,
                      "hand_R": rhand,
                      "middle00_R": rhand,
                      "lowerarm_R": rarm,
                      "middle02_R": rhand,
                      "middle03_R": rhand,
                      "ring02_R": rhand,
                      "ring03_R": rhand,
                      "pinky02_R": rhand,
                      "pinky03_R": rhand,
                      "toes_R": rfoot,
                      "foot_R": rfoot
                    }
        #Make human 1.1 group names
        bdtypes11 = {   "Head" : headValue,
                      "Neck" : neckValue,
                      "Neck1" : neckValue,
                      "Spine" : chestValue,
                      "Spine1" : chestValue,
                      "LeftShoulder" : lshoulder,
                      "RightShoulder" : rshoulder,
                      "Hips" : pelvisValue,
                      "LowerBack" : pelvisValue,
                      "LHipJoint" : pelvisValue,
                      "RHipJoint" : pelvisValue,
                      "LeftArm" : larm,
                      "RightArm" : rarm,
                      "LeftForeArm" : larm,
                      "RightForeArm" : rarm,
                      "LeftUpLeg" : lthigh,
                      "RightUpLeg" : rthigh,
                      "LThumb" : lhand,
                      "LeftFingerBase" : lhand,
                      "LeftForeArm" : lhand,
                      "LeftHandFinger1" : lhand,
                      "LeftHand" : lhand,
                      "RThumb" : rhand,
                      "RightFingerBase" : rhand,
                      "RightForeArm" : rhand,
                      "RightHandFinger1" : rhand,
                      "RightHand" : rhand,
                      "LeftLeg" : lleg,
                      "RightLeg" : rleg,
                      "LeftToeBase" : lfoot,
                      "LeftFoot" : lfoot,                      
                      "RightToeBase" : rfoot,
                      "RightFoot" : rfoot, 
                    }        
        
        bdtypes.update(bdtypes11)
        #bdtypes = bdtypes11
        self.teethNode = None
        with open(objfilename,'r+') as obj:
            facialFeatureEncountered = False
            for lines in obj:
                if lines.startswith('v '):
                    tok = lines.split(' ')
                    self.nodes[ndctr] = np.array([float(tok[1]),float(tok[2]),float(tok[3])])
                    self.centroid += self.nodes[ndctr]
                    ndctr += 1
                elif lines.startswith('vn '):
                    tok = lines.split(' ')
                    self.nodeNormals[nnctr] = np.array([float(tok[1]),float(tok[2]),float(tok[3])])
                    nnctr += 1                                       
                elif lines.startswith('f '):
                    #Handle quads and triangles
                    tok = lines.split(' ')
                    v1t = tok[1].split('/')
                    v1  = int(v1t[0])
                    if v1-1 not in self.nodeGroup:
                        self.nodeGroup[v1-1] = [lastpolygroup]
                    else:
                        self.nodeGroup[v1-1].append(lastpolygroup)
                    v2t = tok[2].split('/')
                    v2  = int(v2t[0])
                    if v2-1 not in self.nodeGroup:
                        self.nodeGroup[v2-1] = [lastpolygroup]
                    else:
                        self.nodeGroup[v2-1].append(lastpolygroup)
                    v3t = tok[3].split('/')
                    v3  = int(v3t[0])
                    if v3-1 not in self.nodeGroup:
                        self.nodeGroup[v3-1] = [lastpolygroup]
                    else:
                        self.nodeGroup[v3-1].append(lastpolygroup)
                    
                    if len(tok) > 4:
                        v4t = tok[4].split('/')                    
                        v4  = int(v4t[0])
                        if v4-1 not in self.nodeGroup:
                            self.nodeGroup[v4-1] = [lastpolygroup]
                        else:
                            self.nodeGroup[v4-1].append(lastpolygroup)
                        self.faces[fctr] = [v1-1,v2-1,v3-1,v4-1]
                        self.faceNormals[fctr] = [int(v1t[2])-1,int(v2t[2])-1,int(v3t[2])-1,int(v4t[2])-1]
                    else:
                        self.faces[fctr] = [v1-1,v2-1,v3-1]
                        self.faceNormals[fctr] = [int(v1t[2])-1,int(v2t[2])-1,int(v3t[2])-1]
                    
                    if filterFaces and self.teethNode is None and facialFeatureEncountered:
                        self.teethNode = fctr
                    fctr += 1   
                elif lines.startswith('usemtl'):
                    mline = lines.strip().lower()
                    #Check if we encounter the teeth or eye brow
                    if mline.startswith('usemtl teeth') or mline.startswith('usemtl eye_br'):
                        facialFeatureEncountered = True
                elif lines.startswith('g '): #polygroup
                    tok = lines.split(' ')
                    ky = tok[1].strip()
                    lastpolygroup = 0
                    if ky in bdtypes:
                        lastpolygroup = bdtypes[ky]
                    else:
                        bdtypes[ky] = gc + 1
                        #print ky,bdtypes[ky]
                        gc += 1
        self.centroid /= ndctr
        #Determine face 
        if filterFaces:
            teethCoord = np.mean([self.nodes[i] for i in self.faces[self.teethNode]],axis=0)
            headNodes = []
        #Determine the chest and back based on centroid
        #Some of the lower spine is assigned to nodes in the pelvis
        #Reassign them to the pelvis based on pelvis height (y-axis)
        cz = 0
        ctr = 0
        cymax = 0 
        for nd,vals in self.nodeGroup.items():
            bt = np.asarray(vals).min()
            if filterFaces and bt==headValue:
                headNodes.append(nd)
            if bt==chestValue or bt==abdomainValue:
                cz += self.nodes[nd][2]
                ctr += 1
            if bt==pelvisValue:
                if self.nodes[nd][1] > cymax:
                    cymax = self.nodes[nd][1]
        
        cz /= ctr
        for nd,vals in self.nodeGroup.items():
            bt = np.asarray(vals).min()
            if bt==chestValue or bt==abdomainValue:
                z = self.nodes[nd][2] - cz
                if z < 0:
                    self.nodeGroup[nd] = [backValue]
                if self.nodes[nd][1] < cymax:
                    self.nodeGroup[nd] = [pelvisValue]
                if z > 0 and self.nodes[nd][1] > cymax and bt==abdomainValue:
                    self.nodeGroup[nd] = [pelvisValue]
        

        if filterFaces:
            headCentroid = np.mean([self.nodes[nd] for nd in headNodes],axis=0)
            faceNormal = teethCoord-headCentroid
            faceNormal /= np.linalg.norm(faceNormal)
            #Determine "face" faces
            self.faceDofs = np.zeros((fctr,1),dtype=bool)
            for fc,fn in self.faceNormals.items():
                faceN = np.array([self.nodeNormals[i] for i in fn])
                match = np.dot(faceN,faceNormal)
                faceside = np.min(match)>0
                for fnode in self.faces[fc]:
                    faceside = faceside and fnode in headNodes
                self.faceDofs[fc] = faceside
        
        totalSurfaceArea = 0
        for fid,nds in self.faces.items():
            if len(nds)==4:
                pg = np.min([np.min(self.nodeGroup[nds[0]]),np.min(self.nodeGroup[nds[1]]),np.min(self.nodeGroup[nds[2]]),np.min(self.nodeGroup[nds[3]])])
                le = np.linalg.norm(np.asarray(self.nodes[nds[0]])-np.asarray(self.nodes[nds[1]]))
                br = np.linalg.norm(np.asarray(self.nodes[nds[0]])-np.asarray(self.nodes[nds[2]]))
                self.faceAreas[fid] = le*br
                totalSurfaceArea += le*br
            else:
                pg = np.min([np.min(self.nodeGroup[nds[0]]),np.min(self.nodeGroup[nds[1]]),np.min(self.nodeGroup[nds[2]])])
                a = np.linalg.norm(np.asarray(self.nodes[nds[0]])-np.asarray(self.nodes[nds[1]]))
                b = np.linalg.norm(np.asarray(self.nodes[nds[0]])-np.asarray(self.nodes[nds[2]]))
                c = np.linalg.norm(np.asarray(self.nodes[nds[1]])-np.asarray(self.nodes[nds[2]]))
                s = (a+b+c)/2
                self.faceAreas[fid] = np.sqrt(s*(s-a)*(s-b)*(s-c))
                totalSurfaceArea += self.faceAreas[fid]

            self.facegroup[fid] = pg

        self.totalSurfaceArea = totalSurfaceArea
        
        self.surfaceAreas = dict()
        for i in range(rfoot+1):
            self.surfaceAreas[i] = 0
        
        for fid,fval in self.faceAreas.items():
            self.surfaceAreas[self.facegroup[fid]] += fval
        
        self.numberOfFaces = len(self.faceAreas)
        #Store the surface area factors
        self.surfaceFactors = np.zeros(self.numberOfFaces)
        self.surfaceFaceAreas= np.zeros(self.numberOfFaces)
        for fid,ar in self.faceAreas.items():
            self.surfaceFaceAreas[fid] = ar
            self.surfaceFactors[fid] = ar/self.surfaceAreas[self.facegroup[fid]]
        
        self.dofIndexes = dict()
        for i in range(16):
            self.dofIndexes[i] = np.zeros(self.numberOfFaces,dtype='bool')
            
        for fd,gp in self.facegroup.items():
            self.dofIndexes[gp][fd] = True
            
        #Find width of nodes
        self.anatomyWidths = dict()
        anatomyNodes = dict()
        for i in range(17):
            anatomyNodes[i] = []
            
        for nd,vals in self.nodeGroup.items():
            us = list(set(vals))
            for v in us:
                anatomyNodes[v].append(self.nodes[nd])
        #Combine nodes of connected regions
        anatomyNodes[1].extend(anatomyNodes[2])
        anatomyNodes[1].extend(anatomyNodes[16])
        del anatomyNodes[2]
        del anatomyNodes[16]
        
        for at,nodes in anatomyNodes.items():
            coords = np.asarray(nodes)
            widths = coords.max(axis=0) - coords.min(axis=0)
            #Take the two lowest values
            ow = np.sort(widths)
            if ow[0]==0:
                ow[0] = 1
            area = ow[0]*ow[1]
            self.anatomyWidths[at] = np.sqrt(area/np.pi)
    
    
    def personalizeParameters(self,gender='male',height=1.72,weight=74.43,age=35,**kwargs):
        dataDir = os.path.dirname(os.path.realpath(__file__))
        if 'CardiacIndex' in kwargs or 'AgingCoeffientForBlood' in kwargs or 'SexBasedMetabolicRatio' in kwargs \
            or not (gender=='male' and height==1.72 and weight==74.43 and age==35): 
            parameters = PersonalizedTanabe16SegmentBodyData(gender,height,weight,age)
            parameters.loadStandardData(os.path.join(dataDir,'../database/standardData.pickle'))            
            for k,v in kwargs.items():
                if k == 'CardiacIndex':
                    parameters.setCardiacIndex(v)
                elif k == 'AgingCoeffientForBlood':
                    parameters.setAgingCoeffientForBlood(v)
                elif k =='SexBasedMetabolicRatio':
                    parameters.setMetbSexRatio(v) 
            parameters.personalize()
            personalizedParameters = parameters.getParameters()
        else:
            parameters = PersonalizedTanabe16SegmentBodyData()
            parameters.loadStandardData(os.path.join(dataDir,'../database/standardData.pickle'))
            personalizedParameters = parameters.getParameters()
            for i in range(16):
                self.surfaceFaceAreas[i] = personalizedParameters['bodySurfaceArea'][i]            
        #Used when creating project simulations
        self.bodyDataModel = parameters
        self.CI = parameters.CI
        self.Rage = parameters.Rage
        self.Metb_sexratio = parameters.getMetbSexRatio()
        
        #Personalize the standard 16 segment data forr the current mesh
        #See Table 11 of S.-i. Tanabe et al, Energy and Buildings 34 (2002) 637-646
        for i in range(16):
            personalizedParameters['bodySurfaceArea'][i] = self.surfaceAreas[i]
        #Metabolic factors
        mfac = np.power(self.totalSurfaceArea/self.basemodelSurfaceArea,self.metabolicScalingFactor)
        personalizedParameters['metabolicRate'][:,0] *= mfac
        personalizedParameters['metabolicRate'][:,1] *= mfac
        personalizedParameters['metabolicRate'][:,2] *= mfac
        personalizedParameters['metabolicRate'][:,4] *= mfac

        personalizedParameters['basalBloodFlow'][:,0] *= mfac
        personalizedParameters['basalBloodFlow'][:,1] *= mfac
        personalizedParameters['basalBloodFlow'][:,2] *= mfac

        personalizedParameters['thermalResitance'][:,0] *= mfac
        personalizedParameters['thermalResitance'][:,1] *= mfac
        personalizedParameters['thermalResitance'][:,2] *= mfac

        personalizedParameters['weightingAndDistributionCoefficients'][:,1] *= mfac
        personalizedParameters['weightingAndDistributionCoefficients'][:,4] *= mfac

        self.personalizedParameters = personalizedParameters
    
    def getPersonalizedParameters(self):
        return self.personalizedParameters
    
    def getFaceIndexes(self):
        if hasattr(self, "faceDofs"):
            return self.faceDofs
        return np.zeros((len(self.faces),1),dtype=np.bool)
    
    
    def computeIncidantFlux(self,source,location):
        if not hasattr(self,'nodeNormalArray'):
            self.nodeNormalArray = np.zeros((len(self.nodes),3))
            self.nodeValues = np.zeros((len(self.nodes),3))
            for nd,v in self.nodes.items():
                self.nodeValues[nd]=v
            for nd,v in self.nodeNormals.items():
                self.nodeNormalArray[nd]=v

        dist = np.linalg.norm(self.nodeValues-np.array(location),axis=1)
        nodeflux = source/(dist*dist)
        dvec = np.array(location)-self.centroid
        dvec /=np.linalg.norm(dvec)
        dvals = np.dot(self.nodeNormalArray,dvec)
        dvals[dvals<0] = 0.0
        #nodeflux[dvals<=0] = 0.0 #Fluxes for rays going away from the source are set to 0
        nodeflux *=dvals
        faceFluxes = np.zeros((len(self.faces),1))
        for fctr in self.faces:
            fn = self.faceNormals[fctr]
            faceFluxes[fctr] = np.mean(nodeflux[fn])
        return faceFluxes
        
    
    def generateMesh(self,context=None,fieldData=None,zeroCenter=False):
        if context is None:
            context = Context('Cartography')
        maxTimeValue=1
        if not fieldData is None:
            maxTimeValue = fieldData.numberOfTimeSamples
        if zincDebug:
            logger = context.getLogger()
        #Clear the region if it already exists
        defaultregion = context.getDefaultRegion()
        region = defaultregion.findChildByName ('manequin')
        if region.isValid():
            defaultregion.removeChild(region)
            
        region = defaultregion.createChild('manequin')
                
        fieldModule = region.getFieldmodule()
        fieldCache = fieldModule.createFieldcache()
        coordinateField = fieldModule.createFieldFiniteElement(3)
        # Set the name of the field, we give it label to help us understand it's purpose
        coordinateField.setName('coordinates')
        coordinateField.setTypeCoordinate(True)
                
        skinTemperature = fieldModule.createFieldFiniteElement(1)
        skinTemperature.setName('Tskin')
        coreTemperature = fieldModule.createFieldFiniteElement(1)
        coreTemperature.setName('Tcore')
        skinWettedNess = fieldModule.createFieldFiniteElement(1)
        skinWettedNess.setName('SkinWettedness')
        thermalResistance= fieldModule.createFieldFiniteElement(1)
        thermalResistance.setName('ThermalResistance')
        evaporativeResistance = fieldModule.createFieldFiniteElement(1)
        evaporativeResistance.setName('EvaporativeResistance')
        
        #above fields may vary with time
        tlist = list(range(maxTimeValue))
        
        # Find a special node set named 'cmiss_nodes'
        nodeset = fieldModule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodeTemplate = nodeset.createNodetemplate()
        # Set the finite element coordinate field for the nodes to use
        nodeTemplate.defineField(coordinateField)
        if cubicHermite:
            nodeTemplate.setValueNumberOfVersions(coordinateField, -1, Node.VALUE_LABEL_D_DS1, 1)
            nodeTemplate.setValueNumberOfVersions(coordinateField, -1, Node.VALUE_LABEL_D_DS2, 1)
            nodeTemplate.setValueNumberOfVersions(coordinateField, -1, Node.VALUE_LABEL_D2_DS1DS2, 1)

        centroid = np.zeros(3)
        if zeroCenter:
            centroid = self.centroid

        fieldModule.beginChange()
        nodeHandles = dict()
        nVals = []
        numFaces = len(self.faces) + 1 #Ensure that the first nodes are for face data handling
        for ky,val in self.nodes.items():
            if ky in self.nodeGroup: #In case of decimated mesh some nodes are not used even though they are defined
                node = nodeset.createNode(numFaces+ky, nodeTemplate)
                fieldCache.setNode(node)
                coordinateField.assignReal(fieldCache,(val-centroid).tolist())
                nodeHandles[numFaces+ky] = node
                nVals.append(val)
        
        nvarray = np.array(nVals)
        self.bbox = [np.max(nvarray,axis=0),np.min(nvarray,axis=0)] 

        #Create a set of nodes for each element to hold element time values
        nodeTemplate = nodeset.createNodetemplate()

        timeSequence = fieldModule.getMatchingTimesequence(tlist)
        nodeTemplate.defineField(skinTemperature)
        nodeTemplate.defineField(coreTemperature)
        nodeTemplate.defineField(skinWettedNess)
        nodeTemplate.defineField(thermalResistance)
        nodeTemplate.defineField(evaporativeResistance)
        nodeTemplate.setTimesequence(skinTemperature,timeSequence)
        nodeTemplate.setTimesequence(coreTemperature,timeSequence)
        nodeTemplate.setTimesequence(skinWettedNess,timeSequence)
        nodeTemplate.setTimesequence(thermalResistance,timeSequence)
        nodeTemplate.setTimesequence(evaporativeResistance,timeSequence)
        

        mesh = fieldModule.findMeshByDimension(2)
        # Specify the dimension and the interpolation function for the element basis function. 
        linear_basis = fieldModule.createElementbasis(2, Elementbasis.FUNCTION_TYPE_LINEAR_LAGRANGE)
        trilinear_basis = fieldModule.createElementbasis(2, Elementbasis.FUNCTION_TYPE_LINEAR_SIMPLEX)
        const_basis = fieldModule.createElementbasis(2, Elementbasis.FUNCTION_TYPE_CONSTANT)
        if cubicHermite:
            linear_basis = fieldModule.createElementbasis(2, Elementbasis.FUNCTION_TYPE_CUBIC_HERMITE)
        
        #Requires new zinc
        qeft = mesh.createElementfieldtemplate(linear_basis)
        teft = mesh.createElementfieldtemplate(trilinear_basis)
        ceft = mesh.createElementfieldtemplate(const_basis)
        
        quadElementTemplate = mesh.createElementtemplate()
        quadElementTemplate.setElementShapeType(Element.SHAPE_TYPE_SQUARE)        
        quadElementTemplate.defineField(coordinateField, -1,qeft)
        quadElementTemplate.defineField(skinTemperature, -1,ceft)
        quadElementTemplate.defineField(coreTemperature, -1,ceft)
        quadElementTemplate.defineField(skinWettedNess, -1,ceft)
        quadElementTemplate.defineField(thermalResistance, -1,ceft)
        quadElementTemplate.defineField(evaporativeResistance,-1, ceft) 

        triElementTemplate  = mesh.createElementtemplate()
        triElementTemplate.setElementShapeType(Element.SHAPE_TYPE_TRIANGLE)
        triElementTemplate.defineField(coordinateField, -1,teft)
        triElementTemplate.defineField(skinTemperature, -1,ceft)
        triElementTemplate.defineField(coreTemperature, -1,ceft)
        triElementTemplate.defineField(skinWettedNess, -1,ceft)
        triElementTemplate.defineField(thermalResistance, -1,ceft)
        triElementTemplate.defineField(evaporativeResistance, -1,ceft)
        dataNodes = dict()
        for fid,nodes in self.faces.items():
            nNumbers = [n+numFaces for n in nodes]
            if len(nodes)==4:
                eno = [nNumbers[0],nNumbers[1],nNumbers[3],nNumbers[2]]
                element = mesh.createElement(-1, quadElementTemplate)
                element.setNodesByIdentifier(qeft, eno)
            else:
                element = mesh.createElement(-1, triElementTemplate)
                element.setNodesByIdentifier(teft, nNumbers)
            
            node = nodeset.createNode(fid+1, nodeTemplate)
            dataNodes[fid] = node
            #Add these nodes to a group so that it is easy to access them                
            element.setNodesByIdentifier(ceft, [node.getIdentifier()])
        
        if not fieldData is None:
            for nd,node in dataNodes.items():
                fieldCache.setNode(node)
                for i in range(maxTimeValue):
                    fieldCache.setTime(i)
                    skinTemperature.assignReal(fieldCache,fieldData.skinTemperature[nd,i])
                    coreTemperature.assignReal(fieldCache,fieldData.coreTemperature[nd,i])
                    skinWettedNess.assignReal(fieldCache,fieldData.skinWettedness[nd,i])
                    thermalResistance.assignReal(fieldCache,fieldData.thermalResistance[nd,i])
                    evaporativeResistance.assignReal(fieldCache,fieldData.evaporativeResistance[nd,i])
                    
        if cubicHermite:
            smooth = fieldModule.createFieldsmoothing()
            coordinateField.smooth(smooth)
 
        fieldModule.defineAllFaces()
    
        fieldModule.endChange()
        
        if zincDebug:
        # write any logger messages:
            loggerMessageCount = logger.getNumberOfMessages()
            if loggerMessageCount > 0:
                for i in range(1, loggerMessageCount + 1):
                    print(logger.getMessageTypeAtIndex(i), logger.getMessageTextAtIndex(i))
                logger.removeAllMessages()
                
        region.writeFile('test.ex2')            

from thermoregulation.Tanabe65MN import Tanabe65MNModel
if __name__ == '__main__':
    #obj = HumanModel(r'../database/male.obj',filterFaces=True)
    obj = HumanModel(r'D:\Temp\Human\infant.obj',filterFaces=True)
    obj.personalizeParameters()
    trModel = Tanabe65MNModel(obj)
    #flux = obj.computeIncidantFlux(10.0, [-5.57895028e-04, 1.19548007e+00,  100.0])
    #np.savetxt('flux.csv', flux,delimiter=',')
    flux = obj.getFaceIndexes()
    #print(obj.numberOfFaces)
    obj.generateMesh()
    
    #obj.getPersonalizedParameters()