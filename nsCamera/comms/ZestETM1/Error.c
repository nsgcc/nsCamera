// File:      Error.c
//
// Purpose:
//    ZestETM1 Host Library
//    Error functions
//
// Version: 1.00
// Date: 11/10/12

// Copyright (C) 2012 Orange Tree Technologies Ltd. All rights reserved.
// Orange Tree Technologies grants the purchaser of a ZestETM1 the right to use and
// modify this source code in any form in designs that target the ZestETM1.
// Orange Tree Technologies prohibits the use of this source code or any modification of
// it in any form in designs that target any other hardware unless the purchaser of the
// ZestETM1 has purchased the appropriate licence from Orange Tree Technologies.
// Contact Orange Tree Technologies if you want to purchase such a licence.

//*****************************************************************************************
//**
//**  Disclaimer: LIMITED WARRANTY AND DISCLAIMER. These designs are
//**              provided to you "as is". Orange Tree Technologies and its licensors 
//**              make and you receive no warranties or conditions, express, implied, 
//**              statutory or otherwise, and Orange Tree Technologies specifically 
//**              disclaims any implied warranties of merchantability, non-infringement,
//**              or fitness for a particular purpose. Orange Tree Technologies does not
//**              warrant that the functions contained in these designs will meet your 
//**              requirements, or that the operation of these designs will be 
//**              uninterrupted or error free, or that defects in the Designs will be 
//**              corrected. Furthermore, Orange Tree Technologies does not warrant or 
//**              make any representations regarding use or the results of the use of the 
//**              designs in terms of correctness, accuracy, reliability, or otherwise.
//**
//**              LIMITATION OF LIABILITY. In no event will Orange Tree Technologies 
//**              or its licensors be liable for any loss of data, lost profits, cost or 
//**              procurement of substitute goods or services, or for any special, 
//**              incidental, consequential, or indirect damages arising from the use or 
//**              operation of the designs or accompanying documentation, however caused 
//**              and on any theory of liability. This limitation will apply even if 
//**              Orange Tree Technologies has been advised of the possibility of such 
//**              damage. This limitation shall apply notwithstanding the failure of the 
//**              essential purpose of any limited remedies herein.
//**
//*****************************************************************************************

#include <stdint.h>
#include "ZestETM1.h"
#include "Private.h"

/******************************************************************************
* Globals                                                                     *
******************************************************************************/
char *ZestETM1_ErrorStrings[] =
{
    "Success (no error)",
    "Error communicating with socket",
    "An unspecified internal error occurred",
    "Status code is out of range",
    "NULL was used illegally as one of the parameter values",
    "Not enough memory to complete the requested operation",
    "The requested connection type is invalid",
    "The requested connection is invalid",
    "The connection was closed unexpectedly",
    "Operation timed out",
    "One of the parameters has an illegal value",

};
ZESTETM1_ERROR_FUNC ZestETM1_ErrorHandler;


/******************************************************************************
* Register a user error handling function to be called                        *
* Set to NULL to disable error callbacks                                      *
******************************************************************************/
ZESTETM1_STATUS ZestETM1RegisterErrorHandler(ZESTETM1_ERROR_FUNC Function)
{
    ZestETM1_ErrorHandler = Function;
    return ZESTETM1_SUCCESS;
}


/******************************************************************************
* Get a human-readable error string for a status code                         *
******************************************************************************/
ZESTETM1_STATUS ZestETM1GetErrorMessage(ZESTETM1_STATUS Status,
                                      char **Buffer)
{
    if (Status>ZESTETM1_MAX_ERROR ||
        (Status<ZESTETM1_ERROR_BASE && Status>=ZESTETM1_MAX_WARNING) ||
        (Status<ZESTETM1_WARNING_BASE && Status>=ZESTETM1_MAX_INFO))
    {
        return ZESTETM1_ILLEGAL_STATUS_CODE;
    }

    *Buffer = ZESTETM1_ERROR_STRING(Status);
    return ZESTETM1_SUCCESS;
}


