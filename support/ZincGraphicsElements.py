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

from opencmiss.zinc.scenecoordinatesystem import SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_LEFT,\
    SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_TOP
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.spectrum import Spectrumcomponent

def createZincTitleBar(context):
    defaultregion = context.getDefaultRegion()
    fm = context.getFontmodule()
    fnt = fm.getDefaultFont()
    fnt.setBold(True)
    ds = defaultregion.getScene() 
    graphics = ds.findGraphicsByName('TitleBar')
    if not graphics.isValid():
        graphics = ds.createGraphicsPoints()
        graphics.setName('TitleBar')
        graphics.setScenecoordinatesystem(SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_TOP)
    titleBar = graphics.getGraphicspointattributes()                 
    #Size is required to ensure that the text is rendered on the top
    titleBar.setBaseSize([1.0,1.0,1.0])
    titleBar.setGlyphOffset([-0.4,0.9,0.0])

    titleBar.setLabelText(1,'Mesh not yet loaded')
    return graphics, titleBar
                


class GenerateZincGraphicsElements(object):
    '''
    Create the mesh surface and related datafields for rendering mesh and the results 
    '''
    displaySpectrum = None

    def __init__(self, context,regionName):
        '''
        Constructor
        '''
        self.context = context
        self.regionName = regionName
        self.spectrums = dict()
        self.spectrumComponent = dict()
        self.dataField = dict()
        self.colorbars = dict()
        self.scene = None
        self.lights = dict()
                        
    def setTime(self,time):
        try:
            self.timekeeper.setTime(time)
        except:
            pass
    
    def removeLightSource(self,name):
        if name in self.lights:
            lnode = self.lights[name][0]
            nset = lnode.getNodeset()
            nset.destroyNode(lnode)
            del self.lights[name]

    def setColorBarFontColor(self,mat=str('black')):
        if hasattr(self, 'colorbars') and 'Tskin' in self.colorbars:
            mm = self.context.getMaterialmodule()
            mm.defineStandardMaterials()
            self.colorbars['Tskin'].setMaterial(mm.findMaterialByName(mat))   
            self.colorbars['Tskin'].setVisibilityFlag(True)          
        
    def hideColorBar(self):
        if hasattr(self, 'currentColorBar'):
            self.currentColorBar.setVisibilityFlag(False)

    def createLightSource(self,name,pos,rgb,fullintensity):
        if fullintensity>0.0:
            intensity = np.log(fullintensity)/2.3
        else:
            intensity = fullintensity
        if intensity>10:
            intensity = 10.0
        if fullintensity!=0.0:
            intensity +=1
        #Ensure that the position is not too far from visible region (5*mesh extant)
        if hasattr(self, 'meshExtants'):
            for i in range(3):
                if np.fabs(pos[i])>10*self.meshExtants[i]:
                    pos[i] = np.sign(pos[i])*10*self.meshExtants[i]
            
        if name not in self.lights:        
            defaultregion = self.context.getDefaultRegion()
            region = defaultregion.findChildByName("lighting")
            if not region.isValid():
                region = defaultregion.createChild("lighting")
                
            fieldModule = region.getFieldmodule()
            coordinateField = fieldModule.findFieldByName('coordinates')
            nameField = fieldModule.findFieldByName('name')
            scaleField = fieldModule.findFieldByName('scale')
            colorField  = fieldModule.findFieldByName('color')
            if not coordinateField.isValid():
                coordinateField = fieldModule.createFieldFiniteElement(3)
                # Set the name of the field, we give it label to help us understand it's purpose
                coordinateField.setName('coordinates')
                coordinateField.setTypeCoordinate(True)
                nameField = fieldModule.createFieldStoredString()
                nameField.setName("name")
                scaleField = fieldModule.createFieldFiniteElement(9)
                scaleField.setName("scale")
                colorField = fieldModule.createFieldFiniteElement(3)
                # Set the name of the field, we give it label to help us understand it's purpose
                colorField.setName('color')
                
            scene = region.getScene()
            scene.beginChange()
            spectrum_module = scene.getSpectrummodule()
            spectrum = spectrum_module.createSpectrum()
            spectrum.setMaterialOverwrite(True) #This will ensure that the transparency of the material is used
            
            cmpt = [Spectrumcomponent.COLOUR_MAPPING_TYPE_RED,\
                    Spectrumcomponent.COLOUR_MAPPING_TYPE_GREEN,Spectrumcomponent.COLOUR_MAPPING_TYPE_BLUE]
            for i,scmp in enumerate(cmpt):
                spectrum_comp1 = spectrum.createSpectrumcomponent()
                spectrum_comp1.setColourMappingType(scmp)
                spectrum_comp1.setExtendBelow(True)
                spectrum_comp1.setExtendAbove(True)
                spectrum_comp1.setRangeMaximum(1)
                spectrum_comp1.setRangeMinimum(0)
                spectrum_comp1.setFieldComponent(i+1)
                            
            scene.endChange()

            nodeset = fieldModule.findNodesetByFieldDomainType(coordinateField.DOMAIN_TYPE_NODES)
            nodeTemplate = nodeset.createNodetemplate()
            # Set the finite element coordinate field for the nodes to use
            nodeTemplate.defineField(coordinateField)
            nodeTemplate.defineField(nameField)
            nodeTemplate.defineField(scaleField)
            nodeTemplate.defineField(colorField)
            lightNode = nodeset.createNode(-1, nodeTemplate)
            fieldCache = fieldModule.createFieldcache()
            fieldCache.setNode(lightNode)
            coordinateField.assignReal(fieldCache,pos)
            nameField.assignString(fieldCache,name)
            scaleField.assignReal(fieldCache,[intensity,0.0,0.0,0.0,intensity,0.0,0.0,0.0,intensity])
            colorField.assignReal(fieldCache,rgb)
            scene = region.getScene()
            glyphModule = scene.getGlyphmodule()
            glyphModule.defineStandardGlyphs() 
            
            graphics = scene.createGraphicsPoints()
            graphics.setFieldDomainType(coordinateField.DOMAIN_TYPE_NODES)
            graphics.setCoordinateField(coordinateField)
            pointattributes = graphics.getGraphicspointattributes()
            pointattributes.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
            pointattributes.setOrientationScaleField(scaleField)
            graphics.setDataField(colorField)
            graphics.setSpectrum(spectrum)
            graphics.setVisibilityFlag(True)    
            self.lightFieldCache = fieldCache
            self.lightCoordinatedField = coordinateField
            self.lightScaleField = scaleField
            self.lightColorField = colorField 
            self.lights[name] = [lightNode,graphics]              
        else:
            lightNode = self.lights[name][0]
            self.lightFieldCache.setNode(lightNode)
            self.lightCoordinatedField.assignReal(self.lightFieldCache,pos)
            self.lightScaleField.assignReal(self.lightFieldCache,[intensity,0.0,0.0,0.0,intensity,0.0,0.0,0.0,intensity])
            self.lightColorField.assignReal(self.lightFieldCache,rgb)
    
    def createCentroidGlyph(self,pos,meshExtants=[1,1,1]):
        if hasattr(self, 'centroidGlyph'):
            return self.centroidGlyph
        defaultregion = self.context.getDefaultRegion()
        region = defaultregion.findChildByName(self.regionName)
        if not region.isValid():
            region = defaultregion.createChild(self.regionName)
            
        fieldModule = region.getFieldmodule()
        coordinateField = fieldModule.findFieldByName('coordinates')
        if not coordinateField.isValid():
            coordinateField = fieldModule.createFieldFiniteElement(3)
            # Set the name of the field, we give it label to help us understand it's purpose
            coordinateField.setName('coordinates')
            coordinateField.setTypeCoordinate(True)
 
        nodeset = fieldModule.findNodesetByFieldDomainType(coordinateField.DOMAIN_TYPE_DATAPOINTS)
        nodeTemplate = nodeset.createNodetemplate()
        # Set the finite element coordinate field for the nodes to use
        nodeTemplate.defineField(coordinateField)
        self.centroidnode = nodeset.createNode(-1, nodeTemplate)
        fieldCache = fieldModule.createFieldcache()
        fieldCache.setNode(self.centroidnode)
        coordinateField.assignReal(fieldCache,pos.tolist())

        scene = region.getScene()
        glyphModule = scene.getGlyphmodule()
        glyphModule.defineStandardGlyphs() 
        
        graphics = scene.createGraphicsPoints()
        graphics.setFieldDomainType(coordinateField.DOMAIN_TYPE_DATAPOINTS)
        graphics.setCoordinateField(coordinateField)
        pointattributes = graphics.getGraphicspointattributes()
        pointattributes.setGlyphShapeType(Glyph.SHAPE_TYPE_AXES_SOLID_XYZ)
        self.meshExtants = meshExtants
        me = max(meshExtants)/2.0
        pointattributes.setBaseSize([me,me,me])      
        graphics.setVisibilityFlag(False)      
        self.centroidGlyph = graphics       
        return graphics
        
    def updateRadiationFluxField(self,flux):
        fieldName = 'Tskin'
        defaultregion = self.context.getDefaultRegion()
        region = defaultregion.findChildByName(self.regionName)
        fieldModule = region.getFieldmodule()
        fieldModule.beginChange()
        fieldCache = fieldModule.createFieldcache()
        spectrum_comp1 = self.spectrumComponent[fieldName]
        spectrum_comp1.setRangeMaximum(flux.max())
        spectrum_comp1.setRangeMinimum(flux.min())
        potentialField = fieldModule.findFieldByName(fieldName)  
        ns = fieldModule.findNodesetByFieldDomainType(potentialField.DOMAIN_TYPE_NODES)
        for i,v in enumerate(flux):
            node = ns.findNodeByIdentifier(i+1)
            fieldCache.setNode(node)
            potentialField.assignReal(fieldCache,v.tolist())
        fieldModule.endChange()
        self.currentColorBar = self.colorbars['Tskin']
        self.currentColorBar.setVisibilityFlag(True)     
            
            
    def createGraphicsElements(self,maxPotentials = {},minPotentials = {}):
        logger = self.context.getLogger()
        defaultregion = self.context.getDefaultRegion()
        region = defaultregion.findChildByName(self.regionName)
            
        if region.isValid():
            scene = region.getScene()
            self.scene = scene
            timekeepermodule = scene.getTimekeepermodule()
            timekeeper = timekeepermodule.getDefaultTimekeeper()
            timekeeper.setMinimumTime(0)
            self.timekeeper = timekeeper
            #The order in which the scene objects are created is the order in which they are rendered 
            #Ensure that objects that need to be transparent are drawn last
                
            # We use the beginChange and endChange to wrap any immediate changes and will
            # streamline the rendering of the scene.
            scene.beginChange()
            spectrum_module = scene.getSpectrummodule()
            glyphModule = scene.getGlyphmodule()
            glyphModule.defineStandardGlyphs() 
            # createSurfaceGraphic graphic start
            fieldModule = region.getFieldmodule()
            coordinateField = fieldModule.findFieldByName('coordinates')
            def setupField(fieldName):
                potentialField = fieldModule.findFieldByName(fieldName)
                spectrum = spectrum_module.createSpectrum()
                spectrum.setMaterialOverwrite(True) #This will ensure that the transparency of the material is used
                #spectrum.setName(fieldName)
                spectrum_comp1 = spectrum.createSpectrumcomponent()
                spectrum_comp1.setColourMappingType(spectrum_comp1.COLOUR_MAPPING_TYPE_RAINBOW)
                spectrum_comp1.setColourReverse(True)
                spectrum_comp1.setExtendBelow(True)
                spectrum_comp1.setExtendAbove(True)
                if fieldName in maxPotentials:
                    spectrum_comp1.setRangeMaximum(maxPotentials[fieldName])
                if fieldName in minPotentials:
                    spectrum_comp1.setRangeMinimum(minPotentials[fieldName])
                
                self.spectrums[fieldName] = spectrum
                self.spectrumComponent[fieldName] = spectrum_comp1
                self.dataField[fieldName] = potentialField
            fields = ['Tskin','Tcore','SkinWettedness','ThermalResistance','EvaporativeResistance']
            for fieldName in fields:                
                setupField(fieldName)

            #Setup the Tessellation
            tessellationModule = scene.getTessellationmodule()
            if not hasattr(self,'tessellation'):     
                tessellationModule.beginChange()
                tessellation = tessellationModule.createTessellation()
                tessellation.setName('surface')
                tessellation.setMinimumDivisions([4,4,4])
                tessellationModule.endChange()
                self.tessellation = tessellation
            # Skin geometry coordinates
            outerSkinSurface = scene.createGraphicsSurfaces()
            outerSkinSurface.setCoordinateField(coordinateField)
            #Set the material
            #outerSkinSurface.setMaterial(material)
            #Set the data field
            outerSkinSurface.setDataField(self.dataField['Tskin'])
            outerSkinSurface.setSpectrum(self.spectrums['Tskin'])
            outerSkinSurface.setTessellation(self.tessellation)
            self.surface = outerSkinSurface
            
            def setupColorBars(fieldName):
                glyphModule.beginChange()
                colourbar = glyphModule.createGlyphColourBar(self.spectrums[fieldName])
                if fieldName in ['Tskin','Tcore']:
                    colourbar.setNumberFormat('%0.2g')
                    colourbar.setLabelDivisions(5)
                    self.spectrumComponent[fieldName].setExtendBelow(True)
                    self.spectrumComponent[fieldName].setExtendAbove(True)
                else:
                    colourbar.setNumberFormat('%0.5g')
                    #colourbar.setLabelDivisions(5)
                #colourbar.setName(fieldName)
                
                graphics = scene.createGraphicsPoints()
                #graphics.setName("%scolourbar"%fieldName)
                graphics.setScenecoordinatesystem(SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_LEFT)
                pointattributes = graphics.getGraphicspointattributes()
                pointattributes.setGlyph(colourbar)
                pointattributes.setBaseSize([1.0,1.0,1.0])
                pointattributes.setGlyphOffset([-0.9,0.0,0.0])       
                graphics.setVisibilityFlag(False)             
                
                glyphModule.endChange()
                self.colorbars[fieldName] = graphics

            for fieldName in fields:
                setupColorBars(fieldName)

            self.currentColorBar = self.colorbars['Tskin']
            if 'Tskin' in maxPotentials:
                self.currentColorBar.setVisibilityFlag(True)                            
            
            scene.endChange()
        loggerMessageCount = logger.getNumberOfMessages()
        if loggerMessageCount > 0:
            for i in range(1, loggerMessageCount + 1):
                print(logger.getMessageTypeAtIndex(i), logger.getMessageTextAtIndex(i))
            logger.removeAllMessages()            
    
    def destroyGraphicsElements(self):
        self.spectrums.clear()
        self.spectrumComponent.clear()
        self.dataField.clear()        
        self.colorbars.clear()
        self.scene.removeAllGraphics()
        self.surface = None
        self.scene = None
        self.lights = dict()
        if hasattr(self, 'centroidGlyph'):
            del self.centroidGlyph
        
    
    def setDataField(self,fieldName):
        self.scene.beginChange()
        self.surface.setDataField(self.dataField[fieldName])
        self.surface.setSpectrum(self.spectrums[fieldName])
        self.currentColorBar.setVisibilityFlag(False)
        self.currentColorBar = self.colorbars[fieldName]
        self.currentColorBar.setVisibilityFlag(True)        
        self.scene.endChange()