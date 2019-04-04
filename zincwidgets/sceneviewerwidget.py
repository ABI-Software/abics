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
 
# This python module is intended to facilitate users creating their own applications that use OpenCMISS-Zinc
# See the examples at https://svn.physiomeproject.org/svn/cmiss/zinc/bindings/trunk/python/ for further
# information.
from PyQt5.Qt import pyqtSignal

try:
    from PyQt5 import QtCore, QtOpenGL
except ImportError:
    from PySide import QtCore, QtOpenGL

# from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.sceneviewer import Sceneviewer, Sceneviewerevent
from opencmiss.zinc.sceneviewerinput import Sceneviewerinput
from opencmiss.zinc.scenecoordinatesystem import \
        SCENECOORDINATESYSTEM_LOCAL, \
        SCENECOORDINATESYSTEM_WINDOW_PIXEL_TOP_LEFT,\
        SCENECOORDINATESYSTEM_WORLD
from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.status import OK

# mapping from qt to zinc start
# Create a button map of Qt mouse buttons to Zinc input buttons
button_map = {QtCore.Qt.LeftButton: Sceneviewerinput.BUTTON_TYPE_LEFT,
              QtCore.Qt.MidButton: Sceneviewerinput.BUTTON_TYPE_MIDDLE,
              QtCore.Qt.RightButton: Sceneviewerinput.BUTTON_TYPE_RIGHT}

# Create a modifier map of Qt modifier keys to Zinc modifier keys
def modifier_map(qt_modifiers):
    '''
    Return a Zinc Sceneviewerinput modifiers object that is created from
    the Qt modifier flags passed in.
    '''
    modifiers = Sceneviewerinput.MODIFIER_FLAG_NONE
    if qt_modifiers & QtCore.Qt.SHIFT:
        modifiers = modifiers | Sceneviewerinput.MODIFIER_FLAG_SHIFT

    return modifiers
# mapping from qt to zinc end

SELECTION_RUBBERBAND_NAME = 'selection_rubberband'

# projectionMode start
class ProjectionMode(object):

    PARALLEL = 0
    PERSPECTIVE = 1
# projectionMode end


# selectionMode start
class SelectionMode(object):

    NONE = -1
    EXCLUSIVE = 0
    ADDITIVE = 1
# selectionMode end


