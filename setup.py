# -*- coding: utf-8 -*-
"""
Setup script for nsCamera.

Author: Jeremy Martin Hill (jerhill@llnl.gov)

Copyright (c) 2025, Lawrence Livermore National Security, LLC.  All rights reserved.
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under 
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy (DOE)
and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new contributions must
be made under this license.

Version: 2.1.2     (February 2025)

         2.1.1     (July 2021)
         2.1.0     (October 2020)
         2.0.9     (March 2020)
         2.0.8     (June 2019)
         2.0.7     (January 2019)
         2.0.6     (November 2018)
         2.0.5     (September 2018)
         2.0.4     (July 2018)
         2.0.3     (April 2018)
         2.0.2     (March 2018)
         2.0.1     (February 2018)
         2.0       (February 2018)
         1.3       (January 2018)
         1.2       (May 2017)
         1.1       (March 2017)
         1.0       (January 2017)
"""
# TODO: update to '.toml' setup

from setuptools import setup, find_packages

setup(
    name="nsCamera",
    version="2.1.2",
    author="Jeremy Martin Hill",
    author_email="jerhill@llnl.gov",
    packages=find_packages(exclude=["_archive.*", "output", "*.output", "*.output.*"]),
    install_requires=[
        "pyserial >= 3",
        "numpy >= 1",
        "matplotlib >= 1",
        "cython",
        "joblib",
        "pillow",
        "future",
        "setuptools",
        "h5py"
    ],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "License :: Other/Proprietary License",
        "Topic :: Scientific/Engineering",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ],
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
