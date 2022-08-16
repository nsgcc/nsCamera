// File:      Data.c
//
// Purpose:
//    ZestETM1 Host Library
//    Data transfer functions
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

#define _CRT_SECURE_NO_WARNINGS
#ifdef WINGCC
#define __USE_W32_SOCKETS
#endif

#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <memory.h>
#include "ZestETM1.h"
#include "Private.h"

// Read/write register command structures
typedef struct
{
    uint8_t Command;
    uint8_t Addr;
    uint16_t Data;
} ZESTETM1_WRITE_REG_CMD;
typedef struct
{
    uint8_t Command;
    uint8_t Status;
    uint8_t Dummy1[2];
} ZESTETM1_WRITE_REG_RESPONSE;
typedef struct
{
    uint8_t Command;
    uint8_t Addr;
    uint8_t Dummy[2];
} ZESTETM1_READ_REG_CMD;
typedef struct
{
    uint8_t Command;
    uint8_t Status;
    uint16_t Value;
} ZESTETM1_READ_REG_RESPONSE;
typedef struct
{
    uint8_t Command;
    uint8_t Dummy[3];
} ZESTETM1_MAILBOX_INT_CMD;
typedef struct
{
    uint8_t Command;
    uint8_t Status;
    uint16_t Dummy;
} ZESTETM1_MAILBOX_INT_RESPONSE;
#define ZESTETM1_COMMAND_SPI 0xee
#define ZESTETM1_COMMAND_WRITE_REG 0xf6
#define ZESTETM1_COMMAND_READ_REG 0xf7
#define ZESTETM1_COMMAND_MAILBOX_INT 0xf8

/**********************************************************************
* Open a connection to a ZestETM1 for data transfer (internal version) *
**********************************************************************/
ZESTETM1_STATUS ZestETM1_OpenConnection(ZESTETM1_CARD_INFO *CardInfo,
                                        ZESTETM1_CONNECTION_TYPE Type,
                                        uint16_t Port,
                                        uint16_t LocalPort,
                                        ZESTETM1_CONNECTION *Connection)
{
    ZESTETM1_CONNECTION_STRUCT *NewStruct;
    SOCKET Socket = -1;
    char AddrBuffer[32];
    char PortBuffer[32];

    if (Connection==NULL || CardInfo==NULL)
    {
        return ZESTETM1_NULL_PARAMETER;
    }

    // Allocate data structure
    NewStruct = malloc(sizeof(ZESTETM1_CONNECTION_STRUCT));
    if (NewStruct==NULL)
    {
        return ZESTETM1_OUT_OF_MEMORY;
    }

    // Build target addresses
    sprintf(AddrBuffer, "%d.%d.%d.%d", CardInfo->IPAddr[0], CardInfo->IPAddr[1],
                    CardInfo->IPAddr[2], CardInfo->IPAddr[3]);
    sprintf(PortBuffer, "%d", Port);

    if (Type==ZESTETM1_TYPE_UDP)
    {
        // Open UDP connection
        struct sockaddr_in SourceIP;
        int SourceLen = (int)sizeof(struct sockaddr_in);
        Socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (Socket<0)
            return ZESTETM1_SOCKET_ERROR;
        SourceIP.sin_family = AF_INET;
        SourceIP.sin_addr.s_addr = htonl(INADDR_ANY);
        SourceIP.sin_port = htons(LocalPort);
        bind(Socket, (const struct sockaddr *)&SourceIP, SourceLen);

        NewStruct->Target.sin_family = AF_INET;
        NewStruct->Target.sin_addr.s_addr = inet_addr(AddrBuffer);
        NewStruct->Target.sin_port = htons(atoi(PortBuffer));
    }
    else if (Type==ZESTETM1_TYPE_TCP)
    {
        // Open TCP connection
        struct addrinfo *AddrResult = NULL,
                        *Ptr = NULL,
                        Hints;
        int Result;
        struct sockaddr_in SourceIP;
        int SourceLen = (int)sizeof(struct sockaddr_in);

        memset(&Hints, 0, sizeof(Hints));
        Hints.ai_family = AF_UNSPEC;
        Hints.ai_socktype = SOCK_STREAM;
        Hints.ai_protocol = IPPROTO_TCP;

        // Resolve the server address and port
        Result = getaddrinfo(AddrBuffer, PortBuffer, &Hints, &AddrResult);
        if (Result!=0)
        {
            free(NewStruct);
            return ZESTETM1_SOCKET_ERROR;
        }

        // Attempt to connect to an address until one succeeds
        for (Ptr=AddrResult; Ptr!=NULL; Ptr=Ptr->ai_next)
        {
            // Create a SOCKET for connecting to server
            Socket = socket(Ptr->ai_family, Ptr->ai_socktype, 
                            Ptr->ai_protocol);
            if (Socket<0)
            {
                freeaddrinfo(AddrResult);
                free(NewStruct);
                return ZESTETM1_SOCKET_ERROR;
            }

            // Connect to ZestETM1
            Result = connect(Socket, Ptr->ai_addr, (int)Ptr->ai_addrlen);
            if (Result<0)
            {
                closesocket(Socket);
                Socket = -1;
                continue;
            }
            break;
        }

        SourceIP.sin_family = AF_INET;
        SourceIP.sin_addr.s_addr = htonl(INADDR_ANY);
        SourceIP.sin_port = 0;
        bind(Socket, (const struct sockaddr *)&SourceIP, SourceLen);
        freeaddrinfo(AddrResult);
    }
    else
    {
        free(NewStruct);
        return ZESTETM1_INVALID_CONNECTION_TYPE;
    }

    if (Socket==-1)
    {
        free(NewStruct);
        return ZESTETM1_SOCKET_ERROR;
    }

    NewStruct->Magic = ZESTETM1_CONNECTION_HANDLE_MAGIC;
    NewStruct->Type = Type;
    NewStruct->Port = Port;
    NewStruct->LocalPort = LocalPort;
    NewStruct->Socket = Socket;
    NewStruct->CardInfo = CardInfo;
    *Connection = NewStruct;

    return ZESTETM1_SUCCESS;
}

