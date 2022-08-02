# -*- coding: utf-8 -*-
"""
Script for automating GenTec light meter measurements

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

import serial
import serial.tools.list_ports  # for RS422 serial link setup


class GenTec:
    def __init__(self):
        self.serial = None
        ports = list(serial.tools.list_ports.comports())
        for p, desc, add in ports:
            try:
                ser = serial.Serial(
                    p,
                    115200,
                    parity=serial.PARITY_NONE,
                    timeout=0.01,
                    write_timeout=0.01,
                )
                resp = self.sendSerial(ser, "*VER")
                if "Maestro" in resp:
                    self.serial = ser
                    break
                # print (desc, add, resp)   # uncomment to see available ports
            except Exception as e:
                print(e)
        if not self.serial:
            print("Unable to contact a GenTec Device")

    def closeDevice(self):
        self.serial.close()

    def sendSerial(self, ser, message, sleep=0.3):
        ser.write(message)
        time.sleep(sleep)
        avail = ser.in_waiting
        return ser.read(avail)

    def ready(self):
        self.sendSerial(self.serial, "*CVU")  # should clear NVU in prep for new data

    def GenTecReadTest(self):
        print(self.sendSerial(self.serial, "*VER"))
        print("Press ctrl-c to stop read")
        try:
            while 1:
                time.sleep(1)
                if not "Not" in self.sendSerial(
                    self.serial, "*NVU"
                ):  # skip when response is 'Not Available'
                    print(self.sendSerial(self.serial, "*CVU"))
        except KeyboardInterrupt:
            print("\n --GenTecTest terminated--")
            # self.serial.close()


"""Command list, with response in []
"*SCS03" - set display range to index 03 (see manual p61 for indices) []
"*STL18.0" - set internal trigger level to 18% []
"*GTL" - get internal trigger level [2.0\r\n]
"*GMD" - get index of current display mode (see manual p65) [0\r\n]
"*CVU" - get current device reading [0.012\r\n]
"*NVU" - check if new data available [text response]
"*PWC01550" - set wavelength (interpolate for non-standard) to 1550nm (five digits) []
"*GWL" - get wavelength setting [1064\r\n]
"*VER" - get device info [MAESTRO Version 1.00.18\r\n]
"*STS" - query status [extended list, see p72]
"*ST2" - extended query status [extended list, see p74]

see p58 for parsing joulemeters in binary
"""

if __name__ == "__main__":
    gt = GenTec()
    gt.GenTecTest()

"""
Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.
"""
