# -*- coding: utf-8 -*-
"""
Example script for acquiring images using the nsCamera application. Successful image
  acquisition requires the code in the (REQUIRED) sections. Code in the (OPTIONAL)
  sections demonstrate other available methods.

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

from nsCamera.CameraAssembler import CameraAssembler

#### (1) Initialization (REQUIRED) #####################################################
#
# The CameraAssembler code initializes and manages objects corresponding to the
# three components that comprise a particular nsCamera system. The 'verbose'
# flag controls the output of status messages as the code executes.
#
############

BOARD = "LLNL_v4"
# BOARD = 'LLNL_v1'

COMM = "GigE"
# COMM = 'RS422'

# SENSOR = "icarus"
SENSOR = "icarus2"
# SENSOR = 'daedalus'


ca = CameraAssembler(commname=COMM, boardname=BOARD, sensorname=SENSOR, verbose=4)
# Optional: for commname='RS422',  add the parameter port=n to specify a board attached
#   to a particular COM port, e.g., port=4

# Optional: for commname='GigE', add the parameter ip='w.x.y.z' to specify a board with
#   a particular IP address, e.g., ip='192.168.1.100'. If the board is not using the
#   default port (20482) this must also be specified using the port parameter, e.g.,
#   port=65000

#### (2) Timing (OPTIONAL) #############################################################
#
# The initialization phase sets the default high-speed timing parameters. Override these
#   settings here; alternatively, switch to manual shutter control
#
###########

ca.setTiming("A", (5, 2))  # override side A high-speed timing to '5-2'
ca.setTiming("B", (2, 1))  # override side B high-speed timing to '2-1'

# enables and controls manual shutters
ca.setManualShutters(
    timing=[(100, 50, 100, 50, 100, 50, 100), (100, 50, 100, 50, 100, 50, 100)]
)


#### (3) Customization (OPTIONAL) ######################################################
#
# The initialization phase sets default operating parameters. These parameters may be
#   overridden by explicit directives as shown here.
#
###########

#######
# setPotV (potname, voltage) - Voltage is float
#   setPotV sets contents of pot 'potname' to the value corresponding to 'voltage'
#     based on board.monVmin and board.monVmax
#   Valid 'name' entries are listed as keys in the 'channel_lookups' dictionary in the
#     board code
ca.setPotV("HST_RO_IBIAS", 2.5)  # set ring oscillator frequency
# set relaxation oscillator frequency, use monitor to tune actual voltage
ca.setPotV("HST_OSC_CTL", 1.45, tune=True)

#######
# getPotV (potname)
#   getPotV returns the setting of pot 'potname'
#   Valid 'name' entries are listed as keys in the 'channel_lookups' or
#     'monitor_lookups' dictionaries in the board code
# confirm pot8 setting
print("HST_A_NDELAY voltage setting: " + str(ca.getPotV("HST_A_NDELAY")))

#######
# getMonV (potname)
#   getMonV returns the monitor voltage reading associated with pot 'potname'
#   Valid 'name' entries are listed as keys in the 'channel_lookups' or
#     'monitor_lookups' dictionaries in the board code

# read ADC monitor 8
print(
    "HST_A_NDELAY monitor voltage: " + str(ca.getMonV("HST_A_NDELAY"))
)

#######
# setPot (name, val) - 'val' is float where 0.0 <= val < 1.0
#   setPot sets contents of register or subregister object 'name' to (int)val * max
#     where 'max' is the maximum possible value, e.g., for a single byte subregister,
#     max = 0xFF; val = 0.5 results in the subregister being set to 0x80
#   Valid 'name' entries are listed as keys in the 'channel_lookups' dictionary in the
#     board code
ca.setPot("HST_B_NDELAY", 1)

#######
# getPot (name)
#   getPot returns the contents of register or subregister object 'name'
#   normalized to float value between 0.0 and 1.0
#       e.g., for a single byte subregister, max = 0xFF; a setting of 0xAB returns a
#         float value, approximately .6706
#   Valid 'name' entries are listed as keys in the 'channel_lookups' or
#     'monitor_lookups' dictionaries in the board code
print(
    "HST_B_NDELAY setting (0.0-1.0) : " + str(ca.getPot("HST_B_NDELAY"))
)  # confirm pot8 setting
print(
    "HST_B_NDELAY monitor voltage: " + str(ca.getMonV("HST_B_NDELAY"))
)  # read ADC monitor 8

#######
# setRegister (name, hexString)
#   setRegister sets contents of register 'name' to hexString
#   Valid 'name' entries are listed as keys in the 'registers' dictionary in the board
#     code
ca.setRegister("LED_GP", "000000FF")  # light all general purpose LEDs

#######
# getRegister (name)
#   getRegister returns contents of register 'name' as hexstring
#   Valid 'name' entries are listed as keys in the 'registers' dictionary in the board
#     code
print("Timer: " + ca.getRegister("TIMER_VALUE")[1])  # prints contents of timer counter

#######
# setSubregister (name, bitString)
#   setRegister sets contents of subregister 'name' to bitString
#   Valid 'name' entries are listed as keys in the 'channel_lookups' dictionary in the
#     board code
ca.setSubregister("COLQUENCHEN", "0")  # disable column quench function.

#######
# getSubregister (name)
#   getSubregister returns contents of subregister 'name' as bit string
#   Valid 'name' entries are listed as keys in the 'channel_lookups' or
#     'monitor_lookups' dictionaries in the board code
print("SRAM status: " + ca.getSubregister("SRAM_READY")[1])  # read status of ready flag

### (4) Activation (REQUIRED) ##########################################################
#
# Once operating parameters have been set as desired, arm the camera. Once the camera
#   has acquired data, download and save the images
#
###########


#######
# arm camera; image capture commences when camera receives software-initiated trigger;
# use "HARDWARE" or leave blank to use external hardware trigger
ca.arm("SOFTWARE")

# wait for data ready status flag on board, then download images
(frames, datalen, data_err,) = ca.readoff()

if data_err:
    print("Error in data acquisition!")

ca.saveTiffs(frames)  # save images to disk as tiffs
ca.saveNumpys(frames)  # save images to disk as numpy data files
ca.plotFrames(frames)  # generate plots of images

### (4) Miscellaneous (OPTIONAL) #######################################################
#
# Other methods that may be useful
#
###########

# bits of status register in reverse order (i.e., the contents of bit '0' of the
#   register is at ca.checkStatus()[0]
print("Status bits: " + ca.checkStatus())
ca.reportStatus()  # prints brief report based on contents of status register

# reads on-board timer (seconds since power-up or reset)
print("Timer: " + str(ca.getTimer()))
ca.resetTimer()  # reset on-board timer

# reads on-board temperature sensor (if available)
print("Temperature reading: " + str(ca.getTemp()) + " C")

print("\n\nRegister dump:\n")
print("\n".join(ca.dumpRegisters()))

### (6) Shutdown (REQUIRED) ############################################################
#
# Disconnect comms session and free resources
#
###########

ca.closeDevice()

"""
Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.
"""