/****************************************************
* Close a connection to a ZestETM1 (internal version *
****************************************************/
ZESTETM1_STATUS ZestETM1_CloseConnection(ZESTETM1_CONNECTION Connection)
{
    ZESTETM1_CONNECTION_STRUCT *Conn = (ZESTETM1_CONNECTION_STRUCT *)Connection;

    if (Conn==NULL)
    {
        return ZESTETM1_NULL_PARAMETER;
    }
    if (Conn->Magic!=ZESTETM1_CONNECTION_HANDLE_MAGIC)
    {
        return ZESTETM1_ILLEGAL_CONNECTION;
    }

    // Cleanup
    closesocket(Conn->Socket);
    Conn->Magic = 0;
    free(Conn);

    return ZESTETM1_SUCCESS;
}

/******************************************************
* Write data to ZestETM1 connection (internal version) *
******************************************************/
static ZESTETM1_STATUS ZestETM1_WriteData(ZESTETM1_CONNECTION Connection,
                                        void *Buffer,
                                        uint32_t Length,
                                        unsigned long *Written,
                                        uint32_t Timeout)
{
    ZESTETM1_CONNECTION_STRUCT *Conn = (ZESTETM1_CONNECTION_STRUCT *)Connection;
    fd_set WriteFDS;
    struct timeval Time;
    uint32_t BufferPtr = 0;
    int Result;
    int TargetLen = (int)sizeof(struct sockaddr_in);
    unsigned int MaxSize;

    if (Conn==NULL)
    {
        if (Written!=NULL) *Written = 0;
        return ZESTETM1_NULL_PARAMETER;
    }
    if (Conn->Magic!=ZESTETM1_CONNECTION_HANDLE_MAGIC)
    {
        if (Written!=NULL) *Written = 0;
        return ZESTETM1_ILLEGAL_CONNECTION;
    }

    if (Conn->Type==ZESTETM1_TYPE_UDP)
    {
        // Get maximum transfer size
#if defined(MSVC) || defined(WINGCC)
        int MaxSizeLen = sizeof(MaxSize);
        getsockopt(Conn->Socket, SOL_SOCKET, SO_MAX_MSG_SIZE, 
                   (char *)&MaxSize, &MaxSizeLen);
#else
        //FIXME: Linux doesn't support SO_MAX_MSG_SIZE
        MaxSize = 65507;
#endif
    }

    do
    {
        uint32_t Bytes = Length-BufferPtr;

        if (Conn->Type==ZESTETM1_TYPE_UDP && Bytes>MaxSize)
            Bytes = MaxSize;

        // Wait for socket to become ready
        {
            int CurTime = 0;
            while (CurTime!=Timeout)
            {
                int T = (Timeout-CurTime)<1000 ? Timeout-CurTime : 1000;
                FD_ZERO(&WriteFDS);
                FD_SET(Conn->Socket, &WriteFDS);
                Time.tv_sec = T/1000;
                Time.tv_usec = (T%1000)*1000;
                Result = select((int)Conn->Socket+1, NULL, &WriteFDS, NULL, &Time);
                if (Result>0) break;
                CurTime+=T;
            }
        }
        if (Result<0 || !FD_ISSET(Conn->Socket, &WriteFDS))
        {
            if (Written!=NULL) *Written = BufferPtr;
            return ZESTETM1_TIMEOUT;//FIXME: Any other errors?
        }

        if (Conn->Type==ZESTETM1_TYPE_UDP)
        {
            Result = sendto(Conn->Socket, (char *)Buffer+BufferPtr,
                            Bytes, 0,
                            (struct sockaddr *)&Conn->Target, TargetLen);
        }
        else if (Conn->Type==ZESTETM1_TYPE_TCP)
        {
            Result = send(Conn->Socket, (char *)Buffer+BufferPtr,
                          Bytes, 0);
        }
        else
        {
            if (Written!=NULL) *Written = BufferPtr;
            return ZESTETM1_ILLEGAL_CONNECTION;
        }

        // Update counters
        if (Result>0)
        {
            BufferPtr += Result;
        }
        else if (Result==0)
        {
            // Connection closed
            if (Written!=NULL) *Written = BufferPtr;
            return ZESTETM1_SOCKET_CLOSED;
        }
        else
        {
            // Socket error
            if (Written!=NULL) *Written = BufferPtr;
            return ZESTETM1_SOCKET_ERROR;
        }
    } while (Result>0 && BufferPtr<Length);

    if (Written!=NULL) *Written = BufferPtr;
    return ZESTETM1_SUCCESS;
}

