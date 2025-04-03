# -*- coding: utf-8 -*-
"""
Subregister object represents a subset of a full register

Author: Matthew Dayton (dayton5@llnl.gov)
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


class SubRegister:
    """
    Represents a subset of a 32-bit register [31..0] starting at 'start_bit' consisting
      of 'width' bits. Consistent with the ICD usage, start_bit is MSB e.g., for [7..0],
      the start_bit is '7'.
    """

    def __init__(
        self,
        board,
        name,
        register,
        start_bit=31,
        width=8,
        writable=False,
        value=255,
        minV=0,
        maxV=5,
    ):
        self.name = name
        self.register = register
        self.addr = board.registers[register]
        self.start_bit = start_bit
        self.width = width
        self.value = value
        self.max_value = 2**width - 1  # used to normalize the input values to 1
        self.min = 0
        self.max = self.max_value
        self.writable = writable
        self.minV = minV
        self.maxV = maxV
        # resolution should be reset after init if actual min and max are different
        self.resolution = (1.0 * maxV - minV) / self.max_value


"""
Copyright (c) 2025, Lawrence Livermore National Security, LLC.  All rights reserved.  
LLNL-CODE-838080

This work was produced at the Lawrence Livermore National Laboratory (LLNL) under 
contract no. DE-AC52-07NA27344 (Contract 44) between the U.S. Department of Energy (DOE)
and Lawrence Livermore National Security, LLC (LLNS) for the operation of LLNL.
'nsCamera' is distributed under the terms of the MIT license. All new contributions must
be made under this license.
"""
