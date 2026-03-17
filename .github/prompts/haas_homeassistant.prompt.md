---
name: haas_homeassistant
description: Initial repo creation
---
Format this folder as a github repository.
Keep a log of chat interactions in a file named `chat_log.md` in the root of the repository.
Keep critical projects notes and information for use with LLMS in a file named `project_notes.md` in the root of the repository.


I have a HAAS UMC500 5 axis CNC milling machine, running the HAAS NGC controller. It supports data collection via MTConnect or telnet, and I would like to use an existing project: [Haas MQTT MTConnect Adapter](https://github.com/EfrainRodriguez/Haas-MQTT-MTConnect-Adapter) to interface with it. I want to use this project to create a custom integration in Home Assistant that allows me to monitor my CNC machine from within the Home Assistant interface.


I'd like to be able to monitor virtually all of the exposed status parameters and machine variables. 
The critical ones are:
- Machine status (running, idle, error, etc.)
- Current job information (job name, progress, estimated time remaining, etc. We might have to calculate some of this information ourselves based on the data we have access to, such as the current program line and the total number of lines in the program, as well as recent runs of the same program to get an estimate of how long the program takes to run.)
- Error notifications (if the machine encounters an error/alarm, I want to be notified in Home Assistant)
- Maintenance alerts (if the machine requires maintenance, I want to be notified in Home Assistant)
- Sensor data (temperature, spindle speed, air pressure, coolant tank status etc.)
- Probe/measuring data and active tool information and work offset information. 
- Current tool in spindle
- Current tool length and diameter measurements, and any changes to those measurements during operation.
- Axis positions (X, Y, Z, A, B, C)


The Home Assistant integration should be designed to be as efficient as possible, minimizing the number of mtconnect queries while still providing real-time updates on the machine's status and job information. I want to be able to see the machine's status and job information in the Home Assistant dashboard

Information such as remaining time, running status, and error notifications should be updated in real-time or near real-time (remaining time can be decoupled into a timer we manage instead of constantly polling the machine) in the Home Assistant interface. Tool information should be update less frequently but still often so we can monitor for changes in measured length throughout the duration of a program or throughout the day. Administrative information such as the machine verion, software version, and other static information can be updated less frequently, perhaps once a day or when the integration is first set up. Axis positions and sensor data should be updated at the same rate as the machine status and job information, as these can change frequently during operation. 


Build the framework for the Home Assistant integration, including the necessary configuration files and code structure according to best practices for Home Assistant custom integrations. For the moment lets use standard icons and other home assistant graphical elements. Later on we can customize the icons and graphical elements. 

For starters I only need the entities exposed for the critical endpoints mentioned above. Once we have those working we can expand to include the nice-to-have features and any other endpoints that are available in MTConnect. 