/*********************************************************
* Read data from a ZestETM1 connection (internal version) *
*********************************************************/
static ZESTETM1_STATUS ZestETM1_ReadData(ZESTETM1_CONNECTION Connection,
                                       void *Buffer,
                                       uint32_t Length,
                                       unsigned long *Read,
                                       uint32_t Timeout)
{
    ZESTETM1_CONNECTION_STRUCT *Conn = (ZESTETM1_CONNECTION_STRUCT *)Connection;
    fd_set ReadFDS;
    struct timeval Time;
    uint32_t BufferPtr = 0;
    int Result;
    struct sockaddr_in Target;
    int TargetLen = (int)sizeof(struct sockaddr_in);

    if (Conn==NULL)
    {
        if (Read!=NULL) *Read = 0;
        return ZESTETM1_NULL_PARAMETER;
    }
    if (Conn->Magic!=ZESTETM1_CONNECTION_HANDLE_MAGIC)
    {
        if (Read!=NULL) *Read = 0;
        return ZESTETM1_ILLEGAL_CONNECTION;
    }

    do
    {
        int OK = 1;

        // Wait for socket to become ready
        {
            int CurTime = 0;
            while (CurTime!=Timeout)
            {
                int T = (Timeout-CurTime)<1000 ? Timeout-CurTime : 1000;
                FD_ZERO(&ReadFDS);
                FD_SET(Conn->Socket, &ReadFDS);
                Time.tv_sec = T/1000;
                Time.tv_usec = (T%1000)*1000;
                Result = select((int)Conn->Socket+1, &ReadFDS, NULL, NULL, &Time);
                if (Result>0) break;
                CurTime+=T;
            }
        }
        if (Result<0 || !FD_ISSET(Conn->Socket, &ReadFDS))
        {
            if (Read!=NULL) *Read = BufferPtr;
            return ZESTETM1_TIMEOUT;//FIXME: Any other errors?
        }

        if (Conn->Type==ZESTETM1_TYPE_UDP)
        {
            Result = recvfrom(Conn->Socket, (char *)Buffer+BufferPtr,
                              Length-BufferPtr, 0,
                              (struct sockaddr *)&Target, &TargetLen);
            if (Conn->LocalPort!=0 && Target.sin_port!=htons(Conn->LocalPort))
                OK = 0;
        }
        else if (Conn->Type==ZESTETM1_TYPE_TCP)
        {
            Result = recv(Conn->Socket, (char *)Buffer+BufferPtr,
                         Length-BufferPtr, 0);
        }
        else
        {
            if (Read!=NULL) *Read = BufferPtr;
            return ZESTETM1_ILLEGAL_CONNECTION;
        }

        // Update counters
        if (Result>0 && OK==1)
        {
            BufferPtr += Result;
        }
        else if (Result==0)
        {
            // Connection closed
            if (Read!=NULL) *Read = BufferPtr;
            return ZESTETM1_SOCKET_CLOSED;
        }
        else if (Result<0)
        {
            // Socket error
            if (Read!=NULL) *Read = BufferPtr;
            return ZESTETM1_SOCKET_ERROR;
        }
    } while (Result>0 && BufferPtr<Length);

    if (Read!=NULL) *Read = BufferPtr;
    return ZESTETM1_SUCCESS;
}

