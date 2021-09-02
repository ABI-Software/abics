Auckland Bioengineering Institute Comfort Simulator (ABICS)
===========================================================

The Auckland Bioengineering Institute (ABI) Comfort Simulator (CS) is a user friendly, free, open-source, python based tool that enables the simulation of thermoregulation on realistic human geometries for various environmental, body constitution and metabolic activity levels.
A user manual describing the features of the tool, outlining the steps to setup an experiment, simulate, and visualize it is available in the docs folder.
#Installation 
The code is compatible with python 3.6 or higher. The tool relies on dependencies which are expected to be available in the host python environment (both the client and the server). 
Current opencmisszinc release requires python 3.9, so a python 3.9 or higher environment is required. 
Install Python v 3.9 or higher.
-------------
You may use an existing python distribution, ensure the packages are installed through appropriate installers.
Install dependencies
-------------
  Below are the commands for installing dependencies in an anaconda based environment. 
```
conda install pyqt=5 
conda install scipy json
conda install -c conda-forge diskcache pyqtgraph sqlitedict pyzmq
```
Install/Link with opencmiss-zinc
-------------
Install opencmiss zinc library from pypi
```
pip install opencmiss.zinc
```

Launching the tool
------------------
The tool can be launched from the commandline using the script abics.bat (.sh) on Windows(Linux). 

Launching the server
--------------------
The server can be launched using the script server.bat (.sh) on Windows(Linux). The default portno is 5570, to change the port number the script should be edited and the port number should be passed as on option "-p <portno>".
