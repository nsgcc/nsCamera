# -*- coding: utf-8 -*-
"""
Miscellaneous utilities, including batch processing of images acquired using the 
  nsCamera. These are functions that don't require a cameraAssembler object to be 
  instantiated before use.
  
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

import binascii
import collections
import logging
import os
import sys
from datetime import datetime

import numpy as np
from matplotlib import pyplot as plt
from past.builtins import raw_input
from PIL import Image

# TODO: is the self-reference necessary?
# import nsCamera.utils.misc
from nsCamera.utils import crc16pure


# TODO: check error messages
def makeLogLabels(logtag, label):
    if logtag is None:
        logtag = ""

    logcritbase = "CRITICAL{logtag}: ".format(logtag=logtag)
    logerrbase = "ERROR{logtag}: ".format(logtag=logtag)
    logwarnbase = "WARNING{logtag}: ".format(logtag=logtag)
    loginfobase = "INFO{logtag}: ".format(logtag=logtag)
    logdebugbase = "DEBUG{logtag}: ".format(logtag=logtag)

    logcrit = "{base}{label}".format(base=logcritbase, label=label)
    logerr = "{base}{label}".format(base=logerrbase, label=label)
    logwarn = "{base}{label}".format(base=logwarnbase, label=label)
    loginfo = "{base}{label}".format(base=loginfobase, label=label)
    logdebug = "{base}{label}".format(base=logdebugbase, label=label)

    return logcrit, logerr, logwarn, loginfo, logdebug


def getEnter(text):
    """
    Wait for enter key to be pressed.

    Args:
        text: message asking for keypress
    """
    python, _, _, _, _ = sys.version_info
    if python >= 3:
        input(text)
    else:
        raw_input(text)


def checkCRC(rval):
    """
    Calculate CRC for rval[:-4] and compare with expected CRC in rval[-4:]

    Args:
        rval: hexadecimal string

    Returns:
        boolean, True if CRCs match, False if they don't match or the input is invalid
    """
    if not isinstance(rval, str) or len(rval) < 5:
        logging.error("ERROR: checkCRC: Invalid input: {rval}".format(rval=rval))
        return False
    data_crc = int(rval[-4:], base=16)
    CRC_calc = crc16pure.crc16xmodem(str2bytes(rval[:-4]))
    return CRC_calc == data_crc


def str2bytes(astring):
    """
    Python-version-agnostic converter of hexadecimal strings to bytes

    Args:
        astring: hexadecimal string without '0x'

    Returns:
        byte string equivalent to input string
    """

    python, _, _, _, _ = sys.version_info
    if python >= 3:
        try:
            dbytes = binascii.a2b_hex(astring)
        except:
            logging.error(
                "ERROR: str2bytes: invalid input: '{astring}'; returning zero"
                " byte".format(astring=astring)
            )
            dbytes = b"\x00"
    else:
        try:
            dbytes = astring.decode("hex")
        except:
            logging.error(
                "ERROR: str2bytes: invalid input: '{astring}'; returning zero "
                " byte".format(astring=astring)
            )
            dbytes = b"\x00"
    return dbytes


def bytes2str(bytesequence):
    """
    Python-version-agnostic converter of bytes to hexadecimal strings

    Args:
        bytesequence: sequence of bytes as string (Py2) or bytes (Py3)

    Returns:
        hexadecimal string representation of 'bytes' without '0x'
    """
    try:
        estring = binascii.b2a_hex(bytesequence)
    except TypeError:
        logging.error(
            "ERROR: bytes2str: Invalid byte sequence: '{bytesequence}'; returning an"
            " empty string".format(bytesequence=bytesequence)
        )
        return ""
    python, _, _, _, _ = sys.version_info
    if python >= 3:
        estring = str(estring)[2:-1]
    return estring


def str2nparray(valstring):
    """
    Convert string into array of uint16s

    Args:
        valstring: string of hexadecimal characters

    Returns:
        numpy array of uint16
    """
    if not isinstance(valstring, str):
        logging.error(
            "ERROR: str2nparray: Invalid input: {valstring} is not a string. Returning"
            " an empty array".format(valstring=valstring)
        )
        return np.array([])
    stringlen = len(valstring)
    arraylen = int(stringlen / 4)
    outarray = np.empty(int(arraylen), dtype="uint16")

    for i in range(0, arraylen):
        try:
            outarray[i] = int(valstring[4 * i : 4 * i + 4], 16)
        except ValueError:
            logging.error(
                "ERROR: str2nparray: input string does not represent a hexadecimal"
                " integer. Returning an empty array"
            )
            return np.array([])
    return outarray


def flattenlist(x):
    """
    Flatten list of lists recursively into single list
    """
    python, _, _, _, _ = sys.version_info
    try:
        if python >= 3:
            if isinstance(x, collections.abc.Iterable):
                return [a for i in x for a in flattenlist(i)]
            else:
                return [x]
        else:
            if isinstance(x, collections.Iterable):
                return [a for i in x for a in flattenlist(i)]
            else:
                return [x]
    except RecursionError:
        logging.error(
            "ERROR: flattenlist: input '{x}' is pathological and cannot be flattened."
            " Attempting to return the input unchanged"
        )
        return x


class fakeCA:
    """
    Fake 'cameraAssembler' object to use as a parameter object in offline functions.
      Returned by generateFrames(), it contains the frame details required to save and
      plot images.
    """

    def __init__(
        self,
        sensorname="icarus2",
        firstframe=0,
        lastframe=3,
        width=512,
        height=1024,
        padToFull=True,
        firstrow=0,
        lastrow=1023,
        maxwidth=512,
        maxheight=1024,
        bytesperpixel=2,
        interlacing=None,
        columns=1,
        logtag=None,
    ):
        
        # add section to specify parameters for specific sensor
        # in _init, set everything to None
        # use sensorname to select parameter dictionary
        # if None, assign to parameter from dictionary
        # e.g.,
        # daeddict = {
            # "firstframe" : 0
        # if sensorname is "daedalus"
        #    sensdict = daeddict
        # if firstframe is None:
        #    firstframe = sensdict["firstframe"]
        # ...
        #
        # Need to be sure explicit parameters get set into sensor
        # If this doesn't work, try changing parameters after initialization in load  
        
    
        
        
        
        self.sensorname = sensorname
        self.boardname = None
        self.padToFull = padToFull
        if logtag is None:
            self.logtag = ""
        else:
            self.logtag = logtag

        self.logcritbase = "CRITICAL" + self.logtag + ": "
        self.logerrbase = "ERROR" + self.logtag + ": "
        self.logwarnbase = "WARNING" + self.logtag + ": "
        self.loginfobase = "INFO" + self.logtag + ": "
        self.logdebugbase = "DEBUG" + self.logtag + ": "

        self.logcrit = self.logcritbase + "[FS] "
        self.logerr = self.logerrbase + "[FS] "
        self.logwarn = self.logwarnbase + "[FS] "
        self.loginfo = self.loginfobase + "[FS] "
        self.logdebug = self.logdebugbase + "[FS] "

        if self.sensorname == "icarus":
            import nsCamera.sensors.icarus as snsr
        elif self.sensorname == "icarus2":
            import nsCamera.sensors.icarus2 as snsr
        elif self.sensorname == "daedalus":
            import nsCamera.sensors.daedalus as snsr

        self.sensor = snsr(self)

    def partition(self, parsed, columns):
        # return nsCamera.utils.misc.partition(self, parsed, columns)
        return partition(self, parsed, columns)


def generateFrames(camassem, data, columns=1):
    """
    Processes data stream from board into frames and applies sensor-specific parsing.
      Generates padded data for full-size option of setRows.
    If used for offline processing, replace the 'self' object with the parameter object
      returned by loadDumpedData().
    If the data stream is incomplete (e.g., from an interrupted download), the data is
      padded with zeros to the correct length.

    Args:
        self: during normal operation, is the CameraAssembler object. During offline
          operation, is a parameters object as returned by loadDumpedData()
        data: text stream from board or loaded file, or numpy from loaded file
        columns: 1 for single image, 2 for separate hemisphere images

    Returns: list of parsed frames
    """
    logging.debug("DEBUG" + camassem.logtag + ": generateFrames")
    if isinstance(data[0], str):
        allframes = str2nparray(data)
    else:
        allframes = data
    nframes = camassem.sensor.lastframe - camassem.sensor.firstframe + 1
    frames = [0] * nframes
    framesize = camassem.sensor.width * (
        camassem.sensor.lastrow - camassem.sensor.firstrow + 1
    )
    if hasattr(camassem, "ca"):
        padIt = camassem.ca.padToFull
    else:
        padIt = camassem.padToFull
    if padIt:
        toprows = camassem.sensor.firstrow
        botrows = (camassem.sensor.maxheight - 1) - camassem.sensor.lastrow
        padtop = np.zeros(toprows * camassem.sensor.maxwidth, dtype=int)
        padbot = np.zeros(botrows * camassem.sensor.maxwidth, dtype=int)
        for n in range(nframes):
            thisframe = np.concatenate(
                (padtop, allframes[n * framesize : ((n + 1) * framesize)], padbot)
            )
            frames[n] = thisframe
    else:
        for n in range(nframes):
            frames[n] = allframes[n * framesize : (n + 1) * framesize]
    # self.clearStatus()
    parsed = camassem.sensor.parseReadoff(frames, columns)
    return parsed


def loadDumpedData(
    filename="frames.txt",
    path=None,
    filetype="txt",
    sensor="daedalus",
    firstframe=None,
    lastframe=None,
    width=None,
    height=None,
    padToFull=None,
    firstrow=None,
    lastrow=None,
    maxwidth=None,
    maxheight=None,
    bytesperpixel=None,
    interlacing=None,
    columns=1,
):
    """_summary_

        Output can be piped directly to saveTiffs:
            pars,frames=loadDumpedData(filename="Dump.npy")
            saveTiffs(pars,frames)
    Args:
        filename (str, optional): _description_. Defaults to "frames.txt".
        path (_type_, optional): _description_. Defaults to None.
        filetype (str, optional): _description_. Defaults to "txt".
        sensor (str, optional): _description_. Defaults to "daedalus".
        firstframe (_type_, optional): _description_. Defaults to None.
        lastframe (_type_, optional): _description_. Defaults to None.
        width (_type_, optional): _description_. Defaults to None.
        height (_type_, optional): _description_. Defaults to None.
        padToFull (_type_, optional): _description_. Defaults to None.
        firstrow (_type_, optional): _description_. Defaults to None.
        lastrow (_type_, optional): _description_. Defaults to None.
        maxwidth (_type_, optional): _description_. Defaults to None.
        maxheight (_type_, optional): _description_. Defaults to None.
        interlacing (_type_, optional): _description_. Defaults to None.
        columns (int, optional): _description_. Defaults to 1.


    Returns:
        Tuple (parameter object, list of data frames)
    """
    logging.debug("DEBUG: loadDumpedData")
    if sensor.lower() == "daedalus":
        import nsCamera.sensors.daedalus as snsr
    elif sensor.lower() == "icarus":
        import nsCamera.sensors.icarus as snsr
    elif sensor.lower() == "icarus2":
        import nsCamera.sensors.icarus2 as snsr
    else:
        logging.error(
            "ERROR loadDumpedData: invalid sensor type provided, defaulting to icarus2"
        )
        import nsCamera.sensors.icarus2 as snsr

    # def buildEmptyFrames():
    #     cols = [0] * 512
    #     frame = np.array([cols] * (lastrow - firstrow + 1))
    #     return [frame] * (lastframe - firstframe + 1)
    
    def buildEmptyFrames():
        cols = [0] * 512
        frame = np.array([cols]//(interlacing+1) * (lastrow - firstrow + 1))
        return [frame] * (lastframe - firstframe + 1) *(interlacing+1)

    # get defaults from class declarations if not specified as parameter
    if firstframe is None:
        firstframe = snsr.firstframe
    if lastframe is None:
        lastframe = snsr.lastframe
    # TODO: first frame number
    if width is None:
        width = snsr.width
    if height is None:
        height = snsr.height
    if firstrow is None:
        firstrow = snsr.firstrow
    if lastrow is None:
        lastrow = snsr.lastrow
    if maxwidth is None:
        maxwidth = snsr.maxwidth
    if maxheight is None:
        maxheight = snsr.maxheight
    if bytesperpixel is None:
        bytesperpixel = snsr.bytesperpixel
    if interlacing is None:
        interlacing = snsr.interlacing

    parameters = fakeCA(
        sensor,
        firstframe,
        lastframe,
        width,
        height,
        padToFull,
        firstrow,
        lastrow,
        maxwidth,
        maxheight,
        bytesperpixel,
        interlacing,
    )

    if path is None:
        path = os.path.join(os.getcwd())
    datafile = os.path.join(path, filename)
    if filename[-3:].lower() == "txt":
        filetype = "txt"
    elif filename[-3:].lower() == "npy":
        filetype = "npy"
    # TODO: return empty frames if error

    if filetype == "npy":
        expectedlength = (lastframe - firstframe + 1) * (lastrow - firstrow + 1) * width
        try:
            f = np.load(datafile)
            padding = expectedlength - len(f)
            if padding:
                logging.warning(
                    "{logwarn}loadDumpedData: Payload is shorter than expected."
                    " Padding with '0's".format(logwarn=parameters.logwarn)
                )
                f = np.pad(f, (0, padding), "constant", constant_values=(0))
            frames = generateFrames(parameters, f, columns)
            return parameters, frames

        except OSError as err:
            logging.error(
                "{logerr}loadDumpedData: OS error: {err}. Returning empty"
                " frames.".format(logerr=parameters.logerr, err=err)
            )
            return parameters, buildEmptyFrames()
        except:
            logging.error(
                "{logerr}loadDumpedData: Unexpected error: {err}. Returning empty"
                " frames.".format(logerr=parameters.logerr, err=str(sys.exc_info()[0]))
            )
            return parameters, buildEmptyFrames()
    # if filetype is not explicitly npy, try loading as text
    else:
        # Payload size as string implied by provided parameters
        expectedlength = (
            4 * (lastframe - firstframe + 1) * (lastrow - firstrow + 1) * width
        )

        try:
            f = open(datafile, "r")
            s = f.read()

            padding = expectedlength - len(s)
            if padding:
                logging.warning(
                    "{logwarn}loadDumpedData: Payload is shorter than expected."
                    " Padding with '0's".format(logwarn=parameters.logwarn)
                )
                s = s.ljust(expectedlength, "0")

            frames = generateFrames(parameters, s)
            return parameters, frames

        except OSError as err:
            logging.error(
                "{logerr}loadDumpedData: OS error: {err}. Returning empty"
                " frames.".format(logerr=parameters.logerr, err=err)
            )
            return parameters, buildEmptyFrames()
        except ValueError:
            logging.error(
                "{logerr}loadDumpedData: Could not convert data to an integer."
                " Returning empty frames.".format(logerr=parameters.logerr)
            )
            return parameters, buildEmptyFrames()
        except:
            logging.error(
                "{logerr}loadDumpedData: Unexpected error: {err}. Returning empty"
                " frames.".format(logerr=parameters.logerr, err=str(sys.exc_info()[0]))
            )
            return parameters, buildEmptyFrames()


def saveTiffs(
    self,
    frames,
    path=None,
    filename="Frame",
    prefix=None,
    index=None,
):
    """
    Save numpy array or list of numpy arrays or single array to disk as individual
      tiffs, with frame number appended to filename. If used for standalone, use the
      parameter object returned by loadDumpedData() as the first argument

    Args:
        self: during normal operation, is cameraAssembler object. During offline
          operation, is the parameter object returned by loadDumpedData()
        frames: numpy array or list of numpy arrays
        path: save path, defaults to './output'
        filename: defaults to 'Frame' followed by frame number
        prefix: prepended to 'filename', defaults to time/date
          (e.g. '160830-124704_')
        index: number to start frame numbering

    Returns:
        Error string
    """
    # logging.info("INFO" + self.logtag + ": saveTiffs")
    logging.info("{loginfo}: saveTiffs".format(loginfo=self.loginfo))
    err = ""
    if path is None:
        path = os.path.join(os.getcwd(), "output")
    if prefix is None:
        prefix = datetime.now().strftime("%y%m%d-%H%M%S%f")[:-5] + "_"
    if not os.path.exists(path):
        os.makedirs(path)
    if index is None:
        firstnum = self.sensor.firstframe
    else:
        firstnum = index

    if not isinstance(frames, list):
        frames = [frames]

    # if this is a text string from fast readoff, do the numpy conversion now
    if isinstance(frames[0], str):
        frames = generateFrames(frames)

    framestemp = np.copy(frames)

    for idx, frame in enumerate(framestemp):
        if idx < len(framestemp) / 2:
            interlacing = self.sensor.interlacing[0]
        else:
            interlacing = self.sensor.interlacing[1]
        try:
            if self.padToFull:
                frame = np.reshape(
                    frame, (self.sensor.maxheight // (interlacing + 1), -1)
                )
            else:
                frame = np.reshape(
                    frame,
                    (
                        (self.sensor.lastrow - self.sensor.firstrow + 1)
                        // (interlacing + 1),
                        -1,
                    ),
                )
            frame_16bit = frame.astype(np.int16) 
            frameimg = Image.fromarray(frame_16bit, "I;16")
            namenum = filename + "_%d" % firstnum
            tifpath = os.path.join(path, prefix + namenum + ".tif")
            frameimg.save(tifpath)
            firstnum += 1
        except Exception:
            err = "saveTiffs: unable to save images"
            # logging.error("ERROR" + self.logtag + ": " + err)
            logging.error("{logerr}: {err}".format(logerr=self.logerr, err=err))
    return err

## TODO: refactor common code with saveTiffs
def plotFrames(self, frames, index=None):
    """
    Plot frame or list of frames as individual graphs.

    Args:
        self: during normal operation, is cameraAssembler object. During offline
          operation, is the parameter object returned by loadDumpedData()
        frames: numpy array or list of numpy arrays
        index: number to start frame numbering

    Returns:
        Error string
    """
    # logging.info(self.loginfo + "plotFrames: index = " + str(index))
    logging.info(
        "{loginfo}: plotFrames: index = {index}".format(
            loginfo=self.loginfo, index=index
        )
    )
    err = ""
    if index is None:
        nframe = self.sensor.firstframe
    else:
        nframe = index

    if not isinstance(frames, list):
        frames = [frames]

    # if this is a text string from fast readoff, do the numpy conversion now
    if isinstance(frames[0], str):
        frames = generateFrames(frames)

    framestemp = np.copy(frames)
    
    for idx, frame in enumerate(framestemp):
        if idx < len(framestemp) / 2:
            interlacing = self.sensor.interlacing[0]
        else:
            interlacing = self.sensor.interlacing[1]
        try:
            if self.padToFull:
                frame = np.reshape(
                    frame, (self.sensor.maxheight // (interlacing + 1), -1)
                )
            else:
                frame = np.reshape(
                    frame,
                    (
                        (self.sensor.lastrow - self.sensor.firstrow + 1)
                        // (interlacing + 1),
                        -1,
                    ),
                )
        except:
            err = "{logerr}plotFrames: unable to plot frame".format(logerr=self.logerr)
            logging.error(err)
            continue
        plt.imshow(frame, cmap="gray")
        name = "Frame %d" % nframe
        plt.title(name)
        plt.show()
        nframe += 1
    return err


#  TODO: separate images for hemispheres with different timing


def partition(self, frames, columns):
    """
    Extracts interlaced frames and divides images by hemispheres. If interlacing does
      not evenly divide the height, remainder lines will be dropped

    Args:
        self: during normal operation, is sensor object. During offline
          operation, is the parameter.sensor object returned by loadDumpedData()
        frames: list of full-sized frames
        columns: 1 for single image, 2 for separate hemisphere images

    Returns: list of deinterlaced frames
    """
    logging.debug(
        "{logdebug}partition: columns = {columns}, interlacing = {interlacing}".format(
            logdebug=self.logdebug, columns=columns, interlacing=self.sensor.interlacing
        )
    )

    def unshuffle(frames, ifactor):
        warntrimmed = False
        if self.padToFull:
            newheight = self.sensor.maxheight // (ifactor + 1)
            if newheight != (self.sensor.maxheight / (ifactor + 1)):
                warntrimmed = True
        else:
            newheight = self.sensor.height // (ifactor + 1)
            if newheight != (self.sensor.height / (ifactor + 1)):
                warntrimmed = True

        if warntrimmed:
            logging.warning(
                "{logwarn} partition: interlacing setting requires dropping of lines to"
                " maintain consistent frame sizes ".format(logwarn=self.logwarn)
            )
        delaced = []
        for frame in frames:
            for sub in range(ifactor + 1):
                current = np.zeros((newheight, self.sensor.width // columns), dtype=int)
                for line in range(newheight):
                    current[line] = frame[(ifactor + 1) * line + sub]
                delaced.append(current)
        nframes = self.sensor.lastframe - self.sensor.firstframe + 1
        resorted = [None] * len(delaced)
        for sub in range(ifactor + 1):
            for idx, frame in enumerate(frames):
                resorted[sub * nframes + idx] = delaced[idx * (ifactor + 1) + sub]
        return resorted

    if self.sensor.interlacing[0] != self.sensor.interlacing[1]:
        columns = 2  # true even if not explicitly requested by readoff
    if columns == 1:
        if self.sensor.interlacing == [0, 0]:  # don't do anything
            return frames
        else:
            return unshuffle(frames, self.sensor.interlacing[0])
    else:
        # reshape frame into the proper shape, then split horizontally
        if self.padToFull:
            framesab = [
                np.hsplit(frame.reshape(self.sensor.maxheight, -1), 2)
                for frame in frames
            ]
        else:
            framesab = [
                np.hsplit(
                    frame.reshape((self.sensor.lastrow - self.sensor.firstrow + 1), -1),
                    2,
                )
                for frame in frames
            ]
        framesa = [hemis[0] for hemis in framesab]
        framesb = [hemis[1] for hemis in framesab]
    if self.sensor.interlacing == [0, 0]:
        return framesa + framesb
    else:
        return unshuffle(framesa, self.sensor.interlacing[0]) + unshuffle(
            framesb, self.sensor.interlacing[1]
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
