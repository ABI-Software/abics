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
from __future__ import print_function, unicode_literals
import sip

#Ensure we use pyqt api 2 and consistency across python 2 and 3
API_NAMES = ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]
API_VERSION = 2
for name in API_NAMES:
    sip.setapi(name, API_VERSION)

import logging, sys, os
from PyQt5 import QtCore, QtWidgets, QtGui

dir_path = os.path.dirname(os.path.realpath(sys.argv[0]))
if not hasattr(sys, 'frozen'): #For py2exe
    dir_path = os.path.join(dir_path,"..")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    icon = QtGui.QIcon(os.path.join(dir_path,'./uifiles/images/ABI.ico'))
    app.setWindowIcon(icon)

# Create and display the splash screen
    splash_pix = QtGui.QPixmap(os.path.join(os.path.dirname(os.path.realpath(__file__)),'../uifiles/images/splash.png'))

    splash = QtWidgets.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
    splash.setEnabled(False)

    # adding progress bar
    progressBar = QtWidgets.QProgressBar(splash)
    progressBar.setMaximum(5)
    progressBar.setGeometry(0, splash_pix.height() - 10, splash_pix.width(), 20)

    splash.setMask(splash_pix.mask())
    splash.raise_()
    splash.show()
    splash.activateWindow()
    splash.showMessage("", int(QtCore.Qt.AlignTop | QtCore.Qt.AlignCenter), QtCore.Qt.black)
#Check if imports are available and packages are available
    try:
        import opencmiss.zinc
        #Check version
        version = opencmiss.zinc.__version__.split('.')
        #version = list(map(int,opencmiss.zinc.__version__.split('.')))
        logging.info("Opencmiss zinc version %s. Tested against (3.3.0)"%opencmiss.zinc.__version__)
        if int(version[0]) < 3 and int(version[1]) < 1 and int(version[2]) < 2:
            QtWidgets.QMessageBox.critical(app, "Required module missing", "Python Package OpenCMISS Zinc release #3.3.0 or higher is required!! Install or contact your administrator")
            sys.exit(0)
        progressBar.setValue(1)
        app.processEvents()                    
        from PyQt5.QtCore import QT_VERSION_STR
        logging.info("pyqt5 version %s. Tested against (5.6.2)"%QT_VERSION_STR)
        progressBar.setValue(2)
        app.processEvents()
        import pyqtgraph
        logging.info("pyqtgraph version %s. Tested against (0.10.0)"%pyqtgraph.__version__)
        progressBar.setValue(3)
        app.processEvents()
        from diskcache.fanout import FanoutCache        
        from userinterface.Simulator import WorkspaceWidget, SimulationMainWindow
    except ImportError as e:
        QtWidgets.QMessageBox.critical(None, "Required module missing", "%s\n Install or contact your administrator"%e)
        sys.exit(0)
    
    workspaceWidget = WorkspaceWidget()
    
    mw = SimulationMainWindow()
    def createDiskCache(diskCacheLocation):
        workspaceWidget.hide()
        splash.show()
        global icmaDiskCache
        icmaDiskCache = FanoutCache(str(diskCacheLocation), shards=10, timeout=2)
        sizeLimit = int(icmaDiskCache.get('BGECACHESIZELIMIT',default=1048576)) #Default 1 MB
        limitSet = bool(icmaDiskCache.get('BGECACHESIZELIMITSET',default=False))
        if not limitSet:
            icmaDiskCache.reset('size_limit',sizeLimit)
            icmaDiskCache.reset('cull_limit', 0)
            icmaDiskCache.set('BGECACHESIZELIMITSET',True)
            icmaDiskCache.set('BGECACHESIZELIMIT',sizeLimit)

        mw.reconfigure(icmaDiskCache)
        splash.hide()
        mw.show()
        
    progressBar.setValue(5)
    app.processEvents()            
    workspaceWidget.diskSpaceSelected.connect(createDiskCache)
    splash.hide()
    workspaceWidget.show()

    sys.exit(app.exec_())
    
