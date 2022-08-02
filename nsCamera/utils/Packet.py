# -*- coding: utf-8 -*-
"""
Packet object for communication with boards

Author: Brad Funsten (funsten1@llnl.gov)
Author: Jeremy Hill (hill35@llnl.gov)

Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.

Version: 2.1.1  (July 2021)
"""

from __future__ import absolute_import

import binascii
import sys

from nsCamera.utils import crc16pure


class Packet:
    """
    Packet object for communication with boards. See ICD for details.

    Single Command/Response packet:
    +----------+-----------+-----------+------------+-----------+
    | 16 bits  |  4 bits   |  12 bits  |   32 bits  |  16 bits  |
    | Preamble |  Command  |  Address  |    Data    |   CRC16   |
    +----------+-----------+-----------+------------+-----------+

    Read Burst Response packet:

    +----------+-----------+---------------+---------------+
    | 16 bits  |  4 bits   |    4 bits     |    16 bits    %
    | Preamble |  Command  |  Sub-command  |  Sequence ID  %
    +----------+-----------+---------------+---------------+
                                            +-----------------+------------+-----------+
                                            %      16 bits    |  Variable  |  16 bits  |
                                            %  Payload Length |  Payload   |   CRC16   |
                                            +-----------------+------------+-----------+

    """

    def __init__(
        # NOTE: 'numerical' components are handled as hex strings
        self,
        preamble="aaaa",
        cmd="0",
        addr="",
        data="00000000",
        seqID="",
        payload_length="",
        payload="",
        crc="",
    ):
        self.PY3 = sys.version_info > (3,)
        self._preamble = preamble  # 16 bit packet preamble
        self._cmd = str(cmd)  # 4 bit command packet
        self._addr = addr.zfill(3)  # 12 bit address packet
        self._data = data.zfill(8)  # 32 bit data packet
        # 16 bit sequence ID packet (only Read Burst)
        self._seqID = seqID
        # 16 bit payload packet (only Read Burst)
        self._payload_length = payload_length
        # variable payload packet (only Read Burst) for now it's 16 bits
        self._payload = payload
        # 16 bit CRC-CCIT (XModem) packet
        self._crc = crc
        self._type = ""
        if self._crc == "":  # check if packet to be sent needs crc appended
            self._crc = self.calculateCRC()

    def pktStr(self):
        """
        Generate hexadecimal string form of packet

        Returns:
            packet as hexadecimal string without '0x'
        """
        if self._seqID != "":
            # Read burst response
            packetparts = [
                self._preamble,
                self._cmd,
                self._seqID,
                self._payload_length,
                self._payload,
                self._crc,
            ]
        else:
            # Single Command/Response response
            packetparts = [self._preamble, self._cmd, self._addr, self._data, self._crc]
        stringparts = [
            part.decode("ascii") if isinstance(part, bytes) else part
            for part in packetparts
        ]
        out = "".join(stringparts)
        return out

    def calculateCRC(self):
        """
        Calculate CRC-CCIT (XModem) (2 bytes) from 8 byte packet for send and rcv

        Returns:
            CRC as hexadecimal string without '0x'
        """
        preamble = self._preamble
        crc = self._crc
        self._crc = ""
        self._preamble = ""

        CRC_dec = crc16pure.crc16xmodem(self.str2bytes(self.pktStr()))
        # input = int type decimal, output = hex string with 0x at the beginning
        CRC_hex_0x = "0x%0.4X" % CRC_dec
        # make all hex letters lower case for comparison
        CRC_hex = CRC_hex_0x.lower()
        # input = hex string with 0x at the beginning, output = hex str with 0x removed
        CRC_hex = CRC_hex[2:]
        self._preamble = preamble
        self._crc = crc
        return CRC_hex

    def checkCRC(self):
        """
        Returns: boolean, True if CRC check passes
        """
        if self.calculateCRC() == self._crc:
            return True
        else:
            return False

    def checkReadPacket(self, resppkt):
        """
        Confirm that Read Single occurred without error
        Args:
            resppkt: response packet

        Returns:
            tuple (error string, response packet as string)
        """
        err = ""
        if int(resppkt._cmd.upper(), 16) - int(self._cmd.upper(), 16) != 0x8:
            err = "invalid command; "
        if resppkt._addr.upper() != self._addr.upper():
            err += "invalid address; "
        if resppkt._crc.upper() != resppkt.calculateCRC().upper():
            err += "invalid CRC; "
        return err, resppkt.pktStr()

    def checkResponsePacket(self, resppkt):
        """
        Confirm that Write Single occurred without error
        Args:
            resppkt: response packet

        Returns:
            tuple (error string, response packet as string)
        """
        err = ""
        if int(resppkt._data, 16) & 1:
            err += "Checksum error; "
        if int(resppkt._data, 16) & 2:
            err += "Invalid command / command not executed; "
        err1, rval = self.checkReadPacket(resppkt)
        err += err1
        return err, rval

    def checkResponseString(self, respstr):
        """
        Checks response string for error indicators
        Args:
            respstr: packet as hexadecimal string

        Returns:
            tuple (error string, response packet string)
        """
        respstring = respstr.decode(encoding="UTF-8")
        resppkt = Packet(
            preamble=respstring[0:4],
            cmd=respstring[4],
            addr=respstring[5:8],
            data=respstring[8:16],
        )

        if resppkt._cmd == "8":
            # verify response to write command
            err, rval = self.checkResponsePacket(resppkt)
        elif resppkt._cmd == "9":
            err, rval = self.checkReadPacket(resppkt)  # verify response to read command
        else:
            err = "Packet command invalid; "
            rval = ""
        return err, rval

    def str2bytes(self, bstring):
        """
        Python-version-agnostic converter of hexadecimal strings to bytes

        Args:
            bstring: hexadecimal string without '0x'

        Returns:
            byte string equivalent to input string
        """
        if self.PY3:
            dbytes = binascii.a2b_hex(bstring)
        else:
            dbytes = bstring.decode("hex")
        return dbytes

    def bytes2str(self, bytesequence):
        """
        Python-version-agnostic converter of bytes to hexadecimal strings

        Args:
            bytesequence: sequence of bytes as string (Py2) or bytes (Py3)

        Returns:
            hexadecimal string representation of 'bytes' without '0x'
        """
        estring = binascii.b2a_hex(bytesequence)
        if self.PY3:
            estring = str(estring)[2:-1]
        return estring


"""
Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.
"""