class SceneviewerWidget(QtOpenGL.QGLWidget):
    
    try:
        # PyQt
        graphicsInitialized = pyqtSignal()
    except AttributeError:
        # PySide
        graphicsInitialized = QtCore.Signal()        
    

    # Create a signal to notify when the sceneviewer is ready.
    graphicsInitialized = pyqtSignal()

    # init start
    def __init__(self, parent=None, shared=None):
        '''
        Call the super class init functions, set the  Zinc context and the scene viewer handle to None.
        Initialise other attributes that deal with selection and the rotation of the plane.
        '''
        QtOpenGL.QGLWidget.__init__(self, parent, shared)
        # Create a Zinc context from which all other objects can be derived either directly or indirectly.
        self._context = None
        self._sceneviewer = None
        self._scenepicker = None

        # Selection attributes
        self._nodeSelectMode = True
        self._dataSelectMode = True
        self._elemSelectMode = True
        self._selection_mode = SelectionMode.NONE
        self._selectionGroup = None
        self._selectionBox = None # created and destroyed on demand in mouse events
        self._ignore_mouse_events = False
        self._selectionKeyPressed = False
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        # init end

    def setContext(self, context):
        '''
        Sets the context for this ZincWidget.  This should be set before the initializeGL()
        method is called otherwise the scene viewer cannot be created.
        '''
        self._context = context

    def getContext(self):
        if not self._context is None:
            return self._context
        else:
            raise RuntimeError("Zinc context has not been set in Sceneviewerwidget.")

    def getSceneviewer(self):
        '''
        Get the scene viewer for this ZincWidget.
        '''
        return self._sceneviewer
    
    def setSelectionModeAdditive(self):
        self._selectionAlwaysAdditive = True

    def setSelectModeNode(self):
        '''
        Set the selection mode to select *only* nodes.
        '''
        self._nodeSelectMode = True
        self._dataSelectMode = False
        self._elemSelectMode = False

    def setSelectModeData(self):
        '''
        Set the selection mode to select *only* datapoints.
        '''
        self._nodeSelectMode = False
        self._dataSelectMode = True
        self._elemSelectMode = False

    def setSelectModeElement(self):
        '''
        Set the selection mode to select *only* elements.
        '''
        self._nodeSelectMode = False
        self._dataSelectMode = False
        self._elemSelectMode = True

    def setSelectModeAll(self):
        '''
        Set the selection mode to select both nodes and elements.
        '''
        self._nodeSelectMode = True
        self._dataSelectMode = True
        self._elemSelectMode = True
        
    def setBackgroundColor(self,rgb):
        if self._sceneviewer is not None:
            self._sceneviewer.setBackgroundColourRGB(rgb)

    # initializeGL start
    def initializeGL(self):
        '''
        Initialise the Zinc scene for drawing the axis glyph at a point.  
        '''
        # Following throws exception if you haven't called setContext() yet
        self.getContext()
        if self._sceneviewer is None:
            # Get the scene viewer module.
            scene_viewer_module = self._context.getSceneviewermodule()

            # From the scene viewer module we can create a scene viewer, we set up the
            # scene viewer to have the same OpenGL properties as the QGLWidget.
            self._sceneviewer = scene_viewer_module.createSceneviewer(Sceneviewer.BUFFERING_MODE_DOUBLE, Sceneviewer.STEREO_MODE_DEFAULT)
            self._sceneviewer.setProjectionMode(Sceneviewer.PROJECTION_MODE_PERSPECTIVE)

            # Create a filter for visibility flags which will allow us to see our graphic.
            filter_module = self._context.getScenefiltermodule()
            # By default graphics are created with their visibility flags set to on (or true).
            graphics_filter = filter_module.createScenefilterVisibilityFlags()

            # Set the graphics filter for the scene viewer otherwise nothing will be visible.
            self._sceneviewer.setScenefilter(graphics_filter)
            region = self._context.getDefaultRegion()
            scene = region.getScene()
            fieldmodule = region.getFieldmodule()

            self._sceneviewer.setScene(scene)

            self._selectionGroup = fieldmodule.createFieldGroup()
            scene.setSelectionField(self._selectionGroup)

            self._scenepicker = scene.createScenepicker()
            self._scenepicker.setScenefilter(graphics_filter)

            # Set up unproject pipeline
            self._window_coords_from = fieldmodule.createFieldConstant([0, 0, 0])
            self._global_coords_from = fieldmodule.createFieldConstant([0, 0, 0])
            unproject = fieldmodule.createFieldSceneviewerProjection(self._sceneviewer, SCENECOORDINATESYSTEM_WINDOW_PIXEL_TOP_LEFT, SCENECOORDINATESYSTEM_WORLD)
            project = fieldmodule.createFieldSceneviewerProjection(self._sceneviewer, SCENECOORDINATESYSTEM_WORLD, SCENECOORDINATESYSTEM_WINDOW_PIXEL_TOP_LEFT)

    #         unproject_t = fieldmodule.createFieldTranspose(4, unproject)
            self._global_coords_to = fieldmodule.createFieldProjection(self._window_coords_from, unproject)
            self._window_coords_to = fieldmodule.createFieldProjection(self._global_coords_from, project)


            self._sceneviewer.viewAll()

    #  Not really applicable to us yet.
    #         self._selection_notifier = scene.createSelectionnotifier()
    #         self._selection_notifier.setCallback(self._zincSelectionEvent)

            self._sceneviewernotifier = self._sceneviewer.createSceneviewernotifier()
            self._sceneviewernotifier.setCallback(self._zincSceneviewerEvent)

            self.graphicsInitialized.emit()
            # initializeGL end

    def setProjectionMode(self, mode):
        if mode == ProjectionMode.PARALLEL:
            self._sceneviewer.setProjectionMode(Sceneviewer.PROJECTION_MODE_PARALLEL)
        elif mode == ProjectionMode.PERSPECTIVE:
            self._sceneviewer.setProjectionMode(Sceneviewer.PROJECTION_MODE_PERSPECTIVE)

    def getProjectionMode(self):
        if self._sceneviewer.getProjectionMode() == Sceneviewer.PROJECTION_MODE_PARALLEL:
            return ProjectionMode.PARALLEL
        elif self._sceneviewer.getProjectionMode() == Sceneviewer.PROJECTION_MODE_PERSPECTIVE:
            return ProjectionMode.PERSPECTIVE

    def getViewParameters(self):
        result, eye, lookat, up = self._sceneviewer.getLookatParameters()
        if result == OK:
            angle = self._sceneviewer.getViewAngle()
            return (eye, lookat, up, angle)

        return None

    def setViewParameters(self, eye, lookat, up, angle):
        self._sceneviewer.beginChange()
        self._sceneviewer.setLookatParametersNonSkew(eye, lookat, up)
        self._sceneviewer.setViewAngle(angle)
        self._sceneviewer.endChange()

    def setScenefilter(self, scenefilter):
        self._sceneviewer.setScenefilter(scenefilter)

    def getScenefilter(self):
        return self._sceneviewer.getScenefilter()

    def getScenepicker(self):
        return self._scenepicker

    def setScenepicker(self, scenepicker):
        self._scenepicker = scenepicker

    def setPickingRectangle(self, coordinate_system, left, bottom, right, top):
        self._scenepicker.setSceneviewerRectangle(self._sceneviewer, coordinate_system, left, bottom, right, top);

    def setSelectionfilter(self, scenefilter):
        self._scenepicker.setScenefilter(scenefilter)

    def getSelectionfilter(self):
        result, scenefilter = self._scenepicker.getScenefilter()
        if result == OK:
            return scenefilter

        return None

    def project(self, x, y, z):
        '''
        project the given point in global coordinates into window coordinates
        with the origin at the window's top left pixel.
        '''
        in_coords = [x, y, z]
        fieldmodule = self._global_coords_from.getFieldmodule()
        fieldcache = fieldmodule.createFieldcache()
        self._global_coords_from.assignReal(fieldcache, in_coords)
        result, out_coords = self._window_coords_to.evaluateReal(fieldcache, 3)
        if result == OK:
            return out_coords  # [out_coords[0] / out_coords[3], out_coords[1] / out_coords[3], out_coords[2] / out_coords[3]]

        return None

    def unproject(self, x, y, z):
        '''
        unproject the given point in window coordinates where the origin is
        at the window's top left pixel into global coordinates.  The z value
        is a depth which is mapped so that 0 is on the near plane and 1 is 
        on the far plane.
        ???GRC -1 on the far and +1 on the near clipping plane
        '''
        in_coords = [x, y, z]
        fieldmodule = self._window_coords_from.getFieldmodule()
        fieldcache = fieldmodule.createFieldcache()
        self._window_coords_from.assignReal(fieldcache, in_coords)
        result, out_coords = self._global_coords_to.evaluateReal(fieldcache, 3)
        if result == OK:
            return out_coords  # [out_coords[0] / out_coords[3], out_coords[1] / out_coords[3], out_coords[2] / out_coords[3]]

        return None

    def getViewportSize(self):
        result, width, height = self._sceneviewer.getViewportSize()
        if result == OK:
            return (width, height)

        return None

    def setTumbleRate(self, rate):
        self._sceneviewer.setTumbleRate(rate)

    def _getNearestGraphic(self, x, y, domain_type):
        self._scenepicker.setSceneviewerRectangle(self._sceneviewer, SCENECOORDINATESYSTEM_LOCAL, x - 0.5, y - 0.5, x + 0.5, y + 0.5)
        nearest_graphics = self._scenepicker.getNearestGraphics()
        if nearest_graphics.isValid() and nearest_graphics.getFieldDomainType() == domain_type:
            return nearest_graphics

        return None

    def getNearestGraphics(self):
        return self._scenepicker.getNearestGraphics()

    def getNearestGraphicsNode(self, x, y):
        return self._getNearestGraphic(x, y, Field.DOMAIN_TYPE_NODES)

    def getNearestGraphicsPoint(self, x, y):
        '''
        Assuming given x and y is in the sending widgets coordinates 
        which is a parent of this widget.  For example the values given 
        directly from the event in the parent widget.
        '''
        return self._getNearestGraphic(x, y, Field.DOMAIN_TYPE_POINT)

    def getNearestElementGraphics(self):
        return self._scenepicker.getNearestElementGraphics()

    def getNearestGraphicsMesh3D(self, x, y):
        return self._getNearestGraphic(x, y, Field.DOMAIN_TYPE_MESH3D)

    def getNearestGraphicsMesh2D(self, x, y):
        return self._getNearestGraphic(x, y, Field.DOMAIN_TYPE_MESH2D)

    def getNearestNode(self, x, y):
        self._scenepicker.setSceneviewerRectangle(self._sceneviewer, SCENECOORDINATESYSTEM_LOCAL, x - 0.5, y - 0.5, x + 0.5, y + 0.5)
        node = self._scenepicker.getNearestNode()

        return node

    def addPickedNodesToFieldGroup(self, selection_group):
        self._scenepicker.addPickedNodesToFieldGroup(selection_group)

    def setIgnoreMouseEvents(self, value):
        self._ignore_mouse_events = value

    def viewAll(self):
        '''
        Helper method to set the current scene viewer to view everything
        visible in the current scene.
        '''
        self._sceneviewer.viewAll()

    # paintGL start
    def paintGL(self):
        '''
        Render the scene for this scene viewer.  The QGLWidget has already set up the
        correct OpenGL buffer for us so all we need do is render into it.  The scene viewer
        will clear the background so any OpenGL drawing of your own needs to go after this
        API call.
        '''
        self._sceneviewer.renderScene()
        # paintGL end

    def _zincSceneviewerEvent(self, event):
        '''
        Process a scene viewer event.  The updateGL() method is called for a
        repaint required event all other events are ignored.
        '''
        if event.getChangeFlags() & Sceneviewerevent.CHANGE_FLAG_REPAINT_REQUIRED:
            QtCore.QTimer.singleShot(0, self.updateGL)

