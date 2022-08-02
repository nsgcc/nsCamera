# -*- coding: utf-8 -*-
"""
CameraAssembler assembles the separate camera parts into a camera object. This object
controls a combination of three components:

1. board : FPGA board -- LLNL_V1, LLNL_V4
2. comms: communication interface -- GigE, RS422
3. sensor : sensor type -- icarus, icarus2, daedalus

Author: Matthew Dayton (dayton5@llnl.gov)
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

from __future__ import absolute_import

import binascii
import collections
import importlib
import inspect
import logging
import os
import platform
import socket
import sys
import time
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from nsCamera.utils import crc16pure
from nsCamera.utils.Packet import Packet


class CameraAssembler:
    """
    Code to assemble correct code to manage FPGA, frame grabber, and sensor

    Exposed methods:
        initialize() - initializes board registers and pots, sets up sensor
        reinitialize() - initialize board and sensors, restore last known timer settings
        reboot() - perform software reset of board and reinitialize
        getBoardInfo() - parses FPGA_NUM register to retrieve board description
        getRegister(regname) - retrieves contents of named register
        setRegister(regname, string) - sets named register to given value
        resolveSubreg(srname) - resolves alias and retrieves object associated with
          srname
        getSubregister(subregname) - return substring of register identified in board
          attribute 'subregname'
        setSubregister(subregname, valstring) - replace substring of register identified
          in board attribute 'subregname' with 'valstring'
        submitMessages(messages) - set registers or subregisters based on list of
          destination/payload tuples
        getPot(potname) - returns float (0 < value < 1) corresponding to integer stored
          in pot or monitor 'potname'
        setPot(potname, value) - 0 < value < 1; sets named pot to fixed-point number =
          'value' * (maximum pot value)
        getPotV(potname) - returns voltage setting of 'potname'
        setPotV(potname, voltage) - sets named pot to voltage
        getMonV(monname) - returns voltage read by monitor 'monname' (or monitor
          associated with given potname)
        readImgs() - calls arm() and readoff() functions
        deInterlace(frames, interlacing) - extract interlaced frames
        saveFrames(frames) - save image object as one file
        saveTiffs(frames) - save individual frames as tiffs
        saveNumpys(frames) - save individual frames as numpy data files
        dumpNumpy(datastream) - save datastream string to numpy file
        plotFrames(frames) - plot individual frames as tiffs
        checkCRC(string) - checks last four characters of string is valid CRC for rest
          of string
        checkRegSet(register, string) - test set and get register functions for named
          register
        initPowerCheck() - start timers for power continutity check
        powerCheck(delta) - check that board power has not failed
        dummyCheck(image, margin) - counts how many pixels differ from expected dummy
          sensor values by more than margin
        printBoardInfo() - print board information derived from FPGA_NUM register
        dumpRegisters() - return contents of all board registers
        dumpSubregisters() - return contents of all named board subregisters
        str2bytes(string) - convert hexadecimal string to byte string
        bytes2str(sequence) - convert byte sequence to hexadecimal string
        str2nparray(string) - convert string of hexadecimal values into uint16 array
        flatten(llist) - flattens list of lists into single list
        getEnter(text) - print text, then wait for Enter keypress
        mmReadoff(waitflag, variation) - convenience function for MicroManager plugin
        setFrames(min, max) - select subset of frames for readoff
        setRows(min, max, fullsize) - select subset of rows for readoff
        generateFrames(data) - processes data stream from board into frames
        abortReadoff() - cancel readoff in wait-for-SRAM loop
        batchAquire() - fast acquire a finite series of images
        loadTextFrames() - load data sets previously saved as text and convert to frames

    Includes aliases to board- and sensor- specific functions:
        Board functions
            initBoard() - initialize default board register settings and configures ADCs
            initPots() - configure default pot settings before image acquisition
            latchPots() - latch all pot settings into sensor
            initSensor() - register sensor, set default timing settings
            configADCs() - set default ADC configuration
            startCapture() - reads ADC data into SRAM
            disarm() - take camera out of waiting-for-trigger state
            readSRAM() - trigger read from SRAM
            waitForSRAM() - puts board in wait state until data are ready in SRAM
            clearStatus() - clear contents of status registers
            checkStatus() - print contents of status register as reversed bit string
            checkStatus2() - print contents of status register 2 as reversed bit string
            reportStatus() - print report on contents of status registers
            resetTimer() - reset on-board timer
            getTimer() - read on-board timer
            enableLED(status) - enable (default) or disable (status = 0) on-board LEDs
            setLED(LED#, status) - turn LED on (default) or off (status = 0)
            setPowerSave(status) - turn powersave functionality on (default) or off
              (status = 0)
            getPressure() - read on-board pressure sensor
            getTemp() - read on-board temperature sensor
            checkStatus() - read and return status bits in status register 1
            checkStatus2() - read and return status bits in status register 2
            clearStatus() - clear status registers 1 and 2
            reportStatus() - print out human-readable board status report based on
              status registers
        Sensor functions
            checkSensorVoltStat() - checks that jumper settings match sensor selection
            setTiming(side, sequencetuple, delay) - configure high-speed timing
            setArbTiming(side, sequencelist) - configure arbitrary high-speed timing
              sequence
            getTiming(side) - returns high speed timing settings from registers
            setManualShutters() - configures manual shutter timing
            getManualTiming() - returns manual shutter settings from registers
            sensorSpecific() - returns register settings specific to implemented sensor
            setInterlacing(ifactor) - sets interlacing factor
            setHighFullWell(flag) - controls High Full Well mode
            setZeroDeadTime(flag) - controls Zero Dead Time mode
            setTriggerDelay(delayblocks) - sets trigger delay
            parseReadoff(frames) - performs sensor-specific parsing and separation of
              images
        Comms functions
            sendCMD(pkt)- sends packet object via serial port
            arm() - configures software buffers & arms camera
            readoff() - waits for data ready flag, then downloads image data
            writeSerial(cmdString)- submits string 'cmdstring' (usually string is
              preformed packet)
            readSerial(stringlength) - reads string of length 'stringlength' from serial
              port
            closeDevice() - disconnect interface and release resources
    Informational class variables:
        version - nsCamera software version
        FPGAVersion - firmware version (date)
        FPGANum - firmware implementation identifier
        FPGAboardtype - FPGA self-identified board type (should match 'boardname')
        FPGArad = Boolean indicating radiation-tolerant FPGA build
        FPGAsensor = FPGA self-identified sensor family (should correspond to
          'sensorname')
        FPGAinterfaces = FPGA self-identified interfaces (list should include
          'commname')
        FPGAinvalid = invalid FPGA information in register
    """

    def __init__(
        self,
        boardname="llnl_v4",
        commname="GigE",
        sensorname="icarus2",
        verbose=4,
        port=None,
        ip=None,
        logfile=None,
        logtag=None,
    ):
        """
        Args:
            boardname: name of FPGA board: llnl_v1, llnl_v4
            commname: name of communication interface: rs422, gige
            sensorname: name of sensor: icarus, icarus2, daedalus
            verbose: optional, sets logging level
                0: print no logging messages
                1: print CRITICAL logging messages (camera will not operate, e.g.,
                  unable to connect to board)
                2: print ERROR logging messages (camera will not operate as directed,
                  e.g., an attempt to set the timing mode has failed, but the camera
                  is still operational)
                3: print WARNING logging messages (camera will operate as directed, but
                  perhaps not as expected, e.g., ca.setTiming('A', (9, 8), 1) may be
                  programmed correctly, but the actual timing generated by the board
                  will be {1} [9, 8, 9, 14, 9, 8, 9]
                4: print INFO logging messages (operational messages from ordinary
                  camera operation)
            port: optional integer
                RS422: preselects comport for RS422, bypasses port search
                GigE: preselect OrangeTree control port for GigE (ignored if ip option
                  not also given)
            ip: optional string (e.g., '192.168.1.100')
                GigE: bypasses network search and selects particular OrangeTree board -
                  required for some operating systems
            logfile: optional string, name of file to divert console output
            errtag: suffix to add to logging labels
        """
        self.version = "2.1.1"
        self.currtime = 0
        self.oldtime = 0
        self.trigtime = []
        self.waited = []
        self.read = []
        self.unstringed = []
        self.parsedtime = []
        self.savetime = []
        self.cycle = []
        self.boardname = boardname.lower()
        if self.boardname == "llnlv1":
            self.boardname = "llnl_v1"
        if self.boardname == "llnlv4":
            self.boardname = "llnl_v4"
        self.commname = commname.lower()
        self.sensorname = sensorname.lower()
        self.verbose = verbose
        self.port = port
        self.python, self.pyth1, self.pyth2, _, _ = sys.version_info
        self.PY3 = self.python >= 3
        self.platform = platform.system()
        self.arch, _ = platform.architecture()

        self.FPGAVersion = ""
        self.FPGANum = ""
        # FPGA information here and below populated during initialization using
        #   getBoardInfo
        self.FPGAboardtype = ""
        self.FPGArad = False
        self.FPGAsensor = ""
        self.FPGAinterfaces = []

        # indicates invalid FPGA information in register# (0x80000001 accepted as valid)
        self.FPGAinvalid = False

        self.iplist = None
        self.packageroot = os.path.dirname(inspect.getfile(CameraAssembler))
        self.armed = False

        # only one of these collections (senstiming, sensmanual) should be nonempty at
        #   any given time
        self.senstiming = {}  # preserve HST setting against possible power failure
        self.sensmanual = []  # preserve manual timing
        self.inittime = 0
        self.padToFull = False
        self.abort = False

        self.verbmap = {
            0: 99,
            1: logging.CRITICAL,
            2: logging.ERROR,
            3: logging.WARNING,
            4: logging.INFO,
            5: logging.DEBUG,
        }
        if logtag is None:
            logtag = ""
        self.logtag = logtag
        self.logcritbase = "CRITICAL" + self.logtag + ": "
        self.logerrbase = "ERROR" + self.logtag + ": "
        self.logwarnbase = "WARNING" + self.logtag + ": "
        self.loginfobase = "INFO" + self.logtag + ": "
        self.logdebugbase = "DEBUG" + self.logtag + ": "

        self.logcrit = self.logcritbase + "[CA] "
        self.logerr = self.logerrbase + "[CA] "
        self.logwarn = self.logwarnbase + "[CA] "
        self.loginfo = self.loginfobase + "[CA] "
        self.logdebug = self.logdebugbase + "[CA] "

        self.verblevel = self.verbmap.get(verbose, 5)  # defaults to 5 for invalid entry

        if logfile:
            logging.basicConfig(format="%(message)s", filename=logfile)
        else:
            logging.basicConfig(format="%(message)s")
        logging.getLogger().setLevel(self.verblevel)
        logging.getLogger("matplotlib.font_manager").disabled = True

        if ip:
            try:
                iphex = socket.inet_aton(ip)
            except socket.error:
                logging.critical(self.logcrit + "CameraAssembler: invalid IP provided")
                sys.exit(1)
            ipnum = [0, 0, 0, 0]
            for i in range(4):
                if self.PY3:
                    ipnum[i] = iphex[i]
                else:
                    ipnum[i] = int(iphex[i].encode("hex"), 16)
            self.iplist = ipnum

        self.payloaderror = False
        self.initialize()

    ##### Aliases to other objects' methods

    def initBoard(self):
        return self.board.initBoard()

    def initPots(self):
        return self.board.initPots()

    def latchPots(self):
        return self.board.latchPots()

    def initSensor(self):
        return self.board.initSensor()

    def configADCs(self):
        return self.board.configADCs()

    def disarm(self):
        return self.board.disarm()

    def startCapture(self, mode):
        return self.board.startCapture(mode)

    def readSRAM(self):
        return self.board.readSRAM()

    def waitForSRAM(self, timeout=None):
        return self.board.waitForSRAM(timeout)

    def getTimer(self):
        return self.board.getTimer()

    def resetTimer(self):
        return self.board.resetTimer()

    def enableLED(self, status=1):
        return self.board.enableLED(status)

    def setLED(self, LED=1, status=1):
        return self.board.setLED(LED, status)

    def setPowerSave(self, status=1):
        return self.board.setPowerSave(status)

    def setPPER(self, time=None):
        return self.board.setPPER(time)

    def getTemp(self, scale=None):
        return self.board.getTemp(scale)

    def getPressure(self, offset=None, sensitivity=None, units=None):
        return self.board.getPressure(offset, sensitivity, units)

    def clearStatus(self):
        return self.board.clearStatus()

    def checkStatus(self):
        return self.board.checkStatus()

    def checkStatus2(self):
        return self.board.checkStatus2()

    def reportStatus(self):
        return self.board.reportStatus()

    def reportEdgeDetects(self):
        return self.board.reportEdgeDetects()

    def dumpStatus(self):
        return self.board.dumpStatus()

    def checkSensorVoltStat(self):
        return self.sensor.checkSensorVoltStat()

    def setTiming(self, side=None, sequence=None, delay=None):
        return self.sensor.setTiming(side, sequence, delay)

    def setArbTiming(self, side=None, sequence=None):
        return self.sensor.setArbTiming(side, sequence)

    def getTiming(self, side=None, actual=None):
        return self.sensor.getTiming(side, actual)

    def setManualShutters(self, timing=None):
        return self.sensor.setManualShutters(timing)

    def getManualTiming(self):
        return self.sensor.getManualTiming()

    def sensorSpecific(self):
        return self.sensor.sensorSpecific()

    def setInterlacing(self, ifactor=None):
        return self.sensor.setInterlacing(ifactor)

    def setHighFullWell(self, flag=True):
        return self.sensor.setHighFullWell(flag)

    def setZeroDeadTime(self, flag=True):
        return self.sensor.setZeroDeadTime(flag)

    def setTriggerDelay(self, delayblocks=0):
        return self.sensor.setTriggerDelay(delayblocks)

    def parseReadoff(self, frames):
        return self.sensor.parseReadoff(frames)

    def sendCMD(self, pkt):
        return self.comms.sendCMD(pkt)

    def arm(self, mode=None):
        return self.comms.arm(mode)

    def readoff(self, waitOnSRAM=None, timeout=0, fast=None):
        return self.comms.readoff(waitOnSRAM, timeout, fast)

    def writeSerial(self, cmd, timeout=None):
        return self.comms.writeSerial(cmd, timeout)

    def readSerial(self, size, timeout=None):
        return self.comms.readSerial(size, timeout)

    def closeDevice(self):
        return self.comms.closeDevice()

    ############## End aliases

    def initialize(self):
        """
        Initialize board registers and set pots
        """

        ###############
        # For regular version

        # get sensor
        if self.sensorname == "icarus":
            import nsCamera.sensors.icarus as snsr
        elif self.sensorname == "icarus2":
            import nsCamera.sensors.icarus2 as snsr
        elif self.sensorname == "daedalus":
            import nsCamera.sensors.daedalus as snsr
        else:  # catch-all for added sensors to attempt object encapsulation
            sensormodname = ".sensors." + self.sensorname
            try:
                sensormod = importlib.import_module(sensormodname, "nsCamera")
            except ImportError:
                logging.critical(self.logcrit + "invalid sensor name")
                sys.exit(1)
            snsr = getattr(sensormod, self.sensorname)
        self.sensor = snsr(self)

        # kill existing connections (for reinitialize)
        if hasattr(self, "comms"):
            self.closeDevice()

        # get communications interface
        if self.commname == "rs422":
            import nsCamera.comms.RS422 as comms
        elif self.commname == "gige":
            import nsCamera.comms.GigE as comms
        else:
            commsmodname = ".comms." + self.commname
            try:
                commsmod = importlib.import_module(commsmodname, "nsCamera")
            except ImportError:
                logging.critical(self.logcrit + "invalid comms name")
                sys.exit(1)
            comms = getattr(commsmod, self.commname)
        self.comms = comms(self)

        # get board
        if self.boardname == "llnl_v1":
            import nsCamera.boards.LLNL_v1 as brd

            self.board = brd.llnl_v1(self)
        elif self.boardname == "llnl_v4":
            import nsCamera.boards.LLNL_v4 as brd

            self.board = brd.llnl_v4(self)
        else:
            boardmodname = ".board." + self.boardname
            try:
                boardmod = importlib.import_module(boardmodname, "nsCamera")
            except ImportError:
                logging.critical(self.logcrit + "invalid board name")
                sys.exit(1)
            boardobj = getattr(boardmod, self.boardname)
            self.board = boardobj(self)
        ###############

        # ###############
        # # For cython version
        #
        # # get sensor
        # if self.sensorname == "icarus":
        #     import nsCamera.sensors.icarus as snsr
        #     self.sensor = snsr.icarus(self)
        # elif self.sensorname == "icarus2":
        #     import nsCamera.sensors.icarus2 as snsr
        #     self.sensor = snsr.icarus2(self)
        # elif self.sensorname == "daedalus":
        #     import nsCamera.sensors.daedalus as snsr
        #     self.sensor = snsr.daedalus(self)
        #
        # # kill existing connections (for reinitialize)
        # if hasattr(self, "comms"):
        #     self.closeDevice()
        #
        # # get communications interface
        # if self.commname == "rs422":
        #     import nsCamera.comms.RS422 as comms
        #     self.comms = comms.RS422(self)
        # elif self.commname == "gige":
        #     import nsCamera.comms.GigE as comms
        #     self.comms = comms.GigE(self)
        #
        # # get board
        # if self.boardname == "llnl_v1":
        #     import nsCamera.boards.LLNL_v1 as brd
        #     self.board = brd.llnl_v1(self)
        # elif self.boardname == "llnl_v4":
        #     import nsCamera.boards.LLNL_v4 as brd
        #     self.board = brd.llnl_v4(self)
        # ###############

        err, rval = self.getRegister("FPGA_NUM")
        if err or rval == "":
            err, rval = self.getRegister("FPGA_NUM")
            if err or rval == "":
                logging.critical(
                    self.logcrit + "Initialization failed: unable to communicate with "
                    "board. "
                )
            sys.exit(1)

        self.initBoard()
        self.initPots()
        self.initSensor()
        self.initPowerCheck()
        self.getBoardInfo()
        self.printBoardInfo()

    def reinitialize(self):
        """
        Reinitialize board registers and pots, reinitialize sensor timing (if
          previously set)
        """
        logging.info(self.loginfo + "reinitializing")
        self.initialize()

        for side in self.senstiming:
            self.setTiming(side, self.senstiming[side][0], self.senstiming[side][1])

        if self.sensmanual:  # should be mutually exclusive with anything in senstiming
            self.setManualShutters(self.sensmanual)

    def reboot(self):
        """
        Perform soft reboot on board and reinitialize
        """
        self.board.softReboot()
        self.reinitialize()

    def getBoardInfo(self):
        """
        Get board info from FPGA_NUM register. Returns error flag if register contents
          are invalid and tuple (board version number, rad tolerance flag, sensor name)

        Returns:
            tuple (errorFlag, (board version, rad tolerance flag, sensor name))
        """
        invalidFPGANum = False
        interfaces = []

        if int(self.FPGANum[0], 16) & 8:
            if self.FPGANum[1] == "1":
                boardtype = "LLNLv1"
            elif self.FPGANum[1] == "4":
                boardtype = "LLNLv4"
            else:
                boardtype = "LLNLv?"
                invalidFPGANum = True
        else:
            boardtype = "SNLrevC"
            logging.warning(
                self.logwarn + "FPGA self-identifies as SNLrevC, which is not "
                "supported by this software "
            )
            invalidFPGANum = True
        self.FPGAboardtype = boardtype

        if int(self.FPGANum[6], 16) & 1:
            rad = True
        else:
            rad = False
        self.FPGArad = rad

        if self.FPGANum[7] == "1":
            sensor = "Icarus"
        elif self.FPGANum[7] == "2":
            sensor = "Daedalus"
        elif self.FPGANum[7] == "3":
            sensor = "Horus"
        else:
            sensor = "Undefined"
            invalidFPGANum = True
        self.FPGAsensor = sensor

        if int(self.FPGANum[5], 16) & 1:
            interfaces.append("RS422")
        if int(self.FPGANum[5], 16) & 2:
            interfaces.append("GigE")
        self.FPGAinterfaces = interfaces

        if invalidFPGANum:
            if self.FPGANum == "80000001":
                invalidFPGANum = False
            else:
                logging.warning(self.logwarn + "FPGA self-identification is invalid")
        self.FPGAinvalid = invalidFPGANum

        return invalidFPGANum, (boardtype, rad, sensor)

    def getRegister(self, regname):
        """
        Retrieves contents of named register as hexadecimal string without '0x'

        Args:
            regname: name of register as given in ICD

        Returns:
            tuple: (error string, register contents as hexadecimal string without '0x')
        """
        regname = regname.upper()
        if regname not in self.board.registers:
            err = (
                self.logerr + "invalid register name: " + regname + " ; returning zeros"
            )
            logging.error(err)
            return err, "00000000"
        sendpkt = Packet(cmd="1", addr=self.board.registers[regname])
        err, rval = self.comms.sendCMD(sendpkt)
        if err:
            logging.error(self.logerr + "getRegister " + regname + " " + err)
        return err, rval[8:16]

    def setRegister(self, regname, regval):
        """
        Sets named register to given value as hexadecimal string without '0x'

        Args:
            regname: name of register as given in ICD
            regval: value to assign to register, as hexadecimal string without '0x'

        Returns:
            tuple: (error string, response string)
        """
        regname = regname.upper()
        if regname not in self.board.registers:
            err = self.logerr + "Invalid register name: " + regname
            logging.error(err)
            return err, "00000000"
        pkt = Packet(addr=self.board.registers[regname], data=regval)
        err, rval = self.comms.sendCMD(pkt)
        if err:
            logging.error(self.logerr + "setRegister " + regname + ": " + err)
        return err, rval

    def resolveSubreg(self, srname):
        """
        Resolves subregister name or alias, returns object associated with subregister
          and flag indicating writability

        Args:
            srname: name or alias of subregister

        Returns:
            tuple(subregister name string, associated object, writable flag)
        """
        writable = False
        srname = srname.upper()
        if srname in self.board.subreg_aliases:
            srname = self.board.subreg_aliases[srname].upper()
        if srname in self.board.subreglist:
            srobj = getattr(self.board, srname)
            writable = getattr(self.board, srname).writable
        else:
            srobj = None
        return srname, srobj, writable

    def getSubregister(self, subregname):
        """
        Returns substring of register identified in board attribute 'subregname'

        Args:
            subregname: listed in board.subreg_aliases or defined in board.subregisters

        Returns:
            tuple: (error string, contents of subregister as binary string without '0b')
        """
        subregname, subregobj, _ = self.resolveSubreg(subregname)
        if not subregobj:
            err = (
                self.logerr
                + "getSubregister: invalid lookup: "
                + subregname
                + ' , returning "0" string '
            )
            logging.error(err)
            return err, "".zfill(8)
        err, resp = self.getRegister(subregobj.register)
        if err:
            logging.error(
                self.logerr
                + "getSubregister: unable to retrieve register setting: "
                + subregname
                + ' , returning "0" string'
            )
            return err, "".zfill(8)
        hex_str = "0x" + resp  # this should be a hexadecimalstring
        b_reg_value = "{0:0=32b}".format(int(hex_str, 16))  # convert to binary string
        # list indexing is reversed from bit string; the last bit of the string is at
        #   index 0 in the list (thus bit 0 is at index 0)
        startindex = 31 - subregobj.start_bit
        return "", b_reg_value[startindex : startindex + subregobj.width]

    def setSubregister(self, subregname, valstring):
        """
        Sets substring of register identified in board attribute 'subregname' to
          valstring if subregister is writable

        Args:
            subregname: listed in board.subreg_aliases or defined in board.subregisters
            valstring: binary string without '0b'

        Returns:
            tuple: (error, packet response string) from setRegister
        """
        subregname, subregobj, writable = self.resolveSubreg(subregname)
        if not subregobj:
            err = self.logerr + "setSubregister: invalid lookup: " + subregname
            logging.error(err)
            return err, "0"
        if not writable:
            err = (
                self.logerr
                + "setSubregister: not a writable subregister: "
                + subregname
            )
            logging.error(err)
            return err, "0"
        if len(str(valstring)) > subregobj.width:
            err = self.logerr + "setSubregister: replacement string is too long"
            logging.error(err)
            return err, "0"
        # read current value of register data
        err, resp = self.getRegister(subregobj.register)
        if err:
            logging.error(
                self.logerr + "setSubregister: unable to retrieve register setting; "
                "setting of " + subregname + " likely failed)"
            )
            return err, "0"
        hex_str = "0x" + resp
        b_reg_value = "{0:0=32b}".format(int(hex_str, 16))  # convert to binary
        # list indexing is reversed from bit string; the last bit of the string is at
        #   index 0 in the list (thus bit 0 is at index 0)
        startindex = 31 - subregobj.start_bit
        valstringpadded = str(valstring).zfill(subregobj.width)
        fullreg = list(b_reg_value)
        fullreg[startindex : startindex + subregobj.width] = valstringpadded
        # convert binary string back to hexadecimal string for writing
        new_reg_value = "".join(fullreg)
        h_reg_value = "{num:{fill}{width}x}".format(
            num=int(new_reg_value, 2), fill="0", width=8
        )
        return self.setRegister(subregobj.register, h_reg_value)

    def submitMessages(self, messages, errorstring="Error"):
        """
        Serially set multiple register / subregister values

        Args:
            messages: list of tuples (register name, hexadecimal string without '0x')
              and/or (subregister name, binary string without '0b')
            errorstring: error message to print in case of failure

        Returns:
            tuple (accumulated error string, response string of final message)
        """
        errs = ""
        err = ""
        rval = ""
        for m in messages:
            if m[0].upper() in self.board.registers:
                err, rval = self.setRegister(m[0].upper(), m[1])
            elif m[0].upper() in self.board.subreglist:
                err, rval = self.setSubregister(m[0].upper(), m[1])
            else:
                err = (
                    self.logerr
                    + "submitMessages: Invalid register/subregister: "
                    + errorstring
                    + m[0]
                )
                logging.error(err)
            errs = errs + err
        return err, rval

    def getPot(self, potname, errflag=False):
        """
        Retrieves value of pot or ADC monitor subregister, scaled to [0,1).

        Args:
            potname: name of pot or monitor, e.g., VRST or MON_CH2 found in
              board.subreg_aliases or defined in board.subregisters
            errflag: if True, return tuple with error string

        Returns:
            if errflag:
                tuple: (error string, float value of subregister, scaled to [0,1) )
            else:
                float value of subregister, scaled to [0,1)
        """
        potname, potobj, _ = self.resolveSubreg(potname)
        if not potobj:
            err = (
                self.logerr + "getPot: invalid lookup: " + potname + ' , returning "0" '
            )
            logging.error(err)
            if errflag:
                return err, "0"
            return "0"
        err, b_pot_value = self.getSubregister(potname)
        if err:
            logging.warning(
                self.logerr + "getPot: unable to read subregister " + potname
            )
        # convert binary string back to decimal
        f_reg_value = 1.0 * int(b_pot_value, 2)
        value = (f_reg_value - potobj.min) / (potobj.max - potobj.min)
        if errflag:
            return err, value
        return value

    def setPot(self, potname, value=1.0, errflag=False):
        """
        Sets value of pot to value, normalized so that  '1.0' corresponds with the
          fixed point maximum value of pot.

        Args:
            potname: common name of pot, e.g., VRST found in board.subreg_aliases or
              defined in board.subregisters
            value: float between 0 and 1
            errflag: if True, return tuple with error string

        Returns:
            if errflag:
                tuple: (error string, response packet as string)
            else:
                response packet as string
        """
        if value < 0:
            value = 0.0
        if value > 1:
            value = 1.0

        potname, potobj, writable = self.resolveSubreg(potname)
        if not potobj:
            err = (
                self.logerr + "setPot: invalid lookup: " + potname + ' , returning "0" '
            )
            logging.error(err)
            if errflag:
                return err, "0"
            return "0"
        if not writable:
            err = self.logerr + "setPot: not a writable subregister: " + potname
            logging.error(err)
            if errflag:
                return err, "0"
            return 0
        setpoint = int(round(value * potobj.max_value))
        setpointpadded = "{num:{fill}{width}b}".format(
            num=setpoint, fill="0", width=potobj.width
        )
        err, rval = self.setSubregister(potname, setpointpadded)
        if err:
            logging.error(
                self.logerr
                + "setPot: unable to confirm setting of subregister: "
                + potname
            )
        ident = potname[3:]
        if ident[0].isdigit():  # numbered pot scheme
            potnumlatch = int(ident) * 2 + 1
            potnumlatchstring = "{num:{fill}{width}x}".format(
                num=potnumlatch, fill="0", width=8
            )
            err1, resp = self.setRegister("POT_CTL", potnumlatchstring)
        else:  # alphabetical DAC scheme
            ident = ident.upper()  # expects single character, e.g. 'A' from 'DACA'
            identnum = ord(ident) - ord("A")  # DACA -> 0
            potnumlatch = int(identnum) * 2 + 1
            potnumlatchstring = "{num:{fill}{width}x}".format(
                num=potnumlatch, fill="0", width=8
            )
            err1, resp = self.setRegister("DAC_CTL", potnumlatchstring)
        if err1:
            logging.error(self.logerr + "setPot: unable to latch register")
        if errflag:
            return err + err1, rval
        return rval

    def getPotV(self, potname, errflag=False):
        """
        Reads voltage _setting_ (not actual voltage) of specified pot

        Args:
            potname: name of pot or monitor, e.g., VRST or MON_CH2 found in
              board.subreg_aliases or defined in board.subregisters
            errflag: if True, return tuple with error string

        Returns:
            if errflag:
                tuple: (error string, float value of pot voltage)
            else:
                float value of pot voltage
        """
        potname, potobj, _ = self.resolveSubreg(potname)
        if not potobj:
            err = (
                self.logerr
                + "getPotV: invalid lookup: "
                + potname
                + ' , returning "0" '
            )
            logging.error(err)
            if errflag:
                return err, "0"
            return "0"
        err, val = self.getPot(potname, errflag=True)
        if err:
            logging.error(self.logerr + "getPotV: unable to read pot " + potname)
        minV = potobj.minV
        maxV = potobj.maxV
        if errflag:
            return err, val * (maxV - minV)
        return val * (maxV - minV)

    def setPotV(
        self,
        potname,
        voltage,
        tune=False,
        accuracy=0.01,
        iterations=20,
        approach=0.75,
        errflag=False,
    ):
        """
        Sets pot to specified voltage. If tune=True, uses monitor to adjust pot to
          correct voltage. Tuning will attempt to tune to closest LSB on pot; if
          'accuracy' > LSB resolution, will only complain if tuning is unable to get
          the voltage within 'accuracy'

        Args:
            potname: common name of pot, e.g., VRST found in board.subreg_aliases or
              defined in board.subregisters
            voltage: voltage bound by pot max and min (set in board object)
            tune: if True, iterate with monitor to correct voltage
            accuracy: acceptable error in volts (if None, attempts to find closest
              possible pot setting and warns if last iteration does not reduce error
              below the resolution of the pot)
            iterations: number of iteration attempts
            approach: approximation parameter (>1 may cause overshoot)
            errflag: if True, return tuple with error string

        Returns:
            if errflag:
                tuple: (error string, response string)
            else:
                response string
        """
        potname, potobj, writable = self.resolveSubreg(potname)
        if not potobj:
            err = (
                self.logerr
                + "setPotV: invalid lookup: "
                + potname
                + ' , returning "0" '
            )
            logging.error(err)
            if errflag:
                return err, "0"
            return "0"
        if not writable:
            err = self.logerr + "setPotV: not a writable subregister: " + potname
            logging.error(err)
            if errflag:
                return err, "0"
            return "0"
        if voltage < potobj.minV:
            voltage = potobj.minV
        if voltage > potobj.maxV:
            voltage = potobj.maxV
        setting = (voltage - potobj.minV) / (potobj.maxV - potobj.minV)
        err, rval = self.setPot(potname, setting, errflag=True)
        time.sleep(0.1)
        if tune:
            if potname not in self.board.monitor_controls.values():
                err = (
                    self.logerr
                    + "setPotV: pot '"
                    + potname
                    + "' does not have a corresponding monitor"
                )
                logging.error(err)
                if errflag:
                    return err, rval
                return rval
            self.setPot(potname, 0.65)
            time.sleep(0.2)
            err1, mon65 = self.getMonV(potname, errflag=True)
            self.setPot(potname, 0.35)
            time.sleep(0.2)
            err2, mon35 = self.getMonV(potname, errflag=True)
            # theoretical voltage range assuming linearity
            potrange = (mon65 - mon35) / 0.3
            stepsize = potrange / (potobj.max_value + 1)
            err += err1 + err2
            if err or potrange < 1:
                err += " ERROR: [CA] setPotV: unable to tune pot " + potname
                if potrange < 1:  # potrange should be on the order of 3.3 or 5 volts
                    err += "; monitor shows insufficient change with pot variation"
                logging.error(err)
                if errflag:
                    return err, rval
                return rval
            potzero = 0.35 - (mon35 / potrange)
            potone = 1.65 - (mon65 / potrange)
            if potzero < 0:
                potzero = 0
            if potone > 1:
                potone = 1

            if accuracy > stepsize:
                mindiff = accuracy
            else:
                mindiff = stepsize
            setting = potzero + (voltage / potone)
            self.setPot(potname, setting)
            lastdiff = 0
            smalladjust = 0
            err3 = ""
            for _ in range(iterations):
                err3i, measured = self.getMonV(potname, errflag=True)
                if err3i:
                    err3 = err3 + err3i + " "
                diff = voltage - measured
                if abs(diff - lastdiff) < stepsize / 2:
                    if (
                        smalladjust > 12
                    ):  # magic number for now; if it doesn't converge after several
                        #   tries, it never will, usually because the setting is pinned
                        #   to 0 or 1 and adjust can't change it
                        logging.warning(
                            self.logwarn
                            + "setPotV: Tuning converged too slowly: pot "
                            + potname
                            + " set to "
                            + str(voltage)
                            + "V, monitor returns "
                            + str(measured)
                            + "V"
                        )
                        if errflag:
                            return "", rval
                        return rval
                    smalladjust += 1
                if not int(2 * diff / stepsize):
                    if errflag:
                        return "", rval
                    return rval
                adjust = approach * (diff / potrange)
                setting += adjust
                if setting > 1:
                    setting = 1
                elif setting < 0:
                    setting = 0
                err1, rval = self.setPot(potname, setting, True)
                lastdiff = diff
                time.sleep(0.2)
            err4, measured = self.getMonV(potname, errflag=True)
            diff = voltage - measured
            # code will try to get to within one stepsize, but will only complain if it
            #   doesn't get within mindiff
            if int(diff / mindiff):
                logging.warning(
                    self.logwarn
                    + "setPotV: pot "
                    + potname
                    + " set to "
                    + str(voltage)
                    + "V, monitor returns "
                    + str(measured)
                    + "V"
                )
            err += err1 + err2 + err3 + err4
        if err:
            logging.error(self.logerr + "setPotV: errors occurred: " + err)
        if errflag:
            return err, rval
        return rval

    def getMonV(self, monname, errflag=False):
        """
        Reads voltage from monitor named or that associated with the pot named 'monname'

        Args:
            monname: name of pot or monitor, e.g., VRST or MON_CH2 found in
              board.subreg_aliases or defined in board.subregisters
            errflag: if True, return tuple with error string

        Returns:
            if errflag:
                tuple: (error string, float value of voltage measured by monitor)
            else:
                float value of voltage measured by monitor
        """
        monname = monname.upper()
        if monname in self.board.subreg_aliases:
            monname = self.board.subreg_aliases[monname].upper()
        # else:
        for key, value in self.board.monitor_controls.items():
            if value == monname:
                monname = key
        if monname not in self.board.monitor_controls:
            if monname in self.board.subreglist:
                pass  # no change necessary
            else:
                err = (
                    self.logerr + "getMonV: invalid lookup " + monname + ", returning 0"
                )
                logging.error(err)
                if errflag:
                    return err, 0
                return 0
        err, monval = self.getPot(monname, errflag=True)
        if err:
            logging.error(
                self.logerr + "getMonV: unable to read monitor value for " + monname
            )
        if self.board.ADC5_bipolar:
            if monval >= 0.5:
                monval -= 1  # handle negative measurements (two's complement)
            if errflag:
                return err, 2 * self.board.ADC5_mult * monval * self.board.VREF
            return 2 * self.board.ADC5_mult * monval * self.board.VREF
        else:
            if errflag:
                return err, self.board.ADC5_mult * monval * self.board.VREF
            return self.board.ADC5_mult * monval * self.board.VREF

    def readImgs(self, waitOnSRAM=True, mode="Hardware"):
        """
        Combines arm() and readoff() functions

        Returns:
            tuple (list of numpy arrays, length of downloaded payload, payload error
              flag) returned by readoff
        """
        logging.info(self.loginfo + "readImgs")
        self.arm(mode)
        return self.readoff(waitOnSRAM)

    def deInterlace(self, frames, ifactor=1):
        """
        Extracts interlaced frames. If interlacing does not evenly divide the height,
          remainder lines will be dropped
        Args:
            frames: list of full-sized frames
            ifactor: interlacing factor; number of interlaced lines (generates
              ifactor + 1 images per frame)

        Returns: list of deinterlaced frames
        """
        if ifactor == 0:  # don't do anything
            return frames
        warntrimmed = False
        if self.padToFull:
            newheight = self.sensor.maxheight // (ifactor + 1)
            if newheight != (self.sensor.maxheight / (ifactor + 1)):
                warntrimmed = True
        else:
            newheight = self.sensor.height // (ifactor + 1)
            if newheight != (self.sensor.height / (ifactor + 1)):
                warntrimmed = True

        if warntrimmed:
            logging.warning(
                self.logwarn + "deInterlace: interlacing setting requires dropping of "
                "lines to maintain consistent frame sizes "
            )
        delaced = []
        for frame in frames:
            for sub in range(ifactor + 1):
                current = np.zeros((newheight, self.sensor.width), dtype=int)
                for line in range(newheight):
                    current[line] = frame[(ifactor + 1) * line + sub]
                delaced.append(current)
        return delaced

    def saveFrames(
        self, frames, path=None, filename="frames", prefix=None,
    ):
        """
        Save list of numpy arrays to disk. If passed an unprocessed text string, convert
          to numpy before saving. Use 'prefix=""' for no prefix

        Args:
            frames: numpy array or list of numpy arrays OR text string
            path: save path, defaults to './output'
            filename: defaults to 'frames.bin'
            prefix: prepended to filename, defaults to time/date (e.g. '160830-124704_')

        Returns:
            Error string
        """
        logging.info(self.loginfo + "saveFrames")
        err = ""
        if path is None:
            path = os.path.join(os.getcwd(), "output")
        if prefix is None:
            prefix = datetime.now().strftime("%y%m%d-%H%M%S%f")[:-5] + "_"
        if not os.path.exists(path):
            os.makedirs(path)

        if isinstance(frames[0], str):
            filename = filename + ".txt"
            savefile = open(os.path.join(path, prefix + filename), "w+")
            savefile.write(frames)

        else:
            filename = filename + ".bin"
            stacked = np.stack(frames)
            try:
                stacked = stacked.reshape(
                    (
                        self.sensor.nframes,
                        self.sensor.height // (self.sensor.interlacing + 1),
                        self.sensor.width,
                    )
                )
            except Exception as e:
                err = self.logerr + "saveFrames: unable to save frames: " + str(e)
                logging.error(err)

            stacked.tofile(os.path.join(path, prefix + filename))
        return err

    def saveTiffs(
        self, frames, path=None, filename="Frame", prefix=None, index=None,
    ):
        """
        Save numpy array or list of numpy arrays or single array to disk as individual
          tiffs, with frame number appended to filename.

        Args:
            frames: numpy array or list of numpy arrays
            path: save path, defaults to './output'
            filename: defaults to 'Frame' followed by frame number
            prefix: prepended to 'filename', defaults to time/date
              (e.g. '160830-124704_')
            index: number to start frame numbering

        Returns:
            Error string
        """
        logging.info(self.loginfo + "saveTiffs")
        err = ""
        if path is None:
            path = os.path.join(os.getcwd(), "output")
        if prefix is None:
            prefix = datetime.now().strftime("%y%m%d-%H%M%S%f")[:-5] + "_"
        if not os.path.exists(path):
            os.makedirs(path)
        if index is None:
            nframe = self.sensor.firstframe
        else:
            nframe = index

        if type(frames) is not list:
            frames = [frames]
        # if this is a text string from fast readoff, do the numpy conversion now
        if isinstance(frames[0], str):
            frames = self.generateFrames(frames)

        framestemp = np.copy(frames)
        for frame in framestemp:
            try:
                if self.padToFull:
                    frame.shape = (
                        self.sensor.maxheight // (self.sensor.interlacing + 1),
                        self.sensor.maxwidth,
                    )
                else:
                    frame.shape = (
                        self.sensor.height // (self.sensor.interlacing + 1),
                        self.sensor.width,
                    )
                frameimg = Image.fromarray(frame)
                namenum = filename + "_%d" % nframe
                tifpath = os.path.join(path, prefix + namenum + ".tif")
                frameimg.save(tifpath)
                nframe += 1
            except:
                err = self.logerr + "saveTiffs: unable to save images"
                logging.error(err)
                continue
        return err

    def saveNumpys(
        self, frames, path=None, filename="Frame", prefix=None, index=None,
    ):
        """
        Save numpy array or list of numpy arrays to disk as individual numpy data files,
          with frame number appended to filename.

        Args:
            frames: numpy array or list of numpy arrays or single numpy array
            path: save path, defaults to './output'
            filename: defaults to 'Frame' followed by frame number
            prefix: prepended to 'filename', defaults to time/date
              (e.g. '160830-124704_')
            index: number to start frame numbering

        Returns:
            Error string
        """
        logging.info(self.loginfo + "saveNumpys")
        err = ""
        if path is None:
            path = os.path.join(os.getcwd(), "output")
        if prefix is None:
            prefix = datetime.now().strftime("%y%m%d-%H%M%S%f")[:-5] + "_"
        if not os.path.exists(path):
            os.makedirs(path)
        if index is None:
            nframe = self.sensor.firstframe
        else:
            nframe = index
        if type(frames) is not list:
            frames = [frames]

        # if this is a text string from fast readoff, do the numpy conversion now
        if isinstance(frames[0], str):
            frames = self.generateFrames(frames)

        framestemp = np.copy(frames)
        for frame in framestemp:
            try:
                if self.padToFull:
                    frame.shape = (
                        self.sensor.maxheight // (self.sensor.interlacing + 1),
                        self.sensor.maxwidth,
                    )
                else:
                    frame.shape = (
                        self.sensor.height // (self.sensor.interlacing + 1),
                        self.sensor.width,
                    )
                namenum = filename + "_%d" % nframe
                nppath = os.path.join(path, prefix + namenum + ".npy")
                np.save(nppath, frame)
                nframe += 1
            except:
                err = self.logerr + "saveNumpys: unable to save arrays"
                logging.error(err)
                continue
        return err

    def dumpNumpy(
        self, datastream, path=None, filename="Dump", prefix=None,
    ):
        """
        Datastream is converted directly to numpy array and saved to disk. No attempt
          to parse headers or separate into individual frames is made.

        Args:
            datastream: string to be saved
            path: save path, defaults to './output'
            filename: defaults to 'Dump'
            prefix: prepended to 'filename', defaults to time/date
              (e.g. '160830-124704_')

        Returns:
            Error string
        """
        logging.info(self.loginfo + "dumpNumpy")
        err = ""
        if path is None:
            path = os.path.join(os.getcwd(), "output")
        if prefix is None:
            prefix = time.strftime("%y%m%d-%H%M%S_", time.localtime())
        if not os.path.exists(path):
            os.makedirs(path)
        npdata = self.str2nparray(datastream)
        try:
            nppath = os.path.join(path, prefix + filename + ".npy")
            np.save(nppath, npdata)
        except:
            err = self.logerr + "dumpNumpy: unable to save data stream"
            logging.error(err)
        return err

    def plotFrames(self, frames, index=None):
        """
        Plot frame or list of frames as individual graphs.

        Args:
            frames: numpy array or list of numpy arrays
            index: number to start frame numbering

        Returns:
            Error string
        """
        logging.info(self.loginfo + "plotFrames")
        err = ""
        if index is None:
            nframe = self.sensor.firstframe
        else:
            nframe = index

        if type(frames) is not list:
            frames = [frames]

        # if this is a text string from fast readoff, do the numpy conversion now
        if isinstance(frames[0], str):
            frames = self.generateFrames(frames)

        framestemp = np.copy(frames)
        for frame in framestemp:
            try:
                if self.padToFull:
                    frame.shape = (
                        self.sensor.maxheight // (self.sensor.interlacing + 1),
                        self.sensor.maxwidth,
                    )
                else:
                    frame.shape = (
                        self.sensor.height // (self.sensor.interlacing + 1),
                        self.sensor.width,
                    )
            except:
                err = self.logerr + "plotFrames: unable to plot frame"
                logging.error(err)
                continue
            plt.imshow(frame, cmap="gray")
            name = "Frame %d" % nframe
            plt.title(name)
            plt.show()
            nframe += 1
        return err

    def checkCRC(self, rval):
        """
        Calculate CRC for rval[:-4] and compare with expected CRC in rval[-4:]

        Args:
            rval: hexadecimal string

        Returns:
            boolean, True if CRCs match
        """
        data_crc = int(rval[-4:], base=16)
        CRC_calc = crc16pure.crc16xmodem(self.str2bytes(rval[:-4]))
        return CRC_calc == data_crc

    def checkRegSet(self, regname, teststring):
        """
        Quick check to confirm that data read from register matches data write

        Args:
            regname: register to test
            teststring: value to assign to register, as hexadecimal string without '0x'

        Returns:
            boolean, True if read and write values match
        """
        self.setRegister(regname, teststring)
        # tell board to send data; wait to clear before interrogating register contents
        if regname == "SRAM_CTL":
            time.sleep(2)
            if self.commname == "rs422":
                logging.info(
                    self.loginfo + "skipping 'SRAM_CTL' register check for RS422"
                )
                return True
        else:
            time.sleep(0.1)
        temp = self.getRegister(regname)
        resp = temp[1].upper()
        if resp != teststring.upper():
            logging.error(
                self.logerr
                + "checkRegSet failure: "
                + regname
                + " ; set: "
                + teststring
                + " ; read: "
                + resp
            )
            return False
        return True

    def initPowerCheck(self):
        """
        Reset software and board timers for monitoring power status
        """
        self.inittime = time.time()
        logging.info(self.loginfo + "resetting timer for power check function")
        self.resetTimer()

    def powerCheck(self, delta=10):
        """
        Check to see if board power has persisted since powerCheck was last initialized.
          Compares time elapsed since initialization against board's timer. If
          difference is greater than 'delta,' flag as False (power has likely failed)

        Args:
            delta: difference in seconds permitted between software and board timers

        Returns:
            boolean, 'True' means timer difference is less than 'delta' parameter;
                     'False' indicates power failure
        """
        elapsed = time.time() - self.inittime
        difference = abs(elapsed - self.getTimer())
        if difference > delta:
            logging.warning(
                self.logwarn + "powerCheck function has failed; may indicate current "
                "or recent power failure "
            )
        return difference < delta

    def dummyCheck(self, image, margin, dummyVals=None):
        """
        Compare image with 'canonical' dummy sensor image (actual values estimated)

        Args:
            image: numpy array containing frame image
            margin: maxmimum allowed error for sensor
            dummyVals: condensed array of expected dummy sensor image values

        Returns:
            tuple, (number of pixels exceeding difference margin, numpy array containing
              image subtracted from expected dummy image)
        """
        if dummyVals is None:
            dummyVals = self.board.dummySensorVals
        stripe0 = []
        stripe1 = []
        for i in range(16):
            stripe0.append([dummyVals[0][i]] * 32)
            stripe1.append([dummyVals[1][i]] * 32)
        stripet = [val for sublist in stripe0 for val in sublist]
        stripeb = [val for sublist in stripe1 for val in sublist]
        testVals = [stripet] * 512 + [stripeb] * 512
        testimage = np.array(testVals)
        if image.size == testimage.size:
            image.shape = (self.sensor.height, self.sensor.width)
            diff = testimage - image
            diffabs = [abs(i) for sublist in diff for i in sublist]
            bads = sum(1 for i in diffabs if i > margin)
            return bads, diff
        else:
            logging.error(
                self.logerr + "dummyCheck: Image size does not match dummy image; "
                "returning zero, actual testimage "
            )
            return 0, testimage

    def printBoardInfo(self):
        logging.info(
            self.loginfo
            + "Python version: "
            + str(self.python)
            + "."
            + str(self.pyth1)
            + "."
            + str(self.pyth2)
        )
        logging.info(self.loginfo + "nsCamera software version: " + self.version)
        logging.info(self.loginfo + "FPGA firmware version: " + self.FPGAVersion)
        logging.info(self.loginfo + "FPGA implementation: " + self.FPGANum)
        if self.FPGAinvalid:
            logging.info(self.loginfo + "FPGA information unavailable")
        else:
            logging.info(self.loginfo + "Board type: " + self.FPGAboardtype)
            logging.info(self.loginfo + "Rad-Tolerant: " + str(self.FPGArad))
            logging.info(self.loginfo + "Sensor family: " + self.FPGAsensor)
            logging.info(
                self.loginfo + "Available interfaces: " + ", ".join(self.FPGAinterfaces)
            )
        if self.commname == "gige":
            ci = self.comms.CardInfoP.contents
            ip = ".".join(str(e) for e in [b for b in ci.IPAddr])
            logging.info(
                self.loginfo + "GigE connected to " + ip + ":" + str(self.port)
            )
        elif self.commname == "rs422":
            logging.info(self.loginfo + "RS422 connected to " + self.comms._port)

    def dumpRegisters(self):
        """
        List contents of all registers in board.registers. WARNING: some status flags
          will reset when read.
        DEPRECATED: use dumpStatus() instead

        Returns:
            Sorted list: [register name (register address) : register contents as
              hexadecimal string without '0x']
        """
        dump = {}
        for key in self.board.registers.keys():
            err, rval = self.getRegister(key)
            dump[key] = rval
        reglistmax = int(max(self.board.registers.values()), 16)
        dumplist = [0] * (reglistmax + 1)
        for k, v in dump.items():
            regnum = self.board.registers[k]
            dumplist[int(regnum, 16)] = (
                "(" + regnum + ") {0:<24} {1}".format(k, v.upper())
            )
        reglist = [a for a in dumplist if a]
        return reglist

    def dumpSubregisters(self):
        """
        List contents of all subregisters in board.channel_lookups and
          board.monitor_lookups.
        WARNING: some registers will reset when read- only the first subregister from
          such a register will return the correct value, the remainder will return zeros

        DEPRECATED: use dumpStatus() instead

        Returns:
            dictionary  {subregister name : subregister contents as binary string
              without initial '0b'}
        """
        dump = {}
        for sub in self.board.subreglist:
            key = sub.name
            err, resp = self.getSubregister(key)
            if err:
                logging.warning(
                    self.logwarn + "dumpSubregisters: unable to read subregister " + key
                )
            val = hex(int(resp, 2))
            dump[key] = val
        return dump

    def str2bytes(self, astring):
        """
        Python-version-agnostic converter of hexadecimal strings to bytes

        Args:
            astring: hexadecimal string without '0x'

        Returns:
            byte string equivalent to input string
        """
        if self.PY3:
            dbytes = binascii.a2b_hex(astring)
        else:
            dbytes = astring.decode("hex")
        return dbytes

    def bytes2str(self, bytesequence):
        """
        Python-version-agnostic converter of bytes to hexadecimal strings

        Args:
            bytesequence: sequence of bytes as string (Py2) or bytes (Py3)

        Returns:
            hexadecimal string representation of 'bytes' without '0x'
        """
        estring = binascii.b2a_hex(bytesequence)
        if self.PY3:
            estring = str(estring)[2:-1]
        return estring

    def str2nparray(self, valstring):
        """
        Convert string into array of uint16s

        Args:
            valstring: string of hexadecimal characters

        Returns:
            numpy array of uint16
        """
        stringlen = len(valstring)
        arraylen = int(stringlen / 4)
        outarray = np.empty(int(arraylen), dtype="uint16")

        for i in range(0, arraylen):
            outarray[i] = int(valstring[4 * i : 4 * i + 4], 16)
        return outarray

    def flatten(self, x):
        """
        Flatten list of lists into single list
        """
        if isinstance(x, collections.Iterable):
            return [a for i in x for a in self.flatten(i)]
        else:
            return [x]

    def getEnter(self, text):
        """
        Wait for enter key to be pressed.

        Args:
            text: message asking for keypress
        """
        if self.PY3:
            input(text)
        else:
            raw_input(text)

    def mmReadoff(self, waitOnSRAM, variation=None):
        """
        Convenience function for parsing frames for use by MicroManager plugin
        Args:
            waitOnSRAM: readoff wait flag
            variation: format of frames generated from readoff
                default - return first frame only
                "LastFrame" - return last frame only
                "Average" - provide average of frames as single frame
                "Landscape" - stitch frames together horizontally into single wide frame

        Returns:
            ndarray - single image frame
        """
        frames, datalen, data_err = self.readoff(waitOnSRAM)
        if variation == "LastFrame":
            return frames[self.sensor.nframes - 1]
        elif variation == "Average":
            return np.sum(frames, axis=0) // self.sensor.nframes
        elif variation == "Landscape":
            shaped = [np.reshape(frame, (1024, 512)) for frame in frames]
            return np.concatenate(shaped, axis=1)
        else:
            return frames[0]

    def setFrames(self, minframe=None, maxframe=None):
        """
        Sets bounds on frames returned by board, inclusive (e.g., 0,3 returns four
        frames). If called without parameters, resets to full set of frames.

        Args:
            minframe: first frame to read from board
            maxframe: last frame to read from board

        Returns:
            Error string
        """
        if minframe is None:
            minframe = self.sensor.minframe
        if maxframe is None:
            maxframe = self.sensor.maxframe
        if (
            not isinstance(minframe, int)
            or minframe < self.sensor.minframe
            or minframe > maxframe
            or not isinstance(maxframe, int)
            or maxframe > self.sensor.maxframe
        ):
            err = (
                self.logerr + "setFrames: invalid frame limits submitted. Frame "
                "selection remains unchanged. "
            )
            logging.error(err)
            return err

        initframe = hex(minframe)[2:].zfill(8)
        finframe = hex(maxframe)[2:].zfill(8)
        err1, _ = self.setRegister("FPA_FRAME_INITIAL", initframe)
        err2, _ = self.setRegister("FPA_FRAME_FINAL", finframe)
        self.sensor.firstframe = minframe
        self.sensor.lastframe = maxframe
        self.sensor.nframes = maxframe - minframe + 1
        self.comms.payloadsize = (
            self.sensor.width
            * self.sensor.height
            * self.sensor.nframes
            * self.sensor.bytesperpixel
        )
        plural = ""
        if self.sensor.nframes > 1:
            plural = "s"
        logging.info(
            self.loginfo
            + "Readoff set to "
            + str(self.sensor.nframes)
            + " frame"
            + plural
            + " ("
            + str(minframe)
            + ", "
            + str(maxframe)
            + ")"
        )
        err = err1 + err2
        if err:
            logging.error(
                self.logerr + "setFrames may not have functioned properly: " + err
            )
        return err

    def setRows(self, minrow=0, maxrow=None, fullsize=False):
        """
        Sets bounds on rows returned by board, inclusive (e.g., 0,1023 returns all 1024
          rows). If called without parameters, resets to full image size.

        Args:
            minrow: first row to return from board
            maxrow: last row to return from board
            fullsize: if True, generate full size frames, padding collected rows with
            zeroes as necessary
        """
        err = ""
        if maxrow is None:
            maxrow = self.sensor.maxheight - 1
        if (
            not isinstance(minrow, int)
            or minrow < 0
            or minrow > maxrow
            or not isinstance(maxrow, int)
            or maxrow >= self.sensor.maxheight
        ):
            err = (
                self.logerr + "setRows: invalid row arguments submitted. Frame size "
                "remains unchanged. "
            )
            logging.error(err)
            return err

        initrow = hex(minrow)[2:].zfill(8)
        finrow = hex(maxrow)[2:].zfill(8)
        err1, _ = self.setRegister("FPA_ROW_INITIAL", initrow)
        err2, _ = self.setRegister("FPA_ROW_FINAL", finrow)
        self.sensor.firstrow = minrow
        self.sensor.lastrow = maxrow
        self.sensor.height = maxrow - minrow + 1
        self.comms.payloadsize = (
            self.sensor.width
            * self.sensor.height
            * self.sensor.nframes
            * self.sensor.bytesperpixel
        )

        if self.commname == "rs422":
            self.comms._datatimeout = (
                (1.0 * self.sensor.height / self.sensor.maxheight)
                * 5e7
                * self.sensor.nframes
                / self.comms._baud
            )

        if fullsize:
            self.padToFull = True
        else:
            self.padToFull = False
        logging.info(
            self.loginfo
            + "Readoff set to "
            + str(self.sensor.height)
            + " rows ("
            + str(minrow)
            + ", "
            + str(maxrow)
            + ")"
        )
        err = err1 + err2
        if err:
            logging.error(
                self.logerr + "setRows may not have functioned properly: " + err
            )
        return err

    def generateFrames(self, data):
        """
        Processes data stream from board into frames and applies sensor-specific
          parsing. Generates padded data for fullsize option of setRows.

        Args:
            data: stream from board.

        Returns: list of parsed frames
        """
        allframes = self.str2nparray(data)
        # self.oldtime = self.currtime
        # self.currtime = time.time()
        # self.unstringed.append(self.currtime - self.oldtime)
        frames = [0] * self.sensor.nframes
        framesize = self.sensor.width * self.sensor.height
        if self.padToFull:
            toprows = self.sensor.firstrow
            botrows = (self.sensor.maxheight - 1) - self.sensor.lastrow
            for n in range(self.sensor.nframes):
                padtop = np.zeros(toprows * self.sensor.maxwidth, dtype=int)
                padbot = np.zeros(botrows * self.sensor.maxwidth, dtype=int)
                thisframe = np.concatenate(
                    (padtop, allframes[n * framesize : (n + 1) * framesize], padbot)
                )
                frames[n] = thisframe
        else:
            for n in range(self.sensor.nframes):
                frames[n] = allframes[n * framesize : (n + 1) * framesize]
        self.clearStatus()
        parsed = self.parseReadoff(frames)
        # self.oldtime = self.currtime
        # self.currtime = time.time()
        # self.parsedtime.append(self.currtime - self.oldtime)
        return parsed

    def abortReadoff(self, flag=True):
        """
        Simple abort command for readoff in waiting mode--does not interrupt download in
           progress. Requires external threading to function. WARNING: if not
           intercepted by active readoff command, will terminate next readoff command
           immediately at inception.
        Args:
            flag: Sets passive abort flag read by readoff command
        Returns:
            boolean: updated setting of flag
        """
        self.abort = flag
        return flag

    def batchAcquire(
        self,
        sets=1,
        trig="Hardware",
        path=None,
        filename="Frame",
        prefix=None,
        showProgress=0,
    ):
        """
        Acquire a series of images as fast as possible, then process and save to disk.

        Args:
            sets: Number of acquisitions to perform
            path: save path, defaults to './output'
            filename: defaults to 'frames.bin'
            prefix: prepended to filename, defaults to time/date (e.g. '160830-124704_')
              DO NOT USE unless providing a varying value (a fixed prefix will cause
              overwriting)
            showProgress: if non-zero, show notice every 'showProgress' acquisitions and
              print total acquisition time

        Returns:
            Time taken for acquisition (seconds)
        """
        datalist = ["0"] * sets
        timelist = [datetime.now()] * sets
        logging.info(
            self.loginfo
            + "batchAcquire: temporarily disabling warning and information "
            "logging "
        )
        logging.getLogger().setLevel(self.verbmap.get(2))
        beforeread = time.time()
        for i in range(sets):
            if showProgress and not (i + 1) % showProgress:
                print(self.loginfo + "batchAcquire: Acquiring set " + str(i + 1))
            self.arm(trig)
            data, datalen, data_err = self.readoff(fast=True)
            datalist[i] = data
            timelist[i] = datetime.now()
        afterread = time.time()
        if showProgress:
            print(
                self.loginfo
                + "batchAcquire: "
                + str(afterread - beforeread)
                + " seconds for "
                + str(sets)
                + " sets"
            )
        setnum = 0
        if path is None:
            path = os.path.join(os.getcwd(), "output")
        for (imset, imtime) in zip(datalist, timelist):
            setnum = setnum + 1
            if showProgress and not setnum % showProgress:
                print(self.loginfo + "batchAcquire: Saving set " + str(setnum))
            parsed = self.generateFrames(imset)
            if prefix is None:
                setprefix = imtime.strftime("%y%m%d-%H%M%S%f")[:-2] + "_"
            else:
                setprefix = prefix
            self.saveTiffs(parsed, path, filename, prefix=setprefix)
        logging.getLogger().setLevel(self.verblevel)
        logging.info(self.loginfo + "batchAcquire: re-enabling logging")
        return afterread - beforeread

    def loadTextFrames(self, filename='frames.txt', path=None):
        """
        Load a image set previously saved as text and convert to frames. NOTE: to work
          properly, the cameraAssembler object must have the same geometry and sensor
          tyoe that was used to create the text file

        Args:
            filename: name of textfile to load
            path: path to file, if not the current working directory

       Returns: list of parsed frames
        """
        if path is None:
            path = os.path.join(os.getcwd())
        textfile = os.path.join(path, filename)

        try:
            f = open(textfile, "r")
            s = f.read()
            frames = self.generateFrames(s)
            return frames
        except OSError as err:
            print("OS error: {0}".format(err))
        except ValueError:
            print("Could not convert data to an integer.")
        except:
            print("Unexpected error:", sys.exc_info()[0])


"""
Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.
"""
