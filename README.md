# Rootics – graphical user interface (GUI) for better handling of environmental profiling (microsensors)

The graphical user interface (GUI) aims to improve the handling of sediment profiles measured by electrochemical microsensors from Unisense. 
So far, the GUI includes O2, pH, H2S (or total sulfide), and EP sensor profiles. Based on the sensor output file, all sediment profiles belonging to the same group are identified and plotted together. Rootics automatically determines the sediment-water interface for O2 profiles based on the point of inflection. Additionally, a sensor drift correction is included for EP sensors based either a linear regression or a 2nd order polynomial fit. The user can manually mark outlier or trim the data to the range of interest.
