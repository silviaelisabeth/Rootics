# Rootics – graphical user interface (GUI) for better handling of environmental profiling (microsensors)

This is a graphical user interface (GUI) for improved handling of sediment profiles measured by electrochemical microsensors from Unisense.  
To speed up the often tedious and repetitive tasks of data analysis, I developed a graphical user interface to assist the user. 
This also allows for better reproducibility of the analysis.
So far, the GUI includes O2, pH, H2S (or total sulfide), and EP sensor profiles. Based on the sensor output file, all sediment profiles belonging to the same group are identified and plotted together. Rootics automatically determines the sediment-water interface for O2 profiles based on the point of inflection. Additionally, a sensor drift correction is included for EP sensors based either a linear regression or a 2nd order polynomial fit. The user can manually mark outlier or trim the data to the range of interest.

Depending on your operating system, I provide two different version - one optimized for windows and on eoptimized for macOS.
In both cases, please do not forget to download the pictures folder containing graphics for your GUI. In case you encounter any issues and the icon/pciture is not displayed in the task bar of the GUI, please make sure that the path in Rootics.py is up to date and directs to this folder.

----

#### SOFTWARE FEATURES
Regarding the software features and requirements: 
- **REQUIREMENT**     
Software versions for both operating systems, macOS (version 13+) and Windows (version 11+), are made available here on GitHub. However, due to the size limitations on GitHub, I cannot upload the packed software. If you are anyways interested in the installation file, please reach out via info@silviazieger.com

- **FUNCTIONALITY**   
Support for management and automation of data analysis steps for electrochemical (micro-) sensors. The software enables multiple profile data from different biological key parameters to be analyzed and visualized together, enabling direct comparison of results. Potential parameters processed by the software are:
   - Dissolved oxygen O2
   - pH value
   - Hydrogen sulfide H2S and/or total sulfide
   - Electrochemical potential EP

- **EFFICIENCY**
The software has been tested by researchers and compared to their usual analysis procedure. 

- **RELIABILITY**     
The main purpose of the software is to analyze multiple sensor profiles together and directly compare different key parameters. In this way, environmental mapping in a larger area or over a longer period becomes easier and more efficient.

- **USABILITY**       
The software is designed to guide the user through all necessary analysis steps. Accordingly, the user should understand the underlying  theory to decide whether the results can be considered reasonable or whether adjustments are required. However, no special knowledge is required to operate the software itself.

- **MAINTAINABILITY** 
In case of any bugs reported by the user, I will update the code scripts and provide an updated version on GitHub.

----

#### LEGAL DISCLAIMER
Copyright © 2021 Silvia E. Zieger. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal 
in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and the permission notice included in the software header shall be included in all copies or substantial portions of the Software.