#  Not applicable at the current point in time.
#     def _zincSelectionEvent(self, event):
#         print(event.getChangeFlags())
#         print('go the selection change')

    # resizeGL start
    def resizeGL(self, width, height):
        '''
        Respond to widget resize events.
        '''
        self._sceneviewer.setViewportSize(width, height)
        # resizeGL end
        
    def keyPressEvent(self, event):
        if (event.key() == QtCore.Qt.Key_S) and event.isAutoRepeat() == False:
            self._selectionKeyPressed = True
            event.setAccepted(True)
        else:
            event.ignore()
        
            
    def keyReleaseEvent(self, event):
        if (event.key() == QtCore.Qt.Key_S)  and event.isAutoRepeat() == False:
            self._selectionKeyPressed = False
            event.setAccepted(True)
        else:
            event.ignore()

    def mousePressEvent(self, event):
        '''
        Inform the scene viewer of a mouse press event.
        '''
        event.accept()
        self._handle_mouse_events = False  # Track when the zinc should be handling mouse events
        if self._ignore_mouse_events:
            event.ignore()
        elif button_map[event.button()] == Sceneviewerinput.BUTTON_TYPE_LEFT and self._selectionKeyPressed and (self._nodeSelectMode or self._elemSelectMode):
            self._selection_position_start = (event.x(), event.y())
            self._selection_mode = SelectionMode.EXCLUSIVE
            if event.modifiers() & QtCore.Qt.SHIFT:
                self._selection_mode = SelectionMode.ADDITIVE
        else:
            scene_input = self._sceneviewer.createSceneviewerinput()
            scene_input.setPosition(event.x(), event.y())
            scene_input.setEventType(Sceneviewerinput.EVENT_TYPE_BUTTON_PRESS)
            scene_input.setButtonType(button_map[event.button()])
            scene_input.setModifierFlags(modifier_map(event.modifiers()))
            self._sceneviewer.processSceneviewerinput(scene_input)
            self._handle_mouse_events = True            

    def mouseReleaseEvent(self, event):
        '''
        Inform the scene viewer of a mouse release event.
        '''
        event.accept()
        if not self._ignore_mouse_events and self._selection_mode != SelectionMode.NONE:
            x = event.x()
            y = event.y()
            # Construct a small frustum to look for nodes in.
            root_region = self._context.getDefaultRegion()
            root_region.beginHierarchicalChange()
            if self._selectionBox != None:
                scene = self._selectionBox.getScene()
                scene.removeGraphics(self._selectionBox)
                self._selectionBox = None

            if (x != self._selection_position_start[0] and y != self._selection_position_start[1]):
                left = min(x, self._selection_position_start[0])
                right = max(x, self._selection_position_start[0])
                bottom = min(y, self._selection_position_start[1])
                top = max(y, self._selection_position_start[1])
                self._scenepicker.setSceneviewerRectangle(self._sceneviewer, SCENECOORDINATESYSTEM_LOCAL, left, bottom, right, top);
                if self._selection_mode == SelectionMode.EXCLUSIVE:
                    self._selectionGroup.clear()
                if self._nodeSelectMode or self._dataSelectMode:
                    self._scenepicker.addPickedNodesToFieldGroup(self._selectionGroup)
                if self._elemSelectMode:
                    self._scenepicker.addPickedElementsToFieldGroup(self._selectionGroup)
            else:

                self._scenepicker.setSceneviewerRectangle(self._sceneviewer, SCENECOORDINATESYSTEM_LOCAL, x - 0.5, y - 0.5, x + 0.5, y + 0.5)
                if self._nodeSelectMode and self._elemSelectMode and self._selection_mode == SelectionMode.EXCLUSIVE and not self._scenepicker.getNearestGraphics().isValid():
                    self._selectionGroup.clear()

                if self._nodeSelectMode and (self._scenepicker.getNearestGraphics().getFieldDomainType() == Field.DOMAIN_TYPE_NODES):
                    node = self._scenepicker.getNearestNode()
                    nodeset = node.getNodeset()

                    nodegroup = self._selectionGroup.getFieldNodeGroup(nodeset)
                    if not nodegroup.isValid():
                        nodegroup = self._selectionGroup.createFieldNodeGroup(nodeset)

                    group = nodegroup.getNodesetGroup()
                    if self._selection_mode == SelectionMode.EXCLUSIVE:
                        remove_current = group.getSize() == 1 and group.containsNode(node)
                        self._selectionGroup.clear()
                        if not remove_current:
                            group.addNode(node)
                    elif self._selection_mode == SelectionMode.ADDITIVE:
                        if group.containsNode(node):
                            group.removeNode(node)
                        else:
                            group.addNode(node)

                if self._elemSelectMode and (self._scenepicker.getNearestGraphics().getFieldDomainType() in [Field.DOMAIN_TYPE_MESH1D, Field.DOMAIN_TYPE_MESH2D, Field.DOMAIN_TYPE_MESH3D, Field.DOMAIN_TYPE_MESH_HIGHEST_DIMENSION]):
                    elem = self._scenepicker.getNearestElement()
                    mesh = elem.getMesh()

                    elementgroup = self._selectionGroup.getFieldElementGroup(mesh)
                    if not elementgroup.isValid():
                        elementgroup = self._selectionGroup.createFieldElementGroup(mesh)

                    group = elementgroup.getMeshGroup()
                    if self._selection_mode == SelectionMode.EXCLUSIVE:
                        remove_current = group.getSize() == 1 and group.containsElement(elem)
                        self._selectionGroup.clear()
                        if not remove_current:
                            group.addElement(elem)
                    elif self._selection_mode == SelectionMode.ADDITIVE:
                        if group.containsElement(elem):
                            group.removeElement(elem)
                        else:
                            group.addElement(elem)


            root_region.endHierarchicalChange()
            self._selection_mode = SelectionMode.NONE
        elif not self._ignore_mouse_events and self._handle_mouse_events:
            scene_input = self._sceneviewer.createSceneviewerinput()
            scene_input.setPosition(event.x(), event.y())
            scene_input.setEventType(Sceneviewerinput.EVENT_TYPE_BUTTON_RELEASE)
            scene_input.setButtonType(button_map[event.button()])

            self._sceneviewer.processSceneviewerinput(scene_input)
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        '''
        Inform the scene viewer of a mouse move event and update the OpenGL scene to reflect this
        change to the viewport.
        '''

        event.accept()
        if not self._ignore_mouse_events and self._selection_mode != SelectionMode.NONE:
            x = event.x()
            y = event.y()
            xdiff = float(x - self._selection_position_start[0])
            ydiff = float(y - self._selection_position_start[1])
            if abs(xdiff) < 0.0001:
                xdiff = 1
            if abs(ydiff) < 0.0001:
                ydiff = 1
            xoff = float(self._selection_position_start[0]) / xdiff + 0.5
            yoff = float(self._selection_position_start[1]) / ydiff + 0.5

            # Using a non-ideal workaround for creating a rubber band for selection.
            # This will create strange visual artifacts when using two scene viewers looking at
            # the same scene.  Waiting on a proper solution in the API.
            # Note if the standard glyphs haven't been defined then the
            # selection box will not be visible
            scene = self._sceneviewer.getScene()
            scene.beginChange()
            if self._selectionBox is None:
                self._selectionBox = scene.createGraphicsPoints()
                self._selectionBox.setScenecoordinatesystem(SCENECOORDINATESYSTEM_WINDOW_PIXEL_TOP_LEFT)
            attributes = self._selectionBox.getGraphicspointattributes()
            attributes.setGlyphShapeType(Glyph.SHAPE_TYPE_CUBE_WIREFRAME)
            attributes.setBaseSize([xdiff, ydiff, 0.999])
            attributes.setGlyphOffset([xoff, -yoff, 0])
            #self._selectionBox.setVisibilityFlag(True)
            scene.endChange()
        elif not self._ignore_mouse_events and self._handle_mouse_events:
            scene_input = self._sceneviewer.createSceneviewerinput()
            scene_input.setPosition(event.x(), event.y())
            scene_input.setEventType(Sceneviewerinput.EVENT_TYPE_MOTION_NOTIFY)
            if event.type() == QtCore.QEvent.Leave:
                scene_input.setPosition(-1, -1)

            self._sceneviewer.processSceneviewerinput(scene_input)
        else:
            event.ignore()