/***************************************************
* Send a control command to GigEx and get response *
***************************************************/
ZESTETM1_STATUS ZestETM1_SendCommand(ZESTETM1_CARD_INFO *CardInfo,
                                   ZESTETM1_CONNECTION Connection,
                                   void *WriteBuffer, uint32_t WriteLen,
                                   void *ReadBuffer, uint32_t ReadLen,
                                   int WaitForAck)
{
    ZESTETM1_STATUS Result;
    unsigned long Written;
    unsigned long Received;

    // Send/receive data
    Result = ZestETM1_WriteData(Connection, WriteBuffer, WriteLen, &Written,
                               CardInfo->Timeout);
    if (Result!=ZESTETM1_SUCCESS)
    {
        return Result;
    }
    if (Written!=WriteLen)
    {
        return ZESTETM1_INTERNAL_ERROR;
    }
    *((uint8_t *)ReadBuffer) = 0;
    if (WaitForAck==1)
    {
        Result = ZestETM1_ReadData(Connection, ReadBuffer, ReadLen, &Received,
                                  CardInfo->Timeout);
        if (Result!=ZESTETM1_SUCCESS)
        {
            return Result;
        }
        if (Received!=ReadLen)
        {
            return ZESTETM1_INTERNAL_ERROR;
        }
    }

    return ZESTETM1_SUCCESS;
}

