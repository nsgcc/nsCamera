# -*- coding: utf-8 -*-
"""
The LLNLv4 board is defined here, including monitors and other board-specific settings

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

import logging
import string
import time
from collections import OrderedDict

from nsCamera.utils.Packet import Packet
from nsCamera.utils.Subregister import SubRegister


class llnl_v4:
    """
    Livermore LLNL v4.0 board

    Compatible communication protocols: RS422, GigE
    Compatible sensors: icarus, icarus2, daedalus
    """

    # FPGA register map - use '.upper()' on keys to ensure uppercase lookup
    registers = OrderedDict(
        {  # definitions current as of ICD 2.0
            "FPGA_NUM": "000",
            "FPGA_REV": "001",
            "HS_TIMING_CTL": "010",
            "HS_TIMING_DATA_ALO": "013",
            "HS_TIMING_DATA_AHI": "014",
            "HS_TIMING_DATA_BLO": "015",
            "HS_TIMING_DATA_BHI": "016",
            "SW_TRIGGER_CONTROL": "017",
            "SW_COARSE_CONTROL": "01C",
            "STAT_REG": "024",
            "CTRL_REG": "025",
            "DAC_CTL": "026",
            "DAC_REG_A_AND_B": "027",
            "DAC_REG_C_AND_D": "028",
            "DAC_REG_E_AND_F": "029",
            "DAC_REG_G_AND_H": "02A",
            "SW_RESET": "02D",
            "HST_SETTINGS": "02E",
            "STAT_REG_SRC": "02F",
            "STAT_REG2": "030",
            "STAT_REG2_SRC": "031",
            "ADC_BYTECOUNTER": "032",
            "RBP_PIXEL_CNTR": "033",
            "DIAG_MAX_CNT_0": "034",
            "DIAG_MAX_CNT_1": "035",
            "DIAG_CNTR_VAL_0": "036",
            "DIAG_CNTR_VAL_1": "037",
            "STAT_EDGE_DETECTS": "038",
            "TRIGGER_CTL": "03A",
            "SRAM_CTL": "03B",
            "TIMER_CTL": "03C",
            "TIMER_VALUE": "03D",
            "HSTALLWEN_WAIT_TIME": "03F",
            "FPA_ROW_INITIAL": "042",
            "FPA_ROW_FINAL": "043",
            "FPA_FRAME_INITIAL": "044",
            "FPA_FRAME_FINAL": "045",
            "FPA_DIVCLK_EN_ADDR": "046",
            "FPA_OSCILLATOR_SEL_ADDR": "047",
            "ADC_CTL": "090",
            "ADC1_CONFIG_DATA": "091",
            "ADC2_CONFIG_DATA": "092",
            "ADC3_CONFIG_DATA": "093",
            "ADC4_CONFIG_DATA": "094",
            "ADC5_DATA_1": "095",
            "ADC5_DATA_2": "096",
            "ADC5_DATA_3": "097",
            "ADC5_DATA_4": "098",
            "ADC6_DATA_1": "099",
            "ADC6_DATA_2": "09A",
            "ADC6_DATA_3": "09B",
            "ADC6_DATA_4": "09C",
            "ADC_PPER": "09D",
            "ADC_RESET": "09E",
        }
    )

    subregisters = [
        ## R/W subregs
        # Consistent with ICD usage, start_bit is msb eg, for [7..0] start_bit is 7.
        #   This can cause confusion because the string indices increase left to right
        #   (subreg name, register name, start bit, width, writable)
        ("HST_MODE", "HS_TIMING_CTL", 0, 1, True),
        ("SW_TRIG_START", "SW_TRIGGER_CONTROL", 0, 1, True),
        ("SW_COARSE_TRIGGER", "SW_COARSE_CONTROL", 0, 1, True),
        ("LED_EN", "CTRL_REG", 1, 1, True),
        ("COLQUENCHEN", "CTRL_REG", 2, 1, True),
        ("POWERSAVE", "CTRL_REG", 3, 1, True),
        ("PDBIAS_LOW", "CTRL_REG", 6, 1, True),
        ("DACA", "DAC_REG_A_AND_B", 31, 16, True),
        ("DACB", "DAC_REG_A_AND_B", 15, 16, True),
        ("DACC", "DAC_REG_C_AND_D", 31, 16, True),
        ("DACD", "DAC_REG_C_AND_D", 15, 16, True),
        ("DACE", "DAC_REG_E_AND_F", 31, 16, True),
        ("DACF", "DAC_REG_E_AND_F", 15, 16, True),
        ("DACG", "DAC_REG_G_AND_H", 31, 16, True),
        ("DACH", "DAC_REG_G_AND_H", 15, 16, True),
        ("RESET", "SW_RESET", 0, 1, True),
        ("HST_SW_CTL_EN", "HST_SETTINGS", 0, 1, True),
        ("SW_HSTALLWEN", "HST_SETTINGS", 1, 1, True),
        ("MAXERR_FIT", "DIAG_MAX_CNT_0", 31, 16, True),
        ("MAXERR_SRT", "DIAG_MAX_CNT_0", 7, 8, True),
        ("MAXERR_UTTR", "DIAG_MAX_CNT_1", 31, 16, True),
        ("MAXERR_URTR", "DIAG_MAX_CNT_1", 15, 16, True),
        ("HW_TRIG_EN", "TRIGGER_CTL", 0, 1, True),
        ("DUAL_EDGE_TRIG_EN", "TRIGGER_CTL", 1, 1, True),
        ("SW_TRIG_EN", "TRIGGER_CTL", 2, 1, True),
        ("READ_SRAM", "SRAM_CTL", 0, 1, True),
        ("RESET_TIMER", "TIMER_CTL", 0, 1, True),
        ("OSC_SELECT", "FPA_OSCILLATOR_SEL_ADDR", 1, 2, True),
        ("PPER", "ADC_PPER", 7, 8, True),
        ## Read-only subregs
        # Consistent with ICD usage, start_bit is msb e.g., for [7..0] start_bit is 7.
        #   This can cause confusion for packet handling because the string indices
        #   increase left to right
        # WARNING: reading a subregister may clear the entire associated register!
        ("SRAM_READY", "STAT_REG", 0, 1, False),
        ("STAT_COARSE", "STAT_REG", 1, 1, False),
        ("STAT_FINE", "STAT_REG", 2, 1, False),
        ("STAT_SENSREADIP", "STAT_REG", 5, 1, False),
        ("STAT_SENSREADDONE", "STAT_REG", 6, 1, False),
        ("STAT_SRAMREADSTART", "STAT_REG", 7, 1, False),
        ("STAT_SRAMREADDONE", "STAT_REG", 8, 1, False),
        ("STAT_HSTCONFIGURED", "STAT_REG", 9, 1, False),
        ("STAT_ADCSCONFIGURED", "STAT_REG", 10, 1, False),
        ("STAT_DACSCONFIGURED", "STAT_REG", 11, 1, False),
        ("STAT_TIMERCOUNTERRESET", "STAT_REG", 13, 1, False),
        ("STAT_ARMED", "STAT_REG", 14, 1, False),
        ("STAT_TEMP", "STAT_REG", 23, 7, False),
        ("STAT_PRESS", "STAT_REG", 31, 8, False),
        ("FPA_IF_TO", "STAT_REG2", 0, 1, False),
        ("SRAM_RO_TO", "STAT_REG2", 1, 1, False),
        ("PIXELRD_TOUT_ERR", "STAT_REG2", 2, 1, False),
        ("UART_TX_TO_RST", "STAT_REG2", 3, 1, False),
        ("UART_RX_TO_RST", "STAT_REG2", 4, 1, False),
        ("FIT_COUNT", "DIAG_CNTR_VAL_0", 31, 16, False),
        ("SRT_COUNT", "DIAG_CNTR_VAL_0", 7, 8, False),
        ("UTTR_COUNT", "DIAG_CNTR_VAL_1", 31, 16, False),
        ("URTR_COUNT", "DIAG_CNTR_VAL_1", 15, 16, False),
        # monitor ADC channels defined here - the poll period will need to be set
        #   during camera initialization (x98)
        ("MON_CH1", "ADC5_DATA_1", 11, 12, False),
        ("MON_CH2", "ADC5_DATA_1", 23, 12, False),
        ("MON_CH3", "ADC5_DATA_2", 11, 12, False),
        ("MON_CH4", "ADC5_DATA_2", 23, 12, False),
        ("MON_CH5", "ADC5_DATA_3", 11, 12, False),
        ("MON_CH6", "ADC5_DATA_3", 23, 12, False),
        ("MON_CH7", "ADC5_DATA_4", 11, 12, False),
        ("MON_CH8", "ADC5_DATA_4", 23, 12, False),
        ("MON_CH9", "ADC6_DATA_1", 11, 12, False),
        ("MON_CH10", "ADC6_DATA_1", 23, 12, False),
        ("MON_CH11", "ADC6_DATA_2", 11, 12, False),
        ("MON_CH12", "ADC6_DATA_2", 23, 12, False),
        ("MON_CH13", "ADC6_DATA_3", 11, 12, False),
        ("MON_CH14", "ADC6_DATA_3", 23, 12, False),
        ("MON_CH15", "ADC6_DATA_4", 11, 12, False),
        ("MON_CH16", "ADC6_DATA_4", 23, 12, False),
    ]

    dummySensorVals = [
        [
            32767,
            32767,
            32767,
            32767,
            32767,
            30311,
            27555,
            24868,
            2960,
            5799,
            8581,
            11351,
            14105,
            16787,
            19559,
            22230,
        ],
        [
            2962,
            5790,
            8581,
            11341,
            14087,
            16851,
            19521,
            22134,
            32767,
            32767,
            32767,
            32767,
            32767,
            30291,
            27567,
            24915,
        ],
    ]

    def __init__(self, camassem):
        self.ca = camassem
        self.logcrit = self.ca.logcritbase + "[LLNL_v4] "
        self.logerr = self.ca.logerrbase + "[LLNL_v4] "
        self.logwarn = self.ca.logwarnbase + "[LLNL_v4] "
        self.loginfo = self.ca.loginfobase + "[LLNL_v4] "
        self.logdebug = self.ca.logdebugbase + "[LLNL_v4] "
        logging.info(self.loginfo + "Iinitializing board object")
        self.VREF = 3.3  # must be supplied externally for ADC128S102
        self.ADC5_mult = 1

        # ADC128S102; False => monitor range runs 0 to monmax, True => +/- monmax
        self.ADC5_bipolar = False
        self.rs422_baud = 921600
        self.rs422_cmd_wait = 0.3

        fpgaNum_pkt = Packet(cmd="1", addr=self.registers["FPGA_NUM"])
        fpgaRev_pkt = Packet(cmd="1", addr=self.registers["FPGA_REV"])

        _, _ = self.ca.sendCMD(fpgaNum_pkt)  # dummy duplicate call
        err, rval = self.ca.sendCMD(fpgaNum_pkt)
        self.ca.FPGANum = rval[8:16]

        err, rval = self.ca.sendCMD(fpgaRev_pkt)
        self.ca.FPGAVersion = rval[8:16]

        self.defoff = 34.5  # default pressure sensor offset
        self.defsens = 92.5  # default pressure sensor sensitivity

        # map channels to signal names for abstraction at the camera assembler level;
        #   each requires a corresponding entry in 'subregisters'
        if self.ca.sensorname == "icarus" or self.ca.sensorname == "icarus2":
            self.subreg_aliases = OrderedDict(
                {
                    "HST_A_PDELAY": "DACA",
                    "HST_A_NDELAY": "DACB",
                    "HST_B_PDELAY": "DACC",
                    "HST_B_NDELAY": "DACD",
                    "HST_RO_IBIAS": "DACE",
                    "HST_RO_NC_IBIAS": "DACE",
                    "HST_OSC_CTL": "DACF",
                    "VAB": "DACG",
                    "VRST": "DACH",
                    "MON_PRES_MINUS": "MON_CH1",
                    "MON_PRES_PLUS": "MON_CH2",
                    "MON_TEMP": "MON_CH3",
                    "MON_COL_TOP_IBIAS_IN": "MON_CH4",
                    "MON_HST_OSC_R_BIAS": "MON_CH5",
                    "MON_VAB": "MON_CH6",
                    "MON_HST_RO_IBIAS": "MON_CH7",
                    "MON_HST_RO_NC_IBIAS": "MON_CH7",
                    "MON_VRST": "MON_CH8",
                    "MON_COL_BOT_IBIAS_IN": "MON_CH9",
                    "MON_HST_A_PDELAY": "MON_CH10",
                    "MON_HST_B_NDELAY": "MON_CH11",
                    "DOSIMETER": "MON_CH12",
                    "MON_HST_OSC_VREF_IN": "MON_CH13",
                    "MON_HST_B_PDELAY": "MON_CH14",
                    "MON_HST_OSC_CTL": "MON_CH15",
                    "MON_HST_A_NDELAY": "MON_CH16",
                    "MON_CHA": "MON_CH10",
                    "MON_CHB": "MON_CH16",
                    "MON_CHC": "MON_CH14",
                    "MON_CHD": "MON_CH11",
                    "MON_CHE": "MON_CH7",
                    "MON_CHF": "MON_CH15",
                    "MON_CHG": "MON_CH6",
                    "MON_CHH": "MON_CH8",
                }
            )
            # Read-only; identifies controls corresponding to monitors
            self.monitor_controls = OrderedDict(
                {
                    "MON_CH10": "DACA",
                    "MON_CH16": "DACB",
                    "MON_CH14": "DACC",
                    "MON_CH11": "DACD",
                    "MON_CH7": "DACE",
                    "MON_CH15": "DACF",
                    "MON_CH6": "DACG",
                    "MON_CH8": "DACH",
                }
            )
        else:  # Daedalus
            self.subreg_aliases = OrderedDict(
                {
                    "HST_OSC_VREF_IN": "DACC",
                    "HST_OSC_CTL": "DACE",
                    "COL_TST_IN": "DACF",
                    "VAB": "DACG",
                    "MON_PRES_MINUS": "MON_CH1",
                    "MON_PRES_PLUS": "MON_CH2",
                    "MON_TEMP": "MON_CH3",
                    "MON_VAB": "MON_CH6",
                    "MON_HST_OSC_CTL": "MON_CH7",
                    "MON_TSENSE_OUT": "MON_CH10",
                    "MON_BGREF": "MON_CH11",
                    "DOSIMETER": "MON_CH12",
                    "MON_HST_RO_NC_IBIAS": "MON_CH13",
                    "MON_HST_OSC_VREF_IN": "MON_CH14",
                    "MON_COL_TST_IN": "MON_CH15",
                    "MON_HST_OSC_PBIAS_PAD": "MON_CH16",
                    "MON_CHC": "MON_CH14",
                    "MON_CHE": "MON_CH7",
                    "MON_CHF": "MON_CH15",
                    "MON_CHG": "MON_CH6",
                }
            )
            # Read-only; identifies controls corresponding to monitors
            self.monitor_controls = OrderedDict(
                {
                    "MON_CH14": "DACC",
                    "MON_CH7": "DACE",
                    "MON_CH15": "DACF",
                    "MON_CH6": "DACG",
                }
            )
        self.subreglist = []
        for s in self.subregisters:
            self.subreglist.append(s[0].upper())
            sr = SubRegister(
                self,
                name=s[0].upper(),
                register=s[1].upper(),
                start_bit=s[2],
                width=s[3],
                writable=s[4],
            )
            setattr(self, s[0].upper(), sr)

        # set voltage ranges for all DACs - WARNING: actual output voltage limited to
        #   external supply (3.3 V)
        # setpot('potx', n) will generate 3.3 V for all n > .66
        for n in range(0, 8):
            potname = "DAC" + string.ascii_uppercase[n]
            potobj = getattr(self, potname)
            potobj.minV = 0
            potobj.maxV = 5  #
            potobj.resolution = (
                1.0 * potobj.maxV - potobj.minV
            ) / potobj.max_value  # 76 uV / LSB

    def initBoard(self):
        """
        Register and reset board, set up firmware for sensor

        Returns:
            tuple (error string, response string) from final control message
        """
        logging.info(self.loginfo + "initBoard")
        control_messages = []
        self.clearStatus()
        self.configADCs()
        return self.ca.submitMessages(control_messages, " initBoard: ")

    def initPots(self):
        """
        Dummy function; initial DAC values are set by firmware at startup

        Returns:
            tuple (empty string, empty string)
        """
        return "", ""

    def latchPots(self):
        """
        Latch DAC settings into sensor

        Returns:
            tuple (error string, response string) from final control message
        """
        logging.info(self.loginfo + "latchPots")
        control_messages = [
            ("DAC_CTL", "00000001"),  # latches register settings for DACA
            ("DAC_CTL", "00000003"),
            ("DAC_CTL", "00000005"),
            ("DAC_CTL", "00000007"),
            ("DAC_CTL", "00000009"),
            ("DAC_CTL", "0000000B"),
            ("DAC_CTL", "0000000D"),
            ("DAC_CTL", "0000000F"),
        ]
        return self.ca.submitMessages(control_messages, " latchPots: ")

    def initSensor(self):
        """
        Register sensor, set default timing settings

        Returns:
            tuple (error string, response string) from final control message
        """
        logging.info(self.loginfo + "initSensor")
        if self.ca.FPGANum[7] is not self.ca.sensor.fpganumID:
            logging.warning(
                self.logwarn + "unable to confirm sensor compatibility with FPGA"
            )
        self.registers.update(self.ca.sensor.sens_registers)
        self.subregisters.extend(self.ca.sensor.sens_subregisters)
        for s in self.ca.sensor.sens_subregisters:
            sr = SubRegister(
                self,
                name=s[0].upper(),
                register=s[1].upper(),
                start_bit=s[2],
                width=s[3],
                writable=s[4],
            )
            setattr(self, s[0].upper(), sr)
            self.subreglist.append(s[0])
        # self.ca.checkSensorVoltStat() # SENSOR_VOLT_STAT and SENSOR_VOLT_CTL are
        #   deactivated for v4 icarus and daedalus firmware for now.
        control_messages = self.ca.sensorSpecific() + [
            # ring w/caps=01, relax=00, ring w/o caps = 02
            ("FPA_OSCILLATOR_SEL_ADDR", "00000000"),
            ("FPA_DIVCLK_EN_ADDR", "00000001"),
        ]
        return self.ca.submitMessages(control_messages, " initSensor: ")

    def configADCs(self):
        """
        Sets default ADC configuration (does not latch settings)

        Returns:
            tuple (error string, response string) from final control message
        """
        logging.info(self.loginfo + "configADCs")

        control_messages = [
            # just in case ADC_RESET was set on any of the ADCs (pull all ADCs out of
            #   reset)
            ("ADC_RESET", "00000000"),
            ("ADC1_CONFIG_DATA", "FFFFFFFF"),
            ("ADC2_CONFIG_DATA", "FFFFFFFF"),
            ("ADC3_CONFIG_DATA", "FFFFFFFF"),
            ("ADC4_CONFIG_DATA", "FFFFFFFF"),
            ("ADC_CTL", "FFFFFFFF"),
            ("ADC1_CONFIG_DATA", "81A801FF"),  # ext Vref 1.25V
            ("ADC2_CONFIG_DATA", "81A801FF"),  # ext Vref 1.25V
            ("ADC3_CONFIG_DATA", "81A801FF"),  # ext Vref 1.25V
            ("ADC4_CONFIG_DATA", "81A801FF"),  # ext Vref 1.25V
        ]
        return self.ca.submitMessages(control_messages, " configADCs: ")

    def softReboot(self):
        """
        Perform software reboot of board. WARNING: board reboot will likely prevent
          correct response and therefore will generate an error message

        Returns:
            tuple (error string, response string) from final control message
        """
        logging.info(self.loginfo + "reboot")
        control_messages = [("RESET", "0")]
        return self.ca.submitMessages(control_messages, " disarm: ")

    def disarm(self):
        """
        Takes camera out of trigger wait state. Has no effect if camera is not in wait
          state.

        Returns:
            tuple (error string, response string) from final control message
        """
        logging.info(self.loginfo + "disarm")
        self.ca.clearStatus()
        self.ca.armed = False
        control_messages = [
            ("HW_TRIG_EN", "0"),
            ("DUAL_EDGE_TRIG_EN", "0"),
            ("SW_TRIG_EN", "0"),
        ]
        self.ca.comms.skipError = False
        return self.ca.submitMessages(control_messages, " disarm: ")

    def startCapture(self, mode="Hardware"):
        """
        Reads ADC data into SRAM

        Returns:
            tuple (error string, response string) from final control message
        """
        logging.info(self.loginfo + "startCapture")
        if self.ca.sensmanual:
            timingReg = "MANSHUT_MODE"
        else:
            timingReg = "HST_MODE"

        if mode.upper() == "SOFTWARE":
            trigmess = [
                ("HW_TRIG_EN", "0"),
                ("DUAL_EDGE_TRIG_EN", "0"),
                ("SW_TRIG_EN", "1"),
                ("SW_TRIG_START", "1"),
            ]
        elif mode.upper() == "DUAL":
            trigmess = [
                ("SW_TRIG_EN", "0"),
                ("HW_TRIG_EN", "1"),
                ("DUAL_EDGE_TRIG_EN", "1"),
            ]
        else:  # HARDWARE
            trigmess = [
                ("DUAL_EDGE_TRIG_EN", "0"),
                ("SW_TRIG_EN", "0"),
                ("HW_TRIG_EN", "1"),
            ]

        control_messages = [
            ("ADC_CTL", "0000000F"),  # configure all ADCs
            (timingReg, "1"),
        ]

        control_messages.extend(trigmess)
        return self.ca.submitMessages(control_messages, " startCapture: ")

    def readSRAM(self):
        """
        Start readoff of SRAM

        Returns:
            tuple (error string, response string from register set)
        """
        logging.info(self.loginfo + "readSRAM")
        control_messages = [("READ_SRAM", "1")]
        return self.ca.submitMessages(control_messages, " readSRAM: ")

    def waitForSRAM(self, timeout):
        """
        Wait until subreg 'SRAM_READY' flag is true or timeout is exceeded;
          timeout = None or zero means wait indefinitely

        Args:
            timeout - time in seconds before readoff proceeds automatically without
              waiting for SRAM_READY flag

        Returns:
            error string
        """
        logging.info(self.loginfo + "waitForSRAM")
        waiting = True
        starttime = time.time()
        err = ""
        while waiting:
            err, status = self.ca.getSubregister("SRAM_READY")
            if err:
                err = self.logerr + "error in register read: " + err + " (waitForSRAM)"
                logging.error(err)
            if int(status):
                waiting = False
                logging.info(self.loginfo + "SRAM ready")
            if self.ca.abort:
                waiting = False
                logging.info(self.loginfo + "readoff aborted by user")
                self.ca.abort = False
            if timeout and time.time() - starttime > timeout:
                err += self.logerr + "SRAM timeout; proceeding with download attempt"
                logging.error(err)
                return err

        return err

    def getTimer(self):
        """
        Read value of on-board timer

        Returns:
            timer value as integer
        """
        err, rval = self.ca.getRegister("TIMER_VALUE")
        if err:
            logging.error(
                self.logerr + "unable to retrieve timer information (getTimer), "
                'returning "0" '
            )
            return 0
        return int(rval, 16)

    def resetTimer(self):
        """
        Reset on-board timer

        Returns:
            tuple (error string, response string from register set)
        """
        logging.info(self.loginfo + "resetTimer")
        control_messages = [("RESET_TIMER", "1"), ("RESET_TIMER", "0")]
        return self.ca.submitMessages(control_messages, " resetTimer: ")

    def enableLED(self, status):
        """
        Dummy function; feature is not implemented on Icarus

        Returns:
            tuple: dummy of (error string, response string from subregister set)
        """
        return "", "0"

    def setLED(self, LED, status):
        """
        Dummy function; feature is not implemented on Icarus

        Returns:
            tuple: dummy of (error string, response string from subregister set)
        """
        return "", "0"

    def setPowerSave(self, status):
        """
        Select powersave option

        Args:
            status: setting for powersave option (1 is enabled)

        Returns:
            tuple (error string, response string from subregister set)
        """
        if status:
            status = 1
        return self.ca.setSubregister("POWERSAVE", str(status))

    def setPPER(self, time):
        """
        Set polling period for ADCs.
        Args:
            time: milliseconds, between 1 and 255; defaults to 50

        Returns:
            tuple (error string, response string from subregister set OR invalid time
              setting string)
        """
        if not time:
            time = 50
        if not isinstance(time, int) or time < 1 or time > 255:
            err = (
                self.logerr + "invalid poll period submitted. Setting remains "
                "unchanged. "
            )
            logging.error(err)
            return err, str(time)
        else:
            binset = bin(time)[2:].zfill(8)
            return self.ca.setSubregister("PPER", binset)

    def getTemp(self, scale):
        """
        Read temperature sensor
        Args:
            scale: temperature scale to report (defaults to C, options are F and K)

        Returns:
            temperature as float on given scale
        """
        err, rval = self.ca.getMonV("MON_TEMP", errflag=True)
        if err:
            logging.error(
                self.logerr + "unable to retrieve temperature information ("
                'getTemp), returning "0" '
            )
            return 0.0
        ctemp = rval * 1000 - 273.15
        if scale == "K":
            temp = ctemp + 273.15
        elif scale == "F":
            temp = 1.8 * ctemp + 32
        else:
            temp = ctemp
        return temp

    def getPressure(self, offset, sensitivity, units):
        """
        Read pressure sensor. Uses default offset and sensitivity defined in init
          function unless alternatives are specified. NOTE: to reset defaults, reassign
          board.defoff and board.defsens explicitly

        Args:
            offset: non-default offset in mv/V
            sensitivity: non-default sensitivity in mV/V/span
            units: units to report pressure (defaults to Torr, options are psi, bar,
              inHg, atm)

        Returns:
            Pressure as float in chosen units, defaults to torr
        """

        if offset is None:
            offset = self.defoff
        if sensitivity is None:
            sensitivity = self.defsens
        if units is None:
            units = "torr"

        pplus = self.ca.getMonV("MON_PRES_PLUS")
        pminus = self.ca.getMonV("MON_PRES_MINUS")
        delta = 1000 * (pplus - pminus)
        ratio = sensitivity / 30  # nominal =  21  / 30
        psi = (delta - offset) / ratio
        if units.lower() == "psi":
            press = psi
        elif units.lower() == "bar":
            press = psi / 14.504
        elif units.lower() == "atm":
            press = psi / 14.695
        elif units.lower() == "inHg":
            press = psi * 2.036
        else:
            press = 51.715 * psi  # default to Torr

        return press

    def clearStatus(self):
        """
        Check status registers to clear them

        Returns:
            error string
        """
        err1, rval = self.ca.getRegister("STAT_REG_SRC")
        err2, rval = self.ca.getRegister("STAT_REG2_SRC")
        err = err1 + err2
        if err:
            logging.error(self.logerr + "clearStatus failed")
        return err

    def checkStatus(self):
        """
        Check status register, convert to reverse-order bit stream (i.e., bit 0 is
          statusbits[0])

        Returns:
            bit string (no '0b') in reversed order
        """
        err, rval = self.ca.getRegister("STAT_REG")
        rvalbits = bin(int(rval, 16))[2:].zfill(32)
        statusbits = rvalbits[::-1]
        return statusbits

    def checkStatus2(self):
        """
        Check second status register, convert to reverse-order bit stream (i.e., bit 0
          is statusbits[0])

        Returns: bit string (no '0b') in reversed order
        """
        err, rval = self.ca.getRegister("STAT_REG2")
        rvalbits = bin(int(rval, 16))[2:].zfill(6)
        statusbits = rvalbits[::-1]
        return statusbits

    def reportStatus(self):
        """
        Check contents of status register, print relevant messages
        """
        statusbits = self.checkStatus()
        statusbits2 = self.checkStatus2()
        print("Status report:")
        print("-------------")
        if int(statusbits[0]):
            print("Sensor read complete")
        if int(statusbits[1]):
            print("Coarse trigger detected")
        if int(statusbits[2]):
            print("Fine trigger detected")
        if int(statusbits[3]):
            print("W3_Top_L_Edge1 detected")
        if int(statusbits[4]):
            print("W3_Top_R_Edge1 detected")
        if int(statusbits[5]):
            print("Sensor readout in progress")
        if int(statusbits[6]):
            print("Sensor readout complete")
        if int(statusbits[7]):
            print("SRAM readout started")
        if int(statusbits[8]):
            print("SRAM readout complete")
        if int(statusbits[9]):
            print("High-speed timing configured")
        if int(statusbits[10]):
            print("All ADCs configured")
        if int(statusbits[11]):
            print("All DACs configured")
        if int(statusbits[12]):
            print("HST_All_W_En detected")
        if int(statusbits[13]):
            print("Timer has reset")
        if int(statusbits[14]):
            print("Camera is Armed")
        temp = int(statusbits[23:16:-1], 2) * 3.3 * 1000 / 4096
        print("Temperature reading: " + "{0:1.2f}".format(temp) + " C")
        press = int(statusbits[:23:-1], 2) * 3.3 * 1000 / 4096
        print("Pressure sensor reading: " + "{0:1.2f}".format(press) + " mV")
        if int(statusbits2[0]):
            print("FPA_IF_TO")
        if int(statusbits2[1]):
            print("SRAM_RO_TO")
        if int(statusbits2[2]):
            print("PixelRd Timeout Error")
        if int(statusbits2[3]):
            print("UART_TX_TO_RST")
        if int(statusbits2[4]):
            print("UART_RX_TO_RST")
        if int(statusbits2[5]):
            print("PDBIAS Unready")
        print("-------------")

    def reportEdgeDetects(self):
        """
        Report edge detects
        """
        err, rval = self.ca.getRegister("STAT_EDGE_DETECTS")
        # shift to left to fake missing edge detect
        edgebits = bin(int(rval, 16) << 1)[2:].zfill(32)
        # reverse to get order matching assignment
        bitsrev = edgebits[::-1]
        detdict = {}
        bitidx = 0
        for frame in range(4):
            for vert in ("TOP", "BOT"):
                for edge in range(1, 3):
                    for hor in ("L", "R"):
                        detname = (
                            "W"
                            + str(frame)
                            + "_"
                            + vert
                            + "_"
                            + hor
                            + "_EDGE"
                            + str(edge)
                        )
                        detdict[detname] = bitsrev[bitidx]
                        bitidx += 1
        # remove faked detect
        del detdict["W0_TOP_L_EDGE1"]
        print("Edge detect report:")
        print("-------------")
        for key, val in detdict.items():
            print(key + ": " + val)
        print("-------------")

    def dumpStatus(self):
        """
        Create dictionary of status values, DAC settings, monitor values, and register
          values

        Returns:
            dictionary of system diagnostic values
        """
        statusbits = self.checkStatus()
        statusbits2 = self.checkStatus2()

        temp = int(statusbits[23:16:-1], 2) * 3.3 * 1000 / 4096
        press = int(statusbits[:23:-1], 2) * 3.3 * 1000 / 4096

        statDict = OrderedDict(
            {
                "Temperature sensor reading": "{0:1.2f}".format(temp) + " C",
                "Pressure reading": str(round(self.ca.getPressure(), 3)) + " Torr",
                "Pressure sensor reading": "{0:1.2f}".format(press) + " mV",
                "Sensor read complete": str(statusbits[0]),
                "Coarse trigger detected": str(statusbits[1]),
                "Fine trigger detected": str(statusbits[2]),
                "W3_Top_L_Edge1 detected": str(statusbits[3]),
                "W3_Top_R_Edge1 detected": str(statusbits[4]),
                "Sensor readout in progress": str(statusbits[5]),
                "Sensor readout complete": str(statusbits[6]),
                "SRAM readout started": str(statusbits[7]),
                "SRAM readout complete": str(statusbits[8]),
                "High-speed timing configured": str(statusbits[9]),
                "All ADCs configured": str(statusbits[10]),
                "All DACs configured": str(statusbits[11]),
                "HST_All_W_En detected": str(statusbits[12]),
                "Timer has reset": str(statusbits[13]),
                "Camera is Armed": str(statusbits[14]),
                "FPA_IF_TO": str(statusbits2[0]),
                "SRAM_RO_TO": str(statusbits2[1]),
                "PixelRd Timeout Error": str(statusbits2[2]),
                "UART_TX_TO_RST": str(statusbits2[3]),
                "UART_RX_TO_RST": str(statusbits2[4]),
                "PDBIAS Unready": str(statusbits2[5]),
            }
        )

        DACDict = OrderedDict()
        MonDict = OrderedDict()
        for entry in self.subreg_aliases:
            if self.subreg_aliases[entry][0] == "D":
                val = str(round(self.ca.getPotV(entry), 3)) + " V"
                DACDict["DAC_" + entry] = val
            else:
                val = str(round(self.ca.getMonV(entry), 3)) + " V"
                MonDict[entry] = val

        regDict = OrderedDict()
        for key in self.registers.keys():
            err, rval = self.ca.getRegister(key)
            regDict[key] = rval

        dumpDict = OrderedDict()
        for x in [statDict, MonDict, DACDict, regDict]:
            dumpDict.update(x)
        return dumpDict


"""
Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.
"""
