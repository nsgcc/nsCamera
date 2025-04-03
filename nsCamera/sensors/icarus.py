# -*- coding: utf-8 -*-
"""
Parameters and functions specific to the icarus two-frame sensor

***Do not use this file as a template for new code development***

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
from collections import OrderedDict

from nsCamera.sensors.sensorBase import sensorBase


class icarus(sensorBase):
    specwarn = " and the use of the Icarus model 1 sensor"
    minframe = 1  # fixed value for sensor
    maxframe = 2  # fixed value for sensor
    # WARNING: the camera will always 'acquire' four frames, but will only generate
    #   images for the middle two; HST and manual shutters will manage all four
    #   frames
    maxwidth = 512  # fixed value for sensor
    maxheight = 1024  # fixed value for sensor
    bytesperpixel = 2
    icarustype = 1  # 2-frame version
    fpganumID = 1  # last nybble of FPGA_NUM
    detect = "ICARUS_DET"
    sensfam = "Icarus"
    loglabel = "[Icarus1] "
    firstframe = 1
    lastframe = 2
    nframes = 2
    width = 512
    height = 1024
    firstrow = 0
    lastrow = 1023
    interlacing = [0, 0]  # N/A for icarus
    columns = 1
    padToFull = True

    def __init__(self, ca):
        self.ca = ca
        super(icarus, self).__init__(ca)

        self.sens_registers = OrderedDict(
            {
                "VRESET_WAIT_TIME": "03E",
                "ICARUS_VER_SEL": "041",
                "VRESET_HIGH_VALUE": "04A",
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
            ## R/W subregs
            # Consistent with ICD usage, start_bit is msb: for [7..0] start_bit is 7
            ("MANSHUT_MODE", "MANUAL_SHUTTERS_MODE", 0, 1, True),
            ("REVREAD", "CTRL_REG", 4, 1, True),
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
            ("READOFF_DELAY_EN", "TRIGGER_CTL", 4, 1, True),
            ## Read-only subregs
            # Consistent with ICD usage, start_bit is msb: for [7..0] start_bit is 7.
            # WARNING: reading a subregister may clear the entire associated register!
            ("STAT_W3TOPAEDGE1", "STAT_REG", 3, 1, False),
            ("STAT_W3TOPBEDGE1", "STAT_REG", 4, 1, False),
            ("STAT_HST_ALL_W_EN_DETECTED", "STAT_REG", 12, 1, False),
            ("PDBIAS_UNREADY", "STAT_REG2", 5, 1, False),
        ]

        if self.ca.boardname == "llnl_v1":
            self.sens_subregisters.append(
                ("VRESET_HIGH", "VRESET_HIGH_VALUE", 7, 8, True)
            )
        else:
            self.sens_subregisters.extend(
                [
                    ("VRESET_HIGH", "VRESET_HIGH_VALUE", 15, 16, True),
                    ("READOFF_DELAY_EN", "TRIGGER_CTL", 4, 1, True),
                ]
            )
            self.sens_registers.update({"DELAY_ASSERTION_ROWDCD_EN": "04F"})

    def checkSensorVoltStat(self):
        """
        Checks register tied to sensor select jumpers to confirm match with sensor
          object

        Returns:
            boolean, True if jumpers select for Icarus sensor
        """
        logging.debug(self.logdebug + "checkSensorVoltStat")
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
        icarussettings = [
            ("ICARUS_VER_SEL", "00000001"),
            ("FPA_FRAME_INITIAL", "00000001"),
            ("FPA_FRAME_FINAL", "00000002"),
            ("FPA_ROW_INITIAL", "00000000"),
            ("FPA_ROW_FINAL", "000003FF"),
            ("VRESET_WAIT_TIME", "000927C0"),
            ("HS_TIMING_DATA_BHI", "00000000"),
            ("HS_TIMING_DATA_BLO", "00006666"),  # 0db6 = 2-1; 6666 = 2-2
            ("HS_TIMING_DATA_AHI", "00000000"),
            ("HS_TIMING_DATA_ALO", "00006666"),
        ]
        if self.ca.boardname == "llnl_v1":
            icarussettings.append(
                ("VRESET_HIGH_VALUE", "000000D5")  # 3.3 V (FF = 3.96)
            )
        else:
            icarussettings.append(("VRESET_HIGH_VALUE", "0000FFFF"))
        return icarussettings


"""
Copyright (c) 2025, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under 
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy (DOE)
and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new contributions must
be made under this license.
"""
