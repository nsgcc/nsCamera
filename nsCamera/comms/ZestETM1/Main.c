// File:      Main.c
//
// Purpose:
//    ZestETM1 Host Library
//    Main functions
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
#if defined(MSVC) || defined(WINGCC)
#include <winsock2.h>
#else
#include <sys/socket.h>
#endif
#include "ZestETM1.h"
#include "Private.h"

/*************************************************
* Main initialisation function.                  *
* Must be called before other ZestETM1 functions. *
*************************************************/
ZESTETM1_STATUS ZestETM1Init(void)
{
#if defined(MSVC) || defined(WINGCC)
    WORD VersionRequested;
    WSADATA WSAData;
    int Error;
     
    VersionRequested = MAKEWORD(2, 2);
    Error = WSAStartup(VersionRequested, &WSAData);
    if (Error!=0)
    {
        ZESTETM1_ERROR_GENERAL("ZestETM1Init", ZESTETM1_SOCKET_ERROR);
    }
     
    // Confirm that the WinSock DLL supports 2.2.
    // Note that if the DLL supports versions greater
    // than 2.2 in addition to 2.2, it will still return
    // 2.2 in Version since that is the version we
    // requested.
    if (LOBYTE(WSAData.wVersion)!=2 ||
        HIBYTE(WSAData.wVersion)!=2)
    {
        WSACleanup( );
        ZESTETM1_ERROR_GENERAL("ZestETM1Init", ZESTETM1_SOCKET_ERROR);
    }
#endif

    return ZESTETM1_SUCCESS;
}

/*************************************************
* Main clean up function.                        *
* Must be called after other ZestETM1 functions.  *
*************************************************/
ZESTETM1_STATUS ZestETM1Close(void)
{
#if defined(MSVC) || defined(WINGCC)
    WSACleanup();
#endif

    return ZESTETM1_SUCCESS;
}
