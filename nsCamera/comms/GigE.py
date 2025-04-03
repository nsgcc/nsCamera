# -*- coding: utf-8 -*-
"""
Gigabit Ethernet interface for nsCamera.

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

import ctypes as C
import logging
import os.path
import sys

from nsCamera.utils.misc import generateFrames, str2bytes, bytes2str


class GigE:
    """
    Code to manage Gigabit Ethernet connection to board. Each GigE object manages a
      single OT card; to use multiple cards, instantiate multiple cameraAssembler
      objects, each specifying the unique IPs of the corresponding OT card.

    Note: Orange Tree card must be configured before use. See the README for details

    Exposed methods:
        arm() - puts camera into wait state for external trigger
        readFrames() - waits for data ready register flag, then copies camera image data
          into numpy arrays
        readoff() - waits for data ready register flag, then copies camera image data
          into numpy arrays; returns payload, payload size, and error message
        sendCMD(pkt) - sends packet object via serial port
        readSerial(size, timeout) - read 'size' bytes from connection
        writeSerial(outstring) - submits string 'outstring' over connection
        closeDevice() - close connections and free resources
        getCardIP() - returns IP address of OT card
        getCardInfo() - prints report of details of OT card and connection
    """

    def __init__(self, camassem):
        """
        Args:
            camassem: parent cameraAssembler object
        """
        self.ca = camassem
        self.logcrit = self.ca.logcritbase + "[GigE] "
        self.logerr = self.ca.logerrbase + "[GigE] "
        self.logwarn = self.ca.logwarnbase + "[GigE] "
        self.loginfo = self.ca.loginfobase + "[GigE] "
        self.logdebug = self.ca.logdebugbase + "[GigE] "
        logging.info(self.loginfo + "Initializing GigE comms object")
        self.mode = 1
        self.writeTimeout = 10000
        self.readTimeout = 10000
        self.payloadsize = (
            self.ca.sensor.width
            * self.ca.sensor.height
            * self.ca.sensor.nframes
            * self.ca.sensor.bytesperpixel
        )
        logging.debug(
            self.logdebug + "Payload size: " + str(self.payloadsize) + " bytes"
        )
        self.skipError = False

        self.ZErrorDict = {
            0x8000: "Socket Error",
            0x8001: "Internal Error",
            0x8002: "Illegal Status Code",
            0x8003: "Null Parameter",
            0x8004: "Out of Memory",
            0x8005: "Invalid Connection Type",
            0x8006: "Illegal Connection",
            0x8007: "Socket Closed Unexpectedly",
            0x8008: "Timeout",
            0x8009: "Illegal Parameter",
        }

        if self.ca.port:
            logging.debug(
                self.logdebug + "Port supplied to GigE.py: " + str(self.ca.port)
            )
            if isinstance(self.ca.port, int) and 0 < self.ca.port < 65536:
                self.dport = self.ca.port
            else:
                logging.error(
                    self.logerr + "Invalid port number supplied, defaulting to "
                    "20482 "
                )
                self.dport = 20482
        else:
            self.dport = 20482  # default

        self.ca.port = self.dport
        logging.debug(self.logdebug + "Port used by GigE.py: " + str(self.dport))

        logging.debug(self.logdebug + "CPU architecture: " + str(self.ca.arch))
        if self.ca.arch == "64bit":
            arch = "64"
        else:
            arch = "32"

        logging.debug(self.logdebug + "Operating system: " + str(self.ca.platform))
        if self.ca.platform == "Windows":
            lib_name = "ZestETM1.dll"
        elif self.ca.platform == "Linux" or self.ca.platform == "Darwin":
            lib_name = "libZestETM1.so"
        else:
            logging.warning(
                self.logwarn + "System does not self-identify as Linux, Windows, "
                "or Mac. Assuming posix-style libraries "
            )
            lib_name = "libZestETM1.so"

        self.closecard = False

        libpath = os.path.join(self.ca.packageroot, "comms", "ZestETM1", arch, lib_name)
        self._zest = C.CDLL(libpath)

        self.CardInfo = self.ZESTETM1_CARD_INFO()
        self.CardInfoP = C.pointer(self.CardInfo)

        # functions
        self.ZCountCards = self._zest.ZestETM1CountCards
        self.ZCountCards.argtypes = [
            C.POINTER(C.c_ulong),
            C.POINTER(C.POINTER(self.ZESTETM1_CARD_INFO)),
            C.c_int,
        ]

        self.ZOpenConnection = self._zest.ZestETM1OpenConnection
        self.ZOpenConnection.argtypes = [
            C.POINTER(self.ZESTETM1_CARD_INFO),
            C.c_int,
            C.c_ushort,
            C.c_ushort,
            C.POINTER(C.c_void_p),
        ]

        self.ZWriteData = self._zest.ZestETM1WriteData
        self.ZWriteData.argtypes = [
            C.c_void_p,
            C.c_void_p,
            C.c_ulong,
            C.POINTER(C.c_ulong),
            C.c_ulong,
        ]

        self.ZReadData = self._zest.ZestETM1ReadData
        self.ZReadData.argtypes = [
            C.c_void_p,
            C.c_void_p,
            C.c_ulong,
            C.POINTER(C.c_ulong),
            C.c_ulong,
        ]

        self.Connection = C.c_void_p()
        self.openDevice(self.ca.timeout)

    def sendCMD(self, pkt):
        """
        Submit packet and verify the response packet.
        Packet communications with FPGA omit CRC suffix, so adds fake CRC bytes to
          response

        Args:
            pkt: Packet object

        Returns:
            tuple (error, response string)
        """

        pktStr = pkt.pktStr()[0:16]
        logging.debug(self.logdebug + "sendCMD packet: " + str(pktStr))
        err = ""
        self.ca.writeSerial(pktStr)
        if (
            hasattr(self.ca, "board")
            and pktStr[4] == "0"
            and pktStr[5:8] == self.ca.board.registers["SRAM_CTL"]
        ):
            bufsize = self.payloadsize + 16
            resptext = self.readSerial(bufsize)

            if len(resptext) < 32:
                logging.debug(self.logdebug + "sendCMD resptext = " + str(resptext))
            else:
                logging.debug(
                    self.logdebug
                    + "sendCMD resptext (truncated) = "
                    + str(resptext)[0:32]
                )

            if len(resptext) < bufsize + 16:
                err += (
                    self.logerr + "sendCMD- packet too small, payload may be incomplete"
                )
                logging.error(err)
        else:
            # workaround for initial setup before board object has been initialized
            resp = self.readSerial(8)
            logging.debug(self.logdebug + "sendCMD response: " + str(resp))
            if len(resp) < 8:
                err += self.logerr + "sendCMD- response too small, returning zeros"
                resptext = "00000000000000000000"
                logging.error(err)
            else:
                resptext = resp + "0000"
        return err, resptext

    def arm(self, mode):
        """
        Puts camera into wait state for trigger. Mode determines source; defaults to
          'Hardware'

        Args:
            mode:   'Software'|'S' activates software, disables hardware triggering
                    'Hardware'|'H' activates hardware, disables software triggering
                      Hardware is the default

        Returns:
            tuple (error, response string)
        """
        if not mode:
            mode = "Hardware"
            logging.info(self.loginfo + "arm")
        logging.debug(self.logdebug + "arming mode: " + str(mode))
        self.ca.clearStatus()
        self.ca.latchPots()
        err, resp = self.ca.startCapture(mode)
        if err:
            logging.error(self.logerr + "unable to arm camera")
        else:
            self.ca.armed = True
            self.skipError = True
        return err, resp

    def readFrames(self, waitOnSRAM, timeout=0, fast=False, columns=1):
        """
        Copies image data from board into numpy arrays.

        Args:
            waitOnSRAM: if True, wait until SRAM_READY flag is asserted to begin copying
              data
            timeout: passed to waitForSRAM; after this many seconds begin copying data
              irrespective of SRAM_READY status; 'zero' means wait indefinitely
              WARNING: If acquisition fails, the SRAM will not contain a current image,
                but the code will copy the data anyway
            fast: if False, parse and convert frames to numpy arrays; if True, return
              unprocessed text stream
            columns: 1 for single image per frame, 2 for separate hemisphere images

        Returns:
            list of numpy arrays OR raw text stream

        """
        frames, _, _ = self.readoff(waitOnSRAM, timeout, fast, columns)
        return frames

    def readoff(self, waitOnSRAM, timeout=0, fast=False, columns=1):
        """
        Copies image data from board into numpy arrays; returns data, length of data,
        and error messages. Use 'readFrames()' unless you require this additional
        information

        Args:
            waitOnSRAM: if True, wait until SRAM_READY flag is asserted to begin copying
              data
            timeout: passed to waitForSRAM; after this many seconds begin copying data
              irrespective of SRAM_READY status; 'zero' means wait indefinitely
              WARNING: If acquisition fails, the SRAM will not contain a current image,
                but the code will copy the data anyway
            fast: if False, parse and convert frames to numpy arrays; if True, return
              unprocessed text stream
            columns: 1 for single image per frame, 2 for separate hemisphere images

        Returns:
            tuple (list of numpy arrays OR raw text stream, length of downloaded payload
              in bytes, payload error flag) since CRC check is handled by TCP/IP,
              payload error flag is always False for GigE
        """
        logging.info(self.loginfo + "readoff")
        logging.debug(
            self.logdebug
            + "readoff: waitonSRAM = "
            + str(waitOnSRAM)
            + "; timeout = "
            + str(timeout)
            + "; fast = "
            + str(fast)
        )
        # Wait for data to be ready on board
        # Skip wait only if explicitly tagged 'False' ('None' defaults to True)
        if waitOnSRAM is not False:
            self.ca.waitForSRAM(timeout)
        self.skipError = False
        err, rval = self.ca.readSRAM()
        if err:
            logging.error(self.logerr + "Error detected in readSRAM")
        elif self.ca.boardname == "llnl_v4":
            # self.ca.setSubregister('SWACK','1')
            pass
        # extract the data. Remove header; the FPGA returns a packet without the CRC
        #   suffix
        logging.debug(self.logdebug + "readoff: first 64 chars: " + str(rval[0:64]))
        data = rval[32:]
        if fast:
            return data, len(data) // 2, bool(err)
        else:
            parsed = generateFrames(self.ca, data, columns)
            return parsed, len(data) // 2, bool(err)

    def writeSerial(self, outstring, timeout):
        """
        Transmit string to board

        Args:
            outstring: string to write
            timeout: serial timeout in sec (defaults to self.writeTimeout)

        Returns:
            integer number of bytes written
        """
        logging.debug(
            self.logdebug
            + "writeSerial: outstring = "
            + str(outstring)
            + "; timeout = "
            + str(timeout)
        )
        if not timeout:
            timeout = self.writeTimeout
        outstring = str2bytes(outstring)
        outbuff = C.create_string_buffer(outstring)
        outbuffp = C.pointer(outbuff)
        outbufflen = len(outstring)
        writelen = C.c_ulong(0)
        err = self.ZWriteData(
            self.Connection, outbuffp, outbufflen, C.byref(writelen), timeout
        )
        if err:
            if err == 0x4000:
                logging.warning(
                    self.logerr + "OT Card emitted an undefined warning message"
                )
            else:
                logging.error(
                    self.logerr + "writeSerial error: " + self.ZErrorDict[err]
                )
        logging.debug(self.logdebug + "writeSerial: writelen = " + str(writelen))
        return writelen

    def readSerial(self, size, timeout=None):
        """
        Read bytes from the serial port. Does not verify packets.

        Args:
           size: number of bytes to read
           timeout: serial timeout in sec (defaults to self.readTimeout)

        Returns:
           tuple (error string, string read from serial port)
        """
        logging.debug(
            self.logdebug
            + "readSerial: size = "
            + str(size)
            + "; timeout = "
            + str(timeout)
        )
        if not timeout:
            timeout = self.readTimeout
        inbuff = C.create_string_buffer(size + 1)
        inbuffp = C.pointer(inbuff)
        readlen = C.c_ulong(0)
        err = self.ZReadData(self.Connection, inbuffp, size, C.byref(readlen), timeout)
        if err:
            if self.skipError:
                logging.debug(
                    self.logdebug + "readSerial: skipped error: " + self.ZErrorDict[err]
                )
                self.skipError = False
            elif err == 0x4000:
                logging.warning(
                    self.logerr + "OT Card emitted an undefined warning message"
                )
            else:
                logging.error(self.logerr + "readSerial error: " + self.ZErrorDict[err])
        return bytes2str(inbuff.raw)[:-2]

    # TODO: check for valid timeout, probably in init in CameraAssembler
    def openDevice(self, timeout=30):
        """
        Find Orange Tree card and open a connection; if IP is supplied as parameter for
          the CameraAssembler, bypass network search and connect directly to indicated
          IP address

        Args:
            timeout: timeout in seconds for attempting to connect to a card
        """
        err = self._zest.ZestETM1Init()
        if err:
            logging.critical(self.logcrit + "ZestETM1Init failure")
            sys.exit(1)
        logging.info(self.loginfo + "searching for Orange Tree cards")
        NumCards = C.c_ulong(0)

        if self.ca.iplist:
            ubyte4 = C.c_ubyte * 4
            self.CardInfo.IPAddr = ubyte4(*self.ca.iplist)
            self.CardInfo.ControlPort = C.c_ushort(self.dport)
            self.CardInfo.Timeout = C.c_ulong(self.writeTimeout)
            self.closecard = False
        else:
            wait = 0
            while True:
                logging.debug(
                    self.logdebug + "openDevice: connection wait = " + str(wait)
                )
                err = self.ZCountCards(C.byref(NumCards), C.byref(self.CardInfoP), 1000)
                if err:
                    logging.critical(self.logcrit + "CountCards failure")
                    sys.exit(1)
                if NumCards.value > 0:
                    break
                if wait == timeout:
                    logging.critical(
                        "{}No Orange Tree cards found in {} seconds".format(
                            self.logcrit, timeout
                        )
                    )
                    sys.exit(1)
                elif not wait % 5:
                    logging.info(
                        "{}Still trying to connect after {} seconds...".format(
                            self.loginfo, wait
                        )
                    )
                wait += 1
            logging.info(
                self.loginfo + str(NumCards.value) + " Orange Tree card(s) found"
            )  # TODO: add check for GigE bit in board description
        err = self.ZOpenConnection(
            self.CardInfoP, 0, self.dport, 0, C.byref(self.Connection)
        )
        if err:
            if err == 0x4000:
                logging.warning(
                    self.logerr + "OT Card emitted an undefined warning message"
                )
            else:
                logging.critical(
                    self.logcrit + "OpenConnection failure: " + self.ZErrorDict[err]
                )
            sys.exit(1)

    def closeDevice(self):
        """
        Close connection to Orange Tree card and free resources
        """
        logging.debug(self.logdebug + "Closing connection to Orange Tree card")
        self._zest.ZestETM1CloseConnection(self.Connection)
        if self.closecard:
            try:
                self._zest.ZestETM1FreeCards(self.CardInfoP)
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except Exception:
                logging.error(self.logerr + "Error reported in OT card closure")
        self._zest.ZestETM1Close()

    def getCardIP(self):
        """
        Query IP address of OT card

        Returns: address of OT card as list of bytes
        """
        return self.CardInfo.IPAddr

    # TODO: use logging.info, with override option?
    def getCardInfo(self):
        """
        Prints status message with information returned by OT card
        """
        ci = self.CardInfoP.contents
        print("GigE Card Status:")
        print("-------------")
        print("IP: " + ".".join(str(e) for e in [b for b in ci.IPAddr]))
        print("ControlPort: " + str(ci.ControlPort))
        print("Timeout: " + str(ci.Timeout))
        print("HTTPPort: " + str(ci.HTTPPort))
        print("MACAddr: " + ".".join(format(e, "02X") for e in [b for b in ci.MACAddr]))
        print("SubNet: " + ".".join(str(e) for e in [b for b in ci.SubNet]))
        print("Gateway: " + ".".join(str(e) for e in [b for b in ci.Gateway]))
        print("SerialNumber: " + str(ci.SerialNumber))
        print("FirmwareVersion: " + str(ci.FirmwareVersion))
        print("HardwareVersion: " + str(ci.HardwareVersion))
        print("-------------")

    class ZESTETM1_CARD_INFO(C.Structure):
        ubyte4 = C.c_ubyte * 4
        ubyte6 = C.c_ubyte * 6
        _fields_ = [
            ("IPAddr", ubyte4),
            ("ControlPort", C.c_ushort),
            ("Timeout", C.c_ulong),
            ("HTTPPort", C.c_ushort),
            ("MACAddr", ubyte6),
            ("SubNet", ubyte4),
            ("Gateway", ubyte4),
            ("SerialNumber", C.c_ulong),
            ("FirmwareVersion", C.c_ulong),
            ("HardwareVersion", C.c_ulong),
        ]


"""
Copyright (c) 2025, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under 
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy (DOE)
and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new contributions must
be made under this license.
"""
