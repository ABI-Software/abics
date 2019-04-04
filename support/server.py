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
import signal
import zmq
from multiprocessing import Pool
from PyQt5 import QtCore, QtWidgets
import sqlitedict
import logging
import pickle
import argparse

#Use a file based dict as we are dealing across processes
simulationresults = sqlitedict.SqliteDict('thermoregulationResults.sqlite', autocommit=True)
simulationprogress = sqlitedict.SqliteDict('thermoregulationProgress.sqlite', autocommit=True)

#Call this function in your main after creating the QApplication
def setup_interrupt_handling():
    """Setup handling of KeyboardInterrupt (Ctrl-C) for PyQt."""
    signal.signal(signal.SIGINT, _interrupt_handler)
    # Regularly run some (any) python code, so the signal handler gets a
    # chance to be executed:
    safe_timer(50, lambda: None)


# Define this as a global function to make sure it is not garbage
# collected when going out of scope:
def _interrupt_handler(signum, frame):
    """Handle KeyboardInterrupt: quit application."""
    QtWidgets.QApplication.quit()


def safe_timer(timeout, func, *args, **kwargs):
    """
    Create a timer that is safe against garbage collection and overlapping
    calls. See: http://ralsina.me/weblog/posts/BB974.html
    """
    def timer_event():
        try:
            func(*args, **kwargs)
        finally:
            QtCore.QTimer.singleShot(timeout, timer_event)
    QtCore.QTimer.singleShot(timeout, timer_event)



def simulationTask(ident,simulator):

    def recordProgress(val):
        print(ident,' progressed by ',val)
        simulationprogress[ident]=val
        
    def recordResults(res):
        print(ident,' Completed')
        simulationresults[ident] = res
        simulationprogress[ident]=1.0
            
    maxSteps = simulator.timeValues.shape[0]
    stepFactor = 100.0/float(maxSteps)
    if stepFactor>1:
        stepFactor = 1.0/float(maxSteps)
    recordProgress(0.25)
    try:
        while simulator.currentTimeIndex < maxSteps:
            simulator.run()
            recordProgress(0.25+0.75*simulator.currentTimeIndex*stepFactor)
            simulator.currentTimeIndex +=1
        recordResults(simulator.getCurrentStatus())
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        res = simulator.getCurrentStatus()
        res['error'] = str(e)
        recordResults(res)
    except KeyboardInterrupt:
        sys.exit(0)
        
class ServerWorker(QtCore.QThread):
    """ServerWorker"""
    def __init__(self, context,processes=4):
        QtCore.QThread.__init__ (self)
        self.context = context
        self.pools = Pool(processes=processes)

    def run(self):
        worker = self.context.socket(zmq.DEALER)
        worker.connect('inproc://backend')
        while True:
            try:
                ident, msx = worker.recv_multipart()
                msg = pickle.loads(msx)
                print("Received ",ident,'\t',msg['comm'])
                if msg['comm']=='start':
                    simulator = msg['simulationdef']
                    self.pools.apply_async(simulationTask,(ident, simulator))
                    msg = pickle.dumps({'status':'success','comm':'start'})
                    worker.send_multipart([ident, msg])
                elif msg['comm']=='getresults':
                    idx = msg['identity']
                    result = simulationresults[idx]
                    msg = pickle.dumps(result)
                    worker.send_multipart([ident, msg])                    
                elif msg['comm']=='getstatus':
                    identities = msg['identity']
                    result = dict()
                    for idx in identities:
                        if idx in simulationprogress:
                            result[idx] = simulationprogress[idx]
                        else:
                            result[idx] = 'Not found'                    
                    msg = pickle.dumps(result)
                    worker.send_multipart([ident, msg])
                elif msg['comm']=='remove':
                    idx = msg['identity']
                    if idx in simulationprogress:
                        del simulationprogress[idx]
                    if idx in simulationresults:
                        del simulationresults[idx]
                    msg = pickle.dumps({'status':'success','comm':'remove'})
                    worker.send_multipart([ident, msg])
                else:
                    msg = pickle.dumps({'status':'failed','message':'command not supported'})
                    worker.send_multipart([ident, msg])
            except Exception as e:
                logging.error(ident)
                import traceback
                traceback.print_exc(file=sys.stdout)
                msg = pickle.dumps({'status':'failed','message':str(e)})
                worker.send_multipart([ident, msg])
            except KeyboardInterrupt:
                print("Interrupt received")
                self.pools.terminate()
                self.pools.join()
                break
        worker.close()



class Tanabe65MNServer(QtCore.QThread):
    """Server"""
    def __init__(self,portno=5570,parent=None):
        super(Tanabe65MNServer,self).__init__(parent)
        self.portno = portno
        
    def run(self):
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        frontend.bind('tcp://*:%d'%self.portno)

        backend = context.socket(zmq.DEALER)
        backend.bind('inproc://backend')
        
        worker = ServerWorker(context)
        worker.start()
        print("Server started. Listening to port %d"%self.portno)
        zmq.proxy(frontend, backend)

        frontend.close()
        backend.close()
        context.term()

import sys
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Server for Thermoregulation solve')
    parser.add_argument('-p','--port', default=5570, help='Port for communication')
    args = vars(parser.parse_args())
    app = QtWidgets.QApplication(sys.argv)
    setup_interrupt_handling()
    server = Tanabe65MNServer(portno=int(args['port']))
    server.start()
    server.wait()
    sys.exit(app.exec_())