/*********************************************
* Send data to/from SPI port on GigEx device *
*********************************************/
ZESTETM1_STATUS ZestETM1_SPIReadWrite(ZESTETM1_CARD_INFO *CardInfo, 
                                    ZESTETM1_CONNECTION Connection,
                                    int Device,
                                    int WordLen, uint32_t *WriteData,
                                    uint32_t *ReadData, uint32_t Length,
                                    int ReleaseCS, int WaitForAck)
{
    uint8_t Buffer[65536];
    uint32_t *BufPtr;
    uint32_t i;
    ZESTETM1_STATUS Result;

    // Build command
    Buffer[0] = ZESTETM1_COMMAND_SPI;// Command byte
    Buffer[1] = Device;             // SPI device
    Buffer[2] = WordLen;            // Word length
    Buffer[3] = ReleaseCS;          // Release CS on completion
    BufPtr = (uint32_t *)(Buffer+4);

    BufPtr[0] = WriteData==NULL ? 0 : ZESTETM1_REVERSE(Length);    // Num words
    BufPtr[1] = ReadData==NULL ? 0 : ZESTETM1_REVERSE(Length);
    if (WriteData!=NULL)
    {
        for (i=0; i<Length; i++)
        {
            BufPtr[2+i] = ZESTETM1_REVERSE(WriteData[i]);
        }
    }
    else
        memset(BufPtr+2, 0, Length*4);

    // Send command
    Result = ZestETM1_SendCommand(CardInfo, Connection, Buffer,
                                 WriteData==NULL ? 12 : 12+Length*4,
                                 Buffer, ReadData==NULL ? 4 : 4+Length*4,
                                 WaitForAck);
    if (WaitForAck==0)
        return Result;

    // Extract results
    if (Buffer[0]!=ZESTETM1_COMMAND_SPI || Buffer[1]!=0)
    {
        return ZESTETM1_INTERNAL_ERROR;
    }

    BufPtr = (uint32_t *)(Buffer+4);
    if (ReadData!=NULL)
    {
        for (i=0; i<Length; i++)
        {
            ReadData[i] = ZESTETM1_REVERSE(BufPtr[i]);
        }
    }

    return ZESTETM1_SUCCESS;
}

/***************************************************
* Open a connection to a ZestETM1 for data transfer *
***************************************************/
ZESTETM1_STATUS ZestETM1OpenConnection(ZESTETM1_CARD_INFO *CardInfo,
                                     ZESTETM1_CONNECTION_TYPE Type,
                                     uint16_t Port,
                                     uint16_t LocalPort,
                                     ZESTETM1_CONNECTION *Connection)
{
    ZESTETM1_STATUS Result;

    Result = ZestETM1_OpenConnection(CardInfo, Type, Port, LocalPort, Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1OpenConnection", Result);
    }

    return ZESTETM1_SUCCESS;
}

/**********************************
* Close a connection to a ZestETM1 *
**********************************/
ZESTETM1_STATUS ZestETM1CloseConnection(ZESTETM1_CONNECTION Connection)
{
    ZESTETM1_STATUS Result;
    ZESTETM1_CONNECTION_STRUCT *Conn = (ZESTETM1_CONNECTION_STRUCT*)Connection;

    Result = ZestETM1_CloseConnection(Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR_CONN("ZestETM1CloseConnection", Result);
    }

    return ZESTETM1_SUCCESS;
}

/***********************************
* Write data to ZestETM1 connection *
***********************************/
ZESTETM1_STATUS ZestETM1WriteData(ZESTETM1_CONNECTION Connection,
                                void *Buffer,
                                unsigned long Length,
                                unsigned long *Written,
                                unsigned long Timeout)
{
    ZESTETM1_STATUS Result;
    ZESTETM1_CONNECTION_STRUCT *Conn = (ZESTETM1_CONNECTION_STRUCT*)Connection;

    Result = ZestETM1_WriteData(Connection, Buffer, Length, Written, Timeout);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR_CONN("ZestETM1WriteData", Result);
    }

    return ZESTETM1_SUCCESS;
}

