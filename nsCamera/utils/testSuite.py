# -*- coding: utf-8 -*-
"""
Test suite to exercise most CameraAssembler and board functions

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

from nsCamera.CameraAssembler import CameraAssembler

"""
When run from the command line, testSuite accepts the following parameters:
    -b     	name of board: 'llnl_v1' or 'llnl_v4'; default='llnl_v1'
    -c     	name of comm: 'GigE' or 'RS422'; default='GigE'
    -s     	name of sensor: 'icarus', 'icarus2', or 'daedalus';	default='icarus'
    -p     	specified port number; default=None
    -i     	specified ip address; default='192.168.1.100'
    --batch	run automatically without interaction
    --hw   	wait for hardware triggering  
"""

# TODO: add verbose argument to command line


def testSuite(board, comm, sensor, portNum, ipAdd, interactive=True, swtrigger=True):
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

    """
    # Comment out any tests you wish to skip. Irrelevant tests (e.g., Manual Timing if
    #   Daedalus sensor is attached) will be ignored
    tests = [
        "HST acquisition",
        "SaveTiffs",
        "PlotFrames",
        "POT/DAC set & read",
        "SW Trigger",  # perform SW trigger test when HW triggering selected
        "Arm/Disarm",
        "HST setting",
        "Reinitialization",
        "PowerSave",
        "Timer",
        "Register R/W",
        "Register self-clear",
        "Register dump",
        "LED",
        "Manual Timing",
    ]

    def statusVerify(caObject, checklist):
        errs = 0
        for stat, flag in checklist:
            _, check = caObject.getSubregister(stat)
            if bool(int(check)) is not bool(flag):
                errs += 1
                print("+Error: " + stat + " is not " + str(bool(flag)))
        if not errs:
            print("+Status verify passed")

    errtemp = 0
    sensorregs = {}
    boardregs = {}
    boardselfclear = {}

    def test_v1(ca):
        print("\n# LLNL_v1 board-specific checks")
        if "LED" in tests:
            print("\nRolling LEDs")
            ca.enableLED(0)
            ca.enableLED(1)
            for i in range(1, 5):
                for j in range(1, 9):
                    ca.setLED(j, 1)
                    time.sleep(0.05 * i)
                    ca.setLED(j, 0)

        if "POT/DAC set & read" in tests:
            time.sleep(1)
            print("\n-Pot check-")
            for i in [2, 3, 4, 6, 8]:
                potname = "POT" + str(i)
                monname = "MON_CH" + str(i)
                print("Testing " + potname)
                temperr = 0
                for j in range(7):
                    desired = j * 0.5
                    potobj = getattr(ca.board, potname)
                    minvolt = potobj.resolution
                    ca.setPotV(potname, desired, tune=True)
                    actual = ca.getMonV(monname)
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
        v1selfclear = OrderedDict({"POT_CTL": "00000001",})

        v1restore = [
            ("ADC5_PPER", "001E8480"),
            ("ADC_RESET", "00000000"),
            ("ADC5_CONFIG_DATA", "81A883FF"),
            ("ADC_CTL", "00000010"),
        ]

        return v1regs, v1selfclear, v1restore

    def test_v4(ca):
        print("\n# LLNL_v4 board-specific checks")
        if "POT/DAC set & read" in tests:
            print("\n-DAC check-")
            for i in ["A", "B", "C", "D", "E", "F", "G", "H"]:
                dacname = "DAC" + i
                monname = "MON_CH" + i
                print("Testing " + dacname)
                temperr = 0
                for j in range(7):
                    desired = j * 0.5
                    # semi-arbitrary, need to adjust to minimize search time
                    minvolt = 0.005
                    ca.setPotV(dacname, desired, tune=True)
                    actual = ca.getMonV(monname)
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
            }
        )

        v4selfclear = OrderedDict(
            {"DAC_CTL": "00000001", "SW_COARSE_CONTROL": "FFFFFFFF",}
        )

        v4restore = [
            ("ADC_PPER", "001E8480"),
            ("ADC_RESET", "00000000"),
        ]

        return v4regs, v4selfclear, v4restore

    def test_icarus(ca, interactive, swtrigger):
        print("\n# Icarus sensor-specific checks")

        if "Manual Timing" in tests:
            # MANUAL TIMING & ACQUISITION
            print("\n-Testing manual shutter control-")
            ca.setManualShutters(
                timing=[
                    (100, 100, 100, 100, 100, 100, 100),
                    (100, 100, 100, 100, 100, 100, 100),
                ]
            )
            statusVerify(ca, [("MANSHUT_MODE", 1), ("STAT_HSTCONFIGURED", 0)])
            print(
                "The next few messages should include two error messages about "
                "invalid timing sequences "
            )
            time.sleep(1)
            ca.setManualShutters(timing=[(100, 100, 100, 100, 100, 100, 100)])
            ca.setManualShutters(
                timing=[
                    (10.5, 100, 100, 100, 100, 100, 100),
                    (100, 100, 100, 100, 100, 100, 100),
                ]
            )
            time.sleep(1)

            print("\n-Testing manual shutter acquisition-")
            if swtrigger:
                print("Using software trigger")
                statusVerify(
                    ca,
                    [
                        ("STAT_ADCSCONFIGURED", 1),
                        (ca.potsdacsconfigured, 1),
                        ("STAT_HSTCONFIGURED", 0),
                        ("MANSHUT_MODE", 1),
                    ],
                )
                ca.arm("Software")
                statusVerify(ca, [("STAT_COARSE", 1), ("STAT_FINE", 1)])
            else:
                ca.arm()
                if interactive:
                    ca.getEnter(
                        "> Please initiate hardware trigger, then press ENTER to "
                        "continue. <\n "
                    )

            frames, datalen, data_err = ca.readoff(waitOnSRAM=True)
            print("Data length: " + str(datalen))
            if data_err:
                print("+Error in acquisition!")
            else:
                print("+No error in acquisition reported")

            if interactive:
                if "PlotFrames" in tests:
                    print(
                        "Plots of the acquired frames are being displayed. Please "
                        "inspect to verify proper acquisition. "
                        "\n> Close plots to continue <"
                    )
                    ca.plotFrames(frames)
                if "SaveTiffs" in tests:
                    ca.saveTiffs(frames, filename="msc_test")
                    ca.getEnter(
                        "Tiff files of the acquired frames have been saved. Please "
                        "inspect to verify correct saves. "
                        "\n> Press ENTER to continue <\n"
                    )

            else:
                if "SaveTiffs" in tests:
                    ca.saveTiffs(frames, filename="msc_test")
                    print("Tiffs from manual shutter control test have been saved")

            # REINITIALIZATION WITH MANUAL SHUTTERS
            if "Reinitialization" in tests and interactive:
                ca.setManualShutters(
                    timing=[
                        (25, 50, 75, 100, 125, 150, 175),
                        (175, 150, 125, 100, 75, 50, 25),
                    ]
                )
                ca.getEnter(
                    "\n-Testing reinitialization with manual shutter control-\n> "
                    "Please power-cycle the board, then press ENTER to continue <"
                )
                time.sleep(1)
                if ca.powerCheck():
                    print("\n+Loss of power WAS NOT detected")
                else:
                    print("\n+Loss of power WAS detected")
                time.sleep(1)
                ca.reinitialize()
                statusVerify(ca, [("STAT_TIMERCOUNTERRESET", 1)])
                ca.sensor.getManualTiming()
                if ca.sensor.getManualTiming() != [
                    [25, 50, 75, 100, 125, 150, 175],
                    [175, 150, 125, 100, 75, 50, 25],
                ]:
                    print(
                        "+Manual timing WAS NOT restored properly after "
                        "reinitialization "
                    )
                else:
                    print(
                        "+Manual timing WAS restored properly after "
                        "reinitialization "
                    )

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
            }
        )

        if ca.sensorname == "icarus":
            icarusregs["VRESET_HIGH_VALUE"] = "000000FF"

        return icarusregs

    def test_daedalus(ca, interactive, swtrigger):
        print("\n# Daedalus sensor-specific checks")
        daedalusregs = {}  # TODO: add daedalus registers when available
        return daedalusregs

    print("-Initial setup-")
    ca = CameraAssembler(
        commname=comm,
        boardname=board,
        sensorname=sensor,
        verbose=5,
        port=portNum,
        ip=ipAdd,
    )
    ca.potsdacsconfigured = "STAT_DACSCONFIGURED"

    statusVerify(ca, [("STAT_TIMERCOUNTERRESET", 1)])

    if "PowerSave" in tests:
        print("\n-Testing PowerSave mode-")
        ca.setPowerSave(1)
        statusVerify(ca, [("POWERSAVE", 1)])
        ca.setPowerSave(0)
        statusVerify(ca, [("POWERSAVE", 0)])

    # ARM/DISARM
    if "Arm/Disarm" in tests:
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

    # HIGH SPEED TIMING & ACQUISITION
    if "HST setting" in tests:
        print("\n-Testing high speed timing control-")
        ca.setTiming("A", (39, 1), 0)
        ca.setTiming("B", (1, 1), 31)
        if not ("A", 39, 1, 0) == ca.getTiming("A"):
            errtemp = 1
        if not ("B", 1, 1, 37) == ca.getTiming("B"):
            errtemp = 1
        if errtemp:
            print("Error in setting high speed timing")
            errtemp = 0

        ca.setTiming("A", (5, 2), 3)
        ca.setTiming("B", (3, 4), 1)
        if not ("A", 5, 2, 3) == ca.getTiming("A"):
            errtemp = 1
        if not ("B", 3, 4, 1) == ca.getTiming("B"):
            errtemp = 1
        if errtemp:
            print("Error in setting high speed timing")
            errtemp = 0

        ca.setTiming("B", (10, 10), 0)

        time.sleep(1)
        print(
            "The next few messages should include a warning about inter-frame timing:"
        )
        time.sleep(1)
        ca.setTiming("A", (9, 8), 1)
        print(
            "The next few messages should include a error message regarding timing "
            "sequence: "
        )
        time.sleep(1)
        ca.setTiming("A", (15, 15), 15)

        statusVerify(ca, [("STAT_HSTCONFIGURED", 1), ("MANSHUT_MODE", 0)])
        time.sleep(1)

    # ca.setInterlacing(2)  # TODO: sensor-specific testing?

    if "HST acquisition" in tests:
        print("\n-Testing HST acquisition-")
        ca.arm()
        time.sleep(1)

        ca.reportStatus()
        statusVerify(
            ca,
            [
                ("STAT_ADCSCONFIGURED", 1),
                (ca.potsdacsconfigured, 1),
                ("STAT_HSTCONFIGURED", 1),
                ("MANSHUT_MODE", 0),
                ("STAT_COARSE", 0),
                ("STAT_FINE", 0),
            ],
        )
        if swtrigger:
            print("Using software trigger")
            ca.arm("Software")
            statusVerify(ca, [("STAT_COARSE", 1), ("STAT_FINE", 1)])

        else:
            if interactive:
                ca.getEnter(
                    "> Please initiate hardware trigger, then press ENTER to "
                    "continue. <\n "
                )

        frames, datalen, data_err = ca.readoff(waitOnSRAM=True)

        margin = 1600
        print(
            "Check of dummy sensor; number of pixels exceeding margin of "
            + str(margin)
            + " from dummy sensor expected value:"
        )
        for frame in frames:
            bads, diff = ca.dummyCheck(frame, margin)
            print(bads)

        print("Data length: " + str(datalen) + " bytes")
        if data_err:
            print("+Error in acquisition!")
        else:
            print("+No error in acquisition reported")

        if interactive:
            if "PlotFrames" in tests:
                print(
                    "\nPlots of the acquired frames are being displayed. Please "
                    "inspect to verify proper acquisition. "
                    "\n> Close plots to continue <"
                )
                ca.plotFrames(frames)
            if "SaveTiffs" in tests:
                ca.saveTiffs(frames, filename="hst_test")
                ca.getEnter(
                    "Tiff files of the acquired frames have been saved. Please "
                    "inspect to verify correct saves. "
                    "\n> Press ENTER to continue. <\n"
                )
        else:
            if "SaveTiffs" in tests:
                ca.saveTiffs(frames, filename="hst_test")
                print("Tiffs from HST test have been saved")

        if not swtrigger and "SW Trigger" in tests:
            print("\n-Testing HST acquisition with software trigger-")
            ca.arm()
            time.sleep(1)

            ca.reportStatus()
            statusVerify(
                ca,
                [
                    ("STAT_ADCSCONFIGURED", 1),
                    (ca.potsdacsconfigured, 1),
                    ("STAT_HSTCONFIGURED", 1),
                    ("MANSHUT_MODE", 0),
                    ("STAT_COARSE", 0),
                    ("STAT_FINE", 0),
                ],
            )

            ca.arm("Software")
            statusVerify(ca, [("STAT_COARSE", 1), ("STAT_FINE", 1)])

            frames, datalen, data_err = ca.readoff(waitOnSRAM=True)

            margin = 1600
            print(
                "Check of dummy sensor; number of pixels exceeding margin of "
                + str(margin)
                + " from dummy sensor expected value:"
            )
            for frame in frames:
                bads, diff = ca.dummyCheck(frame, margin)
                print(bads)

            print("Data length: " + str(datalen) + " bytes")
            if data_err:
                print("+Error in acquisition!")
            else:
                print("+No error in acquisition reported")

            if interactive:
                if "PlotFrames" in tests:
                    print(
                        "\nPlots of the acquired frames are being displayed. Please "
                        "inspect to verify proper acquisition. "
                        "\n> Close plots to continue <"
                    )
                    ca.plotFrames(frames)
                if "SaveTiffs" in tests:
                    ca.saveTiffs(frames, filename="SWtrig_test")
                    ca.getEnter(
                        "Tiff files of the acquired frames have been saved. Please "
                        "inspect to verify correct saves. "
                        "\n> Press ENTER to continue. <\n"
                    )
            else:
                if "SaveTiffs" in tests:
                    ca.saveTiffs(frames, filename="SWtrig_test")
                    print("Tiffs from HST test have been saved")

    # REINITIALIZATION
    if "Reinitialization" in tests and interactive:
        time.sleep(1)
        ca.setTiming("A", (2, 3), 4)
        ca.setTiming("B", (5, 3), 1)
        time.sleep(1)
        ca.getEnter(
            "\n-Testing reinitialization with high speed timing-\n>Please power-cycle "
            "the board, then press ENTER to continue <"
        )
        if ca.powerCheck():
            print("\n+Loss of power WAS NOT detected")
        else:
            print("\n+Loss of power WAS detected")
        time.sleep(1)
        ca.reinitialize()
        statusVerify(ca, [("STAT_TIMERCOUNTERRESET", 1)])
        if ("A", 2, 3, 4) != ca.getTiming("A") or ("B", 5, 3, 1,) != ca.getTiming("B"):
            print("+High speed timing WAS NOT restored properly after reinitialization")
        else:
            print("+High speed timing WAS restored properly after reinitialization")

    if ca.sensorname == "icarus" or ca.sensorname == "icarus2":
        sensorregs = test_icarus(ca, interactive, swtrigger)
    elif ca.sensorname == "daedalus":
        sensorregs = test_daedalus(ca, interactive, swtrigger)

    # MISCELLANEOUS
    print("\n\n-Testing miscellaneous board features-")

    if "Timer" in tests:
        print("Checking on-board timer reset")
        ca.resetTimer()
        ztime = ca.getTimer()
        if not ztime:
            print("+Timer reset check successful")
        else:
            print("+Timer reset failed, timer reads " + str(ztime))
        statusVerify(ca, [("STAT_TIMERCOUNTERRESET", 1)])

    print("Temperature sensor reading: " + str(ca.getTemp()))
    time.sleep(1)

    if ca.boardname == "llnl_v1":
        ca.potsdacsconfigured = "STAT_POTSCONFIGURED"
        boardregs, boardselfclear, boardrestore = test_v1(ca)
    elif ca.boardname == "llnl_v4":
        ca.potsdacsconfigured = "STAT_DACSCONFIGURED"
        boardregs, boardselfclear, boardrestore = test_v4(ca)

    if "POT/DAC set & read" in tests:
        print("\n-VRST check-")
        for a in (0, 0.05, 0.15, 0.25, 0.5, 0.75, 1, 3, 3.5):
            ca.setPotV("VRST", voltage=a, tune=True)
            actual = ca.getMonV("VRST")
            print(
                "{0:.2f} : actual = {1:.5f} ; delta = {2:.2f} mV".format(
                    (1.0 * a), actual, 1000 * abs(actual - a)
                )
            )

    if "Register R/W" in tests:
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
                if not ca.checkRegSet(reg, valmasked):
                    temperr = 1
                    continue
            if not temperr:
                print("+ {: <24} - R/W OK".format(reg))

        ca.submitMessages(boardrestore)

    if "Register self-clear" in tests:
        time.sleep(1)
        print("\n\n-Verifying self-clearing registers-\n")

        selfclear = OrderedDict(
            {  # register name: writable bits
                "HS_TIMING_CTL": "FFFFFFFF",  # Read-write registers
                "TIMER_CTL": "FFFFFFFF",
                "ADC_CTL": "FFFFFFFF",
                "STAT_REG_SRC": "00004FFF",  # Read-only registers
                "STAT_REG2_SRC": "FFFFFFFF",
            }
        )

        selfclear.update(boardselfclear)

        for reg, mask in selfclear.items():
            ca.setRegister(reg, "FFFFFFFF")
            ca.getRegister(reg)
            time.sleep(0.1)
            _, resp = ca.getRegister(reg)
            masked = int(resp, 16) & int(mask, 16)

            if not masked:

                print("+ {: <17} - self-clear OK".format(reg))
            else:
                print(
                    "+ {: <17} - self-clear FAIL: ".format(reg)
                    + "0x"
                    + "{0:0=8x}".format(masked)
                )

        ca.submitMessages(boardrestore)

    if "Register dump" in tests:
        time.sleep(1)
        print("\n\n-Register dump-\n")
        print("\n".join(ca.dumpRegisters()))

    ca.closeDevice()
    time.sleep(1)
    logging.info("Done")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-b",
        action="store",
        dest="board",
        default="llnl_v1",
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
        default="icarus",
        help="name of sensor: 'icarus', 'icarus2', or 'daedalus'",
    )
    parser.add_argument(
        "-p", action="store", dest="portNum", default=None, help="specified port number"
    )
    parser.add_argument(
        "-i", action="store", dest="ipAdd", default=None, help="specified ip address"
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
    )

"""
Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.
"""
