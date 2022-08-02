# -*- coding: utf-8 -*-
"""
Script for automating Ophir light meter measurements

Author: Jeremy Martin Hill (jerhill@llnl.gov)

Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.

Version: 2.1.1  (July 2021)
"""

import time

import win32com.client


class Ophir:
    def __init__(self):  # TODO; add initialization parameters for wavelength, etc.
        self.COM = None
        self.DHandle = None
        OphirCOM = win32com.client.Dispatch("OphirLMMeasurement.CoLMMeasurement")
        # Stop & Close all devices
        OphirCOM.StopAllStreams()
        OphirCOM.CloseAll()
        # Scan for connected Devices
        DeviceList = OphirCOM.ScanUSB()
        for Device in DeviceList:  # if any device is connected
            DeviceHandle = OphirCOM.OpenUSBDevice(Device)  # open first device
            exists = OphirCOM.IsSensorExists(DeviceHandle, 0)
            if exists:
                self.COM = OphirCOM
                self.DevHan = DeviceHandle
        if not self.COM:
            print("Unable to open an Ophir device")

        self.COM.SetMeasurementMode(self.DevHan, 0, 1)
        self.SetWavelength(self.DevHan, 0, 3)
        self.SetRange(self.DevHan, 0, 0)
        self.SetThreshold(self.DevHan, 0, 0)

    def closeOphir(self):
        self.COM.StopAllStreams()
        self.COM.CloseAll()

    def OphirTest(self):
        # misc functions
        print("GetDeviceInfo")  # (u'StarBright', u'SB1.37', u'795577')
        print(self.COM.GetDeviceInfo(self.DevHan))
        print("GetDriverVersion")  # WinUSB
        print(self.COM.GetDriverVersion())
        print("GetSensorInfo")  # (u'788341', u'Pyroelectric', u'PD10-pJ-C')
        print(self.COM.GetSensorInfo(self.DevHan, 0))
        print("GetVersion")  # 901
        print(self.COM.GetVersion())
        print("GetDiffuser")  # (0, (u'N/A',)) - no adjustable diffuser on sensor
        print(self.COM.GetDiffuser(self.DevHan, 0))
        print("GetFilter")  # (-1, ()) - only applicable to photodiode sensors
        print(self.COM.GetFilter(self.DevHan, 0))
        print("GetMeasurementMode")  # (1, (u'Power', u'Energy', u'Exposure'))
        print(self.COM.GetMeasurementMode(self.DevHan, 0))
        print("GetPulseLengths")  # (0, (u'5.0us',))
        print(self.COM.GetPulseLengths(self.DevHan, 0))
        print("GetRanges")  # (0, (u'200nJ', u'20.0nJ', u'2.00nJ', u'200pJ'))
        print(self.COM.GetRanges(self.DevHan, 0))
        print("GetThreshold")
        # (0, (u'Min', u'2%', u'3%', u'4%', u'5%', u'6%', u'7%', u'8%', u'9%',
        #   u'10%', u'11%', u'12%', u'13%', u'14%', u'15%', u'16%', u'17%', u'18%',
        #   u'19%', u'20%', u'21%', u'22%', u'23%', u'24%', u'25%'))
        print(self.COM.GetThreshold(self.DevHan, 0))
        print("GetWavelengths")
        # (0, (u'213', u'248', u'355', u'532', u'905', u'1064'))
        print(self.COM.GetWavelengths(self.DevHan, 0))
        print("GetWavelengthsExtra")  # (True, 200, 1100) - true is modifiable
        print(self.COM.GetWavelengthsExtra(self.DevHan, 0))

        # try tweaking some settings
        # Not applicable for PD10: AddWavelength
        print("\nTrying some modifications\n")

        self.COM.SetMeasurementMode(self.DevHan, 0, 2)
        # self.COM.SaveSettings(self.DevHan, 0) # not sure what this actually does
        print("GetMeasurementMode")  # (1, (u'Power', u'Energy', u'Exposure'))
        print(self.COM.GetMeasurementMode(self.DevHan, 0))

        self.COM.SetWavelength(self.DevHan, 0, 3)
        print("GetWavelengths")
        # (0, (u'213', u'248', u'355', u'532', u'905', u'1064'))
        print(self.COM.GetWavelengths(self.DevHan, 0))

        self.COM.SetRange(self.DevHan, 0, 2)
        print("GetRanges")  # (0, (u'200nJ', u'20.0nJ', u'2.00nJ', u'200pJ'))
        print(self.COM.GetRanges(self.DevHan, 0))

        self.COM.SetThreshold(self.DevHan, 0, 9)
        print("GetThreshold")
        # (0, (u'Min', u'2%', u'3%', u'4%', u'5%', u'6%', u'7%', u'8%', u'9%',
        #   u'10%', u'11%', u'12%', u'13%', u'14%', u'15%', u'16%', u'17%', u'18%',
        #   u'19%', u'20%', u'21%', u'22%', u'23%', u'24%', u'25%'))
        print(self.COM.GetThreshold(self.DevHan, 0))

        # self.COM(self.DevHan, 0, 2, 1) #turns on immediate mode, need to watch for
        #   dataready event to use?

        # An Example for Range control. first get the ranges
        # ranges = self.COM.GetRanges(self.DevHan, 0)  # returns outputs as tuple
        # print (ranges)
        # # change range at your will
        # if ranges[0] > 0:
        #     newRange = ranges[0] - 1
        # else:
        #     newRange = ranges[0] + 1
        # # set new range
        # self.COM.SetRange(self.DevHan, 0, newRange)

        # An Example for data retrieving
        self.COM.StartStream(self.DevHan, 0)  # start measuring
        for i in range(10):
            time.sleep(0.2)  # wait a little for data
            data = self.COM.GetData(self.DevHan, 0)
            # data is length 3 tuple of length n tuples of measurements (double),
            #   timestamp (double), status (long)
            if len(data[0]) > 0:
                # if any data available, print the first one from the batch
                print(
                    "Reading = {0}, TimeStamp = {1}, Status = {2} ".format(
                        data[0][0], data[1][0], data[2][0]
                    )
                )
        self.COM.StopStream(self.DevHan, 0)

        # Restore defaults
        self.COM.SetMeasurementMode(self.DevHan, 0, 1)
        self.COM.SetWavelength(self.DevHan, 0, 3)
        self.COM.SetRange(self.DevHan, 0, 0)
        self.COM.SetThreshold(self.DevHan, 0, 0)


"""
Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.
"""