/**************************************
* Read data from a ZestETM1 connection *
**************************************/
ZESTETM1_STATUS ZestETM1ReadData(ZESTETM1_CONNECTION Connection,
                               void *Buffer,
                               unsigned long Length,
                               unsigned long *Read,
                               unsigned long Timeout)
{
    ZESTETM1_STATUS Result;
    ZESTETM1_CONNECTION_STRUCT *Conn = (ZESTETM1_CONNECTION_STRUCT*)Connection;

    Result = ZestETM1_ReadData(Connection, Buffer, Length, Read, Timeout);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR_CONN("ZestETM1ReadData", Result);
    }

    return ZESTETM1_SUCCESS;
}


/*********************************
* Read data from master SPI port *
*********************************/
ZESTETM1_STATUS ZestETM1SPIReadWrite(ZESTETM1_CARD_INFO *CardInfo, ZESTETM1_SPI_RATE Rate,
                                     int WordLen, void *WriteData,
                                     void *ReadData, unsigned long Length,
                                     int ReleaseCS)
{
    ZESTETM1_STATUS Result;
    ZESTETM1_CONNECTION Connection;
    unsigned long RateVal = Rate==ZESTETM1_SPI_RATE_35 ? ZESTETM1_RATE_40MHz :
                            Rate==ZESTETM1_SPI_RATE_17_5 ? ZESTETM1_RATE_20MHz : ZESTETM1_RATE_10MHz;

    if (CardInfo==NULL || (WriteData==NULL && ReadData==NULL))
    {
        ZESTETM1_ERROR("ZestETM1SPIReadWrite", ZESTETM1_NULL_PARAMETER);
    }
    if (WordLen<1 || WordLen>32 || Length>16384)
    {
        ZESTETM1_ERROR("ZestETM1SPIReadWrite", ZESTETM1_ILLEGAL_PARAMETER);
    }

    Result = ZestETM1_OpenConnection(CardInfo, ZESTETM1_TYPE_TCP, CardInfo->ControlPort, 0, &Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1SPIReadWrite", Result);
    }

    Result = ZestETM1_SPIReadWrite(CardInfo, Connection, ZESTETM1_USER_DEVICE_ID|RateVal, WordLen, (uint32_t *)WriteData, (uint32_t *)ReadData, Length, ReleaseCS, 1);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1SPIReadWrite", Result);
    }

    Result = ZestETM1_CloseConnection(Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1SPIReadWrite", Result);
    }

    return ZESTETM1_SUCCESS;
}

/**************************************
* Read/Write user interface registers *
**************************************/
ZESTETM1_STATUS ZestETM1WriteRegister(ZESTETM1_CARD_INFO *CardInfo, unsigned long Addr, unsigned short Data)
{
    ZESTETM1_STATUS Result;
    ZESTETM1_CONNECTION Connection;
    ZESTETM1_WRITE_REG_CMD Cmd;
    ZESTETM1_WRITE_REG_RESPONSE Response;

    if (CardInfo==NULL)
    {
        ZESTETM1_ERROR("ZestETM1WriteRegister", ZESTETM1_NULL_PARAMETER);
    }
    if (Addr>127)
    {
        ZESTETM1_ERROR("ZestETM1WriteRegister", ZESTETM1_ILLEGAL_PARAMETER);
    }

    Result = ZestETM1_OpenConnection(CardInfo, ZESTETM1_TYPE_TCP, CardInfo->ControlPort, 0, &Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1WriteRegister", Result);
    }

    // Write register to the device
    //FIXME: Do we want to be able to copy this value to flash?
    Cmd.Command = ZESTETM1_COMMAND_WRITE_REG;
    Cmd.Addr = (uint8_t)Addr;
    Cmd.Data = ((Data>>8)&0xff) | (Data&0xff);
    Result = ZestETM1_SendCommand(CardInfo, Connection,
                                 &Cmd, sizeof(Cmd),
                                 &Response, sizeof(Response), 1);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZestETM1_CloseConnection(Connection);
        ZESTETM1_ERROR("ZestETM1WriteRegister", Result);
    }
    if (Response.Command!=Cmd.Command || Response.Status!=0)
    {
        ZestETM1_CloseConnection(Connection);
        ZESTETM1_ERROR("ZestETM1WriteRegister", ZESTETM1_INTERNAL_ERROR);
    }

    Result = ZestETM1_CloseConnection(Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1WriteRegister", Result);
    }

    return ZESTETM1_SUCCESS;
}

