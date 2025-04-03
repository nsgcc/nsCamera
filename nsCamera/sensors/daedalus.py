# -*- coding: utf-8 -*-
"""
Parameters and functions specific to the daedalus three-frame sensor


Author: Jeremy Martin Hill (jerhill@llnl.gov)

Copyright (c) 2025, Lawrence Livermore National Security, LLC.  All rights reserved.
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under 
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy (DOE)
and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new contributions must
be made under this license.

Version: 2.1.2 (February 2025)
"""

import logging
import numbers
from collections import OrderedDict

import numpy as np

from nsCamera.sensors.sensorBase import sensorBase
from nsCamera.utils.misc import flattenlist


class daedalus(sensorBase):
    specwarn = ""
    minframe = 0  # fixed value for sensor
    maxframe = 2  # fixed value for sensor
    maxwidth = 512  # fixed value for sensor
    maxheight = 1024  # fixed value for sensor
    bytesperpixel = 2
    fpganumID = 2  # last nybble of FPGA_NUM
    detect = "DAEDALUS_DET"
    sensfam = "Daedalus"
    loglabel = "[Daedalus] "
    ZDT = False
    HFW = False
    firstframe = 0
    lastframe = 2
    nframes = 3
    width = 512
    height = 1024
    firstrow = 0
    lastrow = 1023
    interlacing = [0, 0]
    columns = 1
    padToFull = True
    toffset = -165.76  # default temperature sensor offset
    tslope = 81.36  # default temperature sensor slope

    def __init__(self, ca):
        self.ca = ca
        super(daedalus, self).__init__(ca)

        self.sens_registers = OrderedDict(
            {
                "HST_READBACK_A_LO": "018",
                "HST_READBACK_A_HI": "019",
                "HST_READBACK_B_LO": "01A",
                "HST_READBACK_B_HI": "01B",
                "HSTALLWEN_WAIT_TIME": "03F",
                "VRESET_HIGH_VALUE": "04A",
                "FRAME_ORDER_SEL": "04B",
                "EXT_PHI_CLK_SH0_ON": "050",
                "EXT_PHI_CLK_SH0_OFF": "051",
                "EXT_PHI_CLK_SH1_ON": "052",
                "EXT_PHI_CLK_SH1_OFF": "053",
                "EXT_PHI_CLK_SH2_ON": "054",
                "HST_TRIGGER_DELAY_DATA_LO": "120",
                "HST_TRIGGER_DELAY_DATA_HI": "121",
                "HST_PHI_DELAY_DATA": "122",
                "HST_EXT_CLK_HALF_PER": "129",
                "HST_COUNT_TRIG": "130",
                "HST_DELAY_EN": "131",
                "RSL_HFW_MODE_EN": "133",
                "RSL_ZDT_MODE_B_EN": "135",
                "RSL_ZDT_MODE_A_EN": "136",
                "BGTRIMA": "137",
                "BGTRIMB": "138",
                "COLUMN_TEST_EN": "139",
                "RSL_CONFIG_DATA_B0": "140",
                "RSL_CONFIG_DATA_B1": "141",
                "RSL_CONFIG_DATA_B2": "142",
                "RSL_CONFIG_DATA_B3": "143",
                "RSL_CONFIG_DATA_B4": "144",
                "RSL_CONFIG_DATA_B5": "145",
                "RSL_CONFIG_DATA_B6": "146",
                "RSL_CONFIG_DATA_B7": "147",
                "RSL_CONFIG_DATA_B8": "148",
                "RSL_CONFIG_DATA_B9": "149",
                "RSL_CONFIG_DATA_B10": "14A",
                "RSL_CONFIG_DATA_B11": "14B",
                "RSL_CONFIG_DATA_B12": "14C",
                "RSL_CONFIG_DATA_B13": "14D",
                "RSL_CONFIG_DATA_B14": "14E",
                "RSL_CONFIG_DATA_B15": "14F",
                "RSL_CONFIG_DATA_B16": "150",
                "RSL_CONFIG_DATA_B17": "151",
                "RSL_CONFIG_DATA_B18": "152",
                "RSL_CONFIG_DATA_B19": "153",
                "RSL_CONFIG_DATA_B20": "154",
                "RSL_CONFIG_DATA_B21": "155",
                "RSL_CONFIG_DATA_B22": "156",
                "RSL_CONFIG_DATA_B23": "157",
                "RSL_CONFIG_DATA_B24": "158",
                "RSL_CONFIG_DATA_B25": "159",
                "RSL_CONFIG_DATA_B26": "15A",
                "RSL_CONFIG_DATA_B27": "15B",
                "RSL_CONFIG_DATA_B28": "15C",
                "RSL_CONFIG_DATA_B29": "15D",
                "RSL_CONFIG_DATA_B30": "15E",
                "RSL_CONFIG_DATA_B31": "15F",
                "RSL_CONFIG_DATA_A0": "160",
                "RSL_CONFIG_DATA_A1": "161",
                "RSL_CONFIG_DATA_A2": "162",
                "RSL_CONFIG_DATA_A3": "163",
                "RSL_CONFIG_DATA_A4": "164",
                "RSL_CONFIG_DATA_A5": "165",
                "RSL_CONFIG_DATA_A6": "166",
                "RSL_CONFIG_DATA_A7": "167",
                "RSL_CONFIG_DATA_A8": "168",
                "RSL_CONFIG_DATA_A9": "169",
                "RSL_CONFIG_DATA_A10": "16A",
                "RSL_CONFIG_DATA_A11": "16B",
                "RSL_CONFIG_DATA_A12": "16C",
                "RSL_CONFIG_DATA_A13": "16D",
                "RSL_CONFIG_DATA_A14": "16E",
                "RSL_CONFIG_DATA_A15": "16F",
                "RSL_CONFIG_DATA_A16": "170",
                "RSL_CONFIG_DATA_A17": "171",
                "RSL_CONFIG_DATA_A18": "172",
                "RSL_CONFIG_DATA_A19": "173",
                "RSL_CONFIG_DATA_A20": "174",
                "RSL_CONFIG_DATA_A21": "175",
                "RSL_CONFIG_DATA_A22": "176",
                "RSL_CONFIG_DATA_A23": "177",
                "RSL_CONFIG_DATA_A24": "178",
                "RSL_CONFIG_DATA_A25": "179",
                "RSL_CONFIG_DATA_A26": "17A",
                "RSL_CONFIG_DATA_A27": "17B",
                "RSL_CONFIG_DATA_A28": "17C",
                "RSL_CONFIG_DATA_A29": "17D",
                "RSL_CONFIG_DATA_A30": "17E",
                "RSL_CONFIG_DATA_A31": "17F",
            }
        )

        self.sens_subregisters = [
            ## R/W subregs
            # Consistent with ICD usage, start_bit is msb: for [7..0] start_bit is 7
            ("HST_MODE", "HS_TIMING_CTL", 0, 1, True),
            ("SLOWREADOFF_0", "CTRL_REG", 4, 1, True),
            ("SLOWREADOFF_1", "CTRL_REG", 5, 1, True),
            ("MANSHUT_MODE", "CTRL_REG", 8, 1, True),
            ("INTERLACING_EN", "CTRL_REG", 9, 1, True),
            ("HFW", "RSL_HFW_MODE_EN", 0, 1, True),
            ("ZDT_A", "RSL_ZDT_MODE_A_EN", 0, 1, True),
            ("ZDT_B", "RSL_ZDT_MODE_B_EN", 0, 1, True),
            ("HST_DEL_EN", "HST_DELAY_EN", 0, 1, True),
            ("PHI_DELAY_A", "HST_PHI_DELAY_DATA", 9, 10, True),
            ("PHI_DELAY_B", "HST_PHI_DELAY_DATA", 29, 10, True),
            # Assume that daedalus is not to be used with v1 board
            ("VRESET_HIGH", "VRESET_HIGH_VALUE", 15, 16, True),
            ## Read-only subregs
            # Consistent with ICD usage, start_bit is msb: for [7..0] start_bit is 7.
            # WARNING: reading a subregister may clear the entire associated register!
            ("STAT_SH0RISEUR", "STAT_REG", 3, 1, False),
            ("STAT_SH0FALLUR", "STAT_REG", 4, 1, False),
            ("STAT_RSLNALLWENA", "STAT_REG", 12, 1, False),
            ("STAT_RSLNALLWENB", "STAT_REG", 15, 1, False),
            # ("STAT_CONFIGHSTDONE", "STAT_REG", 16, 1, False),
        ]

    # TODO: add warning if daedalus and v1 board are together
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
            ("RSL_ZDT_MODE_B_EN", "00000000"),
            ("RSL_ZDT_MODE_A_EN", "00000000"),
            ("RSL_CONFIG_DATA_B0", "00000000"),
            ("RSL_CONFIG_DATA_B1", "00000000"),
            ("RSL_CONFIG_DATA_B2", "00000000"),
            ("RSL_CONFIG_DATA_B3", "00000000"),
            ("RSL_CONFIG_DATA_B4", "00000000"),
            ("RSL_CONFIG_DATA_B5", "00000000"),
            ("RSL_CONFIG_DATA_B6", "00000000"),
            ("RSL_CONFIG_DATA_B7", "00000000"),
            ("RSL_CONFIG_DATA_B8", "00000000"),
            ("RSL_CONFIG_DATA_B9", "00000000"),
            ("RSL_CONFIG_DATA_B10", "00000000"),
            ("RSL_CONFIG_DATA_B11", "00000000"),
            ("RSL_CONFIG_DATA_B12", "00000000"),
            ("RSL_CONFIG_DATA_B13", "00000000"),
            ("RSL_CONFIG_DATA_B14", "00000000"),
            ("RSL_CONFIG_DATA_B15", "00000000"),
            ("RSL_CONFIG_DATA_B16", "00000000"),
            ("RSL_CONFIG_DATA_B17", "00000000"),
            ("RSL_CONFIG_DATA_B18", "00000000"),
            ("RSL_CONFIG_DATA_B19", "00000000"),
            ("RSL_CONFIG_DATA_B20", "00000000"),
            ("RSL_CONFIG_DATA_B21", "00000000"),
            ("RSL_CONFIG_DATA_B22", "00000000"),
            ("RSL_CONFIG_DATA_B23", "00000000"),
            ("RSL_CONFIG_DATA_B24", "00000000"),
            ("RSL_CONFIG_DATA_B25", "00000000"),
            ("RSL_CONFIG_DATA_B26", "00000000"),
            ("RSL_CONFIG_DATA_B27", "00000000"),
            ("RSL_CONFIG_DATA_B28", "00000000"),
            ("RSL_CONFIG_DATA_B29", "00000000"),
            ("RSL_CONFIG_DATA_B30", "00000000"),
            ("RSL_CONFIG_DATA_B31", "00000000"),
            ("RSL_CONFIG_DATA_A0", "00000000"),
            ("RSL_CONFIG_DATA_A1", "00000000"),
            ("RSL_CONFIG_DATA_A2", "00000000"),
            ("RSL_CONFIG_DATA_A3", "00000000"),
            ("RSL_CONFIG_DATA_A4", "00000000"),
            ("RSL_CONFIG_DATA_A5", "00000000"),
            ("RSL_CONFIG_DATA_A6", "00000000"),
            ("RSL_CONFIG_DATA_A7", "00000000"),
            ("RSL_CONFIG_DATA_A8", "00000000"),
            ("RSL_CONFIG_DATA_A9", "00000000"),
            ("RSL_CONFIG_DATA_A10", "00000000"),
            ("RSL_CONFIG_DATA_A11", "00000000"),
            ("RSL_CONFIG_DATA_A12", "00000000"),
            ("RSL_CONFIG_DATA_A13", "00000000"),
            ("RSL_CONFIG_DATA_A14", "00000000"),
            ("RSL_CONFIG_DATA_A15", "00000000"),
            ("RSL_CONFIG_DATA_A16", "00000000"),
            ("RSL_CONFIG_DATA_A17", "00000000"),
            ("RSL_CONFIG_DATA_A18", "00000000"),
            ("RSL_CONFIG_DATA_A19", "00000000"),
            ("RSL_CONFIG_DATA_A20", "00000000"),
            ("RSL_CONFIG_DATA_A21", "00000000"),
            ("RSL_CONFIG_DATA_A22", "00000000"),
            ("RSL_CONFIG_DATA_A23", "00000000"),
            ("RSL_CONFIG_DATA_A24", "00000000"),
            ("RSL_CONFIG_DATA_A25", "00000000"),
            ("RSL_CONFIG_DATA_A26", "00000000"),
            ("RSL_CONFIG_DATA_A27", "00000000"),
            ("RSL_CONFIG_DATA_A28", "00000000"),
            ("RSL_CONFIG_DATA_A29", "00000000"),
            ("RSL_CONFIG_DATA_A30", "00000000"),
            ("RSL_CONFIG_DATA_A31", "00000000"),
            ("HST_TRIGGER_DELAY_DATA_LO", "00000000"),
            ("HST_TRIGGER_DELAY_DATA_HI", "00000000"),
            ("HST_PHI_DELAY_DATA", "00000000"),
            ("SLOWREADOFF_0", "0"),
            ("SLOWREADOFF_1", "0"),
        ]

    def setInterlacing(self, ifactor=None, side=None):
        """
        Sets interlacing factor. NOTE: if called directly when HFW or ZDT mode is active,
        this will disengage those modes automatically. If hemispheres have different
        factors when the image is acquired, the resulting frames are separated into
        half-width images

        Args:
            ifactor: number of interlaced lines (generates ifactor + 1 images per frame)
              defaults to 0 (no interlacing)
            side: identify particular hemisphere (A or B) to control. If left blank,
              control both hemispheres

        Returns:
            integer: active interlacing factor (unchanged if error)
        """
        logging.debug(self.logdebug + "setInterlacing; ifactor = " + str(ifactor))
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
            # deactivating one side shouldn't turn off enable for both sides
            # TODO: is it a problem if sides are set separately, so interlacing is zero
            #    but still enabled?
            if side is None:
                self.ca.setSubregister("INTERLACING_EN", "0")
        else:
            pattern = [0] + ifactor * [1]
            reps = 1 + self.maxheight // (ifactor + 1)
            bitscheme = (reps * pattern)[0 : self.maxheight]
            self.ca.setSubregister("INTERLACING_EN", "1")
        err = ""
        for regnum in range(32):
            regbits = bitscheme[32 * regnum : 32 * (regnum + 1)]
            logging.debug(self.logdebug + "regbits = " + str(regbits))
            # generated pattern is reverse order from placement in register (element 0
            #   of the list is the LSB of the register)
            bitsrev = regbits[::-1]
            s = [str(i) for i in bitsrev]
            b = "".join(s)  # assemble as binary number for processing
            hexval = "%x" % int(b, 2)
            val = hexval.zfill(8)
            err0 = ""
            err1 = ""
            if side is None or side.lower() == "a":
                lname = "RSL_CONFIG_DATA_A" + str(regnum)
                err1, _ = self.ca.setRegister(lname, val)
                self.interlacing[1] = ifactor
            if side is None or side.lower() == "b":
                rname = "RSL_CONFIG_DATA_B" + str(regnum)
                err0, _ = self.ca.setRegister(rname, val)
                self.interlacing[0] = ifactor
            err = err + err0 + err1
        if err:
            logging.error(self.logerr + "interlacing may not be set correctly: " + err)
        logging.info(self.loginfo + "Interlacing set to " + str(self.interlacing))
        if self.interlacing[0] == self.interlacing[1]:
            self.columns = 1
        else:
            self.columns = 2
        return self.interlacing

    def setHighFullWell(self, flag):
        """
        Activates High Full Well mode. All frames are acquired simultaneously. Zero Dead
          Time mode and interlacing will be automatically deactivated and column number
          will be reset to 0. NOTE: after deactivating HFW, the board remains in
          uninterlaced mode (interlacing = 0)

        Args:
            flag: True to activate HFW mode, False to deactivate

        Returns:
            Error message
        """
        logging.debug(self.logdebug + "setHighFullWell; flag = " + str(flag))
        err0 = ""
        if flag:
            if self.ZDT:
                logging.warning(
                    self.logwarn + "ZDT mode will be disengaged because of HFW "
                    "setting "
                )
                err0 = self.setZeroDeadTime(False)
            err1, _ = self.ca.setSubregister("HFW", "1")
            self.HFW = False  # preclude HFW deactivation message in setInterlacing
            self.setInterlacing(0)
            self.HFW = True
            logging.info(self.loginfo + "High Full Well mode active")
        else:
            self.HFW = False
            err1, _ = self.ca.setSubregister("HFW", "0")
            logging.info(self.loginfo + "High Full Well mode inactivate")
        err = err0 + err1
        if err:
            logging.error(self.logerr + "HFW option may not be set correctly ")
        return err

    def setZeroDeadTime(self, flag=True, side=None):
        """
        Activates Zero Dead Time mode. Even rows follow the assigned HST schedule; odd
          rows are acquired while the 'shutter' for the even rows are closed. High Full
          Well mode and interlacing will be automatically deactivated.
        *NOTE* after deactivating ZDT, the board reverts to uninterlaced mode
          (interlacing = 0)

        Args:
            flag: True to activate ZDT mode, False to deactivate
            side: identify particular hemisphere (A or B) to control. If left blank,
              control both hemispheres

        Returns:
            Error message
        """
        logging.debug(self.logdebug + "setZeroDeadTime; flag = " + str(flag))
        err0 = ""
        err1 = ""
        err2 = ""
        if flag:
            if self.HFW:
                logging.warning(
                    self.logwarn + "HFW mode will be disengaged because of ZDT "
                    "setting "
                )
                err0 = self.setHighFullWell(False)
            if side is None or side.lower() == "a":
                err2, _ = self.ca.setSubregister("ZDT_A", "1")
                self.interlacing[0] = 1
            if side is None or side.lower() == "b":
                err1, _ = self.ca.setSubregister("ZDT_B", "1")
                self.interlacing[1] = 1
            # self.ZDT = False  # preclude ZDT deactivation message in setInterlacing
            # if self.interlacing != [0, 0]:
            #     self.setInterlacing(0)
            # TODO: need to handle flags when ZDT active for just one side
            self.ZDT = True
            logging.info(
                self.loginfo + "Zero Dead Time mode active; actual interlacing = 1"
            )
        else:
            self.ZDT = False
            if side is None or side.lower() == "a":
                err2, _ = self.ca.setSubregister("ZDT_A", "0")
            if side is None or side.lower() == "b":
                err1, _ = self.ca.setSubregister("ZDT_B", "0")
            self.setInterlacing(0)
            logging.info(self.loginfo + "Zero Dead Time mode inactivate")
        err = err0 + err1 + err2
        if err:
            logging.error(self.logerr + "ZDT option may not be set correctly ")
        return err

    def selectOscillator(self, osc=None):
        """
        Selects oscillator to control sensor timing
        Args:
            osc: 500|100|'ring'|external', defaults to 500 MHz

        Returns:
            error message as string
        """
        logging.info(self.loginfo + "selectOscillator; osc = " + str(osc))
        if osc is None:
            osc = 500
        osc = str(osc)
        if osc[:3] == "500":
            payload = "00"
        elif osc[:3] == "100":
            payload = "01"
        elif osc.upper()[:3] == "RIN":
            payload = "10"
        elif osc.upper()[:3] in ["EXT"]:
            payload = "11"
        else:
            err = (
                self.logerr + "selectOscillator: invalid parameter supplied. "
                "Oscillator selection is unchanged."
            )
            logging.error(err)
            return err
        self.ca.setSubregister("OSC_SELECT", payload)

    def setTriggerDelay(self, delay=0):
        """
        Use trigger delay timer. Actual delay is rounded down to multiple of .15 ns, up
          to a maximum delay of 6 ns

        Args:
            delay: trigger delay in ns

        Returns:
            String of errors, if any
        """
        logging.debug(self.logdebug + "setTriggerDelay; delay = " + str(delay))
        if (
            not (isinstance(delay, int) or isinstance(delay, float))
            or delay < 0
            or delay > 6
        ):
            err = (
                self.logerr + "invalid trigger delay submitted. Delay remains "
                "unchanged. "
            )
            logging.error(err)
            return err
        delayblocks = int(delay / 0.15)
        if delayblocks < 0:
            delayblocks = 0
        if delayblocks > 40:
            delayblocks = 40
        delayseq = (40 - delayblocks) * [0] + delayblocks * [1]
        seqstr = "".join(str(x) for x in delayseq)
        seqhex = "%x" % int(seqstr, 2)
        logging.debug(self.logdebug + "seqhex = " + str(seqhex))
        highpart = seqhex[-10:-8].zfill(8)
        lowpart = seqhex[-8:].zfill(8)
        self.ca.setSubregister("HST_DEL_EN", "1")
        err0, _ = self.ca.setRegister("HST_TRIGGER_DELAY_DATA_LO", lowpart)
        err1, _ = self.ca.setRegister("HST_TRIGGER_DELAY_DATA_HI", highpart)
        err2, _ = self.ca.setSubregister("HST_MODE", "1")
        delayed = delayblocks * 0.15
        logging.info(self.loginfo + "Actual trigger delay = " + str(delayed) + " ns")
        return err0 + err1 + err2

    def setPhiDelay(self, side=None, delay=0):
        """
        Use phi delay timer. Actual delay is rounded down to multiple of .15 ns, up to a
          maximum delay of 1.5 ns
        Args:
            side: hemisphere to delay; if None, delay both hemispheres
            delay: phi delay in ns

        Returns:
            String of errors, if any
        """
        logging.debug(self.logdebug + "setPhiDelay; delay = " + str(delay))
        if (
            not (isinstance(delay, int) or isinstance(delay, float))
            or delay < 0
            or delay > 1.5
        ):
            err = (
                self.logerr + "invalid phi delay submitted. Delay remains "
                "unchanged. "
            )
            logging.error(err)
            return err
        delayblocks = int(delay / 0.15)
        if delayblocks < 0:
            delayblocks = 0
        if delayblocks > 10:
            delayblocks = 10
        delayseq = (10 - delayblocks) * [0] + delayblocks * [1]
        seqstr = "".join(str(x) for x in delayseq)
        err1 = ""
        err2 = ""
        if side is None or side.upper() == "A":
            err1, _ = self.ca.setSubregister("PHI_DELAY_A", seqstr)
        if side is None or side.upper() == "B":
            err2, _ = self.ca.setSubregister("PHI_DELAY_B", seqstr)
        delayed = delayblocks * 0.15
        logging.info(self.loginfo + "Actual phi delay = " + str(delayed) + " ns")
        return err1 + err2

    def setExtClk(self, dilation=None, frequency=None):
        """
        Override the standard board clock with the external clock.
        Args:
            dilation: ratio of base frequency (500 MHz) to desired external clock
              frequency. Default is 25. Overridden if frequency parameter is provided
            frequency: Desired frequency for phi clock.
        Returns:
            error message as string
        """
        logging.debug(
            self.logdebug
            + "setExtClk; dilation = "
            + str(dilation)
            + "; frequency = "
            + str(frequency)
        )
        if not (isinstance(frequency, int) or isinstance(frequency, float)):
            err = (
                self.logerr
                + "invalid external clock frequency submitted. Clock is not "
                + "operating"
            )
            logging.error(err)
            return err
        self.ca.selectOscillator("external")
        if not dilation:
            dilation = 25
        if not frequency:
            frequency = 5e7 / float(dilation)
        count = 2e7 / float(frequency) - 1  # base phi clock is 20 MHz?
        if count < 0:
            count = 0
            warn = (
                self.logwarn
                + "external clock frequency exceeding maximum. Frequency set to "
                + "maximum (20 MHz)"
            )
            logging.warning(warn)
        if count > 0xFFFFFFFF:
            count = 0xFFFFFFFF
        counthex = hex(int(count))[2:].zfill(8)
        self.ca.setRegister("HST_EXT_CLK_HALF_PER", counthex)

    # TODO: enable exponential form for all large number inputs (accept floats)

    def setManualShutters(self, timing=None):
        """
        Legacy alias for setManualTiming()
        """
        self.setManualTiming(timing)

    def setManualTiming(self, timing=None):
        """
        Manual shutter timing, five intervals given in nanoseconds, e.g.,
          [100,50,100,50,100] for frame 0 open for 100 ns, an interframe pause of 50 ns,
           frame 1 open for 100 ns, etc. Timing is set for both hemispheres.

        The actual timing is rounded down to the nearest multiple of 25 ns. (Each
          count = 25 ns. e.g., a request for 140 ns rounds down to a count of '5',
          which corresponds to 125 ns))
            - Minimum timing is 75 ns
            - Maximum is 25 * 2^30 ns (approximately 27 seconds)

        Args:
            timing: 5-element list in nanoseconds

        Returns:
            tuple (error string, response string from final message)
        """
        if timing is None:
            logging.info(
                self.loginfo
                + "No manual timing setting provided, defaulting to (100, 150, 100, "
                " 150, 100, 150, 100) for both hemispheres"
            )
            timing = [(100, 150, 100, 150, 100)]

        logging.info(self.loginfo + "Manual shutter sequence: " + str(timing))
        flattened = flattenlist(timing)
        if (
            len(flattened) != 5
            or not all(isinstance(x, (int, float)) for x in flattened)
            or not all(x >= 25 for x in flattened)
        ):
            err = self.logerr + "Invalid manual shutter timing list: " + str(timing)
            logging.error(err + "; timing settings unchanged")
            return err, "00000000"

        timecounts = [int(a // 25) for a in flattened]
        self.ca.sensmanual = timing
        self.ca.senstiming = {}  # clear HST settings from ca object

        control_messages = [
            ("MANSHUT_MODE", "1"),
            ("EXT_PHI_CLK_SH0_ON", "{0:#0{1}x}".format(timecounts[0], 10)[2:10]),
            ("EXT_PHI_CLK_SH0_OFF", "{0:#0{1}x}".format(timecounts[1], 10)[2:10]),
            ("EXT_PHI_CLK_SH1_ON", "{0:#0{1}x}".format(timecounts[2], 10)[2:10]),
            ("EXT_PHI_CLK_SH1_OFF", "{0:#0{1}x}".format(timecounts[3], 10)[2:10]),
            ("EXT_PHI_CLK_SH2_ON", "{0:#0{1}x}".format(timecounts[4], 10)[2:10]),
        ]
        return self.ca.submitMessages(control_messages, " setManualShutters: ")

    def getManualTiming(self):
        """
        Read off manual shutter timing settings
        Returns:
            list of manual timing intervals
        """
        timing = []
        for reg in [
            "EXT_PHI_CLK_SH0_ON",
            "EXT_PHI_CLK_SH0_OFF",
            "EXT_PHI_CLK_SH1_ON",
            "EXT_PHI_CLK_SH1_OFF",
            "EXT_PHI_CLK_SH2_ON",
        ]:
            _, reghex = self.ca.getRegister(reg)
            timing.append(25 * int(reghex, 16))
        return timing

    def getSensTemp(self, scale=None, offset=None, slope=None, dec=1):
        """
        Read temperature sensor located on the Daedalus sensor
        Args:
            scale: temperature scale to report (defaults to C, options are F and K)
            offset: offset of linear fit of sensor response (defaults to self.toffset)
            slope: slope of linear fit of sensor response (defaults to self.tslope)
            dec: round to 'dec' digits after the decimal point

        Returns:
            temperature as float on given scale, rounded to .1 degree
        """
        err, rval = self.ca.getMonV("MON_TSENSE_OUT", errflag=True)
        if err:
            logging.error(
                self.logerr + "unable to retrieve temperature information ("
                'getTemp), returning "0" '
            )
            return 0.0
        if offset is None:
            offset = self.toffset
        if slope is None:
            slope = self.tslope

        ctemp = offset + slope * rval
        if scale == "K":
            temp = round(ctemp + 273.15, dec)
        elif scale == "F":
            temp = round(1.8 * ctemp + 32, dec)
        else:
            temp = round(ctemp, dec)
        return temp

    def parseReadoff(self, frames, columns):
        """
        Parses frames from board into images
        Args:
            frames: list of data arrays (frames) returned from board
            columns: 1 (full width image) or 2 (hemispheres generate distinct images)
        Returns:
            list of data arrays (frames) reordered and deinterlaced
        """
        logging.debug(self.logdebug + "parseReadoff")
        w = self.width
        if hasattr(self, "ca"):  # TODO: this may no longer be necessary
            padIt = self.ca.padToFull
        else:
            padIt = self.padToFull
        if padIt:
            rows = self.maxheight
        else:
            rows = self.lastrow - self.firstrow + 1
        parsed = []
        for frame in frames:
            current = np.zeros((rows, w), dtype=np.uint16)
            mapped = np.zeros((rows, w), dtype=np.uint16)
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

        images = self.ca.partition(parsed, columns)
        flatimages = [flattenlist(x) for x in images]
        return flatimages

    def reportStatusSensor(self, statusbits, statusbits2):
        """
        Print status messages from sensor-specific bits of status register or object
          status flags

        Args:
            statusbits: result of checkStatus()
            statusbits2: result of checkStatus2()
        """
        if int(statusbits[3]):
            print(self.loginfo + "SH0_rise_B_edge detected")
        if int(statusbits[4]):
            print(self.loginfo + "SH0_fall_B_edge detected")
        if int(statusbits[12]):
            print(self.loginfo + "RSLNALLWENB detected")
        if int(statusbits[15]):
            print(self.loginfo + "RSLNALLWENA detected")
        if self.HFW:
            print(self.loginfo + "High Full Well mode active")
        # TODO: handle two hemispheres for ZDT
        elif self.ZDT:
            print(self.loginfo + "Zero Dead Time mode active")
        elif self.interlacing != [0, 0]:
            print(
                "{loginfo}Interlacing active: {interlacing}".format(
                    loginfo=self.loginfo, interlacing=str(self.interlacing)
                )
            )
        if self.ca.sensmanual == []:
            print(
                "{loginfo}High-speed timing: A:{Atiming}, B:{Btiming}".format(
                    loginfo=self.loginfo,
                    Atiming=self.getTiming(side="A", actual=True),
                    Btiming=self.getTiming(side="B", actual=True),
                )
            )
        else:
            print(
                "{loginfo}Manual timing set to {timing}".format(
                    loginfo=self.loginfo, timing=self.getManualTiming()
                )
            )


"""
Copyright (c) 2025, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under 
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy (DOE)
and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new contributions must
be made under this license.
"""
