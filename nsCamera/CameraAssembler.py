# -*- coding: utf-8 -*-
"""
CameraAssembler assembles the separate camera parts into a camera object. This object
controls a combination of three components:

1. board : FPGA board -- LLNL_V1, LLNL_V4
2. comms: communication interface -- GigE, RS422
3. sensor : sensor type -- icarus, icarus2, daedalus

Author: Jeremy Martin Hill (jerhill@llnl.gov)
Author: Matthew Dayton (dayton5@llnl.gov)

Copyright (c) 2025, Lawrence Livermore National Security, LLC.  All rights reserved.
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under 
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy (DOE)
and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new contributions must
be made under this license.

Version: 2.1.2 (February 2025)
"""

from __future__ import absolute_import

import importlib
import inspect
import logging
import os
import platform
import socket
import sys
import time
import h5py
from datetime import datetime

import numpy as np

from nsCamera.utils.misc import (
    bytes2str,
    checkCRC,
    flattenlist,
    generateFrames,
    getEnter,
    partition,
    plotFrames,
    saveTiffs,
    str2bytes,
    str2nparray,
)

from nsCamera.utils.Packet import Packet

# TODO: move to Sphinx documentation
# TODO: add pytest and tox scripts


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
        saveFrames(frames) - save image object as one file
        saveNumpys(frames) - save individual frames as numpy data files
        dumpNumpy(datastream) - save datastream string to numpy file
        powerCheck(delta) - check that board power has not failed
        printBoardInfo() - print board information derived from FPGA_NUM register
        dumpRegisters() - return contents of all board registers
        dumpSubregisters() - return contents of all named board subregisters
        setFrames(min, max) - select subset of frames for readoff
        setRows(min, max, padToFull) - select subset of rows for readoff
        abortReadoff() - cancel readoff in wait-for-SRAM loop
        batchAquire() - fast acquire a finite series of images
        loadTextFrames() - load data sets previously saved as text and convert to frames

    Includes aliases to board- and sensor- specific methods:
        Board methods
            disarm() - take camera out of waiting-for-trigger state
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
            getTemp() - read on-board temperature sensor
            getPressure() - read on-board pressure sensor
            dumpStatus() - generate dictionary of status, register, and subregister
              contents
        Sensor methods
            checkSensorVoltStat() - checks that jumper settings match sensor selection
            setTiming(side, sequencetuple, delay) - configure high-speed timing
            setArbTiming(side, sequencelist) - configure arbitrary high-speed timing
              sequence
            getTiming(side) - returns high speed timing settings from registers
            setManualTiming() - configures manual shutter timing
            getManualTiming() - returns manual shutter settings from registers
            selectOscillator(osc) - select timing oscillator
            setInterlacing(ifactor) - sets interlacing factor
            setHighFullWell(flag) - controls High Full Well mode
            setZeroDeadTime(flag, side) - controls Zero Dead Time mode
            setTriggerDelay(delayblocks) - sets trigger delay
        Comms methods
            sendCMD(pkt)- sends packet object via serial port
            arm() - configures software buffers & arms camera
            readFrames() - waits for data ready flag, then downloads image data
            readoff() - waits for data ready flag, then downloads image data
            closeDevice() - disconnect interface and release resources
        Miscellaneous functions (bare functions that can be called as methods)
            saveTiffs(frames) - save individual frames as tiffs
            plotFrames(frames) - plot individual frames as tiffs

    Informational class variables:
        version - nsCamera software version
        FPGAVersion - firmware version (date)
        FPGANum - firmware implementation identifier
        FPGAboardtype - FPGA self-identified board type (should match 'boardname')
        FPGArad = Flag indicating radiation-tolerant FPGA build
        FPGAsensor = FPGA self-identified sensor family (should correspond to
          'sensorname')
        FPGAinterfaces = FPGA self-identified interfaces (list should include
          'commname')
        FPGAinvalid = flag indicating invalid FPGA information in register
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
        timeout=30,
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
                  will be {1} [9, 8, 9, 14, 9, 8, 9])
                4: print INFO logging messages (operational messages from ordinary
                  camera operation)
                5. print DEBUG logging messages (detailed messages describing specific
                  operations and messages)
            port: optional integer
                When using RS422, this preselects the comport for RS422 and bypasses
                  port search
                When using GigE, this preselects the OrangeTree control port for GigE
                  (ignored if an ip parameter is not also provided)
            ip: optional string (e.g., '192.168.1.100')
                GigE: bypasses network search and selects particular OrangeTree board -
                  required for some operating systems
            logfile: optional string, name of file to divert console output
            timeout: timeout in seconds for connecting using Gigabit Ethernet
        """
        self.version = "2.1.2"
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
        self.timeout = timeout
        # TODO: parse boardname, etc. in separate method
        if self.boardname in ["llnlv1", "v1", "1", 1]:
            self.boardname = "llnl_v1"
        if self.boardname in ["llnlv4", "v4", "4", 4]:
            self.boardname = "llnl_v4"
        self.commname = commname.lower()
        if self.commname[0] == "g" or self.commname[0] == "e":
            self.commname = "gige"
        if self.commname[0] == "r":
            self.commname = "rs422"
        self.sensorname = sensorname.lower()
        if self.sensorname in ["i1", "ic1", "icarus1"]:
            self.sensorname = "icarus"
        if self.sensorname in ["i2", "ic2"]:
            self.sensorname = "icarus2"
        if self.sensorname == "d":
            self.sensorname = "daedalus"
        self.verbose = int(verbose)
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

        self.logcritbase = "CRITICAL {logtag}: ".format(logtag=logtag)
        self.logerrbase = "ERROR {logtag}: ".format(logtag=logtag)
        self.logwarnbase = "WARNING {logtag}: ".format(logtag=logtag)
        self.loginfobase = "INFO {logtag}: ".format(logtag=logtag)
        self.logdebugbase = "DEBUG {logtag}: ".format(logtag=logtag)

        self.logcrit = "{lb}[CA]".format(lb=self.logcritbase)
        self.logerr = "{lb}[CA]".format(lb=self.logerrbase)
        self.logwarn = "{lb}[CA]".format(lb=self.logwarnbase)
        self.loginfo = "{lb}[CA]".format(lb=self.loginfobase)
        self.logdebug = "{lb}[CA]".format(lb=self.logdebugbase)

        self.verblevel = self.verbmap.get(verbose, 5)  # defaults to 5 for invalid entry

        if logfile:
            logging.basicConfig(format="%(message)s", filename=logfile)
        else:
            logging.basicConfig(format="%(message)s")
        logging.getLogger().setLevel(self.verblevel)
        logging.getLogger("matplotlib.font_manager").disabled = True
        logging.debug(
            "{logdebug}CameraAssembler: boardname = {boardname}; commname = {commname};"
            " sensorname = {sensorname}; verbose = {verbose}; port = {port}; ip = {ip};"
            " logfile = {logfile}; logtag = {logtag}".format(
                logdebug=self.logdebug,
                boardname=boardname,
                commname=commname,
                sensorname=sensorname,
                verbose=verbose,
                port=port,
                ip=ip,
                logfile=logfile,
                logtag=logtag,
            )
        )

        if ip:
            try:
                iphex = socket.inet_aton(ip)
            except socket.error:
                logging.critical(
                    "{logcrit}CameraAssembler: invalid IP provided".format(
                        logcrit=self.logcrit
                    )
                )
                sys.exit(1)
            ipnum = [0, 0, 0, 0]
            for i in range(4):
                if self.PY3:
                    ipnum[i] = iphex[i]
                else:
                    ipnum[i] = int(iphex[i].encode("hex"), 16)
            self.iplist = ipnum

        self.payloaderror = False

        # code pulled out of __init__ to facilitate reinitialization of the board
        #   without needing to instantiate a new CameraAssembler object
        self.initialize()

    ##### Aliases to other objects' methods
    #  TODO: properly delegate these methods

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

    def setPPER(self, pollperiod=None):
        return self.board.setPPER(pollperiod)

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

    def setTiming(self, side="AB", sequence=None, delay=0):
        return self.sensor.setTiming(side, sequence, delay)

    def setArbTiming(self, side="AB", sequence=None):
        return self.sensor.setArbTiming(side, sequence)

    def getTiming(self, side=None, actual=None):
        return self.sensor.getTiming(side, actual)

    def setManualShutters(self, timing=None):
        return self.sensor.setManualTiming(timing)

    def setManualTiming(self, timing=None):
        return self.sensor.setManualTiming(timing)

    def getManualTiming(self):
        return self.sensor.getManualTiming()

    def getSensTemp(self, scale=None, offset=None, slope=None, dec=1):
        return self.sensor.getSensTemp(scale, offset, slope, dec)

    def sensorSpecific(self):
        return self.sensor.sensorSpecific()

    def selectOscillator(self, osc=None):
        return self.sensor.selectOscillator(osc)

    def setInterlacing(self, ifactor=None, side=None):
        return self.sensor.setInterlacing(ifactor, side)

    def setHighFullWell(self, flag=True):
        return self.sensor.setHighFullWell(flag)

    def setZeroDeadTime(self, flag=True, side=None):
        return self.sensor.setZeroDeadTime(flag, side)

    def setTriggerDelay(self, delay=0):
        return self.sensor.setTriggerDelay(delay)

    def setPhiDelay(self, side=None, delay=0):
        return self.sensor.setPhiDelay(side, delay)

    def setExtClk(self, dilation=None, frequency=None):
        return self.sensor.setExtClk(dilation, frequency)

    def parseReadoff(self, frames, columns=1):
        return self.sensor.parseReadoff(frames, columns)

    def sendCMD(self, pkt):
        return self.comms.sendCMD(pkt)

    def arm(self, mode=None):
        return self.comms.arm(mode)

    def readFrames(self, waitOnSRAM=None, timeout=0, fast=False, columns=1):
        frames, _, _ = self.comms.readoff(waitOnSRAM, timeout, fast, columns)
        return frames

    def readoff(self, waitOnSRAM=None, timeout=0, fast=None, columns=1):
        return self.comms.readoff(waitOnSRAM, timeout, fast, columns)

    def writeSerial(self, cmd, timeout=None):
        return self.comms.writeSerial(cmd, timeout)

    def readSerial(self, size, timeout=None):
        return self.comms.readSerial(size, timeout)

    def closeDevice(self):
        return self.comms.closeDevice()

    def saveTiffs(self, frames, path=None, filename="Frame", prefix=None, index=None):
        return saveTiffs(self, frames, path, filename, prefix, index)

    def plotFrames(self, frames, index=None):
        return plotFrames(self, frames, index)

    def getEnter(self, text):
        return getEnter(text)

    def checkCRC(self, rval):
        return checkCRC(rval)

    def str2bytes(self, astring):
        return str2bytes(astring)

    def bytes2str(self, bytesequence):
        return bytes2str(bytesequence)

    def str2nparray(self, valstring):
        return str2nparray(valstring)

    def flattenlist(self, mylist):
        return flattenlist(mylist)

    def partition(self, frames, columns):
        return partition(self, frames, columns)

    ############## End aliases

    def initialize(self):
        """
        Initialize board registers and set pots
        """
        # TODO: automate sensor and board selection from firmware info
        ###############
        # For regular version

        # get sensor
        # TODO: pull sensor, board, comm id out to separate methods
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

        # Now that board exists, initialize board-specific aliases for sensors
        self.sensor.init_board_specific()

        ###############

        # TODO: make cython the standard version
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
                    self.logcrit + "Initialization failed: unable to communicate with"
                    " board. "
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

        # TODO: move to new method (combine with parsing from initialize)
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
                self.logwarn + "FPGA self-identifies as SNLrevC, which is not"
                " supported by this software "
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
        # logging.debug(self.logdebug + "getRegister: regname = " + str(regname))
        logging.debug(
            "{logdebug}getRegister: regname = {regname}".format(
                logdebug=self.logdebug, regname=regname
            )
        )

        regname = regname.upper()
        if regname not in self.board.registers:
            err = "{logerr}getRegister: Invalid register name: {regname}; returning"
            " zeros".format(logerr=self.logerr, regname=regname)
            logging.error(err)
            return err, "00000000"
        sendpkt = Packet(cmd="1", addr=self.board.registers[regname])
        err, rval = self.comms.sendCMD(sendpkt)
        if err:
            logging.error(
                "{logerr}getRegister: {regname}; {err}".format(
                    logerr=self.logerr, regname=regname, err=err
                )
            )

        retval = rval[8:16]
        logging.debug(
            "{logdebug}getRegister: retval = {retval}".format(
                logdebug=self.logdebug, retval=retval
            )
        )

        return err, retval

    def setRegister(self, regname, regval):
        """
        Sets named register to given value

        Args:
            regname: name of register as given in ICD
            regval: value to assign to register, as integer or hexadecimal string
              with or without '0x'

        Returns:
            tuple: (error string, response string)
        """
        logging.debug(
            "{logdebug}setRegister: regname = {regname}; regval = {regval}".format(
                logdebug=self.logdebug, regname=regname, regval=regval
            )
        )

        regname = regname.upper()
        if regname not in self.board.registers:
            err = "{logerr}setRegister: Invalid register name: {regname}".format(
                logerr=self.logerr, regname=regname
            )
            logging.error(err)
            return err, "00000000"
        if isinstance(regval, int):
            regval = hex(regval)
        try:
            if regval[0:2] == "0x":
                regval = regval[2:]
        except TypeError:
            err = "{logerr}setRegister: invalid register value parameter".format(
                logerr=self.logerr
            )
            logging.error(err)
            return err, "00000000"
        pkt = Packet(addr=self.board.registers[regname], data=regval)
        err, rval = self.comms.sendCMD(pkt)
        if err:
            logging.error(
                "{logerr}setRegister: {regname}: {err}".format(
                    logerr=self.logerr, regname=regname, err=err
                )
            )
        if len(rval) < 32:
            logging.debug(
                "{logdebug}SetRegister: rval = {rval}".format(
                    logdebug=self.logdebug, rval=rval
                )
            )
        else:
            logging.debug(
                "{logdebug}SetRegister: rval (truncated)= {rval}".format(
                    logdebug=self.logdebug, rval=rval[0:32]
                )
            )
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
        logging.debug(
            "{logdebug}resolveSubreg: srname = {srname}".format(
                logdebug=self.logdebug,
                srname=srname,
            )
        )
        writable = False
        srname = srname.upper()
        if srname in self.board.subreg_aliases:
            srname = self.board.subreg_aliases[srname].upper()
        if srname in self.board.subreglist:
            srobj = getattr(self.board, srname)
            writable = getattr(self.board, srname).writable
        else:
            # No-object error is handled by calling function
            srobj = None
        logging.debug(
            "{logdebug}resolveSubreg: srobj = {srobj}, writable={writable}".format(
                logdebug=self.logdebug, srobj=srobj, writable=writable
            )
        )

        return srname, srobj, writable

    def getSubregister(self, subregname):
        """
        Returns substring of register identified in board attribute 'subregname'

        Args:
            subregname: listed in board.subreg_aliases or defined in board.subregisters

        Returns:
            tuple: (error string, contents of subregister as binary string without '0b')
        """
        logging.debug(
            "{logdebug}getSubegister: subregname = {subregname}".format(
                logdebug=self.logdebug,
                subregname=subregname,
            )
        )

        subregname, subregobj, _ = self.resolveSubreg(subregname)
        if not subregobj:
            err = "{logerr}getSubregister: invalid lookup: {subregname}; returning"
            " string of zeroes".format(logerr=self.logerr, subregname=subregname)

            logging.error(err)
            return err, "".zfill(8)
        err, resp = self.getRegister(subregobj.register)
        if err:
            logging.error(
                "{logerr}getSubregister: unable to retrieve register setting: \
                {subregname}; returning '0' string".format(
                    logerr=self.logerr, subregname=subregname
                )
            )

            return err, "".zfill(8)
        hex_str = "0x" + resp  # this should be a hexadecimalstring
        b_reg_value = "{0:0=32b}".format(int(hex_str, 16))  # convert to binary string
        # list indexing is reversed from bit string; the last bit of the string is at
        #   index 0 in the list (thus bit 0 is at index 0)
        startindex = 31 - subregobj.start_bit
        retval = b_reg_value[startindex : startindex + subregobj.width]
        logging.debug(
            "{logdebug}getSubregister: retval = {retval}".format(
                logdebug=self.logdebug, retval=retval
            )
        )
        return "", retval

    def setSubregister(self, subregname, valstring):
        """
        Sets substring of register identified in board attribute 'subregname' to
          valstring if subregister is writable

        Args:
            subregname: listed in board.subreg_aliases or defined in board.subregisters
            valstring: integer or binary string with or without '0b'

        Returns:
            tuple: (error, packet response string) from setRegister
        """
        logging.debug(
            "{logdebug}setSubegister: subregname = {subregname}; valstring ="
            " {valstring}".format(
                logdebug=self.logdebug, subregname=subregname, valstring=valstring
            )
        )

        subregname, subregobj, writable = self.resolveSubreg(subregname)
        if not subregobj:
            err = "{logerr}getSubregister: invalid lookup: {subregname}".format(
                logerr=self.logerr, subregname=subregname
            )

            logging.error(err)
            return err, "0"
        if not writable:
            err = "{logerr}getSubregister: not a writable subregister: {subregname}"
            "".format(logerr=self.logerr, subregname=subregname)
            logging.error(err)
            return err, "0"
        if isinstance(valstring, int):
            valstring = bin(valstring)[2:]
        try:
            if valstring[0:2] == "0b":
                valstring = valstring[2:]
        except TypeError:
            err = "{logerr}getSubregister: invalid subregister value parameter".format(
                logerr=self.logerr
            )

            logging.error(err)
            return err, "0"
        if len(str(valstring)) > subregobj.width:
            err = "{logerr}getSubregister: ialue string is too long".format(
                logerr=self.logerr
            )

            logging.error(err)
            return err, "0"
        # read current value of register data
        err, resp = self.getRegister(subregobj.register)
        if err:
            logging.error(
                "{logerr}getSubregister: unable to retrieve register setting; setting"
                " of {subregname} likely failed ".format(
                    logerr=self.logerr, subregname=subregname
                )
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
        err, retval = self.setRegister(subregobj.register, h_reg_value)
        # logging.debug(self.logdebug + "retval = " + str(retval))
        if len(retval) < 32:
            logging.debug(
                "{logdebug}setSubregister: retval = {retval}".format(
                    logdebug=self.logdebug, retval=retval
                )
            )
        else:
            logging.debug(
                "{logdebug}setSubregister: retval (truncated) = {retval}".format(
                    logdebug=self.logdebug, retval=retval[0:32]
                )
            )

        return err, retval

    def submitMessages(self, messages, errorstring="Error"):
        """
        Serially set multiple register / subregister values

        Args:
            messages: list of tuples (register name, integer or hexadecimal string with
              or without '0x') and/or (subregister name, integer or binary string with
              or without '0b')
            errorstring: error message to print in case of failure

        Returns:
            tuple (accumulated error string, response string of final message)
        """
        logging.debug(
            "{logdebug}submitMessages: messages = {messages}; errorstring ="
            " {errorstring}".format(
                logdebug=self.logdebug, messages=messages, errorstring=errorstring
            )
        )

        errs = ""
        err = ""
        rval = ""
        for m in messages:
            if m[0].upper() in self.board.registers:
                err, rval = self.setRegister(m[0].upper(), m[1])
            elif m[0].upper() in self.board.subreglist:
                err, rval = self.setSubregister(m[0].upper(), m[1])
            else:
                err = "{logerr}submitMessages: Invalid register/subregister:"
                " {errorstring}:{m0}; ".format(
                    logerr=self.logerr, errorstring=errorstring, m0=m[0]
                )

                logging.error(err)
            errs = errs + err
        return err, rval

    def getPot(self, potname, errflag=False):
        """
        Retrieves value of pot or ADC monitor subregister, scaled to [0,1). Returns '-1'
          if value is unavailable

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
        logging.debug(
            "{logdebug}getPot: potname = {potname}; errflag = {errflag}".format(
                logdebug=self.logdebug, potname=potname, errflag=errflag
            )
        )

        potname, potobj, _ = self.resolveSubreg(potname)
        if not potobj:
            err = "{logerr}getPot: invalid lookup: {potname}; returning -1".format(
                logerr=self.logerr, potname=potname
            )

            logging.error(err)
            if errflag:
                return err, -1
            return -1
        err, b_pot_value = self.getSubregister(potname)
        if err:
            err = "{logerr}getPot: unable to read subregister: {potname}".format(
                logerr=self.logerr, potname=potname
            )
            b_pot_value = "-0b1"

        # convert binary string back to decimal
        f_reg_value = 1.0 * int(b_pot_value, 2)
        value = (f_reg_value - potobj.min) / (potobj.max - potobj.min)
        # logging.debug(self.logdebug + "getpot: value = " + str(value))

        logging.debug(
            "{logdebug}getpot: value =  {value}".format(
                logdebug=self.logdebug, value=value
            )
        )
        if value < 0:
            value = -1
        if errflag:
            return err, value
        return value

    def setPot(self, potname, value=1.0, errflag=False):
        """
        Sets value of pot to value, normalized so that '1.0' corresponds with the fixed
          point maximum value of pot.

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
        logging.debug(
            "{logdebug}setPot: potname = {potname}; value={value} errflag = {errflag}"
            "".format(
                logdebug=self.logdebug, potname=potname, value=value, errflag=errflag
            )
        )

        if value < 0:
            value = 0.0
        if value > 1:
            value = 1.0

        potname, potobj, writable = self.resolveSubreg(potname)
        if not potobj:
            err = "{logerr}setPot: invalid lookup: {potname}; returning '-0b1'".format(
                logerr=self.logerr, potname=potname
            )

            logging.error(err)
            if errflag:
                return err, "-0b1"
            return "-0b1"
        if not writable:
            err = "{logerr}setPot: not a writable subregister: {potname}; returning"
            " '-0b1'".format(logerr=self.logerr, potname=potname)
            logging.error(err)
            if errflag:
                return err, "-0b1"
            return "-0b1"
        setpoint = int(round(value * potobj.max_value))
        setpointpadded = "{num:{fill}{width}b}".format(
            num=setpoint, fill="0", width=potobj.width
        )
        logging.debug(
            "{logdebug}setpot: setpointpadded =  {setpointpadded}".format(
                logdebug=self.logdebug, setpointpadded=setpointpadded
            )
        )

        err, rval = self.setSubregister(potname, setpointpadded)
        if err:
            logging.error(
                err="{logerr}setPot: unable to confirm setting of subregister:"
                " {potname}".format(logerr=self.logerr, potname=potname)
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
            # logging.error(self.logerr + "setPot: unable to latch register")

            logging.error(
                err="{logerr}setPot: unable to latch register".format(
                    logerr=self.logerr
                )
            )

        if errflag:
            return err + err1, rval
        return rval

    def getPotV(self, potname, errflag=False):
        """
        Reads voltage _setting_ (not actual voltage) of specified pot. Returns negative
          voltage if pot read is invalid

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
        logging.debug(
            self.logdebug
            + "getPotV: potname = "
            + str(potname)
            + "; errflag = "
            + str(errflag)
        )
        potname, potobj, _ = self.resolveSubreg(potname)
        if not potobj:
            err = (
                self.logerr + "getPotV: invalid lookup: " + potname + " , returning -1 "
            )
            logging.error(err)
            if errflag:
                return err, -1
            return -1
        err, val = self.getPot(potname, errflag=True)
        logging.debug(self.logdebug + "getPotV: val = " + str(val))
        if err:
            logging.error(
                self.logerr
                + "getPotV: unable to read pot "
                + potname
                + "; returning a negative voltage"
            )
            val = -1
        minV = potobj.minV
        maxV = potobj.maxV
        if val < 0:
            returnval = -1
        else:
            returnval = val * (maxV - minV)

        if errflag:
            return err, returnval
        return returnval

    # TODO: optimize tuning speed for DACs
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
            accuracy: acceptable error in volts (if None, attempts to find the closest
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
        logging.debug(
            self.logdebug
            + "setPotV: potname = "
            + str(potname)
            + "; voltage = "
            + str(voltage)
            + "; tune = "
            + str(tune)
            + "; accuracy = "
            + str(accuracy)
            + "; iterations = "
            + str(iterations)
            + "; approach = "
            + str(approach)
            + "; errflag = "
            + str(errflag)
        )
        potname, potobj, writable = self.resolveSubreg(potname)
        if not potobj:
            err = (
                self.logerr
                + "setPotV: invalid lookup: "
                + potname
                + " , returning '-0b1' "
            )
            logging.error(err)
            if errflag:
                return err, "-0b1"
            return "-0b1"
        if not writable:
            err = (
                self.logerr
                + "setPotV: not a writable subregister: "
                + potname
                + "; returning '-0b1'"
            )
            logging.error(err)
            if errflag:
                return err, "-0b1"
            return "-0b1"
        if voltage < potobj.minV:
            voltage = potobj.minV
        if voltage > potobj.maxV:
            voltage = potobj.maxV
        setting = (voltage - potobj.minV) / (potobj.maxV - potobj.minV)
        logging.debug(self.logdebug + "setPotV: setting = " + str(setting))
        err, rval = self.setPot(potname, setting, errflag=True)
        time.sleep(0.1)
        # TODO: refactor tuning to separate method
        if tune:
            logging.debug(self.logdebug + "setPotV: beginning tuning")
            if potname not in self.board.monitor_controls.values():
                err = (
                    self.logerr
                    + "setPotV: pot '"
                    + potname
                    + "' does not have a corresponding monitor; returning '-0b1'"
                )
                logging.error(err)
                if errflag:
                    return err, "-0b1"
                return "-0b1"
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
                err += self.logerr + "setPotV: unable to tune pot " + potname
                if potrange < 1:  # potrange should be on the order of 3.3 or 5 volts
                    err += "; monitor shows insufficient change with pot variation; "
                    "retrying setPotV with tune=False"
                logging.warning(err)
                err, rval = self.setPotV(
                    potname=potname, voltage=voltage, tune=False, errflag=True
                )
                if errflag:
                    err += "; unable to set pot; returning '-0b1'"
                    return err, "-0b1"
                return "-0b1"
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
                            + "V; if this value is incorrect, consider trying "
                            + "tune=False"
                        )
                        logging.debug(self.logdebug + "setPotV: tuning complete")
                        if errflag:
                            return "", rval
                        return rval
                    smalladjust += 1
                if not int(2 * diff / stepsize):
                    # TODO: is this check redundant with the first one?
                    logging.debug(self.logdebug + "setPotV: tuning complete")
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
            logging.error(
                self.logerr
                + "setPotV: errors occurred: "
                + err
                + "; returning negative value"
            )
            rval = -1
        if errflag:
            return err, rval
        logging.debug(self.logdebug + "setPotV: tuning complete")
        return rval

    def getMonV(self, monname, errflag=False):
        """
        Reads voltage from monitor named or associated with the pot named 'monname'.
        Returns negative voltage if pot read is invalid

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
        logging.debug(
            self.logdebug
            + "getMonV: monname = "
            + str(monname)
            + "; errflag = "
            + str(errflag)
        )
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
                    self.logerr
                    + "getMonV: invalid lookup "
                    + monname
                    + ", returning -1"
                )
                logging.error(err)
                if errflag:
                    return err, -1
                return -1
        err, monval = self.getPot(monname, errflag=True)
        logging.debug(self.logdebug + "getMonV: monval = " + str(monval))
        if err:
            logging.error(
                self.logerr
                + "getMonV: unable to read monitor value for "
                + monname
                + "; returning -1"
            )
            monval = -1
            return -1
        # Bipolar ADCs can legitimately return a negative voltage, but this is an
        #   error condition for the board
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

    def saveFrames(self, frames, path=None, filename="frames", prefix=None):
        """
        Save list of numpy arrays to disk. If passed an unprocessed text string, saves
          it directly to disk for postprocessing. Use 'prefix=""' for no prefix

        Args:
            frames: numpy array or list of numpy arrays OR text string
            path: save path, defaults to './output'
            filename: defaults to 'frames.bin'
            prefix: prepended to filename, defaults to time/date (e.g. '160830-124704_')

        Returns:
            Error string
        """
        logging.debug(
            self.logdebug
            + "saveFrames: path = "
            + str(path)
            + "; filename = "
            + str(filename)
            + "; prefix = "
            + str(prefix)
        )
        logging.info(self.loginfo + "saveFrames")
        err = ""
        if path is None:
            path = os.path.join(os.getcwd(), "output")
        if prefix is None:
            prefix = datetime.now().strftime("%y%m%d-%H%M%S%f")[:-5] + "_"
        if not os.path.exists(path):
            os.makedirs(path)

        # TODO catch save file exceptions
        if isinstance(frames[0], str):
            logging.debug(self.logdebug + "saveFrames: saving text frames")
            filename = filename + ".txt"
            savefile = open(os.path.join(path, prefix + filename), "w+")
            savefile.write(frames)
        else:
            logging.debug(self.logdebug + "saveFrames: saving numerical frames")
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

    def saveNumpys(
        self,
        frames,
        path=None,
        filename="Frame",
        prefix=None,
        index=None,
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
        logging.debug(
            self.logdebug
            + "saveNumpys: path = "
            + str(path)
            + "; filename = "
            + str(filename)
            + "; prefix = "
            + str(prefix)
            + "; index = "
            + str(index)
        )
        err = ""
        if path is None:
            path = os.path.join(os.getcwd(), "output")
        if prefix is None:
            prefix = datetime.now().strftime("%y%m%d-%H%M%S%f")[:-5] + "_"
        if not os.path.exists(path):
            os.makedirs(path)
        if index is None:
            firstnum = self.sensor.firstframe
        else:
            firstnum = index
        if not isinstance(frames, list):
            frames = [frames]

        # if this is a text string from fast readoff, do the numpy conversion now
        if isinstance(frames[0], str):
            frames = generateFrames(frames)

        framestemp = np.copy(frames)

        for idx, frame in enumerate(framestemp):
            if idx < len(framestemp) / 2:
                interlacing = self.sensor.interlacing[0]
            else:
                interlacing = self.sensor.interlacing[1]
            try:
                if self.padToFull:
                    frame = np.reshape(
                        frame, (self.sensor.maxheight // (interlacing + 1), -1)
                    )
                else:
                    frame = np.reshape(
                        frame,
                        (
                            (self.sensor.lastrow - self.sensor.firstrow + 1)
                            // (interlacing + 1),
                            -1,
                        ),
                    )
                namenum = filename + "_%d" % firstnum
                nppath = os.path.join(path, prefix + namenum + ".npy")
                np.save(nppath, frame)
                firstnum += 1
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except Exception:
                err = self.logerr + "saveNumpys: unable to save arrays"
                logging.error(err)
                continue
        return err

    def dumpNumpy(
        self,
        datastream,
        path=None,
        filename="Dump",
        prefix=None,
    ):
        """
        Datastream is converted directly to numpy array and saved to disk. No attempt to
          parse headers or separate into individual frames is made. The packet header is
          removed before saving

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
        logging.debug(
            self.logdebug
            + "dumpNumpy: path = "
            + str(path)
            + "; filename = "
            + str(filename)
            + "; prefix = "
            + str(prefix)
        )
        err = ""
        if path is None:
            path = os.path.join(os.getcwd(), "output")
        if prefix is None:
            prefix = time.strftime("%y%m%d-%H%M%S_", time.localtime())
        if not os.path.exists(path):
            os.makedirs(path)
        npdata = str2nparray(datastream[36:])
        try:
            nppath = os.path.join(path, prefix + filename + ".npy")
            np.save(nppath, npdata)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except Exception:
            err = self.logerr + "dumpNumpy: unable to save data stream"
            logging.error(err)
        return err

    def checkRegSet(self, regname, teststring):
        """
        Quick check to confirm that data read from register matches data write

        Args:
            regname: register to test
            teststring: value to assign to register, as integer or hexadecimal string
              with or without '0x'

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
          Compares time elapsed since initialization against board's timer. If the
          difference is greater than 'delta,' flag as False (power has likely failed)

        Args:
            delta: difference in seconds permitted between software and board timers

        Returns:
            boolean, 'True' means timer difference is less than 'delta' parameter;
                     'False' indicates power failure
        """
        elapsed = time.time() - self.inittime
        logging.debug(self.logdebug + "powerCheck: elapsed time = " + str(elapsed))
        difference = abs(elapsed - self.getTimer())
        if difference > delta:
            logging.warning(
                self.logwarn + "powerCheck function has failed; may indicate current "
                "or recent power failure "
            )
        return difference < delta

    def printBoardInfo(self):
        # TODO: add override option if logging level is above info
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
            logging.info(self.loginfo + "Sensor label: " + self.sensor.loglabel)
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
            logging.info(self.loginfo + "RS422 connected to " + self.comms.port)

    def dumpRegisters(self):
        """
        *DEPRECATED* use dumpStatus() instead

        List contents of all registers in board.registers. *WARNING* some status flags
          will reset when read.

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
        *DEPRECATED* use dumpStatus() instead

        List contents of all subregisters in board.channel_lookups and
          board.monitor_lookups.
        *WARNING* some registers will reset when read; only the first subregister from
          such a register will return the correct value, the remainder will return zeros

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
            shaped = [
                np.reshape(frame, (self.sensor.maxheight, self.sensor.maxwidth))
                for frame in frames
            ]
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
        logging.debug(
            self.logdebug
            + "setFrames: minframe = "
            + str(minframe)
            + "; maxframe = "
            + str(maxframe)
        )
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

    def setRows(self, minrow=0, maxrow=None, padToFull=False):
        """
        Sets bounds on rows returned by board, inclusive (e.g., 0,1023 returns all 1024
          rows). If called without parameters, resets to full image size.

        Args:
            minrow: first row to return from board
            maxrow: last row to return from board
            padToFull: if True, generate full size frames, padding collected rows with
              zeroes if necessary
        """
        logging.debug(
            self.logdebug
            + "setRows: minrow = "
            + str(minrow)
            + "; maxrow = "
            + str(maxrow)
            + "; padToFull = "
            + str(padToFull)
        )
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
                self.logerr + "setRows: invalid row arguments submitted. Frame size"
                " remains unchanged. "
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
            self.comms.datatimeout = (
                (1.0 * self.sensor.height / self.sensor.maxheight)
                * 5e7
                * self.sensor.nframes
                / self.comms.baud
            )
        self.padToFull = padToFull
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

    def abortReadoff(self, flag=True):
        """
        Simple abort command for readoff in waiting mode--does not interrupt download in
           progress. Requires external threading to function. *WARNING* if not
           intercepted by active readoff command, will terminate next readoff command
           immediately at inception.
        Args:
            flag: Sets passive abort flag read by readoff command
        Returns:
            boolean: updated setting of flag
        """
        logging.info(self.loginfo + "abortReadoff")
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
        *WARNING* This method stores images in RAM, so the number of sets that can be
          acquired in a single call is limited by available memory.

        Args:
            sets: Number of acquisitions to perform
            trig: trigger type; 'hardware', 'software', or 'dual'
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
        logging.debug(
            self.logdebug
            + "batchAcquire: sets = "
            + str(sets)
            + "; trig = "
            + str(trig)
            + "; path = "
            + str(path)
            + "; filename = "
            + str(filename)
            + "; prefix = "
            + str(prefix)
            + "; showProgress = "
            + str(showProgress)
        )
        datalist = ["0"] * sets
        timelist = [datetime.now()] * sets
        logging.info(
            self.loginfo
            + "batchAcquire: temporarily disabling warning and information logging "
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
        for imset, imtime in zip(datalist, timelist):
            setnum = setnum + 1
            if showProgress and not setnum % showProgress:
                print(self.loginfo + "batchAcquire: Saving set " + str(setnum))
            parsed = generateFrames(self, imset)
            if prefix is None:
                setprefix = imtime.strftime("%y%m%d-%H%M%S%f")[:-2] + "_"
            else:
                setprefix = prefix
            self.saveTiffs(parsed, path, filename, prefix=setprefix)
        logging.getLogger().setLevel(self.verblevel)
        logging.info(self.loginfo + "batchAcquire: re-enabling logging")
        return afterread - beforeread

    # TODO: should this be just a flag for readoff instead of a distinct method?
    # TODO: make sure this handles single frames (list made already?), text frames
    # TODO: add documentation
    def saveHDF(
        self,
        frames,
        path=None,
        filename="Acquisition",
        prefix=None,
    ):
        """ """
        logging.info(self.loginfo + ": saveHDF")
        err = ""
        if path is None:
            path = os.path.join(os.getcwd(), "output")
        if prefix is None:
            prefix = datetime.now().strftime("%y%m%d-%H%M%S%f")[:-5] + "_"
        if not os.path.exists(path):
            os.makedirs(path)

        h5file = os.path.join(path, prefix + filename + ".hdf5")
        with h5py.File(h5file, "w") as f:
            # shotgrp = f.create_group("DATA/SHOT")
            frame_index = 0
            for frame in frames:
                grp = f.create_group("DATA/SHOT/FRAME_0" + str(frame_index))
                data = grp.create_dataset(
                    "DATA", (self.sensor.height, self.sensor.width), data=frame
                )
                frame_index += 1


"""
Copyright (c) 2025, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under 
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy (DOE)
and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new contributions must
be made under this license.
"""