ZESTETM1_STATUS ZestETM1ReadRegister(ZESTETM1_CARD_INFO *CardInfo, unsigned long Addr, unsigned short *Data)
{
    ZESTETM1_STATUS Result;
    ZESTETM1_CONNECTION Connection;
    ZESTETM1_READ_REG_CMD Cmd;
    ZESTETM1_READ_REG_RESPONSE Response;

    if (CardInfo==NULL || Data==NULL)
    {
        ZESTETM1_ERROR("ZestETM1ReadRegister", ZESTETM1_NULL_PARAMETER);
    }
    if (Addr>127)
    {
        ZESTETM1_ERROR("ZestETM1ReadRegister", ZESTETM1_ILLEGAL_PARAMETER);
    }

    Result = ZestETM1_OpenConnection(CardInfo, ZESTETM1_TYPE_TCP, CardInfo->ControlPort, 0, &Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1ReadRegister", Result);
    }

    // Read register from the device
    Cmd.Command = ZESTETM1_COMMAND_READ_REG;
    Cmd.Addr = (uint8_t)Addr;
    Result = ZestETM1_SendCommand(CardInfo, Connection,
                                 &Cmd, sizeof(Cmd),
                                 &Response, sizeof(Response), 1);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZestETM1_CloseConnection(Connection);
        ZESTETM1_ERROR("ZestETM1ReadRegister", Result);
    }
    if (Response.Command!=Cmd.Command || Response.Status!=0)
    {
        ZestETM1_CloseConnection(Connection);
        ZESTETM1_ERROR("ZestETM1ReadRegister", ZESTETM1_INTERNAL_ERROR);
    }
    *Data = ((Response.Value>>8)&0xff) | ((Response.Value&0xff)<<8);

    Result = ZestETM1_CloseConnection(Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1ReadRegister", Result);
    }

    return ZESTETM1_SUCCESS;
}

/************************
* Set mailbox interrupt *
************************/
ZESTETM1_STATUS ZestETM1SetInterrupt(ZESTETM1_CARD_INFO *CardInfo)
{
    ZESTETM1_STATUS Result;
    ZESTETM1_CONNECTION Connection;
    ZESTETM1_MAILBOX_INT_CMD Cmd;
    ZESTETM1_MAILBOX_INT_RESPONSE Response;

    if (CardInfo==NULL)
    {
        ZESTETM1_ERROR("ZestETM1SetInterrupt", ZESTETM1_NULL_PARAMETER);
    }

    Result = ZestETM1_OpenConnection(CardInfo, ZESTETM1_TYPE_TCP, CardInfo->ControlPort, 0, &Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1SetInterrupt", Result);
    }

    // Send command to set interrupt
    Cmd.Command = ZESTETM1_COMMAND_MAILBOX_INT;
    Result = ZestETM1_SendCommand(CardInfo, Connection,
                                 &Cmd, sizeof(Cmd),
                                 &Response, sizeof(Response), 1);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZestETM1_CloseConnection(Connection);
        ZESTETM1_ERROR("ZestETM1SetInterrupt", Result);
    }
    if (Response.Command!=Cmd.Command || Response.Status!=0)
    {
        ZestETM1_CloseConnection(Connection);
        ZESTETM1_ERROR("ZestETM1SetInterrupt", ZESTETM1_INTERNAL_ERROR);
    }

    Result = ZestETM1_CloseConnection(Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1SetInterrupt", Result);
    }

    return ZESTETM1_SUCCESS;
}
