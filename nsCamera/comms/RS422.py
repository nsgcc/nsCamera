# -*- coding: utf-8 -*-
"""
RS422 driver for nsCamera

Author: Brad Funsten (funsten1@llnl.gov)
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
import sys
import time  # to time the script

import serial
import serial.tools.list_ports  # for RS422 serial link setup

from nsCamera.utils.misc import generateFrames, str2bytes, bytes2str, checkCRC


class RS422:
    """
    Code to manage RS422 connection. Will automatically query available COM interfaces
      until a board is found. Use the 'port=x' parameter in cameraAssembler call to
      specify a particular COM interface.

    Exposed methods:
        arm() - Puts camera into wait state for external trigger
        readFrames() - waits for data ready register flag, then copies camera image data
          into numpy arrays
        readoff() - waits for data ready register flag, then copies camera image data
          into numpy arrays; returns payload, payload size, and error message
        sendCMD(pkt) - sends packet object via serial port
        readSerial(size, timeout) - read 'size' bytes from serial port
        writeSerial(cmd) - submits string 'cmd' (assumes string is preformed packet)
        closeDevice() - close serial connections
    """

    def __init__(self, camassem, baud=921600, par="O", stop=1):
        """
        Args:
            camassem: parent cameraAssembler object
            baud: bits per second
            par: parity type
            stop: number of stop bits
        """
        self.ca = camassem
        self.logcrit = self.ca.logcritbase + "[RS422] "
        self.logerr = self.ca.logerrbase + "[RS422] "
        self.logwarn = self.ca.logwarnbase + "[RS422] "
        self.loginfo = self.ca.loginfobase + "[RS422] "
        self.logdebug = self.ca.logdebugbase + "[RS422] "
        logging.info(self.loginfo + "initializing RS422 comms object")
        logging.debug(
            self.logdebug
            + "Init: baud = "
            + str(baud)
            + "; par = "
            + str(par)
            + "; stop = "
            + str(stop)
        )
        self.mode = 0
        self.baud = baud  # Baud rate (bits/second)
        self.par = par  # Parity bit
        self.stop = stop  # Number of stop bits
        self.read_timeout = 1  # default timeout for ordinary packets
        self.write_timeout = 1
        # TODO: make datatimeout a cameraAssembler parameter
        self.datatimeout = 60  # timeout for data read
        logging.debug(
            self.logdebug + "Data timeout = " + str(self.datatimeout) + " seconds"
        )
        self.PY3 = sys.version_info > (3,)
        self.skipError = False
        port = ""
        ports = list(serial.tools.list_ports.comports())
        logging.debug(self.logdebug + "Comports: " + str(ports))
        for p, desc, add in ports:
            if self.ca.port is None or p == "COM" + str(self.ca.port):
                logging.info(self.loginfo + "found comm port " + p)
                try:
                    with serial.Serial(
                        p,
                        self.baud,
                        parity=self.par,
                        timeout=0.01,
                        write_timeout=0.01,
                    ) as ser:
                        ser.write(str2bytes("aaaa1000000000001a84"))
                        time.sleep(1)
                        s = ser.read(10)
                        resp = bytes2str(s)
                        logging.debug(self.logdebug + "Init response: " + str(resp))
                        if (
                            resp[0:5].lower() == "aaaa9"
                        ):  # TODO: add check for RS422 bit in board description
                            boardid = resp[8:10]
                            if boardid == "00":
                                logging.critical(
                                    self.logcrit + "SNLrevC board detected - not "
                                    "compatible with nsCamera >= 2.0"
                                )
                                sys.exit(1)
                            elif boardid == "81":
                                logging.info(self.loginfo + "LLNLv1 board detected")
                            elif boardid == "84":
                                logging.info(self.loginfo + "LLNLv4 board detected")
                            else:
                                logging.info(
                                    self.loginfo + "unidentified board detected"
                                )
                            logging.info(self.loginfo + "connected to " + p)
                            port = p
                            ser.reset_input_buffer()
                            ser.reset_output_buffer()
                            break
                except Exception as e:
                    logging.error(self.logerr + "port identification: " + str(e))
        if port == "":
            if self.ca.port:
                logging.critical(
                    self.logcrit + "No usable board found at port " + str(self.ca.port)
                )
                sys.exit(1)
            else:
                logging.critical(self.logcrit + "No usable board found")
                sys.exit(1)
        self.port = port  # COM port to use for RS422 link
        self.ca.port = port[3:]  # re-extract port number from com name

        self._ser = serial.Serial(  # Class RS422
            port=self.port,
            baudrate=self.baud,
            parity=self.par,
            stopbits=self.stop,
            timeout=self.read_timeout,  # timeout for serial read
            bytesize=serial.EIGHTBITS,
        )
        self.payloadsize = (
            self.ca.sensor.width
            * self.ca.sensor.height
            * self.ca.sensor.nframes
            * self.ca.sensor.bytesperpixel
        )
        logging.debug(
            self.logdebug + "Payload size: " + str(self.payloadsize) + " bytes"
        )
        self._ser.flushInput()
        if not self._ser.is_open:
            logging.critical(self.logcrit + "Unable to open serial connection")
            sys.exit(1)

    def serialClose(self):
        """
        Close serial interface
        """
        logging.debug(self.logdebug + "serialclose")
        self._ser.close()  # close serial interface COM port

    def sendCMD(self, pkt):
        """
        Submit packet and verify response packet. Recognizes readoff packet and adjusts
        read size and timeout appropriately

        Args:
            pkt: Packet object

        Returns:
            tuple (error, response string)
        """
        pktStr = pkt.pktStr()
        logging.debug(self.logdebug + "sendCMD packet: " + str(pktStr))
        self._ser.flushInput()
        time.sleep(0.01)  # wait 10 ms in between flushing input and output buffers
        self._ser.flushOutput()
        self.ca.writeSerial(pktStr)
        err0 = ""
        err = ""
        resp = ""
        tries = 3  # TODO: make a function parameter?

        if (
            hasattr(self.ca, "board")
            and pktStr[4] == "0"
            and pktStr[5:8] == self.ca.board.registers["SRAM_CTL"]
        ):
            # download data payload
            logging.info(
                self.loginfo + "Payload size (bytes) = " + str(self.payloadsize)
            )
            crcresp0 = ""
            crcresp1 = ""
            smallresp = ""
            emptyResponse = False
            wrongSize = False
            # TODO: refactor payload error management to another method
            for i in range(tries):
                err, resp = self.readSerial(
                    self.payloadsize + 20, timeout=self.datatimeout
                )
                if err:
                    logging.error(
                        self.logerr + "sendCMD: read payload failed " + pktStr + err
                    )
                    self.ca.payloaderror = True
                else:
                    if not len(resp):
                        err0 = self.logerr + "sendCMD: empty response from board"
                        logging.error(err0)
                        emptyResponse = True
                        self.ca.payloaderror = True
                    elif len(resp) != 2 * (self.payloadsize + 20):
                        err0 = (
                            self.logerr
                            + "sendCMD: incorrect response; expected "
                            + str(self.payloadsize + 20)
                            + " bytes, received "
                            + str(len(resp) // 2)
                        )
                        logging.error(err0)
                        wrongSize = True
                        smallresp = resp
                        self.ca.payloaderror = True
                    elif not checkCRC(resp[4:20]):
                        err0 = (
                            self.logerr
                            + "sendCMD: "
                            + pktStr
                            + " - payload preface CRC fail"
                        )
                        logging.error(err0)
                        self.ca.payloaderror = True
                        crcresp1 = resp
                    elif not checkCRC(resp[24:]):
                        err0 = (
                            self.logerr + "sendCMD: " + pktStr + " - payload CRC fail"
                        )
                        logging.error(err0)
                        self.ca.payloaderror = True
                        crcresp0 = resp
                    err += err0
                time.sleep(5)
                if self.ca.payloaderror:
                    # keep best results over multiple tries; e.g., if first try is
                    #   bad CRC and second try is an incomplete payload, use the
                    #   first payload
                    if i == tries - 1:
                        if crcresp0:
                            logging.error(
                                self.logerr + "sendCMD: Unable to acquire "
                                "CRC-confirmed payload after "
                                + str(tries)
                                + " attempts. Continuing with unconfirmed payload"
                            )
                            resp = crcresp0
                        elif crcresp1:
                            logging.error(
                                self.logerr + "sendCMD: Unable to acquire "
                                "CRC-confirmed readoff after "
                                + str(tries)
                                + " attempts. Continuing with unconfirmed payload"
                            )
                            resp = crcresp1
                        elif wrongSize:
                            logging.error(
                                self.logerr + "sendCMD: Unable to acquire complete "
                                "payload after "
                                + str(tries)
                                + " attempts. Dumping datastream to file."
                            )
                            resp = smallresp
                            self.ca.dumpNumpy(resp)
                        elif emptyResponse:
                            logging.error(
                                self.logerr + "sendCMD: Unable to acquire any "
                                "payload after " + str(tries) + " attempts."
                            )
                    else:
                        logging.info(
                            self.loginfo + "Retrying download, attempt #" + str(i + 1)
                        )
                        err = ""
                        err0 = ""
                        self.ca.payloaderror = False
                        self.ca.writeSerial(pktStr)
                else:
                    logging.info(self.loginfo + "Download successful")
                    if self.ca.boardname == "llnl_v4":
                        # self.ca.setSubregister('SWACK','1')
                        pass
                    break

        else:
            # non-payload messages and workaround for initial setup before board object
            #   has been initialized
            time.sleep(0.03)
            self._ser.timeout = 0.02
            err, resp = self.readSerial(10)
            logging.debug(self.logdebug + "sendCMD response: " + str(resp))
            if err:
                logging.error(
                    self.logerr + "sendCMD: readSerial failed (regular packet) " + err
                )
            elif not checkCRC(resp[4:20]):
                err = self.logerr + "sendCMD- regular packet CRC fail: " + resp
                logging.error(err)
        return err, resp

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

    def readoff(self, waitOnSRAM, timeout, fast, columns=1):
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
              in bytes, payload error flag)
            NOTE: This reduces readoff by <1 second, so will have no noticeable impact
              when using RS422
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
        errortemp = False

        # Wait for data to be ready on board, turns off error messaging
        # Skip wait only if explicitly tagged 'False' ('None' defaults to True)
        if waitOnSRAM is not False:
            logging.getLogger().setLevel(logging.CRITICAL)
            self.ca.waitForSRAM(timeout)
            logging.getLogger().setLevel(self.ca.verblevel)

        # Retrieve data
        err, rval = self.ca.readSRAM()
        if err:
            logging.error(self.logerr + "Error detected in readSRAM")
        time.sleep(0.3)
        logging.debug(self.logdebug + "readoff: first 64 chars: " + str(rval[0:64]))
        # extract only the read burst data. Remove header & CRC footer
        read_burst_data = rval[36:-4]

        # Payload size as string implied by provided parameters
        expectedlength = (
            4
            * (self.ca.sensor.lastframe - self.ca.sensor.firstframe + 1)
            * (self.ca.sensor.lastrow - self.ca.sensor.firstrow + 1)
            * self.ca.sensor.width
        )
        padding = expectedlength - len(read_burst_data)
        if padding:
            logging.warning(
                "{logwarn}readoff: Payload is shorter than expected."
                " Padding with '0's".format(logwarn=self.logwarn)
            )
            read_burst_data = read_burst_data.ljust(expectedlength, "0")

        if fast:
            return read_burst_data, len(read_burst_data) // 2, errortemp
        else:
            parsed = generateFrames(self.ca, read_burst_data, columns)
            return parsed, len(read_burst_data) // 2, errortemp

    def writeSerial(self, outstring, timeout):
        """
        Transmit string to board

        Args:
            outstring: string to write
            timeout: serial timeout in sec
        Returns:
            integer length of string written to serial port
        """
        logging.debug(
            self.logdebug
            + "writeSerial: outstring = "
            + str(outstring)
            + "; timeout = "
            + str(timeout)
        )
        if timeout:
            self._ser.timeout = timeout
        else:
            self._ser.timeout = self.write_timeout
        lengthwritten = self._ser.write(str2bytes(outstring))
        self._ser.timeout = self.read_timeout  # reset if changed above
        return lengthwritten

    def readSerial(self, size, timeout=None):
        """
        Read bytes from the serial port. Does not verify packets.

        Args:
           size: number of bytes to read
           timeout: serial timeout in sec

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
        err = ""
        if timeout:
            self._ser.timeout = timeout
        else:
            self._ser.timeout = self.read_timeout
        resp = self._ser.read(size)
        if len(resp) < 10:  # bytes
            err += (
                self.logerr + "readSerial : packet too small: '" + bytes2str(resp) + "'"
            )
            logging.error(err)
        return err, bytes2str(resp)

    def closeDevice(self):
        """
        Close primary serial interface
        """
        logging.debug(self.logdebug + "Closing RS422 connection")
        self._ser.close()


"""
Copyright (c) 2025, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under 
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy (DOE)
and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new contributions must
be made under this license.
"""
