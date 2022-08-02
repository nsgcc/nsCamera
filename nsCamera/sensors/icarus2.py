# -*- coding: utf-8 -*-
"""
Parameters and functions specific to the four-frame icarus2 sensor

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


class icarus2:
    def __init__(self, camassem):
        self.ca = camassem
        self.logcrit = self.ca.logcritbase + "[Icarus2] "
        self.logerr = self.ca.logerrbase + "[Icarus2] "
        self.logwarn = self.ca.logwarnbase + "[Icarus2] "
        self.loginfo = self.ca.loginfobase + "[Icarus2] "
        self.logdebug = self.ca.logdebugbase + "[Icarus2] "
        logging.info(self.loginfo + "initializing sensor object")
        self.minframe = 0
        self.maxframe = 3
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
        self.icarustype = 0  # 4-frame version
        self.fpganumID = "1"  # last nybble of FPGA_NUM
        self.interlacing = 0

        self.sens_registers = OrderedDict(
            {
                "VRESET_WAIT_TIME": "03E",
                "ICARUS_VER_SEL": "041",
                "MISC_SENSOR_CTL": "04C",
                "MANUAL_SHUTTERS_MODE": "050",
                "W0_INTEGRATION": "051",
                "W0_INTERFRAME": "052",
                "W1_INTEGRATION": "053",
                "W1_INTERFRAME": "054",
                "W2_INTEGRATION": "055",
                "W2_INTERFRAME": "056",
                "W3_INTEGRATION": "057",
                "W0_INTEGRATION_B": "058",
                "W0_INTERFRAME_B": "059",
                "W1_INTEGRATION_B": "05A",
                "W1_INTERFRAME_B": "05B",
                "W2_INTEGRATION_B": "05C",
                "W2_INTERFRAME_B": "05D",
                "W3_INTEGRATION_B": "05E",
                "TIME_ROW_DCD": "05F",
            }
        )

        self.sens_subregisters = [
            ("MANSHUT_MODE", "MANUAL_SHUTTERS_MODE", 0, 1, True),
            ("STAT_W3TOPLEDGE1", "STAT_REG", 3, 1, False),
            ("STAT_W3TOPREDGE1", "STAT_REG", 4, 1, False),
            ("STAT_HST_ALL_W_EN_DETECTED", "STAT_REG", 12, 1, False),
            ("REVREAD", "CTRL_REG", 4, 1, True),
            ("PDBIAS_UNREADY", "STAT_REG2", 5, 1, False),
            ("PDBIAS_LOW", "CTRL_REG", 6, 1, True),
            ("ROWDCD_CTL", "CTRL_REG", 7, 1, True),
            ("ACCUMULATION_CTL", "MISC_SENSOR_CTL", 0, 1, True),
            ("HST_TST_ANRST_EN", "MISC_SENSOR_CTL", 1, 1, True),
            ("HST_TST_BNRST_EN", "MISC_SENSOR_CTL", 2, 1, True),
            ("HST_TST_ANRST_IN", "MISC_SENSOR_CTL", 3, 1, True),
            ("HST_TST_BNRST_IN", "MISC_SENSOR_CTL", 4, 1, True),
            ("HST_PXL_RST_EN", "MISC_SENSOR_CTL", 5, 1, True),
            ("HST_CONT_MODE", "MISC_SENSOR_CTL", 6, 1, True),
            ("COL_DCD_EN", "MISC_SENSOR_CTL", 7, 1, True),
            ("COL_READOUT_EN", "MISC_SENSOR_CTL", 8, 1, True),
        ]

    def checkSensorVoltStat(self):
        """
        Checks register tied to sensor select jumpers to confirm match with sensor
        object

        Returns:
            boolean, True if jumpers select for Icarus sensor
        """
        err, status = self.ca.getSubregister("ICARUS_DET")
        if err:
            logging.error(self.logerr + "unable to confirm sensor status")
            return False
        if not int(status):
            logging.error(self.logerr + "Icarus sensor not detected")
            return False
        return True

    def sensorSpecific(self):
        """
        Returns:
            list of tuples, (Sensor-specific register, default setting)
        """
        return [
            ("ICARUS_VER_SEL", "00000000"),
            ("FPA_FRAME_INITIAL", "00000000"),
            ("FPA_FRAME_FINAL", "00000003"),
            ("FPA_ROW_INITIAL", "00000000"),
            ("FPA_ROW_FINAL", "000003FF"),
            ("HS_TIMING_DATA_BHI", "00000000"),
            ("HS_TIMING_DATA_BLO", "00006666"),  # 0db6 = 2-1; 6666 = 2-2
            ("HS_TIMING_DATA_AHI", "00000000"),
            ("HS_TIMING_DATA_ALO", "00006666"),
        ]

    def setInterlacing(self, ifactor):
        """
        Dummy function; feature is not implemented on Icarus2

        Returns:
            integer 1
        """
        if ifactor:
            logging.warning(
                self.logwarn + "Interlacing is not supported by the Icarus2 sensor."
            )
        return 1

    def setHighFullWell(self, flag):
        """
        Dummy function; feature is not implemented on Icarus2
        """
        if flag:
            logging.warning(
                self.logwarn + "HighFullWell mode is not supported by the Icarus2 "
                "sensor. "
            )

    def setZeroDeadTime(self, flag):
        """
        Dummy function; feature is not implemented on Icarus2
        """
        if flag:
            logging.warning(
                self.logwarn + "ZeroDeadTime mode is not supported by the Icarus2 "
                "sensor. "
            )

    def setTriggerDelay(self, delayblocks):
        """
        Dummy function; feature is not implemented on Icarus2
        """
        if delayblocks:
            logging.warning(
                self.logwarn + "Trigger Delay is not supported by the Icarus2 "
                "sensor. "
            )

    def setTiming(self, side, sequence, delay):
        """
        Sets timing registers based on 'sequence.' WARNING: if entire sequence does not
          fit into the 40-bit register space, then the actual timings may differ from
          those requested. If the timing sequence fits only once into register space
          (i.e., for a single frame, open + closed > 19 ns), then actual timing will be
          (n, 40-n) irrespective of setting of second parameter, e.g. (35,1) will
          actually result in (35,5) timing.
        NOTE: Icarus sensors generally cannot use 1 ns timing, so all values (besides
          the delay) should be at least 2 ns

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
        full40[-(len(repeated) + delay + 1) : -(delay + 1)] = repeated
        full40bin = "".join(str(x) for x in full40)
        full40hex = "%x" % int(full40bin, 2)
        highpart = full40hex[-10:-8].zfill(8)
        lowpart = full40hex[-8:].zfill(8)
        self.ca.setRegister(lowreg, lowpart)
        self.ca.setRegister(highreg, highpart)
        self.ca.setRegister("HS_TIMING_CTL", "00000001")
        # deactivates manual shutter mode if previously engaged
        self.ca.setRegister("MANUAL_SHUTTERS_MODE", "00000000")
        if repeats < self.nframes:
            actual = self.getTiming(side, actual=True)
            expected = [delay] + 3 * list(sequence) + [sequence[0]]
            if actual != expected:
                logging.warning(
                    self.logwarn + "Due to sequence length, actual timing "
                    "sequence for side "
                    + side
                    + " will be "
                    + "{"
                    + str(actual[0])
                    + "}"
                    + " "
                    + str(actual[1 : 2 * self.nframes])
                )
        return "", full40hex

    def setArbTiming(self, side, sequence):
        """
        Set arbitrary high-speed timing sequence. NOTE: Icarus sensors generally cannot
          use 1 ns timing, so all values (besides the delay) should be at least 2 ns
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
        # TODO; restore arbitrary timing after power cycle?
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
                    FPGA as list [delay, open0, closed0, open1, closed1, open2, closed2,
                    open3]
                 False: Returns high speed timing settings as set by setTiming. Assumes
                    that timing was set via the setTiming method--it will not accurately
                    report arbitrary timings set by direct register sets or manual
                    shutter control


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
            times = [int(x[1]) for x in gblist[:-9:-1]]
            times[0] = times[0] - 1
            return times
        else:
            gblist = [[k, len(list(g))] for k, g in itertools.groupby(full40bin)]
            delay = gblist[-1][1] - 1
            timeon = gblist[-2][1]
            if len(gblist) < 4:  # sequence fits only once
                timeoff = 40 - timeon
            else:
                timeoff = gblist[-3][1]
            return side.upper(), timeon, timeoff, delay

    def setManualShutters(self, timing):
        """
        Manual shutter timing, seven intervals for each side of the imager given in
          nanoseconds, e.g., [(100,50,100,50,100,50,100),(100,50,100,50,100,50,100)]

        The timing list is flattened before processing; the suggested tuple structure is
          just for clarity (first tuple is A, second is B) and is optional.

        The actual timing is rounded down to nearest multiple of 25 ns. (Each
          count = 25 ns. e.g., 140 ns rounds down to a count of '5' which corresponds
          to 125 ns))

        Args:
            timing: 14-element list (substructure optional) in nanoseconds

        Returns:
            tuple (error string, response string from final message)
        """
        if timing is None:
            timing = [
                (100, 50, 100, 50, 100, 50, 100),
                (100, 50, 100, 50, 100, 50, 100),
            ]
        logging.info(self.loginfo + "Manual shutter sequence: " + str(timing))
        flattened = self.ca.flatten(timing)
        if len(flattened) != 14 or not all(type(x) is int for x in flattened):
            err = self.logerr + "Invalid manual shutter timing list: " + str(timing)
            logging.error(err + "; timing settings unchanged")
            return err, "00000000"

        timecounts = [a // 25 for a in flattened]
        self.ca.sensmanual = timing
        self.ca.senstiming = {}  # clear HST settings from ca object

        control_messages = [
            ("W0_INTEGRATION", "{0:#0{1}x}".format(timecounts[0], 10)[2:10]),
            ("W0_INTERFRAME", "{0:#0{1}x}".format(timecounts[1], 10)[2:10]),
            ("W1_INTEGRATION", "{0:#0{1}x}".format(timecounts[2], 10)[2:10]),
            ("W1_INTERFRAME", "{0:#0{1}x}".format(timecounts[3], 10)[2:10]),
            ("W2_INTEGRATION", "{0:#0{1}x}".format(timecounts[4], 10)[2:10]),
            ("W2_INTERFRAME", "{0:#0{1}x}".format(timecounts[5], 10)[2:10]),
            ("W3_INTEGRATION", "{0:#0{1}x}".format(timecounts[6], 10)[2:10]),
            ("W0_INTEGRATION_B", "{0:#0{1}x}".format(timecounts[7], 10)[2:10]),
            ("W0_INTERFRAME_B", "{0:#0{1}x}".format(timecounts[8], 10)[2:10]),
            ("W1_INTEGRATION_B", "{0:#0{1}x}".format(timecounts[9], 10)[2:10]),
            ("W1_INTERFRAME_B", "{0:#0{1}x}".format(timecounts[10], 10)[2:10]),
            ("W2_INTEGRATION_B", "{0:#0{1}x}".format(timecounts[11], 10)[2:10]),
            ("W2_INTERFRAME_B", "{0:#0{1}x}".format(timecounts[12], 10)[2:10]),
            ("W3_INTEGRATION_B", "{0:#0{1}x}".format(timecounts[13], 10)[2:10]),
            ("HS_TIMING_CTL", "00000000"),
            ("MANUAL_SHUTTERS_MODE", "00000001"),
        ]
        return self.ca.submitMessages(control_messages, " setManualShutters: ")

    def getManualTiming(self):
        """
        Read off manual shutter settings
        Returns:
            list of 2 lists of timing from A and B sides, respectively
        """
        aside = []
        bside = []
        for reg in [
            "W0_INTEGRATION",
            "W0_INTERFRAME",
            "W1_INTEGRATION",
            "W1_INTERFRAME",
            "W2_INTEGRATION",
            "W2_INTERFRAME",
            "W3_INTEGRATION",
        ]:
            _, reghex = self.ca.getRegister(reg)
            aside.append(25 * int(reghex, 16))
        for reg in [
            "W0_INTEGRATION_B",
            "W0_INTERFRAME_B",
            "W1_INTEGRATION_B",
            "W1_INTERFRAME_B",
            "W2_INTEGRATION_B",
            "W2_INTERFRAME_B",
            "W3_INTEGRATION_B",
        ]:
            _, reghex = self.ca.getRegister(reg)
            bside.append(25 * int(reghex, 16))
        return [aside, bside]

    def parseReadoff(self, frames):
        """
        Dummy function; unnecessary for Icarus2 sensor
        """
        return frames

    def reportStatusSensor(self, statusbits):
        """
        Print status messages from sensor-specific bits of status register

        Args:
            statusbits: result of checkStatus()
        """
        if int(statusbits[3]):
            logging.info(self.loginfo + "W3_Top_L_Edge1 detected")
        if int(statusbits[4]):
            logging.info(self.loginfo + "W3_Top_R_Edge1 detected")
        if int(statusbits[12]):
            logging.info(self.loginfo + "HST_All_W_En detected")


"""
Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.
"""
