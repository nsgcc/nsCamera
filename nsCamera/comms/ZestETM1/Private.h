// File:      Private.h
//
// Purpose:
//    ZestETM1 Host Library
//    Internal header file
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
#include "Winsock2.h"
#include "Ws2tcpip.h"
#else
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <arpa/inet.h>
typedef int SOCKET;
#define SD_BOTH SHUT_RDWR
#define closesocket close
#endif

/**************
* Error macro *
**************/
extern ZESTETM1_ERROR_FUNC ZestETM1_ErrorHandler;
#define ZESTETM1_ERROR(f, x) \
    { \
        if (ZestETM1_ErrorHandler!=NULL) \
            ZestETM1_ErrorHandler(f, CardInfo, x, ZESTETM1_ERROR_STRING(x)); \
        return (x); \
    }
#define ZESTETM1_ERROR_GENERAL(f, x) \
    { \
        if (ZestETM1_ErrorHandler!=NULL) \
            ZestETM1_ErrorHandler(f, NULL, x, ZESTETM1_ERROR_STRING(x)); \
        return (x); \
    }
#define ZESTETM1_ERROR_CONN(f, x) \
    { \
        if (ZestETM1_ErrorHandler!=NULL) \
        ZestETM1_ErrorHandler(f, (Conn!=NULL ? Conn->CardInfo : NULL), x, ZESTETM1_ERROR_STRING(x)); \
        return (x); \
    }
#define ZESTETM1_ERROR_STRING(x) \
    ZestETM1_ErrorStrings[(x)>=ZESTETM1_ERROR_BASE ? \
                            (x)-ZESTETM1_ERROR_BASE+(ZESTETM1_MAX_INFO-ZESTETM1_INFO_BASE)+(ZESTETM1_MAX_WARNING-ZESTETM1_WARNING_BASE) : \
                        ((x)>=ZESTETM1_WARNING_BASE ? (x)-ZESTETM1_WARNING_BASE+(ZESTETM1_MAX_INFO-ZESTETM1_INFO_BASE) : (x)-ZESTETM1_INFO_BASE)]
extern char *ZestETM1_ErrorStrings[];

/******************************************
* Network connection descriptor structure *
******************************************/
#define ZESTETM1_CONNECTION_HANDLE_MAGIC 0xdeadbed1
typedef struct
{
    uint32_t Magic;
    ZESTETM1_CARD_INFO *CardInfo;
    ZESTETM1_CONNECTION_TYPE Type;
    struct sockaddr_in Target;
    uint16_t Port;
    uint16_t LocalPort;
    SOCKET Socket;
} ZESTETM1_CONNECTION_STRUCT;

/************
* Constants *
************/
#define ZESTETM1_DEFAULT_TIMEOUT 10000

// SPI Device ID and clock
#define ZESTETM1_RATE_40MHz (0<<4)
#define ZESTETM1_RATE_20MHz (1<<4)
#define ZESTETM1_RATE_10MHz (2<<4)
#define ZESTETM1_USER_DEVICE_ID      (1)

// Reverse bytes in 32 bit word
#define ZESTETM1_REVERSE(x) ((((x)&0xff)<<24) | (((x)&0xff00)<<8) | (((x)&0xff0000)>>8) | (((x)&0xff000000)>>24))

/******************
* Local functions *
******************/
ZESTETM1_STATUS ZestETM1_OpenConnection(ZESTETM1_CARD_INFO *CardInfo,
                                        ZESTETM1_CONNECTION_TYPE Type,
                                        uint16_t Port,
                                        uint16_t LocalPort,
                                        ZESTETM1_CONNECTION *Connection);
ZESTETM1_STATUS ZestETM1_CloseConnection(ZESTETM1_CONNECTION Connection);
ZESTETM1_STATUS ZestETM1_SendCommand(ZESTETM1_CARD_INFO *CardInfo,
                                     ZESTETM1_CONNECTION Connection,
                                     void *WriteBuffer, uint32_t WriteLen,
                                     void *ReadBuffer, uint32_t ReadLen,
                                     int WaitForAck);
ZESTETM1_STATUS ZestETM1_SPIReadWrite(ZESTETM1_CARD_INFO *CardInfo, 
                                      ZESTETM1_CONNECTION Connection,
                                      int Device,
                                      int WordLen, uint32_t *WriteData,
                                      uint32_t *ReadData, uint32_t Length,
                                      int ReleaseCS, int WaitForAck);
ZESTETM1_STATUS ZestETM1_WriteFlash(ZESTETM1_CARD_INFO *CardInfo,
                                    uint32_t Address,
                                    void *Buffer,
                                    uint32_t Length);
ZESTETM1_STATUS ZestETM1_EraseFlashSector(ZESTETM1_CARD_INFO *CardInfo,
                                          ZESTETM1_CONNECTION Connection,
                                          uint32_t Address);


