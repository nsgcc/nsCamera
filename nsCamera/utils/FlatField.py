# -*- coding: utf-8 -*-
"""
Functions for batch flat-field image corrections

***Do not use this file as a template for new code development***

Author: Jeremy Martin Hill (jerhill@llnl.gov)
Author: Matthew Dayton (dayton5@llnl.gov)

Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.

Version: 2.1.1  (July 2021)
"""

import os
import re

import numpy as np
from PIL import Image
from joblib import parallel, delayed
from scipy.stats import theilslopes
from skimage.external.tifffile import imread


def getFilenames(frame="Frame 1"):
    """
    get a list of tiff filenames in current working director for frame
    """
    onlyfiles = next(os.walk("./"))[2]
    return [k for k in onlyfiles if frame in k and "tif" in k]


def getROIvector(imgfilename, roi):
    """
    return a numpy row vector of version of the image
    """
    img = imread(imgfilename)
    vroi = img[(roi[1]) : (roi[3]), (roi[0]) : (roi[2])].flatten()
    return vroi


def tslopes(x, y):
    """
    theilslopes implements a method for robust linear regression.
    It computes the slope as the median of all slopes between paired values.
    """
    val = theilslopes(x, y)
    return [val[0], val[1]]


def generateFF(
    FRAMES=["Frame_0", "Frame_1", "Frame_2", "Frame_3"],
    roi=[0, 0, 512, 1024],
    directory="",
    ncores=-1,
):
    # TODO: documentation
    # use of ROI here not compatible with use of ROI in removeFF

    if directory:
        cwd = os.getcwd()
        newpath = os.path.join(cwd, directory)
        os.chdir(newpath)
    if not FRAMES:
        print("No framelist provided, defaulting to four frames")
        FRAMES = ["Frame_0", "Frame_1", "Frame_2", "Frame_3"]
    for f in FRAMES:
        files = getFilenames(frame=f)
        imgslist = [getROIvector(fn, roi) for fn in files]  # a list of flattened images
        imgsarray = np.vstack(imgslist)  # turn the list into an array
        npix = np.shape(imgsarray)[1]  # total number of pixels
        x = np.median(imgsarray, axis=1)  # median of each image used for flat fielding
        y = []
        for i in range(npix):
            # each member of y represents a pixel, as a list of magnitudes over all the
            #   images
            y.append(imgsarray[:, i])
        # get pixel gain and offset for flatfield ff using Thiel-Sen slopes
        ff = []
        ff = parallel.Parallel(n_jobs=ncores, verbose=5, pre_dispatch="2 * n_jobs")(
            delayed(tslopes)(x, pixel) for pixel in y
        )
        # x is the dependent variable; here uses median of image as characteristic of
        #   noise level
        m, c = zip(*ff)  # separate into gain and offset
        m = np.array(m)
        m[m < 0.1] = 0.1  # handle outliers
        m[m > 1000] = 1000  # handle outliers
        m = 1.0 / m
        m = m.reshape(roi[3] - roi[1], roi[2] - roi[0])  # turn into matrix
        c = np.array(c).reshape(roi[3] - roi[1], roi[2] - roi[0])  # turn into matrix

        with open("px_gain_%s.txt" % f.replace("Frame_", "f"), "w+") as file:
            np.savetxt(file, m)
        with open("px_off_%s.txt" % f.replace("Frame_", "f"), "w+") as file:
            np.savetxt(file, c)


def removeFF(filename, directory="", roi=[0, 0, 512, 1024]):
    if directory:
        cwd = os.getcwd()
        newpath = os.path.join(cwd, directory)
        os.chdir(newpath)
    framenum = re.search("Frame_(\d)", filename).group(1)
    gainFilename = "px_gain_f" + framenum + ".txt"
    gainall = np.loadtxt(gainFilename)
    gain = gainall[(roi[1]) : (roi[3]), (roi[0]) : (roi[2])]
    offFilename = "px_off_f" + framenum + ".txt"
    offsetall = np.loadtxt(offFilename, dtype="uint32")
    offset = offsetall[(roi[1]) : (roi[3]), (roi[0]) : (roi[2])]

    beforeImageall = imread(filename)
    beforeImage = beforeImageall[(roi[1]) : (roi[3]), (roi[0]) : (roi[2])]
    imageMed = np.median(beforeImage)

    flat = imageMed * gain + offset
    flat = flat.clip(0)
    fix = beforeImage - flat
    clipped = fix.clip(0)
    fixinit = clipped.astype("uint16")
    fiximg = Image.fromarray(fixinit)

    fixFilename = filename[:-4] + "ff" + filename[-4:]
    fiximg.save(fixFilename)

def removeFFall(
    directory="",
    FRAMES=["Frame_0", "Frame_1", "Frame_2", "Frame_3"],
    roi=[0, 0, 512, 1024],
):
    cwd = os.getcwd()
    if directory:
        newpath = os.path.join(cwd, directory)
    else:
        newpath = cwd
    os.chdir(newpath)
    files = next(os.walk("./"))[2]
    filelist = []
    for frame in FRAMES:
        filelist.extend([k for k in files if frame in k and "tif" in k])
    for fname in filelist:
        removeFF(fname, directory, roi)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", action="store", dest="directory", default="", help="VRST scan directory"
    )
    parser.add_argument(
        "-f",
        nargs="+",
        action="store",
        dest="frames",
        default="",
        help="Frame numbers to process, eg. -f 2 3",
    )
    args = parser.parse_args()
    framelist = ["Frame_" + str(frame) for frame in args.frames]
    generateFF(framelist, directory=args.directory)

"""
Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.
"""
