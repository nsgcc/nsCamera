# -*- coding: utf-8 -*-
"""
The LLNLv1 board is defined here, including monitors, pots, and other board-specific
  settings

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
import time
from collections import OrderedDict

from nsCamera.utils.Packet import Packet
from nsCamera.utils.Subregister import SubRegister


class llnl_v1:
    """
    Livermore LLNL v1.0 board

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
            "STAT_REG": "024",
            "CTRL_REG": "025",
            "POT_CTL": "026",
            "POT_REG4_TO_1": "027",
            "POT_REG8_TO_5": "028",
            "POT_REG12_TO_9": "029",
            "POT_REG13": "02A",
            "LED_GP": "02B",
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
            "FRAME_ORDER_SEL": "04B",
            "SENSOR_VOLT_STAT": "082",
            "SENSOR_VOLT_CTL": "083",
            "ADC_CTL": "090",
            "ADC1_CONFIG_DATA": "091",
            "ADC2_CONFIG_DATA": "092",
            "ADC3_CONFIG_DATA": "093",
            "ADC4_CONFIG_DATA": "094",
            "ADC5_CONFIG_DATA": "095",
            "ADC5_DATA_1": "096",
            "ADC5_DATA_2": "097",
            "ADC5_DATA_3": "098",
            "ADC5_DATA_4": "099",
            "ADC5_PPER": "09A",
            "ADC_STANDBY": "09B",  # board version <= AD
            "ADC_RESET": "09B",  # board version > AD
            "TEMP_SENSE_PPER": "0A0",
            "TEMP_SENSE_DATA": "0A1",
        }
    )

    subregisters = [
        ## R/W subregs
        # Consistent with ICD usage, start_bit is msb eg, for [7..0] start_bit is 7.
        #   This can cause confusion because the string indices increase left to right
        #   (subreg name, register name, start bit, width, writable)
        ("HST_MODE", "HS_TIMING_CTL", 0, 1, True),
        ("SW_TRIG_START", "SW_TRIGGER_CONTROL", 0, 1, True),
        ("LED_EN", "CTRL_REG", 1, 1, True),
        ("COLQUENCHEN", "CTRL_REG", 2, 1, True),
        ("POWERSAVE", "CTRL_REG", 3, 1, True),
        ("POT1", "POT_REG4_TO_1", 7, 8, True),
        ("POT2", "POT_REG4_TO_1", 15, 8, True),
        ("POT3", "POT_REG4_TO_1", 23, 8, True),
        ("POT4", "POT_REG4_TO_1", 31, 8, True),
        ("POT5", "POT_REG8_TO_5", 7, 8, True),
        ("POT6", "POT_REG8_TO_5", 15, 8, True),
        ("POT7", "POT_REG8_TO_5", 23, 8, True),
        ("POT8", "POT_REG8_TO_5", 31, 8, True),
        ("POT9", "POT_REG12_TO_9", 7, 8, True),
        ("POT10", "POT_REG12_TO_9", 15, 8, True),
        ("POT11", "POT_REG12_TO_9", 23, 8, True),
        ("POT12", "POT_REG12_TO_9", 31, 8, True),
        ("POT13", "POT_REG13", 7, 8, True),
        ("LED1", "LED_GP", 0, 1, True),
        ("LED2", "LED_GP", 1, 1, True),
        ("LED3", "LED_GP", 2, 1, True),
        ("LED4", "LED_GP", 3, 1, True),
        ("LED5", "LED_GP", 4, 1, True),
        ("LED6", "LED_GP", 5, 1, True),
        ("LED7", "LED_GP", 6, 1, True),
        ("LED8", "LED_GP", 7, 1, True),
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
        ("ADC5_VREF", "ADC5_CONFIG_DATA", 9, 10, True),
        ("ADC5_VREF3", "ADC5_CONFIG_DATA", 13, 1, True),
        ("ADC5_INT", "ADC5_CONFIG_DATA", 15, 1, True),
        ("ADC5_MULT", "ADC5_CONFIG_DATA", 24, 6, True),
        ("PPER", "ADC5_PPER", 7, 8, True),
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
        ("STAT_POTSCONFIGURED", "STAT_REG", 11, 1, False),
        ("STAT_TIMERCOUNTERRESET", "STAT_REG", 13, 1, False),
        ("STAT_ARMED", "STAT_REG", 14, 1, False),
        ("STAT_TEMP", "STAT_REG", 27, 11, False),
        ("STAT_PRESS", "STAT_REG", 31, 4, False),
        ("FPA_IF_TO", "STAT_REG2", 0, 1, False),
        ("SRAM_RO_TO", "STAT_REG2", 1, 1, False),
        ("PIXELRD_TOUT_ERR", "STAT_REG2", 2, 1, False),
        ("UART_TX_TO_RST", "STAT_REG2", 3, 1, False),
        ("UART_RX_TO_RST", "STAT_REG2", 4, 1, False),
        ("SENSOR_POSN", "SENSOR_VOLT_STAT", 0, 1, False),
        ("SENSOR_NEGP", "SENSOR_VOLT_STAT", 1, 1, False),
        ("ICARUS_DET", "SENSOR_VOLT_STAT", 2, 1, False),
        ("DAEDALUS_DET", "SENSOR_VOLT_STAT", 3, 1, False),
        ("HORUS_DET", "SENSOR_VOLT_STAT", 4, 1, False),
        ("SENSOR_POWER", "SENSOR_VOLT_STAT", 5, 1, False),
        ("FIT_COUNT", "DIAG_CNTR_VAL_0", 31, 16, False),
        ("SRT_COUNT", "DIAG_CNTR_VAL_0", 7, 8, False),
        ("UTTR_COUNT", "DIAG_CNTR_VAL_1", 31, 16, False),
        ("URTR_COUNT", "DIAG_CNTR_VAL_1", 15, 16, False),
        # monitor ADC channels defined here - the poll period will need to be set during
        #   camera initialization (x98)
        ("MON_CH2", "ADC5_DATA_1", 15, 16, False),
        ("MON_CH3", "ADC5_DATA_1", 31, 16, False),
        ("MON_CH4", "ADC5_DATA_2", 15, 16, False),
        ("MON_CH5", "ADC5_DATA_2", 31, 16, False),
        ("MON_CH6", "ADC5_DATA_3", 15, 16, False),
        ("MON_CH7", "ADC5_DATA_3", 31, 16, False),
        ("MON_CH8", "ADC5_DATA_4", 15, 16, False),
        ("MON_VRST", "ADC5_DATA_4", 31, 16, False),
    ]

    dummySensorVals = [  # nominal stripe values for dummy sensor
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
        self.logcrit = self.ca.logcritbase + "[LLNL_v1] "
        self.logerr = self.ca.logerrbase + "[LLNL_v1] "
        self.logwarn = self.ca.logwarnbase + "[LLNL_v1] "
        self.loginfo = self.ca.loginfobase + "[LLNL_v1] "
        self.logdebug = self.ca.logdebugbase + "[LLNL_v1] "
        logging.info(self.loginfo + "initializing board object")
        self.VREF = 2.5  # default
        self.ADC5_mult = 2  # monmax = 2 * VREF
        # False => monitor range runs 0 to monmax, True => +/- monmax
        self.ADC5_bipolar = True

        self.rs422_baud = 921600
        self.rs422_cmd_wait = 0.3

        fpgaNum_pkt = Packet(cmd="1", addr=self.registers["FPGA_NUM"])
        fpgaRev_pkt = Packet(cmd="1", addr=self.registers["FPGA_REV"])

        _, _ = self.ca.sendCMD(fpgaNum_pkt)  # dummy duplicate call
        err, rval = self.ca.sendCMD(fpgaNum_pkt)
        self.ca.FPGANum = rval[8:16]

        err, rval = self.ca.sendCMD(fpgaRev_pkt)
        self.ca.FPGAVersion = rval[8:16]

        # map channels to signal names for abstraction at the camera assembler level;
        #   each requires a corresponding entry in 'subregisters'
        if self.ca.sensorname == "icarus" or self.ca.sensorname == "icarus2":
            self.subreg_aliases = OrderedDict(
                {
                    "COL_BOT_IBIAS_IN": "POT1",
                    "HST_A_PDELAY": "POT2",
                    "HST_B_NDELAY": "POT3",
                    "HST_RO_IBIAS": "POT4",
                    "HST_OSC_VREF_IN": "POT5",
                    "HST_B_PDELAY": "POT6",
                    "HST_OSC_CTL": "POT7",
                    "HST_A_NDELAY": "POT8",
                    "COL_TOP_IBIAS_IN": "POT9",
                    "HST_OSC_R_BIAS": "POT10",
                    "VAB": "POT11",
                    "HST_RO_NC_IBIAS": "POT12",
                    "VRST": "POT13",
                    "MON_HST_A_PDELAY": "MON_CH2",
                    "MON_HST_B_NDELAY": "MON_CH3",
                    "MON_HST_RO_IBIAS": "MON_CH4",
                    "MON_HST_OSC_VREF_IN": "MON_CH5",
                    "MON_HST_B_PDELAY": "MON_CH6",
                    "MON_HST_OSC_CTL": "MON_CH7",
                    "MON_HST_A_NDELAY": "MON_CH8",
                }
            )
            # Read-only; identifies controls corresponding to monitors
            self.monitor_controls = OrderedDict(
                {
                    "MON_CH2": "POT2",
                    "MON_CH3": "POT3",
                    "MON_CH4": "POT4",
                    "MON_CH5": "POT5",
                    "MON_CH6": "POT6",
                    "MON_CH7": "POT7",
                    "MON_CH8": "POT8",
                    # Note: VRST is not measured across the pot; it will read a voltage
                    #   approximately 1 Volt lower than pot13's actual output
                    "MON_VRST": "POT13",
                }
            )
        else:  # Daedalus
            self.subreg_aliases = OrderedDict(
                {
                    "HST_OSC_CTL": "POT4",
                    "HST_RO_NC_IBIAS": "POT5",
                    "HST_OSC_VREF_IN": "POT6",
                    "VAB": "POT11",
                    "MON_TSENSEOUT": "MON_CH2",
                    "MON_BGREF": "MON_CH3",
                    "MON_HST_OSC_CTL": "MON_CH4",
                    "MON_HST_RO_NC_IBIAS": "MON_CH5",
                    "MON_HST_OSC_VREF_IN": "MON_CH6",
                    "MON_COL_TST_IN": "MON_CH7",
                    "MON_HST_OSC_PBIAS_PAD": "MON_CH8",
                }
            )
            # Read-only; identifies controls corresponding to monitors
            self.monitor_controls = OrderedDict(
                {
                    "MON_CH4": "POT4",
                    "MON_CH5": "POT5",
                    "MON_CH6": "POT6",
                    # Note: VRST is not measured across the pot; it will read a voltage
                    #   lower than pot13's actual output
                    "MON_VRST": "POT13",
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

        # set voltage ranges for all pots
        for n in range(1, 13):
            potname = "POT" + str(n)
            potobj = getattr(self, potname)
            potobj.minV = 0
            potobj.maxV = 3.3
            # resolution is approximately .0129 V / LSB
            potobj.resolution = (1.0 * potobj.maxV - potobj.minV) / potobj.max_value
        self.POT13.minV = 0
        self.POT13.maxV = 3.96
        # POT13 resolution is approximately .0155 V / LSB
        self.POT13.resolution = (
            1.0 * self.POT13.maxV - self.POT13.minV
        ) / self.POT13.max_value

    def initBoard(self):
        """
        Register and reset board, set up firmware for sensor

        Returns:
            tuple (error string, response string) from final control message
        """
        logging.info(self.loginfo + "initBoard")
        control_messages = [("LED_EN", "1")]

        self.clearStatus()
        self.configADCs()

        err, resp = self.ca.getSubregister("ADC5_VREF3")
        if err:
            logging.error(self.logerr + "unable to read 'ADC5_VREF3'")
        if int(resp, 2):  # check to see if Vref is 3 or 2.5 volts
            vrefmax = 3.0
        else:
            vrefmax = 2.5
        err, resp = self.ca.getSubregister("ADC5_VREF")
        if err:
            logging.error(self.logerr + "unable to read 'ADC5_VREF'")
        self.VREF = vrefmax * int(resp, 2) / 1024.0
        err, multmask = self.ca.getSubregister("ADC5_MULT")
        if err:
            logging.error(self.logerr + "unable to read 'ADC5_MULT'")
        if multmask[0] and multmask[1] and multmask[3] and multmask[5]:
            self.ADC5_mult = 2
        elif not (multmask[0] or multmask[1] or multmask[3] or multmask[5]):
            self.ADC5_mult = 4
        else:
            logging.error(self.logerr + "inconsistent mode settings on ADC5")
        return self.ca.submitMessages(control_messages, " initBoard: ")

    def initPots(self):
        """
        Configure default pot settings before image acquisition

        Returns:
            tuple (error string, response string) from final control message
        """
        logging.info(self.loginfo + "initPots")
        if self.ca.sensorname == "icarus" or self.ca.sensorname == "icarus2":
            err0, _ = self.ca.setPot("HST_A_PDELAY", 0, errflag=True)
            err1, _ = self.ca.setPotV("HST_B_NDELAY", 3.3, errflag=True)
            err2, _ = self.ca.setPotV("HST_RO_IBIAS", 2.5, tune=True, errflag=True)
            err3, _ = self.ca.setPotV("HST_OSC_VREF_IN", 2.9, tune=True, errflag=True)
            err4, _ = self.ca.setPot("HST_B_PDELAY", 0, errflag=True)
            err5, _ = self.ca.setPotV("HST_OSC_CTL", 1.45, tune=True, errflag=True)
            err6, _ = self.ca.setPotV("HST_A_NDELAY", 3.3, errflag=True)
            err7, _ = self.ca.setPotV("VAB", 0.5, errflag=True)
            err8, _ = self.ca.setPotV("HST_RO_NC_IBIAS", 2.5, errflag=True)
            err9, _ = self.ca.setPotV("VRST", 0.3, tune=True, errflag=True)
            err = err0 + err1 + err2 + err3 + err4 + err5 + err6 + err7 + err8 + err9
        else:  # Daedalus
            err0, _ = self.ca.setPotV("HST_OSC_CTL", 1.0, tune=True, errflag=True)
            err1, _ = self.ca.setPotV("HST_RO_NC_IBIAS", 1.0, errflag=True)
            err2, _ = self.ca.setPotV("HST_OSC_VREF_IN", 1.0, tune=True, errflag=True)
            err3, _ = self.ca.setPotV("VAB", 0.5, errflag=True)
            err = err0 + err1 + err2 + err3
        return err, ""

    def latchPots(self):
        """
        Latch pot settings into sensor

        Returns:
            tuple (error string, response string) from final control message
        """
        logging.info(self.loginfo + "latchPots")

        control_messages = [
            ("POT_CTL", "00000003"),  # latches register settings for pot 1
            ("POT_CTL", "00000005"),
            ("POT_CTL", "00000007"),
            ("POT_CTL", "00000009"),
            ("POT_CTL", "0000000B"),
            ("POT_CTL", "0000000D"),
            ("POT_CTL", "0000000F"),
            ("POT_CTL", "00000011"),
            ("POT_CTL", "00000013"),
            ("POT_CTL", "00000015"),
            ("POT_CTL", "00000017"),
            ("POT_CTL", "00000019"),
            ("POT_CTL", "0000001B"),
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
            logging.error(
                self.logerr + "unable to confirm sensor compatibility with FPGA"
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
        self.ca.checkSensorVoltStat()
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
            # just in case ADC_RESET was set (pull all ADCs out # of reset)
            (
                "ADC_RESET",
                "00000000",
            ),
            # workaround for uncertain behavior after previous readoff
            (
                "ADC1_CONFIG_DATA",
                "FFFFFFFF",
            ),
            ("ADC2_CONFIG_DATA", "FFFFFFFF"),
            ("ADC3_CONFIG_DATA", "FFFFFFFF"),
            ("ADC4_CONFIG_DATA", "FFFFFFFF"),
            ("ADC_CTL", "FFFFFFFF"),
            ("ADC1_CONFIG_DATA", "81A801FF"),  # ext Vref 1.25V
            ("ADC2_CONFIG_DATA", "81A801FF"),  # ext Vref 1.25V
            ("ADC3_CONFIG_DATA", "81A801FF"),  # ext Vref 1.25V
            ("ADC4_CONFIG_DATA", "81A801FF"),  # ext Vref 1.25V
            ("ADC5_CONFIG_DATA", "81A883FF"),  # int Vref 2.50V
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
        control_messages = [("RESET", "1")]
        return self.ca.submitMessages(control_messages, " disarm: ")

    def disarm(self):
        """
        Takes camera out of trigger wait state. Has no effect if camera is not already
          in wait state.

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
            ("ADC_CTL", "0000001F"),  # configure all ADCs
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
                logging.error(
                    self.logerr + "error in register read: " + err + " (waitForSRAM)"
                )
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
        Enable/disable on-board LEDs

        Args:
            status: 0 for disabled, 1 for enabled

        Returns:
            tuple: (error string, response string from subregister set)
        """
        if status:
            status = 1
        return self.ca.setSubregister("LED_EN", str(status))

    def setLED(self, LED, status):
        """
        Illuminate on-board LED

        Args:
            LED: LED number (1-8)
            status: 0 is off, 1 is on

        Returns:
            tuple: (error string, response string from subregister set)
        """
        key = "LED" + str(LED)
        return self.ca.setSubregister(key, str(status))

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
            time: milliseconds, between 1 and 255, defaults to 50

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
        err, rval = self.ca.getRegister("TEMP_SENSE_DATA")
        if err:
            logging.error(
                self.logerr + "unable to retrieve temperature information ("
                'getTemp), returning "0" '
            )
            return 0.0

        ctemp = int(rval[-3:], 16) / 16.0
        if scale == "K":
            temp = ctemp + 273.15
        elif scale == "F":
            temp = 1.8 * ctemp + 32
        else:
            temp = ctemp
        return temp

    def getPressure(self, offset, sensitivity, units):
        """
        Read pressure sensor

        Currently unimplemented

        Returns:
            0 as float
        """
        logging.warning(
            "WARNING: [LLNL_v1] 'getPressure' is not implemented on the LLNLv1 board"
        )
        return 0.0

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
        if not rval:
            logging.error(
                self.logerr + "Unable to check status register (zeroes returned)"
            )
            rval = "0"
        rvalbits = bin(int(rval, 16))[2:].zfill(32)
        statusbits = rvalbits[::-1]
        return statusbits  # TODO: add error handling

    def checkStatus2(self):
        """
        Check second status register, convert to reverse-order bit stream (i.e., bit 0
          is statusbits[0])

        Returns: bit string (no '0b') in reversed order
        """
        err, rval = self.ca.getRegister("STAT_REG2")
        if not rval:
            logging.error(
                self.logerr + "Unable to check status register 2 (zeroes returned)"
            )
            rval = "0"
        rvalbits = bin(int(rval, 16))[2:].zfill(5)
        statusbits = rvalbits[::-1]
        return statusbits  # TODO: add error handling

    def reportStatus(self):
        """
        Check contents of status register, print relevant messages
        """
        statusbits = self.checkStatus()
        statusbits2 = self.checkStatus2()
        logging.info(self.loginfo + "Status report:")
        if int(statusbits[0]):
            logging.info(self.loginfo + "Sensor read complete")
        if int(statusbits[1]):
            logging.info(self.loginfo + "Coarse trigger detected")
        if int(statusbits[2]):
            logging.info(self.loginfo + "Fine trigger detected")
        if int(statusbits[5]):
            logging.info(self.loginfo + "Sensor readout in progress")
        if int(statusbits[6]):
            logging.info(self.loginfo + "Sensor readout complete")
        if int(statusbits[7]):
            logging.info(self.loginfo + "SRAM readout started")
        if int(statusbits[8]):
            logging.info(self.loginfo + "SRAM readout complete")
        if int(statusbits[9]):
            logging.info(self.loginfo + "High-speed timing configured")
        if int(statusbits[10]):
            logging.info(self.loginfo + "All ADCs configured")
        if int(statusbits[11]):
            logging.info(self.loginfo + "All pots configured")
        if int(statusbits[13]):
            logging.info(self.loginfo + "Timer has reset")
        if int(statusbits[14]):
            logging.info(self.loginfo + "Camera is Armed")
        self.ca.sensor.reportStatusSensor(statusbits)
        temp = int(statusbits[27:15:-1], 2) / 16.0
        logging.info(
            self.loginfo + "Temperature reading: " + "{0:1.2f}".format(temp) + " C"
        )
        press = int(statusbits[:27:-1], 2)
        logging.info(self.loginfo + "Pressure reading: " + "{0:1.2f}".format(press))
        if int(statusbits2[0]):
            logging.info(self.loginfo + "FPA_IF_TO")
        if int(statusbits2[1]):
            logging.info(self.loginfo + "INFO: [LLNL_v1] SRAM_RO_TO")
        if int(statusbits2[2]):
            logging.info(self.loginfo + "PixelRd Timeout Error")
        if int(statusbits2[3]):
            logging.info(self.loginfo + "UART_TX_TO_RST")
        if int(statusbits2[4]):
            logging.info(self.loginfo + "UART_RX_TO_RST")

    def reportEdgeDetects(self):
        """
        Unimplemented
        """
        logging.warning(
            self.logwarn + "'reportEdgeDetects' is not implemented on the LLNLv1 "
            "board "
        )

    def dumpStatus(self):
        """
        Create dictionary of status values, DAC settings, monitor values, and register
          values

        WARNING: the behavior of self-resetting subregisters may be difficult to predict
          and may generate contradictory results

        Returns:
            dictionary of system diagnostic values
        """
        statusbits = self.checkStatus()
        statusbits2 = self.checkStatus2()
        temp = self.ca.getTemp()

        statDict = OrderedDict(
            {
                "Temperature reading": "{0:1.2f}".format(temp) + " C",
                "Sensor read complete": str(statusbits[0]),
                "Coarse trigger detected": str(statusbits[1]),
                "Fine trigger detected": str(statusbits[2]),
                "Sensor readout in progress": str(statusbits[5]),
                "Sensor readout complete": str(statusbits[6]),
                "SRAM readout started": str(statusbits[7]),
                "SRAM readout complete": str(statusbits[8]),
                "High-speed timing configured": str(statusbits[9]),
                "All ADCs configured": str(statusbits[10]),
                "All pots configured": str(statusbits[11]),
                "HST_All_W_En detected": str(statusbits[12]),
                "Timer has reset": str(statusbits[13]),
                "Camera is Armed": str(statusbits[14]),
                "FPA_IF_TO": str(statusbits2[0]),
                "SRAM_RO_TO": str(statusbits2[1]),
                "PixelRd Timeout Error": str(statusbits2[2]),
                "UART_TX_TO_RST": str(statusbits2[3]),
                "UART_RX_TO_RST": str(statusbits2[4]),
            }
        )

        DACDict = OrderedDict()
        MonDict = OrderedDict()
        for entry in self.subreg_aliases:
            if self.subreg_aliases[entry][0] == "P":
                val = str(round(self.ca.getPotV(entry), 3)) + " V"
                DACDict["POT_" + entry] = val
            else:
                val = str(round(self.ca.getMonV(entry), 3)) + " V"
                MonDict[entry] = val

        regDict = OrderedDict()
        for key in self.registers.keys():
            err, rval = self.ca.getRegister(key)
            regDict[key] = rval

        dumpDict = OrderedDict()
        for x in [statDict, MonDict, POTDict, regDict]:
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
