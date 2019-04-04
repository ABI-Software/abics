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
#Ensure we use pyqt api 2 and consistency across python 2 and 3
import sip

API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)
from opencmiss.zinc.context import Context
from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.node import Node

#If the mesh is a triangular mesh that face constants are not supported
faceValues = False
cubicHermite = False

class ClothingMeshModel(object):
    '''
    Converts obj file based on manuel bastoni to opencmiss zinc
    In order to get the part a face belong to export the mesh from blender in obj format
    In Export select
        polygroups
        Keep vertex order
    This will generate polygroups where faces belonging to a group are generated
    '''
    
    nodes = dict()
    faces = dict()
        
    def __init__(self, objfilename):
        '''
        Constructor
        '''
        ndctr = 0
        fctr = 0
        
        with open(objfilename,'r+') as obj:
            for lines in obj:
                if lines.startswith('v '):
                    tok = lines.split(' ')
                    self.nodes[ndctr] = [float(tok[1]),float(tok[2]),float(tok[3])]
                    ndctr += 1
                elif lines.startswith('f '):
                    #Handle quads and triangles
                    tok = lines.split(' ')
                    v1  = int(tok[1].split('/')[0])
                    v2  = int(tok[2].split('/')[0])
                    v3  = int(tok[3].split('/')[0])
                    if len(tok) > 4:                    
                        v4  = int(tok[4].split('/')[0])
                        self.faces[fctr] = [v1-1,v2-1,v3-1,v4-1]
                    else:
                        self.faces[fctr] = [v1-1,v2-1,v3-1]
                    fctr += 1
        
    
    
    def generateMesh(self,context,regionName):
        defaultregion = context.getDefaultRegion()
        #If region with regionName exists - delete it
        region = defaultregion.findChildByName(regionName)
        if region.isValid():
            defaultregion.removeChild(region)
        region = defaultregion.createChild(regionName)
                
        fieldModule = region.getFieldmodule()
        fieldCache = fieldModule.createFieldcache()
        coordinateField = fieldModule.createFieldFiniteElement(3)
        # Set the name of the field, we give it label to help us understand it's purpose
        coordinateField.setName('coordinates')
        coordinateField.setTypeCoordinate(True)
        self.region = region
        self.fieldModule = fieldModule
        self.coordinateField = coordinateField
        
        # Find a special node set named 'cmiss_nodes'
        nodeset = fieldModule.findNodesetByName('nodes')
        nodeTemplate = nodeset.createNodetemplate()
        # Set the finite element coordinate field for the nodes to use
        nodeTemplate.defineField(coordinateField)
        if cubicHermite:
            nodeTemplate.setValueNumberOfVersions(coordinateField, -1, Node.VALUE_LABEL_D_DS1, 1)
            nodeTemplate.setValueNumberOfVersions(coordinateField, -1, Node.VALUE_LABEL_D_DS2, 1)
            nodeTemplate.setValueNumberOfVersions(coordinateField, -1, Node.VALUE_LABEL_D2_DS1DS2, 1)
            
        fieldModule.beginChange()
        nodeHandles = dict()

        for ky,val in self.nodes.items():
            node = nodeset.createNode(ky, nodeTemplate)
            fieldCache.setNode(node)
            coordinateField.assignReal(fieldCache,val)
            nodeHandles[ky] = node

        mesh = fieldModule.findMeshByDimension(2)
        quadElementTemplate = mesh.createElementtemplate()
        quadElementTemplate.setElementShapeType(Element.SHAPE_TYPE_SQUARE)
        
        element_node_count = 4
        quadElementTemplate.setNumberOfNodes(element_node_count)
        # Specify the dimension and the interpolation function for the element basis function. 
        linear_basis = fieldModule.createElementbasis(2, Elementbasis.FUNCTION_TYPE_LINEAR_LAGRANGE)
        if cubicHermite:
            linear_basis = fieldModule.createElementbasis(2, Elementbasis.FUNCTION_TYPE_CUBIC_HERMITE)
        # The indexes of the nodes in the node template we want to use
        linear_node_indexes = [1, 2, 3, 4]
        quadElementTemplate.defineFieldSimpleNodal(coordinateField, -1, linear_basis, linear_node_indexes)
        
        triElementTemplate  = mesh.createElementtemplate()
        triElementTemplate.setElementShapeType(Element.SHAPE_TYPE_TRIANGLE)
        
        trielement_node_count = 3
        triElementTemplate.setNumberOfNodes(trielement_node_count)
        # Specify the dimension and the interpolation function for the element basis function. 
        trilinear_basis = fieldModule.createElementbasis(2, Elementbasis.FUNCTION_TYPE_LINEAR_SIMPLEX)
        # The indexes of the nodes in the node template we want to use
        trilinear_node_indexes = [1, 2, 3]
        triElementTemplate.defineFieldSimpleNodal(coordinateField, -1, trilinear_basis, trilinear_node_indexes)
        
        
        for nodes in list(self.faces.values()):
            if len(nodes)==4:
                quadElementTemplate.setNode(1, nodeHandles[nodes[0]])
                quadElementTemplate.setNode(2, nodeHandles[nodes[1]])
                quadElementTemplate.setNode(4, nodeHandles[nodes[2]])
                quadElementTemplate.setNode(3, nodeHandles[nodes[3]])
                elem = mesh.createElement(-1, quadElementTemplate)
                #Field element constant only for quads
                fieldCache.setElement(elem)
            else:
                triElementTemplate.setNode(1, nodeHandles[nodes[2]])
                triElementTemplate.setNode(2, nodeHandles[nodes[1]])
                triElementTemplate.setNode(3, nodeHandles[nodes[0]])
                elem = mesh.createElement(-1, triElementTemplate)
                

 
        if cubicHermite:
            smooth = fieldModule.createFieldsmoothing()
            coordinateField.smooth(smooth)
 
        fieldModule.defineAllFaces()
    
        fieldModule.endChange()
        
        '''
        sir = defaultregion.createStreaminformationRegion()
        sir.createStreamresourceFile('femaleSuiteWithHat.exregion')
        defaultregion.write(sir)
    
        print 'Completed Mesh Generation'
        '''
    def createSurfaceGraphics(self):
        scene = self.region.getScene()
        scene.beginChange()
        #Setup the Tessellation
        tessellationModule = scene.getTessellationmodule()
                 
        tessellationModule.beginChange()
        tessellation = tessellationModule.createTessellation()
        tessellation.setName('ClothingSurface')
        tessellation.setMinimumDivisions([4,4,4])
        tessellationModule.endChange()
                
        # Clothing geometry coordinates
        surface = scene.createGraphicsSurfaces()
        surface.setCoordinateField(self.coordinateField)
        #Set the material
        #surface.setMaterial(material)
        surface.setTessellation(tessellation)
        scene.endChange()



if __name__ == '__main__':
    context = Context('Clothing')
    obj = ClothingMeshModel('femaleSuiteWithHat.obj')
    print(len(obj.faces))
    obj.generateMesh(context,'suite')
