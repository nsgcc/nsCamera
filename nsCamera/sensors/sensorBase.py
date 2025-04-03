# -*- coding: utf-8 -*-
"""
Superclass for nsCamera sensors

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
import itertools
import logging
import numbers

from nsCamera.utils.misc import flattenlist, makeLogLabels


class sensorBase(object):
    """
    Base class for sensors. 'Virtual' methods below default to Icarus behavior.
    daedalus.py overrides these methods as necessary
    """

    def __init__(self, camassem):
        self.ca = camassem
        # skip board settings if no board object exists
        if hasattr(self.ca, "board"):
            self.init_board_specific()

        (
            self.logcrit,
            self.logerr,
            self.logwarn,
            self.loginfo,
            self.logdebug,
        ) = makeLogLabels(self.ca.logtag, self.loglabel)

        # skip assignment if no comms object exists
        if hasattr(self.ca, "comms"):
            self.ca.comms.payloadsize = (
                self.width * self.height * self.nframes * self.bytesperpixel
            )

        logging.info(self.loginfo + "Initializing sensor object")

    def init_board_specific(self):
        """Initialize aliases and subregisters specific to the current board and sensor."""

        if self.ca.sensorname == "icarus" or self.ca.sensorname == "icarus2":
            self.ca.board.subreg_aliases = self.ca.board.icarus_subreg_aliases
            self.ca.board.monitor_controls = self.ca.board.icarus_monitor_controls
        else:
            self.ca.board.subreg_aliases = self.ca.board.daedalus_subreg_aliases
            self.ca.board.monitor_controls = self.ca.board.daedalus_monitor_controls

    # TODO: Check if 'jumpers' still apply for newer boards
    def checkSensorVoltStat(self):
        """
        Checks register tied to sensor select jumpers to confirm match with sensor
        object

        Returns:
            boolean, True if jumpers select for Icarus sensor
        """
        logging.debug(self.logdebug + "checkSensorVoltStat")
        err, status = self.ca.getSubregister(self.detect)
        if err:
            logging.error(self.logerr + "Unable to confirm sensor status")
            return False
        if not int(status):
            logging.error(self.logerr + self.sensfam + " sensor not detected")
            return False
        return True

    def setInterlacing(self, ifactor):
        """
        Virtual function; feature is not implemented on Icarus
        Overridden in daedalus.py

        Returns:
            integer 0
        """
        if ifactor:
            logging.warning(
                self.logwarn + "Interlacing is not supported by Icarus sensors. "
            )
        return 0

    def setHighFullWell(self, flag):
        """
        Virtual function; feature is not implemented on Icarus
        Overridden in daedalus.py
        """
        if flag:
            logging.warning(
                self.logwarn + "HighFullWell mode is not supported by Icarus sensors. "
            )

    def setZeroDeadTime(self, flag):
        """
        Virtual function; feature is not implemented on Icarus
        Overridden in daedalus.py
        """
        if flag:
            logging.warning(
                self.logwarn + "ZeroDeadTime mode is not supported by Icarus sensors. "
            )

    def setTriggerDelay(self, delay):
        """
        Virtual function; feature is not implemented on Icarus
        Overridden in daedalus.py
        """
        if delay:
            logging.warning(
                self.logwarn + "Trigger Delay is not supported by Icarus sensors. "
            )

    def setPhiDelay(self, delay):
        """
        Virtual function; feature is not implemented on Icarus
        Overridden in daedalus.py
        """
        if delay:
            logging.warning(
                self.logwarn + "Phi Delay is not supported by Icarus sensors. "
            )

    def setExtClk(self, delay):
        """
        Virtual function; feature is not implemented on Icarus
        Overridden in daedalus.py
        """
        if delay:
            logging.warning(
                self.logwarn + "External Phi Clock is not supported by Icarus sensors. "
            )

    # TODO: update docs to reflect all sensors
    # TODO: remove default timing?
    # TODO: double-check o+c>20 ns in doc block
    def setTiming(self, side="AB", sequence=None, delay=0):
        """
        Sets timing registers based on 'sequence.' Requesting (0,0) timing will clear the
          timing register.
        *WARNING* if the entire sequence does not fit into the 40-bit register space,
          then the actual timings generated may differ from those requested. If the
          timing sequence fits only once into the register space (i.e., for a single
          frame, open + closed > 20 ns), then the actual timing will be (n, 40-n),
          irrespective of the setting of second parameter, e.g. (35,1) will actually
          result in (35,5) timing.
        *NOTE* Icarus sensors generally cannot use 1 ns timing, so all values for these
          devices (besides the delay) should be at least 2 ns

        Args:
            side: Hemisphere 'A', 'B', 'AB'
            sequence: two-element tuple of timing durations in ns, e.g., '(5,2)'
            delay: initial delay in ns (1 ns delay is acceptable)

        Returns:
            tuple (error string, 10-character hexadecimal representation of timing
              sequence)
        """
        logging.info(
            "{}setTiming; side={}, sequence={}, delay={}".format(
                self.loginfo, side, sequence, delay
            )
        )
        if sequence is None:
            sequence = (3, 2)
        if delay is None:
            delay = 0
        logging.info(
            self.loginfo
            + "HST side "
            + side.upper()
            + ": "
            + str(sequence)
            + "; delay = "
            + str(delay)
        )
        err = ""
        if len(sequence) != 2:
            err = (
                self.logerr
                + "Invalid sequence setting for side: "
                + side
                + "; timing settings are unchanged"
            )
            logging.error(err)
            return err, "0000000000"
        if side.upper() == "AB":
            err1, _ = self.setTiming(side="A", sequence=sequence, delay=delay)
            err2, full40hex = self.setTiming(side="B", sequence=sequence, delay=delay)
            return err1 + err2, full40hex
        if side.upper() == "A":
            lowreg = "HS_TIMING_DATA_ALO"
            highreg = "HS_TIMING_DATA_AHI"
        elif side.upper() == "B":
            lowreg = "HS_TIMING_DATA_BLO"
            highreg = "HS_TIMING_DATA_BHI"
        else:
            err = (
                self.logerr
                + "setTiming: Invalid sensor side: "
                + side
                + "; timing settings unchanged"
            )
            logging.error(err)
            return err, "0000000000"
        if (sequence[0] + sequence[1]) + delay > 40:
            err = (
                self.logerr
                + "setTiming:  Timing sequence is too long to be implemented; "
                "timing settings unchanged "
            )
            logging.error(err)
            return err, "0000000000"

        self.ca.senstiming[side.upper()] = (sequence, delay)
        self.ca.sensmanual = []  # clear manual settings from ca

        full40 = [0] * 40
        bitlist = []
        flag = 1
        sequence = sequence[:2]  # TODO: is this redundant?
        for a in sequence:
            add = [flag] * a
            bitlist += add
            if flag:
                flag = 0
            else:
                flag = 1
        # automatically truncates sequence to 39 characters
        logging.debug(self.logdebug + "bitlist = " + str(bitlist))
        if bitlist:  # skip this if timing is [0,0]
            reversedlist = bitlist[39::-1]
            trunclist = reversedlist[:]
            while trunclist[0] == 0:
                trunclist.pop(0)
            # fullrepeat counts open/closed cycles, doesn't include final frame
            fullrepeats = (40 - len(trunclist) - delay) // len(reversedlist)
            logging.debug(self.logdebug + "fullrepeats = " + str(fullrepeats))
            # Pattern from sequence repeated to fit inside 40 bits
            repeated = trunclist + reversedlist * fullrepeats
            full40[-(len(repeated) + delay + 1) : -(delay + 1)] = repeated
        else:
            logging.warning(self.logwarn + "setTiming: all-zero timing supplied")
            fullrepeats = self.nframes
        full40bin = "".join(str(x) for x in full40)
        logging.debug(self.logdebug + "full40bin = " + str(full40bin))
        full40hex = "%x" % int(full40bin, 2)
        logging.debug(self.logdebug + "full40hex = " + str(full40hex))
        highpart = full40hex[-10:-8].zfill(8)
        lowpart = full40hex[-8:].zfill(8)
        err0, _ = self.ca.setRegister(lowreg, lowpart)
        err1, _ = self.ca.setRegister(highreg, highpart)
        err2, _ = self.ca.setSubregister("MANSHUT_MODE", "0")
        err3, _ = self.ca.setSubregister("HST_MODE", "1")
        err = err0 + err1 + err2 + err3
        if err:
            logging.error(
                self.logerr + "setTiming: Timing may not have been set correctly"
            )
        if fullrepeats < self.nframes - 1:
            actual = self.getTiming(side, actual=True)
            if self.fpganumID == 2:
                expected = [delay] + 2 * list(sequence) + [sequence[0]]
            else:
                expected = [delay] + 3 * list(sequence) + [sequence[0]]
            if actual != expected:
                logging.warning(
                    self.logwarn
                    + "setTiming: Due to sequence length"
                    + self.specwarn
                    + ", the actual timing "
                    "sequence for side "
                    + side
                    + " will be "
                    + "{"
                    + str(actual[0])
                    + "}"
                    + " "
                    + str(actual[1 : 2 * self.nframes])
                )
        elif self.ca.sensorname == "icarus":
            f0delay = sequence[0] + sequence[1]
            logging.warning(
                self.logwarn + "setTiming: Due to use of the Icarus model 1 sensor, the"
                " initial delay for side "
                + side
                + " will actually be "
                + str(delay + f0delay)
                + " nanoseconds"
            )
        return err, full40hex

    # TODO: restore after power cycle?
    # TODO: smart interpretation of Icarus1 timing?
    # TODO: error checking like in getTiming
    def setArbTiming(self, side="AB", sequence=None):
        """
        Set arbitrary high-speed timing sequence.
        Args:
            side: Hemisphere 'A', 'B', 'AB'
            sequence: list of arbitrary timing intervals, beginning with initial delay.
              The conventional timing (3,2) with delay = 0 would be represented by
              [0,3,2,3,2,3,2,3] on icarus devices, [0,3,2,3,2,3] on daedalus. If used
              for interlacing or ZDT, you should populate the entire 40-bit register,
              e.g., [0,3,2,3,2,3,2,3,2,3,2,3,2,3,2,3,2]

            *NOTE* Icarus sensors generally cannot use 1 ns timing, so should use at
              least 2 ns for frames 2 and 3 integration and interframe times (an initial
              delay of only 1 ns is acceptable)

            *NOTE* although the Icarus model 1 only images the middle two frames, timing
              entries must be provided for all four frames; to implement frame 1 open
              for X ns, shutter closed for Y ns, and frame 2 open for Z ns, use the
              sequence [0,1,1,X,Y,Z,1,1]

            *WARNING* arbitrary timings will not be restored after a board power cycle

        Returns:
            list: Actual timing results
        """
        logging.info(
            "{}setArbTiming; side={}, sequence={}".format(self.loginfo, side, sequence)
        )
        if sequence is None:
            if self.sensfam == "Daedalus":
                sequence = [0, 2, 3, 4, 5, 6]
            else:
                sequence = [0, 2, 3, 4, 5, 6, 7, 8]
        logging.info(
            self.loginfo + "HST side " + side.upper() + " (arbitrary): " + str(sequence)
        )
        if side.upper() == "AB":
            err1, _ = self.setArbTiming(side="A", sequence=sequence)
            err2, actual = self.setArbTiming(side="B", sequence=sequence)
            return err1 + err2, actual
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
            logging.error("{}setArbTiming: {}".format(self.logerr, err))
            return err, "0000000000"

        full40 = [0] * 40
        bitlist = []
        flag = 0  # similar to setTiming, but starts with delay

        for a in sequence:
            add = [flag] * a
            bitlist += add
            if flag:
                flag = 0
            else:
                flag = 1

        logging.debug(self.logdebug + "bitlist = " + str(bitlist))
        reversedlist = bitlist[39::-1]
        full40[-(len(reversedlist) + 1) : -1] = reversedlist
        full40bin = "".join(str(x) for x in full40)
        logging.debug(self.logdebug + "full40bin = " + str(full40bin))
        full40hex = "%x" % int(full40bin, 2)
        logging.debug(self.logdebug + "full40hex = " + str(full40hex))
        highpart = full40hex[-10:-8].zfill(8)
        lowpart = full40hex[-8:].zfill(8)
        self.ca.setRegister(lowreg, lowpart)
        self.ca.setRegister(highreg, highpart)
        # deactivates manual shutter mode if previously engaged
        self.ca.setSubregister("MANSHUT_MODE", "0")
        self.ca.setSubregister("HST_MODE", "1")
        actual = self.getTiming(side, actual=True)
        f0delay = sequence[1] + sequence[2]

        if self.ca.sensorname == "icarus":
            if actual != sequence[:1] + sequence[3:6]:
                logging.warning(
                    self.logwarn + "Due to sequence length and use of the Icarus model "
                    "1 sensor, the actual timing sequence for side "
                    + side
                    + " will be "
                    + "{"
                    + str(actual[0] + f0delay)
                    + "}"
                    + " "
                    + str(actual[1 : 2 * self.nframes])
                )
            else:
                logging.warning(
                    self.logwarn + "Due to use of the Icarus model 1 sensor, the actual"
                    " timing sequence for side "
                    + side
                    + " will be "
                    + "{"
                    + str(actual[0] + f0delay)
                    + "}"
                    + " "
                    + str(actual[1 : 2 * self.nframes])
                )
        else:
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
        return "", actual

    # TODO: figure out how to handle interlacing?
    def getTiming(self, side, actual):
        """
        actual = True: returns actual high speed intervals that will be generated by the
                    FPGA as list
                 False: Returns high speed timing settings as set by setTiming. Assumes
                    that timing was set via the setTiming method--it will not accurately
                    report arbitrary timings set by direct register sets or manual
                    shutter control

        Args:
            side: Hemisphere 'A' or 'B'
            actual: False: return HST settings
                    True: calculate and return actual HST behavior

        Returns:
            actual= True: list of shutter intervals;
                        icarus: [delay, open0, closed0, open1, closed1, open2, closed2,
                                  open3]
                        daedalus: [delay, open0, closed0, open1, closed1, open2]
                    False: tuple (hemisphere label,
                                    'open shutter' in ns,
                                    'closed shutter' in ns,
                                    initial delay in ns)

        """
        logging.info("{}getTiming".format(self.loginfo))
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
        logging.debug(self.logdebug + "full40bin = " + str(full40bin))
        if actual:
            if full40bin == "0" * 40:  # all-zero timing
                if self.fpganumID == 2:
                    times = [0] * 6
                else:
                    times = [0] * 8
            else:
                full160 = 4 * full40bin
                gblist = [[k, len(list(g))] for k, g in itertools.groupby(full160)]
                if self.fpganumID == 2:
                    times = [int(x[1]) for x in gblist[:-7:-1]]
                else:
                    times = [int(x[1]) for x in gblist[:-9:-1]]
                times[0] = times[0] - 1
            if self.ca.sensorname == "icarus":
                # get timing for frames 1 and 2, keep delay as offset
                # TODO: should this give a 'correct' offset from frame 0?
                times12 = [times[0]] + times[3:6]
                return times12
            return times
        else:
            if full40bin == "0" * 40:  # all-zero timing
                timeon, timeoff, delay = (0, 0, 0)
            else:
                gblist = [[k, len(list(g))] for k, g in itertools.groupby(full40bin)]
                delay = gblist[-1][1] - 1
                timeon = gblist[-2][1]

                if self.ca.sensorname == "icarus":
                    if len(gblist) == 2:  # 39,1 corner case
                        timeoff = 1
                    elif len(gblist) == 3:  # sequence fits only once
                        timeoff = 40 - timeon
                    else:
                        timeoff = gblist[-3][1]
                else:
                    if len(gblist) < self.nframes:  # sequence fits only once
                        timeoff = 40 - timeon
                    else:
                        # TODO: confirm '-3' works for daedalus
                        timeoff = gblist[-3][1]
            return side.upper(), timeon, timeoff, delay

    def setManualShutters(self, timing=None):
        """
        Legacy alias for setManualTiming()
        """
        self.setManualTiming(timing)

    def setManualTiming(self, timing=None):
        """
        Manual shutter timing, seven intervals to assign to both hemispheres, e.g.,
          [(100,150,100,150,100,150,100)] for frame 0 open for 100 ns, an interframe
          pause of 50 ns,frame 1 open for 100 ns, etc.
        Provide two sets of seven intervals, e.g., [(100,150,100,150,100,150,100),
          (200,250,200,250,200,250,200)] to program the A and B hemispheres
          independently

        Overridden in daedalus.py

        The timing list is flattened before processing; the suggested tuple structure is
          just for clarity (first tuple is A, second is B) and is optional.

        The actual timing is rounded down to the nearest multiple of 25 ns. (Each
          count = 25 ns. e.g., a request for 140 ns rounds down to a count of '5',
          which corresponds to 125 ns))
            - Minimum timing is 75 ns
            - Maximum is 25 * 2^30 ns (approximately 27 seconds)

        Args:
            timing: 7- or 14-element list (substructure optional) in nanoseconds

        Returns:
            tuple (error string, response string from final message)
        """
        if timing is None:
            logging.info(
                self.loginfo
                + "No manual timing setting provided, defaulting to (100, 150, 100, "
                " 150, 100, 150, 100) for both hemispheres"
            )
            timing = [
                (100, 150, 100, 150, 100, 150, 100),
                (100, 150, 100, 150, 100, 150, 100),
            ]
        logging.info(self.loginfo + "Manual shutter sequence: " + str(timing))
        flattened = flattenlist(timing)
        if len(flattened) == 7:
            flattened = 2 * flattened
        if (
            len(flattened) != 14
            or not all(isinstance(x, numbers.Real) for x in flattened)
            or not all(x >= 75 for x in flattened)
            or not all(x <= 26843545600 for x in flattened)
        ):
            err = self.logerr + "Invalid manual shutter timing list: " + str(timing)
            logging.error(err + "; timing settings unchanged")
            return err, "00000000"

        timecounts = [int(a // 25) for a in flattened]
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
            ("HST_MODE", "0"),
            ("MANSHUT_MODE", "1"),
        ]
        return self.ca.submitMessages(control_messages, " setManualShutters: ")

    def getManualTiming(self):
        """
        Read off manual shutter timing settings
        Overridden in daedalus.py
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

    def getSensTemp(self, scale=None, offset=None, slope=None, dec=None):
        """
        Virtual method (Temperature sensor is not present on Icarus sensors). Returns 0.
        Overridden by Daedalus method
        """
        return 0

    def selectOscillator(self, osc=None):
        """
        Selects oscillator to control sensor timing
        Overridden in daedalus.py
        Args:
            osc: 'relaxation'|'ring'|'ringnoosc'|'external', defaults to relaxation

        Returns:
            error message as string
        """
        logging.info(self.loginfo + "selectOscillator; osc = " + str(osc))
        if osc is None:
            osc = "rel"
        osc = str(osc)
        if osc.upper()[:3] == "REL":
            payload = "00"
        elif osc.upper()[:3] == "RIN":
            if "NO" in osc.upper() or "0" in osc:
                payload = "10"
            else:
                payload = "01"
        elif osc.lower()[:3] in ["ext", "phi"]:
            payload = "11"
        else:
            err = (
                self.logerr + "selectOscillator: invalid parameter supplied. "
                "Oscillator selection is unchanged."
            )
            logging.error(err)
            return err
        self.ca.setSubregister("OSC_SELECT", payload)

    def parseReadoff(self, frames, columns):
        """
        Virtual method (Order parsing is unnecessary for Icarus, continue to hemisphere
          parsing.)
        Overridden by Daedalus method
        """
        return self.ca.partition(frames, columns)

    def getSensorStatus(self):
        """
        Wrapper for reportSensorStatus so that the user doesn't have to query statusbits
        """
        sb1 = self.ca.board.checkstatus()
        sb2 = self.ca.board.checkstatus2()
        self.reportStatusSensor(sb1, sb2)

    def reportStatusSensor(self, statusbits, statusbits2):
        """
        Print status messages from sensor-specific bits of status register, default for
          Icarus family sensors
        Args:
            statusbits: result of checkStatus()
            statusbits2: result of checkStatus2()
        """
        if int(statusbits[3]):
            print(self.loginfo + "W3_Top_A_Edge1 detected")
        if int(statusbits[4]):
            print(self.loginfo + "W3_Top_B_Edge1 detected")
        if int(statusbits[12]):
            print(self.loginfo + "HST_All_W_En detected")
        if self.ca.boardname == "llnl_v4" and int(statusbits2[5]):
            print(self.loginfo + "PDBIAS Unready")


# TODO: add function to control TIME_ROW_DCD delay

"""
Copyright (c) 2025, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under 
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy (DOE)
and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new contributions must
be made under this license.
"""
