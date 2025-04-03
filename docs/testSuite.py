# -*- coding: utf-8 -*-
"""
Test suite to exercise most CameraAssembler and board functions

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
import time
from collections import OrderedDict
import json
from nsCamera.CameraAssembler import CameraAssembler
from nsCamera.utils.misc import getEnter

"""
When run from the command line, testSuite accepts the following parameters:
    -b     	name of board: 'llnl_v1' or 'llnl_v4'; default='llnl_v4'
    -c     	name of comm: 'GigE' or 'RS422'; default='GigE'
    -s     	name of sensor: 'icarus', 'icarus2', or 'daedalus';	default='icarus2'
    -p     	specified port number; default=None
    -i     	specified ip address; default='192.168.1.100'
    -v      verbosity level; default=4
    --batch	run automatically without interaction
    --hw   	wait for hardware triggering  
"""


def testSuite(
    board, comm, sensor, portNum, ipAdd, interactive=True, swtrigger=True, verbose=4
):
    """
    Regression testing script to exercise cameraAssembler functions and camera features.
    Comment out entries in 'tests' list to skip component tests

    Args:
        board: board name for cameraAssembler
        comm: comm name for cameraAssembler
        sensor: sensor name for cameraAssembler
        portNum: (optional) port number
        ipAdd: (optional) ip address (e.g., '192.168.1.100')
        interactive: if False, does not wait for user input, skips some tests
        swtrigger: if True, uses software triggering, does not wait for external
          triggers
        verbose: verbosity level

    """
    # Comment out any tests you wish to skip. Irrelevant tests (e.g., Manual Timing if
    #   Daedalus sensor is attached) will be ignored
    # TODO: make this an input file?
    tests = [
        "HST acquisition",
        "SaveTiffs",
        "PlotFrames",
        "SplitFrames",
        "POT/DAC set & read",
        "SW Trigger",  # perform SW trigger test when HW triggering selected
        "Arm/Disarm",
        "HST setting",
        "Reinitialization",
        "PowerSave",
        "Timer",
        "Register R/W",
        "Register self-clear",
        "Status dump",
        "LED",
        "Manual Timing",  # Icarus only
        "HFW",  # Daedalus only
        "ZDT",  # Daedalus only
        "Interlacing",  # Daedalus only
    ]

    print("-Initial setup-")
    ca = CameraAssembler(
        commname=comm,
        boardname=board,
        sensorname=sensor,
        verbose=verbose,
        port=portNum,
        ip=ipAdd,
    )

    # simplify passing these parameters to functions
    ca.tests = tests
    ca.interactive = interactive
    ca.swtrigger = swtrigger

    if ca.boardname == "llnl_v1":
        ca.potsdacsconfigured = "STAT_POTSCONFIGURED"
    elif ca.boardname == "llnl_v4":
        ca.potsdacsconfigured = "STAT_DACSCONFIGURED"
    else:
        print("Invalid boardname, assuming LLNL_v4")
        ca.potsdacsconfigured = "STAT_DACSCONFIGURED"
        boardregs, boardselfclear, boardrestore = test_v4(ca)

    statusVerify(ca, [("STAT_TIMERCOUNTERRESET", 1)])

    if "PowerSave" in tests:
        powersave(ca)

    # ARM/DISARM
    if "Arm/Disarm" in tests:
        arm_disarm(ca)

    # HIGH SPEED TIMING & ACQUISITION
    if "HST setting" in tests:
        hst_setting(ca)

    # ca.setInterlacing(2)  # TODO: sensor-specific testing?

    if "HST acquisition" in tests:
        hst_acquisition(ca)

    # REINITIALIZATION
    if "Reinitialization" in tests and interactive:
        reinitialization(ca)

    if ca.sensorname == "icarus" or ca.sensorname == "icarus2":
        sensorregs = test_icarus(ca)
    elif ca.sensorname == "daedalus":
        sensorregs = test_daedalus(ca)
    else:
        print("Invalid sensorname, assuming Daedalus")
        sensorregs = test_daedalus(ca)

    if ca.boardname == "llnl_v1":
        boardregs, boardselfclear, boardrestore = test_v1(ca)
    elif ca.boardname == "llnl_v4":
        boardregs, boardselfclear, boardrestore = test_v4(ca)
    else:
        print("Invalid boardname, assuming LLNL_v4")
        boardregs, boardselfclear, boardrestore = test_v4(ca)
    
    
    # MISCELLANEOUS
    print("\n\n-Testing miscellaneous board features-")

    if "Timer" in tests:
        timer(ca)

    print("Temperature sensor reading: " + str(ca.getTemp()))
    time.sleep(1)

    if "POT/DAC set & read" in tests:
        potdacsetread(ca)

    if "Register self-clear" in tests:
        register_selfclear(boardrestore, boardselfclear, ca)
        
    if "Register R/W" in tests:
        registerRW(boardregs, boardrestore, ca, sensorregs)

    if "Status dump" in tests:
        statusDump(ca)

    ca.closeDevice()
    time.sleep(1)
    logging.info("Done")


def statusVerify(caObject, checklist):
    errs = 0
    for stat, flag in checklist:
        _, check = caObject.getSubregister(stat)
        if bool(int(check)) is not bool(flag):
            errs += 1
            print("+Error: " + stat + " is not " + str(bool(flag)))
    if not errs:
        print("+Status verify passed")


def powersave(caObject):
    print("\n-Testing PowerSave mode-")
    caObject.setPowerSave(1)
    statusVerify(caObject, [("POWERSAVE", 1)])
    caObject.setPowerSave(0)
    statusVerify(caObject, [("POWERSAVE", 0)])


def arm_disarm(ca):
    print("\n-Testing Arm-")
    # HST has to be set for arming to complete; tested separately later
    ca.setTiming("A", (2, 2))
    ca.setTiming("B", (2, 2))
    ca.arm()
    time.sleep(1)
    statusVerify(
        ca,
        [
            ("STAT_ADCSCONFIGURED", 1),
            (ca.potsdacsconfigured, 1),
            ("STAT_COARSE", 0),
            ("STAT_FINE", 0),
            ("STAT_ARMED", 1),
        ],
    )
    time.sleep(1)
    print("\n-Testing Disarm-")
    ca.disarm()
    statusVerify(ca, [("STAT_ARMED", 0)])
    time.sleep(1)


def hst_setting(caObject):
    print("\n-Testing high speed timing control-")
    errtemp = 0
    caObject.setTiming("A", (39, 1), 0)
    caObject.setTiming("B", (1, 1), 31)
    if ("A", 39, 1, 0) != caObject.getTiming("A"):
        errtemp = 1
    if ("B", 1, 1, 37) != caObject.getTiming("B"):
        errtemp = 1
    if errtemp:
        print("Error in setting high speed timing")
        errtemp = 0
    caObject.setTiming("A", (5, 2), 3)
    caObject.setTiming("B", (3, 4), 1)
    if ("A", 5, 2, 3) != caObject.getTiming("A"):
        errtemp = 1
    if ("B", 3, 4, 1) != caObject.getTiming("B"):
        errtemp = 1
    if errtemp:
        print("Error in setting high speed timing")
    caObject.setTiming("B", (10, 10), 0)
    time.sleep(1)
    print("The next few messages should include a warning about inter-frame timing:")
    time.sleep(1)
    caObject.setTiming("A", (9, 8), 1)
    print(
        "The next few messages should include a error message regarding timing "
        "sequence: "
    )
    time.sleep(1)
    caObject.setTiming("A", (15, 15), 15)
    statusVerify(caObject, [("STAT_HSTCONFIGDONE", 1), ("MANSHUT_MODE", 0)])
    time.sleep(1)


def hst_acquisition(caObject):
    print("\n-Testing HST acquisition-")
    checkArmStatus(caObject)
    armBoard(caObject)
    frames, datalen, data_err = caObject.readoff(waitOnSRAM=True)
    margin = 1600
    if data_err:
        print("+Error in acquisition!")
    else:
        print("+No error in acquisition reported")
    plottiffs(caObject, frames, label="hst_test")
    if "SplitFrames" in caObject.tests:
        print("\n-Testing split-frame (two column) feature-")
        armBoard(caObject)
        frames, datalen, data_err = caObject.readoff(waitOnSRAM=True, columns=2)
        plottiffs(caObject, frames, label="splitframe_test")

    if not caObject.swtrigger and "SW Trigger" in caObject.tests:
        print("\n-Testing HST acquisition with software trigger-")
        checkArmStatus(caObject)

        caObject.arm("Software")
        statusVerify(caObject, [("STAT_COARSE", 1), ("STAT_FINE", 1)])

        frames, datalen, data_err = caObject.readoff(waitOnSRAM=True)

        print("Data length: " + str(datalen) + " bytes")
        if data_err:
            print("+Error in acquisition!")
        else:
            print("+No error in acquisition reported")

        plottiffs(caObject, frames, label="SWtrig_test")


def checkArmStatus(caObject):
    caObject.arm()
    time.sleep(1)
    caObject.reportStatus()
    statusVerify(
        caObject,
        [
            ("STAT_ADCSCONFIGURED", 1),
            (caObject.potsdacsconfigured, 1),
            ("STAT_HSTCONFIGDONE", 1),
            ("MANSHUT_MODE", 0),
            ("STAT_COARSE", 0),
            ("STAT_FINE", 0),
        ],
    )


def armBoard(caObject):
    if caObject.swtrigger:
        print("Using software trigger")
        caObject.arm("Software")
        statusVerify(caObject, [("STAT_COARSE", 1), ("STAT_FINE", 1)])

    else:
        if caObject.interactive:
            caObject.arm()
            getEnter(
                "> Please initiate hardware trigger, then press ENTER to "
                "continue. <\n "
            )


def plottiffs(caObject, frames, label):
    if caObject.interactive:
        if "PlotFrames" in caObject.tests:
            print(
                "\nPlots of the acquired frames are being displayed. Please "
                "inspect to verify proper acquisition. "
                "\n> Close plots to continue <"
            )
            caObject.plotFrames(frames)
        if "SaveTiffs" in caObject.tests:
            caObject.saveTiffs(frames, filename=label)
            getEnter(
                "Tiff files of the acquired frames have been saved. Please "
                "inspect to verify correct saves. "
                "\n> Press ENTER to continue. <\n"
            )
    else:
        if "SaveTiffs" in caObject.tests:
            caObject.saveTiffs(frames, filename=label)
            print("Tiffs from" + label + " have been saved")


def reinitialization(caObject):
    time.sleep(1)
    caObject.setTiming("A", (2, 3), 4)
    caObject.setTiming("B", (5, 3), 1)
    time.sleep(1)
    getEnter(
        "\n-Testing reinitialization with high speed timing-\n>Please power-cycle "
        "the board, then press ENTER to continue <"
    )
    if caObject.powerCheck():
        print("\n+Loss of power WAS NOT detected")
    else:
        print("\n+Loss of power WAS detected")
    time.sleep(1)
    caObject.reinitialize()
    statusVerify(caObject, [("STAT_TIMERCOUNTERRESET", 1)])
    if ("A", 2, 3, 4) != caObject.getTiming("A") or (
        "B",
        5,
        3,
        1,
    ) != caObject.getTiming("B"):
        print("+High speed timing WAS NOT restored properly after reinitialization")
    else:
        print("+High speed timing WAS restored properly after reinitialization")


def test_icarus(caObject):
    print("\n# Icarus sensor-specific checks")

    if "Manual Timing" in caObject.tests:
        icarusManual(caObject)

    icarusregs = OrderedDict(
        {
            "VRESET_WAIT_TIME": "7FFFFFFF",
            "ICARUS_VER_SEL": "00000001",
            "MANUAL_SHUTTERS_MODE": "00000001",
            "W0_INTEGRATION": "03FFFFFF",
            "W0_INTERFRAME": "03FFFFFF",
            "W1_INTEGRATION": "03FFFFFF",
            "W1_INTERFRAME": "03FFFFFF",
            "W2_INTEGRATION": "03FFFFFF",
            "W2_INTERFRAME": "03FFFFFF",
            "W3_INTEGRATION": "03FFFFFF",
            "W0_INTEGRATION_B": "03FFFFFF",
            "W0_INTERFRAME_B": "03FFFFFF",
            "W1_INTEGRATION_B": "03FFFFFF",
            "W1_INTERFRAME_B": "03FFFFFF",
            "W2_INTEGRATION_B": "03FFFFFF",
            "W2_INTERFRAME_B": "03FFFFFF",
            "W3_INTEGRATION_B": "03FFFFFF",
            "MISC_SENSOR_CTL": "000001FF",  # TODO: does this break sensor operation?
            # "TIME_ROW_DCD": "FFFFFFFF",
        }
        # TODO: check TIME_ROW_DCD only if LLNL_v4TIME_ROW_DCD
    )

    if caObject.sensorname == "icarus":
        icarusregs["VRESET_HIGH_VALUE"] = "000000FF"

    return icarusregs


def icarusManual(caObject):
    # MANUAL TIMING & ACQUISITION
    print("\n-Testing manual shutter control-")
    caObject.setManualShutters(
        timing=[
            (100, 100, 100, 100, 100, 100, 100),
            (100, 100, 100, 100, 100, 100, 100),
        ]
    )
    statusVerify(caObject, [("MANSHUT_MODE", 1), ("STAT_HSTCONFIGDONE", 0)])
    print(
        "The next few messages should include two error messages about "
        "invalid timing sequences "
    )
    time.sleep(1)
    caObject.setManualShutters(timing=[(100, 100, 100, 100, 100, 100, 100)])
    caObject.setManualShutters(
        timing=[
            (10.5, 100, 100, 100, 100, 100, 100),
            (100, 100, 100, 100, 100, 100, 100),
        ]
    )
    time.sleep(1)
    print("\n-Testing manual shutter acquisition-")
    if caObject.swtrigger:
        print("Using software trigger")
        statusVerify(
            caObject,
            [
                ("STAT_ADCSCONFIGURED", 1),
                (caObject.potsdacsconfigured, 1),
                ("STAT_HSTCONFIGDONE", 0),
                ("MANSHUT_MODE", 1),
            ],
        )
        armBoard(caObject)
    else:
        caObject.arm()
        if caObject.interactive:
            getEnter(
                "> Please initiate hardware trigger, then press ENTER to "
                "continue. <\n "
            )
        else:
            print("Waiting for hardware trigger")
    frames, datalen, data_err = caObject.readoff(waitOnSRAM=True)
    print("Data length: " + str(datalen))
    if data_err:
        print("+Error in acquisition!")
    else:
        print("+No error in acquisition reported")
        plottiffs(caObject, frames, "msc_test")

    # REINITIALIZATION WITH MANUAL SHUTTERS
    if "Reinitialization" in caObject.tests and caObject.interactive:
        caObject.setManualShutters(
            timing=[
                (25, 50, 75, 100, 125, 150, 175),
                (175, 150, 125, 100, 75, 50, 25),
            ]
        )
        getEnter(
            "\n-Testing reinitialization with manual shutter control-\n> "
            "Please power-cycle the board, then press ENTER to continue <"
        )
        time.sleep(1)
        if caObject.powerCheck():
            print("\n+Loss of power WAS NOT detected")
        else:
            print("\n+Loss of power WAS detected")
        time.sleep(1)
        caObject.reinitialize()
        statusVerify(caObject, [("STAT_TIMERCOUNTERRESET", 1)])
        caObject.sensor.getManualTiming()
        if caObject.sensor.getManualTiming() != [
            [25, 50, 75, 100, 125, 150, 175],
            [175, 150, 125, 100, 75, 50, 25],
        ]:
            print("+Manual timing WAS NOT restored properly after " "reinitialization ")
        else:
            print("+Manual timing WAS restored properly after " "reinitialization ")


def test_daedalus(caObject):
    print("\n# Daedalus sensor-specific checks")

    if "HFW" in caObject.tests:
        hfwTest(caObject)
    if "ZDT" in caObject.tests:
        zdtTest(caObject)
    if "Interlacing" in caObject.tests:
        interlaceTest(caObject)

    daedalusregs = OrderedDict(
        {
            # TODO: should I include the enables here, or are they self-clearing?
            "HSTALLWEN_WAIT_TIME": "7FFFFFFF",
            "VRESET_HIGH_VALUE": "0000FFFF",
            "FRAME_ORDER_SEL": "00000007",
            "HST_TRIGGER_DELAY_DATA_LO": "FFFFFFFF",
            "HST_TRIGGER_DELAY_DATA_HI": "000000FF",
            "HST_PHI_DELAY_DATA": "3FF003FF",
            "HST_COUNT_TRIG": "00000001",
            "HST_DELAY_EN": "00000001",
            "RSL_HFW_MODE_EN": "00000001",
            "RSL_ZDT_MODE_B_EN": "00000001",
            "RSL_ZDT_MODE_A_EN": "00000001",
            "BGTRIMA": "00000007",
            "BGTRIMB": "0000000F",
            "COLUMN_TEST_EN": "00000001",
            "RSL_CONFIG_DATA_B0": "FFFFFFFF",
            "RSL_CONFIG_DATA_B1": "FFFFFFFF",
            "RSL_CONFIG_DATA_B2": "FFFFFFFF",
            "RSL_CONFIG_DATA_B3": "FFFFFFFF",
            "RSL_CONFIG_DATA_B4": "FFFFFFFF",
            "RSL_CONFIG_DATA_B5": "FFFFFFFF",
            "RSL_CONFIG_DATA_B6": "FFFFFFFF",
            "RSL_CONFIG_DATA_B7": "FFFFFFFF",
            "RSL_CONFIG_DATA_B8": "FFFFFFFF",
            "RSL_CONFIG_DATA_B9": "FFFFFFFF",
            "RSL_CONFIG_DATA_B10": "FFFFFFFF",
            "RSL_CONFIG_DATA_B11": "FFFFFFFF",
            "RSL_CONFIG_DATA_B12": "FFFFFFFF",
            "RSL_CONFIG_DATA_B13": "FFFFFFFF",
            "RSL_CONFIG_DATA_B14": "FFFFFFFF",
            "RSL_CONFIG_DATA_B15": "FFFFFFFF",
            "RSL_CONFIG_DATA_B16": "FFFFFFFF",
            "RSL_CONFIG_DATA_B17": "FFFFFFFF",
            "RSL_CONFIG_DATA_B18": "FFFFFFFF",
            "RSL_CONFIG_DATA_B19": "FFFFFFFF",
            "RSL_CONFIG_DATA_B20": "FFFFFFFF",
            "RSL_CONFIG_DATA_B21": "FFFFFFFF",
            "RSL_CONFIG_DATA_B22": "FFFFFFFF",
            "RSL_CONFIG_DATA_B23": "FFFFFFFF",
            "RSL_CONFIG_DATA_B24": "FFFFFFFF",
            "RSL_CONFIG_DATA_B25": "FFFFFFFF",
            "RSL_CONFIG_DATA_B26": "FFFFFFFF",
            "RSL_CONFIG_DATA_B27": "FFFFFFFF",
            "RSL_CONFIG_DATA_B28": "FFFFFFFF",
            "RSL_CONFIG_DATA_B29": "FFFFFFFF",
            "RSL_CONFIG_DATA_B30": "FFFFFFFF",
            "RSL_CONFIG_DATA_B31": "FFFFFFFF",
            "RSL_CONFIG_DATA_A0": "FFFFFFFF",
            "RSL_CONFIG_DATA_A1": "FFFFFFFF",
            "RSL_CONFIG_DATA_A2": "FFFFFFFF",
            "RSL_CONFIG_DATA_A3": "FFFFFFFF",
            "RSL_CONFIG_DATA_A4": "FFFFFFFF",
            "RSL_CONFIG_DATA_A5": "FFFFFFFF",
            "RSL_CONFIG_DATA_A6": "FFFFFFFF",
            "RSL_CONFIG_DATA_A7": "FFFFFFFF",
            "RSL_CONFIG_DATA_A8": "FFFFFFFF",
            "RSL_CONFIG_DATA_A9": "FFFFFFFF",
            "RSL_CONFIG_DATA_A10": "FFFFFFFF",
            "RSL_CONFIG_DATA_A11": "FFFFFFFF",
            "RSL_CONFIG_DATA_A12": "FFFFFFFF",
            "RSL_CONFIG_DATA_A13": "FFFFFFFF",
            "RSL_CONFIG_DATA_A14": "FFFFFFFF",
            "RSL_CONFIG_DATA_A15": "FFFFFFFF",
            "RSL_CONFIG_DATA_A16": "FFFFFFFF",
            "RSL_CONFIG_DATA_A17": "FFFFFFFF",
            "RSL_CONFIG_DATA_A18": "FFFFFFFF",
            "RSL_CONFIG_DATA_A19": "FFFFFFFF",
            "RSL_CONFIG_DATA_A20": "FFFFFFFF",
            "RSL_CONFIG_DATA_A21": "FFFFFFFF",
            "RSL_CONFIG_DATA_A22": "FFFFFFFF",
            "RSL_CONFIG_DATA_A23": "FFFFFFFF",
            "RSL_CONFIG_DATA_A24": "FFFFFFFF",
            "RSL_CONFIG_DATA_A25": "FFFFFFFF",
            "RSL_CONFIG_DATA_A26": "FFFFFFFF",
            "RSL_CONFIG_DATA_A27": "FFFFFFFF",
            "RSL_CONFIG_DATA_A28": "FFFFFFFF",
            "RSL_CONFIG_DATA_A29": "FFFFFFFF",
            "RSL_CONFIG_DATA_A30": "FFFFFFFF",
            "RSL_CONFIG_DATA_A31": "FFFFFFFF",
        }
    )
    return daedalusregs


def hfwTest(caObject):
    print("\n-Testing High Full Well mode-")
    caObject.setHighFullWell(True)
    armBoard(caObject)
    frames, datalen, data_err = caObject.readoff(waitOnSRAM=True)
    plottiffs(caObject, frames, label="hfw_test")
    caObject.setHighFullWell(False)


def zdtTest(caObject):
    print("\n-Testing Zero Dead Time mode-")
    caObject.setZeroDeadTime(True)
    armBoard(caObject)
    frames, datalen, data_err = caObject.readoff(waitOnSRAM=True)
    plottiffs(caObject, frames, label="zdt_test")
    caObject.setZeroDeadTime(False)


def interlaceTest(caObject):
    print("\n-Testing Interlacing (factor = 2)-")
    caObject.setInterlacing(2)
    armBoard(caObject)
    frames, datalen, data_err = caObject.readoff(waitOnSRAM=True)
    plottiffs(caObject, frames, label="interlace_test")
    caObject.setInterlacing(0)


def timer(caObject):
    print("Checking on-board timer reset")
    caObject.resetTimer()
    ztime = caObject.getTimer()
    if not ztime:
        print("+Timer reset check successful")
    else:
        print("+Timer reset failed, timer reads " + str(ztime))
    statusVerify(caObject, [("STAT_TIMERCOUNTERRESET", 1)])


def test_v1(caObject):
    print("\n# LLNL_v1 board-specific checks")
    if "LED" in caObject.tests:
        print("\nRolling LEDs")
        caObject.enableLED(0)
        caObject.enableLED(1)
        for i in range(1, 5):
            for j in range(1, 9):
                caObject.setLED(j, 1)
                time.sleep(0.05 * i)
                caObject.setLED(j, 0)

    if "POT/DAC set & read" in caObject.tests:
        time.sleep(1)
        print("\n-Pot check-")
        for i in [2, 3, 4, 6, 8]:
            potname = "POT" + str(i)
            monname = "MON_CH" + str(i)
            print("Testing " + potname)
            temperr = 0
            for j in range(7):
                desired = j * 0.5
                potobj = getattr(caObject.board, potname)
                minvolt = potobj.resolution
                caObject.setPotV(potname, desired, tune=True)
                actual = caObject.getMonV(monname)
                # skip v=0, we expect it to be off
                if abs(desired - actual) > minvolt and bool(desired):
                    print(
                        "{0:.2f} : actual = {1:.5f} ; delta = {2:.2f} mV".format(
                            (1.0 * desired), actual, 1000 * abs(actual - desired)
                        )
                    )
                    temperr = 1
            if not temperr:
                print("+" + potname + " tunes properly")

    v1regs = OrderedDict(
        {
            "ADC_RESET": "0000001F",
            "ADC5_CONFIG_DATA": "FFFFFFFF",
            "POT_REG4_TO_1": "FFFFFFFF",
            "POT_REG8_TO_5": "FFFFFFFF",
            "POT_REG12_TO_9": "FFFFFFFF",
            "POT_REG13": "000000FF",
            "ADC5_PPER": "0FFFFFFF",
            "LED_GP": "000000FF",
            "ADC_STANDBY": "0000001F",
            "TEMP_SENSE_PPER": "0FFFFFFF",
            "SENSOR_VOLT_CTL": "00000001",
        }
    )
    v1selfclear = OrderedDict(
        {
            "POT_CTL": "00000001",
        }
    )

    v1restore = [
        ("ADC5_PPER", "001E8480"),
        ("ADC_RESET", "00000000"),
        ("ADC5_CONFIG_DATA", "81A883FF"),
        ("ADC_CTL", "00000010"),
    ]

    return v1regs, v1selfclear, v1restore


def test_v4(caObject):
    print("\n# LLNL_v4 board-specific checks")
    if "POT/DAC set & read" in caObject.tests:
        print("\n-DAC check-")
        if caObject.sensorname == "daedalus":
            daclist = ["C", "E", "F", "G", "H"]
        else:
            daclist = ["A", "B", "C", "D", "E", "F", "G", "H"]
        for i in daclist:
            dacname = "DAC" + i
            monname = "MON_CH" + i
            print("Testing " + dacname)
            temperr = 0
            for j in range(7):
                desired = j * 0.5
                # semi-arbitrary, need to adjust to minimize search time
                minvolt = 0.01
                caObject.setPotV(dacname, desired, tune=True)
                actual = caObject.getMonV(monname)
                # skip v=0, we expect it to be off
                if abs(desired - actual) > minvolt and bool(desired):
                    print(
                        "{0:.2f} : actual = {1:.5f} ; delta = {2:.2f} mV".format(
                            (1.0 * desired), actual, 1000 * abs(actual - desired)
                        )
                    )
                    temperr = 1
            if not temperr:
                print("+" + dacname + " tunes properly")

    v4regs = OrderedDict(
        {
            "ADC_RESET": "0000000F",
            "DAC_REG_A_AND_B": "FFFFFFFF",
            "DAC_REG_C_AND_D": "FFFFFFFF",
            "DAC_REG_E_AND_F": "FFFFFFFF",
            "DAC_REG_G_AND_H": "FFFFFFFF",
            "SUSPEND_TIME": "FFFFFFFF",
            "DELAY_READOFF": "FFFFFFFF",
        }
    )
    v4selfclear = OrderedDict(
        {
            "DAC_CTL": "00000001",
            "SW_COARSE_CONTROL": "FFFFFFFF",
        }
    )
    v4restore = [
        ("ADC_PPER", "001E8480"),
        ("ADC_RESET", "00000000"),
    ]
    return v4regs, v4selfclear, v4restore


def potdacsetread(caObject):
    print("\n-VRST check-")
    for a in (0, 0.05, 0.15, 0.25, 0.5, 0.75, 1, 3, 3.5):
        caObject.setPotV("VRST", voltage=a, tune=True)
        actual = caObject.getMonV("VRST")
        print(
            "{0:.2f} : actual = {1:.5f} ; delta = {2:.2f} mV".format(
                (1.0 * a), actual, 1000 * abs(actual - a)
            )
        )


def registerRW(boardregs, boardrestore, caObject, sensorregs):
    print("\n\n-Verifying register read/writes-\n")
    regchecklist = OrderedDict(
        {  # register name: writable bits
            # read-only, write-only, and self-clearing registers are skipped
            "HS_TIMING_DATA_ALO": "FFFFFFFF",
            "HS_TIMING_DATA_AHI": "000000FF",
            "HS_TIMING_DATA_BLO": "FFFFFFFF",
            "HS_TIMING_DATA_BHI": "000000FF",
            "CTRL_REG": "0000000F",
            "HST_SETTINGS": "00000003",
            "DIAG_MAX_CNT_0": "FFFF00FF",
            "DIAG_MAX_CNT_1": "FFFFFFFF",
            "TRIGGER_CTL": "00000003",
            "FPA_ROW_INITIAL": "000003FF",
            "FPA_ROW_FINAL": "000003FF",
            "FPA_FRAME_INITIAL": "00000003",
            "FPA_FRAME_FINAL": "00000003",
            "FPA_DIVCLK_EN_ADDR": "00000001",
            "FPA_OSCILLATOR_SEL_ADDR": "00000003",
            # "SUSPEND_TIME": "FFFFFFFF",
            # "DELAY_READOFF": "FFFFFFFF",
            "ADC1_CONFIG_DATA": "FFFFFFFF",
            "ADC2_CONFIG_DATA": "FFFFFFFF",
            "ADC3_CONFIG_DATA": "FFFFFFFF",
            "ADC4_CONFIG_DATA": "FFFFFFFF",
            "ADC_RESET": "0000001F",
        }
    )
    regchecklist.update(sensorregs)
    regchecklist.update(boardregs)
    checkvals = ["00000000", "FFFFFFFF"]
    for reg, mask in regchecklist.items():
        temperr = 0
        for val in checkvals:
            valmasked = "{0:0=8x}".format(int(val, 16) & int(mask, 16))
            if temperr:
                continue
            if not caObject.checkRegSet(reg, valmasked):
                temperr = 1
        if not temperr:
            print("+ {: <24} - R/W OK".format(reg))
    caObject.submitMessages(boardrestore)


def register_selfclear(boardrestore, boardselfclear, caObject):
    time.sleep(1)
    print("\n\n-Verifying self-clearing registers-\n")
    selfclear = OrderedDict(
        {  # register name: writable bits
            "HS_TIMING_CTL": "FFFFFFFF",  # Read-write registers
            "SW_TRIGGER_CONTROL": "00000001",
            "CTRL_REG": "FFFFFC00",
            "TIMER_CTL": "FFFFFFFF",
            "ADC_CTL": "FFFFFFFF",
            "STAT_REG_SRC": "00004FFF",  # Read-only registers
            "STAT_REG2_SRC": "FFFFFFDF",
        }
    )
    selfclear.update(boardselfclear)
    for reg, mask in selfclear.items():
        caObject.setRegister(reg, "FFFFFFFF")
        caObject.getRegister(reg)
        time.sleep(0.1)
        _, resp = caObject.getRegister(reg)
        masked = int(resp, 16) & int(mask, 16)

        if not masked:

            print("+ {: <17} - self-clear OK".format(reg))
        else:
            print(
                "+ {: <17} - self-clear FAIL: ".format(reg)
                + "0x"
                + "{0:0=8x}".format(masked)
            )
    caObject.submitMessages(boardrestore)


def statusDump(caObject):
    time.sleep(1)
    print("\n\n-Status dump-\n")
    print(json.dumps(caObject.dumpStatus(), indent=4))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-b",
        action="store",
        dest="board",
        default="llnl_v4",
        help="name of board: 'llnl_v1' or 'llnl_v4'",
    )
    parser.add_argument(
        "-c",
        action="store",
        dest="comm",
        default="GigE",
        help="name of comm: 'GigE' or 'RS422'",
    )
    parser.add_argument(
        "-s",
        action="store",
        dest="sensor",
        default="icarus2",
        help="name of sensor: 'icarus', 'icarus2', or 'daedalus'",
    )
    parser.add_argument(
        "-p", action="store", dest="portNum", default=None, help="specified port number"
    )
    parser.add_argument(
        "-i", action="store", dest="ipAdd", default=None, help="specified ip address"
    )
    parser.add_argument(
        "-v", action="store", dest="verbose", default=4, help="verbosity level"
    )
    parser.add_argument(
        "--batch", action="store_true", help="run automatically without interaction"
    )
    parser.add_argument(
        "--hw", action="store_true", help="wait for hardware triggering"
    )

    args = parser.parse_args()

    testSuite(
        interactive=not args.batch,
        swtrigger=not args.hw,
        board=args.board,
        comm=args.comm,
        sensor=args.sensor,
        portNum=args.portNum,
        ipAdd=args.ipAdd,
        verbose=args.verbose,
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
