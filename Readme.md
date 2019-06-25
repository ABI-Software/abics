Auckland Bioengineering Institute Comfort Simulator (ABICS)
===========================================================

The Auckland Bioengineering Institute (ABI) Comfort Simulator (CS) is a user friendly, free, open-source, python based tool that enables the simulation of thermoregulation on realistic human geometries for various environmental, body constitution and metabolic activity levels.
A user manual describing the features of the tool, outlining the steps to setup an experiment, simulate, and visualize it is available in the docs folder.

Installation Instructions
-------------------------
Download opencmiss zinc library from the development releases for the target operating system
The binaries can be found at
http://opencmiss.org/downloads.html#/package/opencmisslibs/devreleases

Install/Extract the archive and determine the python binding version that has been provided.
Look into the OpenCMISS-Libraries<VERSION>/lib directory
If the directory python2.7 exists then zinc bindings for python 2.7 exists
If the directory python3.6 exists then zinc bindings for python 3.6 exists
If both exist, choose one that you like (note that python 3.6 bindings will not work in python 3.7)
Install Python 
(you can use an existing python distribution, ensure the packages are installed through appropriate installers)

miniconda 2.7 or 3.6 (Based on the opencmiss-zinc library) 

Install dependencies
--------------------
conda install pyqt=5
conda install scipy json 
conda install -c conda-forge diskcache pyqtgraph
pip install sqlitedict 

Install/Link with opencmiss-zinc
Zinc can be installed by executing
python setup.py install 
from the OpenCMISS-Libraries<VERSION>/lib/python<2,3>/Release/opencmiss.zinc/

Alternatively, this library can be linked through PYTHONPATH
in bash
export PYTHONPATH=OpenCMISS-Libraries<VERSION>/lib/python<2,3>/Release/opencmiss.zinc/:$PYTHONPATH

in windows
set  PYTHONPATH=OpenCMISS-Libraries<VERSION>\lib\python<2,3>\Release\opencmiss.zinc\;%PYTHONPATH%

Launching the tool
------------------
The tool can be launched from the commandline using the script abics.bat (.sh) on Windows(Linux). 

Launching the server
--------------------
The server can be launched using the script server.bat (.sh) on Windows(Linux). The default portno is 5570, to change the port number the script should be edited and the port number should be passed as on option "-p <portno>".