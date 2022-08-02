# -*- coding: utf-8 -*-
"""
Setup script for nsCamera.

Author: Jeremy Martin Hill (jerhill@llnl.gov)

Copyright (c) 2022, Lawrence Livermore National Security, LLC.  All rights reserved.
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy
(DOE) and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new
contributions must be made under this license.

Version: 2.1.1     (July 2021)
Version: 2.1.0     (October 2020)
Version: 2.0.9     (March 2020)
Version: 2.0.8     (June 2019)
Version: 2.0.7     (January 2019)
Version: 2.0.6     (November 2018)
Version: 2.0.5     (September 2018)
Version: 2.0.4     (July 2018)
Version: 2.0.3     (April 2018)
Version: 2.0.2     (March 2018)
Version: 2.0.1     (February 2018)
Version: 2.0       (February 2018)
Version: 1.3       (January 2018)
Version: 1.2       (May 2017)
Version: 1.1       (March 2017)
Version: 1.0       (January 2017)
"""

from setuptools import setup, find_packages
from Cython.Build import cythonize

setup(
    name="nsCamera",
    version="2.1.1",
    packages=find_packages(exclude=["_archive.*", "output", "*.output", "*.output.*"]),
    install_requires=["pyserial >= 3", "numpy >= 1", "matplotlib >= 1", "cython"],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License".
        "Topic :: Scientific/Engineering",
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ],
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
