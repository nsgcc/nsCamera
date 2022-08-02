# -*- coding: utf-8 -*-
"""
Parameters and functions specific to the daedalus three-frame sensor

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

import itertools
import logging
from collections import OrderedDict

import numpy as np


class daedalus:
    def __init__(self, camassem):
        self.ca = camassem
        self.logcrit = self.ca.logcritbase + "[Daedalus] "
        self.logerr = self.ca.logerrbase + "[Daedalus] "
        self.logwarn = self.ca.logwarnbase + "[Daedalus] "
        self.loginfo = self.ca.loginfobase + "[Daedalus] "
        self.logdebug = self.ca.logdebugbase + "[Daedalus] "
        logging.info(self.loginfo + "initializing sensor object")

        self.minframe = 0
        self.maxframe = 2
        self.firstframe = self.minframe
        self.lastframe = self.maxframe
        self.nframes = self.maxframe - self.minframe + 1
        self.maxwidth = 512
        self.maxheight = 1024
        self.firstrow = 0
        self.lastrow = self.maxheight - 1
        self.width = self.maxwidth
        self.height = self.maxheight
        self.bytesperpixel = 2
        self.fpganumID = "2"  # last nybble of FPGA_NUM
        self.interlacing = 0
        self.ZDT = False
        self.HFW = False

        self.sens_registers = OrderedDict(
            {
                "HST_READBACK_A_LO": "018",
                "HST_READBACK_A_HI": "019",
                "HST_READBACK_B_LO": "01A",
                "HST_READBACK_B_HI": "01B",
                "HSTALLWEN_WAIT_TIME": "03F",
                "FRAME_ORDER_SEL": "04B",
                "HST_TRIGGER_DELAY_DATA_LO": "120",
                "HST_TRIGGER_DELAY_DATA_HI": "121",
                "HST_PHI_DELAY_DATA_LO": "122",
                "HST_PHI_DELAY_DATA_HI": "123",
                "HST_TRIG_DELAY_READBACK_LO": "125",
                "HST_TRIG_DELAY_READBACK_HI": "126",
                "HST_PHI_DELAY_READBACK_LO": "127",
                "HST_PHI_DELAY_READBACK_HI": "128",
                "HST_COUNT_TRIG": "130",
                "HST_DELAY_EN": "131",
                "HST_TEST_PHI_EN": "132",
                "RSL_HFW_MODE_EN": "133",
                "RSL_ZDT_MODE_R_EN": "135",
                "RSL_ZDT_MODE_L_EN": "136",
                "BGTRIMA": "137",
                "BGTRIMB": "138",
                "COLUMN_TEST_EN": "139",
                "RSL_CONFIG_DATA_R0": "140",
                "RSL_CONFIG_DATA_R1": "141",
                "RSL_CONFIG_DATA_R2": "142",
                "RSL_CONFIG_DATA_R3": "143",
                "RSL_CONFIG_DATA_R4": "144",
                "RSL_CONFIG_DATA_R5": "145",
                "RSL_CONFIG_DATA_R6": "146",
                "RSL_CONFIG_DATA_R7": "147",
                "RSL_CONFIG_DATA_R8": "148",
                "RSL_CONFIG_DATA_R9": "149",
                "RSL_CONFIG_DATA_R10": "14A",
                "RSL_CONFIG_DATA_R11": "14B",
                "RSL_CONFIG_DATA_R12": "14C",
                "RSL_CONFIG_DATA_R13": "14D",
                "RSL_CONFIG_DATA_R14": "14E",
                "RSL_CONFIG_DATA_R15": "14F",
                "RSL_CONFIG_DATA_R16": "150",
                "RSL_CONFIG_DATA_R17": "151",
                "RSL_CONFIG_DATA_R18": "152",
                "RSL_CONFIG_DATA_R19": "153",
                "RSL_CONFIG_DATA_R20": "154",
                "RSL_CONFIG_DATA_R21": "155",
                "RSL_CONFIG_DATA_R22": "156",
                "RSL_CONFIG_DATA_R23": "157",
                "RSL_CONFIG_DATA_R24": "158",
                "RSL_CONFIG_DATA_R25": "159",
                "RSL_CONFIG_DATA_R26": "15A",
                "RSL_CONFIG_DATA_R27": "15B",
                "RSL_CONFIG_DATA_R28": "15C",
                "RSL_CONFIG_DATA_R29": "15D",
                "RSL_CONFIG_DATA_R30": "15E",
                "RSL_CONFIG_DATA_R31": "15F",
                "RSL_CONFIG_DATA_L0": "160",
                "RSL_CONFIG_DATA_L1": "161",
                "RSL_CONFIG_DATA_L2": "162",
                "RSL_CONFIG_DATA_L3": "163",
                "RSL_CONFIG_DATA_L4": "164",
                "RSL_CONFIG_DATA_L5": "165",
                "RSL_CONFIG_DATA_L6": "166",
                "RSL_CONFIG_DATA_L7": "167",
                "RSL_CONFIG_DATA_L8": "168",
                "RSL_CONFIG_DATA_L9": "169",
                "RSL_CONFIG_DATA_L10": "16A",
                "RSL_CONFIG_DATA_L11": "16B",
                "RSL_CONFIG_DATA_L12": "16C",
                "RSL_CONFIG_DATA_L13": "16D",
                "RSL_CONFIG_DATA_L14": "16E",
                "RSL_CONFIG_DATA_L15": "16F",
                "RSL_CONFIG_DATA_L16": "170",
                "RSL_CONFIG_DATA_L17": "171",
                "RSL_CONFIG_DATA_L18": "172",
                "RSL_CONFIG_DATA_L19": "173",
                "RSL_CONFIG_DATA_L20": "174",
                "RSL_CONFIG_DATA_L21": "175",
                "RSL_CONFIG_DATA_L22": "176",
                "RSL_CONFIG_DATA_L23": "177",
                "RSL_CONFIG_DATA_L24": "178",
                "RSL_CONFIG_DATA_L25": "179",
                "RSL_CONFIG_DATA_L26": "17A",
                "RSL_CONFIG_DATA_L27": "17B",
                "RSL_CONFIG_DATA_L28": "17C",
                "RSL_CONFIG_DATA_L29": "17D",
                "RSL_CONFIG_DATA_L30": "17E",
                "RSL_CONFIG_DATA_L31": "17F",
                "RSL_READ_BACK_R0": "180",
                "RSL_READ_BACK_R1": "181",
                "RSL_READ_BACK_R2": "182",
                "RSL_READ_BACK_R3": "183",
                "RSL_READ_BACK_R4": "184",
                "RSL_READ_BACK_R5": "185",
                "RSL_READ_BACK_R6": "186",
                "RSL_READ_BACK_R7": "187",
                "RSL_READ_BACK_R8": "188",
                "RSL_READ_BACK_R9": "189",
                "RSL_READ_BACK_R10": "18A",
                "RSL_READ_BACK_R11": "18B",
                "RSL_READ_BACK_R12": "18C",
                "RSL_READ_BACK_R13": "18D",
                "RSL_READ_BACK_R14": "18E",
                "RSL_READ_BACK_R15": "18F",
                "RSL_READ_BACK_R16": "190",
                "RSL_READ_BACK_R17": "191",
                "RSL_READ_BACK_R18": "192",
                "RSL_READ_BACK_R19": "193",
                "RSL_READ_BACK_R20": "194",
                "RSL_READ_BACK_R21": "195",
                "RSL_READ_BACK_R22": "196",
                "RSL_READ_BACK_R23": "197",
                "RSL_READ_BACK_R24": "198",
                "RSL_READ_BACK_R25": "199",
                "RSL_READ_BACK_R26": "19A",
                "RSL_READ_BACK_R27": "19B",
                "RSL_READ_BACK_R28": "19C",
                "RSL_READ_BACK_R29": "19D",
                "RSL_READ_BACK_R30": "19E",
                "RSL_READ_BACK_R31": "19F",
                "RSL_READ_BACK_L0": "1A0",
                "RSL_READ_BACK_L1": "1A1",
                "RSL_READ_BACK_L2": "1A2",
                "RSL_READ_BACK_L3": "1A3",
                "RSL_READ_BACK_L4": "1A4",
                "RSL_READ_BACK_L5": "1A5",
                "RSL_READ_BACK_L6": "1A6",
                "RSL_READ_BACK_L7": "1A7",
                "RSL_READ_BACK_L8": "1A8",
                "RSL_READ_BACK_L9": "1A9",
                "RSL_READ_BACK_L10": "1AA",
                "RSL_READ_BACK_L11": "1AB",
                "RSL_READ_BACK_L12": "1AC",
                "RSL_READ_BACK_L13": "1AD",
                "RSL_READ_BACK_L14": "1AE",
                "RSL_READ_BACK_L15": "1AF",
                "RSL_READ_BACK_L16": "1B0",
                "RSL_READ_BACK_L17": "1B1",
                "RSL_READ_BACK_L18": "1B2",
                "RSL_READ_BACK_L19": "1B3",
                "RSL_READ_BACK_L20": "1B4",
                "RSL_READ_BACK_L21": "1B5",
                "RSL_READ_BACK_L22": "1B6",
                "RSL_READ_BACK_L23": "1B7",
                "RSL_READ_BACK_L24": "1B8",
                "RSL_READ_BACK_L25": "1B9",
                "RSL_READ_BACK_L26": "1BA",
                "RSL_READ_BACK_L27": "1BB",
                "RSL_READ_BACK_L28": "1BC",
                "RSL_READ_BACK_L29": "1BD",
                "RSL_READ_BACK_L30": "1BE",
                "RSL_READ_BACK_L31": "1BF",
            }
        )

        self.sens_subregisters = [
            ("STAT_RSLROWOUTL", "STAT_REG", 3, 1, False),
            ("STAT_RSLROWOUTR", "STAT_REG", 4, 1, False),
            ("STAT_RSLNALLWENR", "STAT_REG", 12, 1, False),
            ("STAT_RSLNALLWENL", "STAT_REG", 15, 1, False),
            ("STAT_CONFIGHSTDONE", "STAT_REG", 16, 1, False),
            ("SLOWREADOFF_0", "CTRL_REG", 4, 1, True),
            ("SLOWREADOFF_1", "CTRL_REG", 5, 1, True),
            ("HFW", "RSL_HFW_MODE_EN", 0, 1, True),
            ("ZDT_R", "RSL_ZDT_MODE_R_EN", 0, 1, True),
            ("ZDT_L", "RSL_ZDT_MODE_L_EN", 0, 1, True),
        ]

    def checkSensorVoltStat(self):
        """
        Checks register tied to sensor select jumpers to confirm match with sensor
          object

        Returns:
            boolean, True if jumpers select for Daedalus sensor
        """
        err, status = self.ca.getSubregister("DAEDALUS_DET")
        if err:
            logging.error(self.logerr + "unable to confirm sensor status")
            return False
        if not int(status):
            logging.error(self.logerr + "Daedalus sensor not detected")
            return False
        return True

    def sensorSpecific(self):
        """
        Returns:
            list of tuples, (Sensor-specific register, default setting)
        """
        return [
            ("FPA_FRAME_INITIAL", "00000000"),
            ("FPA_FRAME_FINAL", "00000002"),
            ("FPA_ROW_INITIAL", "00000000"),
            ("FPA_ROW_FINAL", "000003FF"),
            ("HS_TIMING_DATA_ALO", "00006666"),  # 0db6 = 2-1; 6666 = 2-2
            ("HS_TIMING_DATA_AHI", "00000000"),
            ("HS_TIMING_DATA_BLO", "00006666"),
            ("HS_TIMING_DATA_BHI", "00000000"),
            ("FRAME_ORDER_SEL", "00000000"),
            ("RSL_HFW_MODE_EN", "00000000"),
            ("RSL_ZDT_MODE_R_EN", "00000000"),
            ("RSL_ZDT_MODE_L_EN", "00000000"),
            ("RSL_CONFIG_DATA_R0", "00000000"),
            ("RSL_CONFIG_DATA_R1", "00000000"),
            ("RSL_CONFIG_DATA_R2", "00000000"),
            ("RSL_CONFIG_DATA_R3", "00000000"),
            ("RSL_CONFIG_DATA_R4", "00000000"),
            ("RSL_CONFIG_DATA_R5", "00000000"),
            ("RSL_CONFIG_DATA_R6", "00000000"),
            ("RSL_CONFIG_DATA_R7", "00000000"),
            ("RSL_CONFIG_DATA_R8", "00000000"),
            ("RSL_CONFIG_DATA_R9", "00000000"),
            ("RSL_CONFIG_DATA_R10", "00000000"),
            ("RSL_CONFIG_DATA_R11", "00000000"),
            ("RSL_CONFIG_DATA_R12", "00000000"),
            ("RSL_CONFIG_DATA_R13", "00000000"),
            ("RSL_CONFIG_DATA_R14", "00000000"),
            ("RSL_CONFIG_DATA_R15", "00000000"),
            ("RSL_CONFIG_DATA_R16", "00000000"),
            ("RSL_CONFIG_DATA_R17", "00000000"),
            ("RSL_CONFIG_DATA_R18", "00000000"),
            ("RSL_CONFIG_DATA_R19", "00000000"),
            ("RSL_CONFIG_DATA_R20", "00000000"),
            ("RSL_CONFIG_DATA_R21", "00000000"),
            ("RSL_CONFIG_DATA_R22", "00000000"),
            ("RSL_CONFIG_DATA_R23", "00000000"),
            ("RSL_CONFIG_DATA_R24", "00000000"),
            ("RSL_CONFIG_DATA_R25", "00000000"),
            ("RSL_CONFIG_DATA_R26", "00000000"),
            ("RSL_CONFIG_DATA_R27", "00000000"),
            ("RSL_CONFIG_DATA_R28", "00000000"),
            ("RSL_CONFIG_DATA_R29", "00000000"),
            ("RSL_CONFIG_DATA_R30", "00000000"),
            ("RSL_CONFIG_DATA_R31", "00000000"),
            ("RSL_CONFIG_DATA_L0", "00000000"),
            ("RSL_CONFIG_DATA_L1", "00000000"),
            ("RSL_CONFIG_DATA_L2", "00000000"),
            ("RSL_CONFIG_DATA_L3", "00000000"),
            ("RSL_CONFIG_DATA_L4", "00000000"),
            ("RSL_CONFIG_DATA_L5", "00000000"),
            ("RSL_CONFIG_DATA_L6", "00000000"),
            ("RSL_CONFIG_DATA_L7", "00000000"),
            ("RSL_CONFIG_DATA_L8", "00000000"),
            ("RSL_CONFIG_DATA_L9", "00000000"),
            ("RSL_CONFIG_DATA_L10", "00000000"),
            ("RSL_CONFIG_DATA_L11", "00000000"),
            ("RSL_CONFIG_DATA_L12", "00000000"),
            ("RSL_CONFIG_DATA_L13", "00000000"),
            ("RSL_CONFIG_DATA_L14", "00000000"),
            ("RSL_CONFIG_DATA_L15", "00000000"),
            ("RSL_CONFIG_DATA_L16", "00000000"),
            ("RSL_CONFIG_DATA_L17", "00000000"),
            ("RSL_CONFIG_DATA_L18", "00000000"),
            ("RSL_CONFIG_DATA_L19", "00000000"),
            ("RSL_CONFIG_DATA_L20", "00000000"),
            ("RSL_CONFIG_DATA_L21", "00000000"),
            ("RSL_CONFIG_DATA_L22", "00000000"),
            ("RSL_CONFIG_DATA_L23", "00000000"),
            ("RSL_CONFIG_DATA_L24", "00000000"),
            ("RSL_CONFIG_DATA_L25", "00000000"),
            ("RSL_CONFIG_DATA_L26", "00000000"),
            ("RSL_CONFIG_DATA_L27", "00000000"),
            ("RSL_CONFIG_DATA_L28", "00000000"),
            ("RSL_CONFIG_DATA_L29", "00000000"),
            ("RSL_CONFIG_DATA_L30", "00000000"),
            ("RSL_CONFIG_DATA_L31", "00000000"),
            ("HST_TRIGGER_DELAY_DATA_LO", "00000000"),
            ("HST_TRIGGER_DELAY_DATA_HI", "00000000"),
            ("HST_PHI_DELAY_DATA_LO", "00000000"),
            ("HST_PHI_DELAY_DATA_HI", "00000000"),
            ("SLOWREADOFF_0", "0"),
            ("SLOWREADOFF_1", "0"),
        ]

    def setInterlacing(self, ifactor):
        """
        Sets interlacing factor. NOTE: if called directly when HFW or ZDT mode is
        active, this will disengage those modes automatically.

        Args:
            ifactor: number of interlaced lines (generates ifactor + 1 images per frame)
              defaults to 0 (no interlacing)

        Returns:
            integer: active interlacing factor (unchanged if error)
        """
        if ifactor is None:
            ifactor = 0
        if (
            not isinstance(ifactor, int)
            or ifactor < 0
            or ifactor > (self.maxheight - 1)
        ):
            err = (
                self.logerr + "invalid interlacing factor submitted. "
                "Interlacing remains unchanged. "
            )
            logging.error(err)
            return self.interlacing
        if self.HFW:
            logging.warning(
                self.logwarn + "HFW mode will be disengaged because of new "
                "interlacing setting "
            )
            self.setHighFullWell(False)
        if self.ZDT:
            logging.warning(
                self.logwarn + "ZDT mode will be disengaged because of new "
                "interlacing setting "
            )
            self.setZeroDeadTime(False)
        if ifactor == 0:
            bitscheme = self.maxheight * [0]
        else:
            pattern = [0] + ifactor * [1]
            reps = 1 + self.maxheight // (ifactor + 1)
            bitscheme = (reps * pattern)[0 : self.maxheight]
        err = ""
        for a in range(32):
            rname = "RSL_CONFIG_DATA_R" + str(a)
            lname = "RSL_CONFIG_DATA_L" + str(a)
            regbits = bitscheme[32 * a : 32 * (a + 1)]
            # generated pattern is reverse order from placement in register (element 0
            #   of the list is the LSB of the register)
            bitsrev = regbits[::-1]
            s = [str(i) for i in bitsrev]
            b = "".join(s)  # assemble as binary number for processing
            hexval = "%x" % int(b, 2)
            val = hexval.zfill(8)
            err0, _ = self.ca.setRegister(rname, val)
            err1, _ = self.ca.setRegister(lname, val)
            err = err + err0 + err1
        if err:
            logging.error(self.logerr + "interlacing may not be set correctly: " + err)
        logging.info(self.loginfo + "Interlacing factor set to " + str(ifactor))
        self.interlacing = ifactor
        return self.interlacing

    def setHighFullWell(self, flag):
        """
        Activates High Full Well mode. All frames are acquired simultaneously. Zero Dead
          Time mode and interlacing will be automatically deactivated. NOTE: after
          deactivating HFW, the board remains in uninterlaced mode (interlacing = 0)

        Args:
            flag: True to activate HFW mode, False to deactivate

        Returns:
            Error message
        """
        err0 = ""
        if flag:
            if self.ZDT:
                logging.warning(
                    self.logwarn + "ZDT mode will be disengaged because of HFW "
                    "setting "
                )
                err0 = self.setZeroDeadTime(False)
            err1, _ = self.ca.setSubregister("HFW", "1")
            self.HFW = True
            logging.info(self.loginfo + "High Full Well mode active")
        else:
            self.HFW = False
            err1, _ = self.ca.setSubregister("HFW", "0")
            self.setInterlacing(0)
            logging.info(self.loginfo + "High Full Well mode inactivate")
        err = err0 + err1
        if err:
            logging.error(self.logerr + "HFW option may not be set correctly ")
        return err

    def setZeroDeadTime(self, flag):
        """
        Activates Zero Dead Time mode. Even rows follow the assigned HST schedule; odd
          rows are acquired while the 'shutter' for the even rows are closed. High Full
          Well mode and interlacing will be automatically deactivated.
        NOTE: after deactivating ZDT, the board reverts to uninterlaced mode
          (interlacing = 0)

        Args:
            flag: True to activate ZDT mode, False to deactivate

        Returns:
            Error message
        """
        err0 = ""
        if flag:
            if self.HFW:
                logging.warning(
                    self.logwarn + "HFW mode will be disengaged because of ZDT "
                    "setting "
                )
                err0 = self.setHighFullWell(False)
            err1, _ = self.ca.setSubregister("ZDT_R", "1")
            err2, _ = self.ca.setSubregister("ZDT_L", "1")
            self.ZDT = False  # preclude ZDT deactivation message
            self.setInterlacing(0)
            self.interlacing = 1
            self.ZDT = True
            logging.info(
                self.loginfo + "Zero Dead Time mode active; actual interlacing = 1"
            )
        else:
            self.ZDT = False
            err1, _ = self.ca.setSubregister("ZDT_R", "0")
            err2, _ = self.ca.setSubregister("ZDT_L", "0")
            self.setInterlacing(0)
            logging.info(self.loginfo + "Zero Dead Time mode inactivate")
        err = err0 + err1 + err2
        if err:
            logging.error(self.logerr + "ZDT option may not be set correctly ")
        return err

    def setTriggerDelay(self, delayblocks):
        """
        NOTE: THIS IS BASED ON AN UNCERTAIN INTERPRETATION OF THE HDD

        Args:
            delayblocks: number of 150 ps blocks to delay trigger (maximum of 38?)
        """
        if not isinstance(delayblocks, int) or delayblocks < 0 or delayblocks > 38:
            err = (
                self.logerr + "invalid trigger delay submitted. Delay remains "
                "unchanged. "
            )
            logging.error(err)
            return err
        delayseq = (38 - delayblocks) * [0] + delayblocks * [1] + [0, 1]
        seqstr = "".join(str(x) for x in delayseq)
        seqhex = "%x" % int(seqstr, 2)
        highpart = seqhex[-10:-8].zfill(8)
        lowpart = seqhex[-8:].zfill(8)
        err0, _ = self.ca.setRegister("HST_TRIGGER_DELAY_DATA_LO", lowpart)
        err1, _ = self.ca.setRegister("HST_TRIGGER_DELAY_DATA_HI", highpart)
        err2, _ = self.ca.setRegister("HS_TIMING_CTL", "00000001")
        delayed = delayblocks * 0.15
        logging.info(self.loginfo + "Trigger delay = " + str(delayed) + " ns")

    def setTiming(self, side, sequence, delay):
        """
        Sets timing registers based on 'sequence.' WARNING: if entire sequence does not
          fit into the 40-bit register space, then the actual timings may differ from
          those requested. If the timing sequence fits only once into register space
          (i.e., for a single frame, open + closed > 19 ns ), then actual timing will be
          (n, 40-n) irrespective of setting of second parameter, e.g. (35,1) will
          actually result in (35,5) timing

        Args:
            side: Hemisphere 'A' or 'B'
            sequence: two-element tuple of timing durations in ns, e.g., '(5,2)'
            delay: initial delay in ns

        Returns:
            tuple (error string, 10-character hexadecimal representation of timing
              sequence)
        """
        if side is None:
            side = "A"
        if sequence is None:
            sequence = (3, 2)
        if delay is None:
            delay = 0

        if len(sequence) != 2:
            err = (
                self.logerr
                + "Invalid sequence setting for side: "
                + side
                + "; timing settings are unchanged"
            )
            logging.error(err)
            return err, "0000000000"
        logging.info(
            self.loginfo
            + "HST side "
            + side.upper()
            + ": "
            + str(sequence)
            + "; delay = "
            + str(delay)
        )
        if side.upper() == "A":
            lowreg = "HS_TIMING_DATA_ALO"
            highreg = "HS_TIMING_DATA_AHI"
        elif side.upper() == "B":
            lowreg = "HS_TIMING_DATA_BLO"
            highreg = "HS_TIMING_DATA_BHI"
        else:
            err = (
                self.logerr
                + "Invalid sensor side: "
                + side
                + "; timing settings unchanged"
            )
            logging.error(err)
            return err, "0000000000"
        if (sequence[0] + sequence[1]) + delay > 40:
            err = (
                self.logerr + "Timing sequence is too long to be implemented; "
                "timing settings unchanged "
            )
            logging.error(err)
            return err, "0000000000"

        self.ca.senstiming[side.upper()] = (sequence, delay)
        self.ca.sensmanual = []  # clear manual settings from ca

        full40 = [0] * 40
        bitlist = []
        flag = 1
        sequence = sequence[:2]
        for a in sequence:
            add = [flag] * a
            bitlist += add
            if flag:
                flag = 0
            else:
                flag = 1
        # automatically truncates sequence to 39 characters
        reversedlist = bitlist[39::-1]
        repeats = (40 - delay) // len(reversedlist)
        if repeats > self.nframes:
            repeats = self.nframes
        # Pattern from sequence repeated to fit inside 40 bits up to a maximum of
        #   'nframes' times
        repeated = reversedlist * repeats
        if (len(repeated) + delay + 1) < 40 and repeats == self.nframes:
            # add 'stop' bit for ZDT mode if full sequence is less than the full 40 bits
            repeated = [1] + repeated
        full40[-(len(repeated) + delay + 1) : -(delay + 1)] = repeated
        full40bin = "".join(str(x) for x in full40)
        full40hex = "%x" % int(full40bin, 2)
        highpart = full40hex[-10:-8].zfill(8)
        lowpart = full40hex[-8:].zfill(8)
        err0, _ = self.ca.setRegister(lowreg, lowpart)
        err1, _ = self.ca.setRegister(highreg, highpart)
        err2, _ = self.ca.setRegister("HS_TIMING_CTL", "00000001")
        err = err0 + err1 + err2
        if err:
            logging.error(self.logerr + "Timing may not have been set correctly")
        if repeats < self.nframes:
            actual = self.getTiming(side, actual=True)
            expected = [delay] + 3 * list(sequence) + [sequence[0]]
            if actual != expected:
                logging.warning(
                    self.logwarn + "Warning: Due to sequence length, actual "
                    "timing sequence for side "
                    + side
                    + " will be "
                    + "{"
                    + str(actual[0])
                    + "}"
                    + " "
                    + str(actual[1 : 2 * self.nframes])
                )
        return err, full40hex

    def setArbTiming(self, side, sequence):
        """
        Args:
            side: Hemisphere 'A' or 'B'
            sequence: list of arbitrary timing intervals, beginning with initial delay.
              The conventional timing (5,2) with delay = 3 would be represented by
              [3,5,2,5,2,5,2,5].
            *WARNING* arbitrary timings will not be restored after a board power cycle

        Returns:
            tuple (error string, 10-character hexadecimal representation of timing
              sequence)
        """
        if side is None:
            side = "A"
        if sequence is None:
            sequence = [0, 3, 2, 3, 2, 3, 2, 3]

        logging.info(
            self.loginfo + "HST side " + side.upper() + " (arbitrary): " + str(sequence)
        )
        if side.upper() == "A":
            lowreg = "HS_TIMING_DATA_ALO"
            highreg = "HS_TIMING_DATA_AHI"
        elif side.upper() == "B":
            lowreg = "HS_TIMING_DATA_BLO"
            highreg = "HS_TIMING_DATA_BHI"
        else:
            err = (
                self.logerr
                + "Invalid sensor side: "
                + side
                + "; timing settings unchanged"
            )
            logging.error(err)
            return err, "0000000000"
        full40 = [0] * 40
        bitlist = []
        flag = 0  # similar to setTiming, but starts with delay
        sequence = sequence[: (2 * self.nframes)]
        for a in sequence:
            add = [flag] * a
            bitlist += add
            if flag:
                flag = 0
            else:
                flag = 1
        reversedlist = bitlist[39::-1]
        full40[-(len(reversedlist) + 1) : -1] = reversedlist
        full40bin = "".join(str(x) for x in full40)
        full40hex = "%x" % int(full40bin, 2)
        highpart = full40hex[-10:-8].zfill(8)
        lowpart = full40hex[-8:].zfill(8)
        self.ca.setRegister(lowreg, lowpart)
        self.ca.setRegister(highreg, highpart)
        self.ca.setRegister("HS_TIMING_CTL", "00000001")
        # deactivates manual shutter mode if previously engaged
        self.ca.setRegister("MANUAL_SHUTTERS_MODE", "00000000")
        actual = self.getTiming(side, actual=True)
        if actual != sequence:
            logging.warning(
                self.logwarn + "Due to sequence length, actual timing sequence "
                "for side "
                + side
                + " will be "
                + "{"
                + str(actual[0])
                + "}"
                + " "
                + str(actual[1 : 2 * self.nframes])
            )
        return actual

    def getTiming(self, side, actual):
        """
        actual = True: returns actual high speed intervals that will be generated by the
          FPGA as list [delay, open0, closed0, open1, closed1, open2, closed2, open3]
        actual = False: Returns high speed timing settings as set by setTiming. Assumes
          that timing was set via the setTiming method--it will not accurately report
          arbitrary timings set by direct register sets or manual shutter control

        Args:
            side: Hemisphere 'A' or 'B'
            actual: False: return HST settings
                    True: calculate and return actual HST behavior

        Returns:
            actual= False: tuple   (hemisphere label,
                                    'open shutter' in ns,
                                    'closed shutter' in ns,
                                    initial delay in ns)
                    True: list of times [delay, open0, closed0, open1, closed1, open2,
                      closed2, open3]
        """
        if side is None:
            side = "A"

        logging.info(self.loginfo + "get timing, side " + side.upper())
        if side.upper() == "A":
            lowreg = "HS_TIMING_DATA_ALO"
            highreg = "HS_TIMING_DATA_AHI"
        elif side.upper() == "B":
            lowreg = "HS_TIMING_DATA_BLO"
            highreg = "HS_TIMING_DATA_BHI"
        else:
            logging.error(
                self.logerr
                + "Invalid sensor side: "
                + side
                + "; timing settings unchanged"
            )
            return "", 0, 0, 0
        err, lowpart = self.ca.getRegister(lowreg)
        err1, highpart = self.ca.getRegister(highreg)
        if err or err1:
            logging.error(
                self.logerr + "Unable to retrieve timing setting (getTiming), "
                "returning zeroes "
            )
            return side.upper(), 0, 0, 0
        full40hex = highpart[-2:] + lowpart.zfill(8)
        full40bin = "{0:0=40b}".format(int(full40hex, 16))
        if actual:
            full160 = 4 * full40bin
            gblist = [[k, len(list(g))] for k, g in itertools.groupby(full160)]
            times = [int(x[1]) for x in gblist[:-7:-1]]
            times[0] = times[0] - 1
            return times
        else:
            gblist = [[k, len(list(g))] for k, g in itertools.groupby(full40bin)]
            delay = gblist[-1][1] - 1
            timeon = gblist[-2][1]
            if len(gblist) == 2:  # 39,1 corner case
                timeoff = 1
            elif len(gblist) == 3:  # sequence fits only once
                timeoff = 40 - timeon
            else:
                timeoff = gblist[-3][1]
            return side.upper(), timeon, timeoff, delay

    def setManualShutters(self, timing):
        """
        Dummy function; feature is not implemented on Daedalus

        Returns:
            tuple (error string, dummy response string from final message)
        """
        err = (
            self.logerr + "manual shutter control is not implemented in the "
            "Daedalus sensor "
        )
        logging.error(err)
        return err, "00000000"

    def getManualTiming(self):
        """
        Dummy function; feature is not implemented on Daedalus

        Returns:
            list of 2 dummy lists
        """
        logging.warning(
            self.logwarn + "manual shutter control is not implemented in the "
            "Daedalus sensor "
        )
        return [[0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0]]

    def parseReadoff(self, frames):
        """
        Parses frames from board into images
        Args:
            frames: data sets returned from board
        Returns:
            list of frames reordered and deinterlaced
        """
        w = self.width
        if self.ca.padToFull:
            rows = self.maxheight
        else:
            rows = self.lastrow - self.firstrow + 1
        parsed = []
        for frame in frames:
            current = np.zeros((rows, w), dtype=int)
            mapped = np.zeros((rows, w), dtype=int)
            frame = frame.reshape(rows, w)

            for entry in range(int(w / 2)):
                col = 32 * (entry % 8) + entry // 8  # lookup from daedlookup.xls
                for row in range(rows):
                    current[row][col] = frame[row][2 * entry]
                    current[row][col + 256] = frame[row][2 * entry + 1]

            for row in range(rows):
                mapped[row][0:32] = current[row][320:352]
                mapped[row][32:64] = current[row][352:384]
                mapped[row][64:96] = current[row][192:224]
                mapped[row][96:128] = current[row][160:192]
                mapped[row][128:160] = current[row][256:288]
                mapped[row][160:192] = current[row][288:320]
                mapped[row][192:224] = current[row][416:448]
                mapped[row][224:256] = current[row][32:64]
                mapped[row][256:288] = current[row][128:160]
                mapped[row][288:320] = current[row][224:256]
                mapped[row][320:352] = current[row][384:416]
                mapped[row][352:384] = current[row][448:480]
                mapped[row][384:416] = current[row][480:512]
                mapped[row][416:448] = current[row][0:32]
                mapped[row][448:480] = current[row][64:96]
                mapped[row][480:512] = current[row][96:128]
            parsed.append(mapped)

        images = self.ca.deInterlace(parsed, self.interlacing)
        flatimages = [x.flatten() for x in images]
        return flatimages

    def reportStatusSensor(self, statusbits):
        """
        Print status messages from sensor-specific bits of status register or object
          status flags

        Args:
            statusbits: result of checkStatus()
        """
        if int(statusbits[3]):
            logging.info(self.loginfo + "RSLROWINL detected")
        if int(statusbits[4]):
            logging.info(self.loginfo + "RSLROWINR detected")
        if int(statusbits[12]):
            logging.info(self.loginfo + "RSLNALLWENR detected")
        if int(statusbits[15]):
            logging.info(self.loginfo + "RSLNALLWENL detected")
        if int(statusbits[16]):
            logging.info(self.loginfo + "CONFIGHSTDONE detected")
        if self.HFW:
            logging.info(self.loginfo + "High Full Well mode active")
        if self.ZDT:
            logging.info(self.loginfo + "Zero Dead Time mode active")


"""
Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.
"""
