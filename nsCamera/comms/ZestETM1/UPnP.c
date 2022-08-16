// File:      UPnP.c
//
// Purpose:
//    ZestETM1 Host Library
//    UPnP board discovery functions
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

#ifdef WINGCC
#define _strnicmp strncasecmp
#endif
#if !defined(MSVC) && !defined(WINGCC)
#define _strnicmp strncasecmp
#include <sys/types.h>
#include <sys/ioctl.h>
#include <arpa/inet.h>
#include <ifaddrs.h>
#endif

// UPnP search string
static char *ZestETM1_SearchReq =
"M-SEARCH * HTTP/1.1\r\n"
"ST: upnp:rootdevice\r\n"
"MX: %d\r\n"
"MAN: \"ssdp:discover\"\r\n"
"HOST: 239.255.255.250:1900\r\n"
;

// UPnP broadcast address and port
#define ZESTETM1_UPNP_ADDR "239.255.255.250"
#define ZESTETM1_UPNP_PORT 1900

// Get settings command structure
typedef struct
{
    uint8_t Command;
    uint8_t Dummy[3];
} ZESTETM1_GET_SETTINGS_CMD;
typedef struct
{
    uint8_t Command;
    uint8_t Status;
    uint8_t Dummy1[2];
    uint16_t SoftwareVersion;
    uint16_t HardwareVersion;
    uint32_t SerialNumber;
    uint32_t IPAddr;
    uint32_t Gateway;
    uint32_t SubNet;
    uint16_t HTTPPort;
    uint16_t ControlPort;
    uint8_t MACAddr[6];
    uint8_t Dummy2[2];
} ZESTETM1_GET_SETTINGS_RESPONSE;
#define ZESTETM1_COMMAND_GET_SETTINGS 0xf0

/*************************
* Issue HTTP GET command *
*************************/
static int ZestETM1_HTTPGet(char *IPAddr, char *Port,
                           char *FileName, void *Buffer,
                           int BufferLength, int Wait)
{
    struct addrinfo *Addr = NULL,
                    *Ptr = NULL,
                    Hints;
    int Result;
    SOCKET Socket;
    int Offset = 0;
    char Req[1024];
    char *HdrEnd;
    fd_set ReadFDS;
    struct timeval Timeout;

    Timeout.tv_sec = Wait/1000;
    Timeout.tv_usec = (Wait%1000)*1000;

    // Attempt to connect to the address
    memset(&Hints, 0, sizeof(Hints));
    Hints.ai_family = AF_UNSPEC;
    Hints.ai_socktype = SOCK_STREAM;
    Hints.ai_protocol = IPPROTO_TCP;

    // Resolve the server address and port
    Result = getaddrinfo(IPAddr, Port, &Hints, &Addr);
    if (Result!=0)
        return -1;

    for (Ptr=Addr; Ptr!=NULL; Ptr=Ptr->ai_next)
    {
        // Create a SOCKET for connecting to server
        Socket = socket(Ptr->ai_family, Ptr->ai_socktype, 
                        Ptr->ai_protocol);
        if (Socket<0)
        {
            freeaddrinfo(Addr);
            return -1;
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
    freeaddrinfo(Addr);

    // Send GET request
    sprintf(Req, "GET /%s HTTP/1.1\r\nHOST: %s:%s\r\nContent-length: 0\r\n\r\n", FileName, IPAddr, Port);
    Result = send(Socket, Req, (int)strlen(Req), 0);
    if (Result!=strlen(Req))
    {
        closesocket(Socket);
        return -1;
    }

    // Get response
    ((char*)Buffer)[0] = 0;
    do
    {
        FD_ZERO(&ReadFDS);
        FD_SET(Socket, &ReadFDS);
        Result = select((int)Socket+1, &ReadFDS, NULL, NULL, &Timeout);
        if (Result<0)
        {
            closesocket(Socket);
            return -1;
        }
        if (!FD_ISSET(Socket, &ReadFDS)) break;
        Result = recv(Socket, (char *)Buffer+Offset, BufferLength-Offset, 0);
        if (Result<0)
        {
            closesocket(Socket);
            return -1;
        }
        Offset+=Result;
        if (Offset==BufferLength)
        {
            break;
        }
    } while (Result!=0);

    // Check status response
    if (_strnicmp("HTTP/1.1 200 OK", Buffer, 15)!=0)
    {
        closesocket(Socket);
        return -1;
    }

    // Remove HTTP header
    HdrEnd = strstr(Buffer, "\r\n\r\n");
    if (HdrEnd==NULL)
    {
        Offset = 0;
    }
    else
    {
        Offset -= (int)(HdrEnd+4-(char*)Buffer);
        memcpy(Buffer, HdrEnd+4, Offset);
    }

    closesocket(Socket);
    return Offset;
}

/*******************************
* Read settings from ETM1 flash *
*******************************/
static ZESTETM1_STATUS ZestETM1_ReadSettings(ZESTETM1_CARD_INFO *CardInfo)
{
    ZESTETM1_STATUS Result;
    ZESTETM1_CONNECTION Connection;
    ZESTETM1_GET_SETTINGS_CMD Cmd;
    ZESTETM1_GET_SETTINGS_RESPONSE Response;

    if (CardInfo==NULL)
    {
        return ZESTETM1_NULL_PARAMETER;
    }

    // Open control connection
    Result = ZestETM1_OpenConnection(CardInfo, ZESTETM1_TYPE_TCP,
                                    CardInfo->ControlPort, 0, &Connection);
    if (Result!=ZESTETM1_SUCCESS)
    {
        return Result;
    }

    // Get the settings from the device
    Cmd.Command = ZESTETM1_COMMAND_GET_SETTINGS;
    Result = ZestETM1_SendCommand(CardInfo, Connection,
                                 &Cmd, sizeof(Cmd),
                                 &Response, sizeof(Response), 1);
    if (Result!=ZESTETM1_SUCCESS)
    {
        ZestETM1_CloseConnection(Connection);
        return Result;
    }

    // Result values (including endian conversion)
    CardInfo->FirmwareVersion = ((Response.SoftwareVersion>>8)&0xff)|((Response.SoftwareVersion&0xff)<<8);
    CardInfo->HardwareVersion = ((Response.HardwareVersion>>8)&0xff)|((Response.HardwareVersion&0xff)<<8);
    CardInfo->Gateway[0] = (uint8_t)((Response.Gateway>>0)&0xff);
    CardInfo->Gateway[1] = (uint8_t)((Response.Gateway>>8)&0xff);
    CardInfo->Gateway[2] = (uint8_t)((Response.Gateway>>16)&0xff);
    CardInfo->Gateway[3] = (uint8_t)((Response.Gateway>>24)&0xff);
    CardInfo->SubNet[0] = (uint8_t)((Response.SubNet>>0)&0xff);
    CardInfo->SubNet[1] = (uint8_t)((Response.SubNet>>8)&0xff);
    CardInfo->SubNet[2] = (uint8_t)((Response.SubNet>>16)&0xff);
    CardInfo->SubNet[3] = (uint8_t)((Response.SubNet>>24)&0xff);
    memcpy(CardInfo->MACAddr, Response.MACAddr, 6);
    CardInfo->ControlPort = ((Response.ControlPort>>8)&0xff)|((Response.ControlPort&0xff)<<8);
    CardInfo->HTTPPort = ((Response.HTTPPort>>8)&0xff)|((Response.HTTPPort&0xff)<<8);
    CardInfo->SerialNumber = ZESTETM1_REVERSE(Response.SerialNumber);

    Result = ZestETM1_CloseConnection(Connection);
    if (Result!=ZESTETM1_SUCCESS)
        return Result;

    return ZESTETM1_SUCCESS;
}


/********************************
* Read information about a card *
********************************/
static void ZestETM1_GetCardInfo(char *Location, 
                                uint32_t *NumCards,
                                ZESTETM1_CARD_INFO **CardInfo,
                                int Wait)
{
    static char *Prefix = "http://";
    char Buffer[65536];
    char *IPAddr = NULL;
    char *FileName = NULL;
    char *Port = "80";
    int i;

    // Extract address and port
    for (i=0; Location[i]!=0 && Location[i]!='\r' && Location[i]!='\n'; i++)
    {
        if (IPAddr==NULL && Prefix[i]==0) IPAddr = Location+i;
        if (IPAddr==NULL && Location[i]!=Prefix[i])
            return;
        if (IPAddr!=NULL)
        {
            if (Location[i]=='/' || Location[i]==0 ||
                Location[i]=='\r' || Location[i]=='\n')
            {
                Location[i]=0;
                i++;
                break;
            }
            if (Location[i]==':')
            {
                int j=i;
                while (Location[j]!=0 && Location[j]!='\r' &&
                       Location[j]!='\n' && Location[j]!='/') j++;
                Location[i]=0;
                Location[j]=0;
                Port = Location+i+1;
                i = j+1;
                break;
            }
        }
    }
    if (IPAddr==NULL || Location[i]==0 || Location[i]=='\r' || Location[i]=='\n')
        return;

    // Extract XML filename
    FileName = Location+i;
    while (Location[i]!=0 && Location[i]!='\r' && Location[i]!='\n') i++;
    Location[i] = 0;

    // Get XML file
    memset(Buffer, 0, sizeof(Buffer));
    if (ZestETM1_HTTPGet(IPAddr, Port, FileName,
                        Buffer, sizeof(Buffer), Wait)>0)
    {
        uint8_t IPAddr[4];
        uint32_t i;
        uint16_t Port;

        // Parse XML for service description URL
        char *ControlURL = strstr(Buffer, "<controlURL>");
        if (ControlURL==NULL)
            return;
            
        ControlURL += 12;
        for (i=0; i<4; i++)
        {
            char *EndPtr;
            IPAddr[i] = (uint8_t)strtoul(ControlURL, &EndPtr, 10);
            if ((i!=3 && *EndPtr!='.') || (i==3 && *EndPtr!=':'))
                break;
            ControlURL = EndPtr+1;
        }
        if (i!=4)
            return;
        
        Port = atoi(ControlURL);

        // Make sure only unique devices are added to the list!
        if (*CardInfo!=NULL)
        {
            for (i=0; i<*NumCards; i++)
            {
                if ((*CardInfo)[i].ControlPort==Port &&
                    memcmp((*CardInfo)[i].IPAddr, IPAddr, sizeof(IPAddr))==0)
                {
                    break;
                }
            }
        }
        if (*CardInfo==NULL || i==*NumCards)
        {
            uint32_t Index = (*NumCards);
            ZESTETM1_CARD_INFO *NewBuffer;
            
            // Allocate space for new card info structure
            if ((*CardInfo)==NULL)
                NewBuffer = malloc(sizeof(ZESTETM1_CARD_INFO)*(Index+1));
            else
                NewBuffer = realloc(*CardInfo, sizeof(ZESTETM1_CARD_INFO)*(Index+1));
            
            // Get new card settings
            NewBuffer[Index].ControlPort = Port;
            memcpy(NewBuffer[Index].IPAddr, IPAddr, sizeof(IPAddr));
            NewBuffer[Index].Timeout = Wait;
            if (ZestETM1_ReadSettings(&(NewBuffer[Index]))!=ZESTETM1_SUCCESS)
            {
                if (*CardInfo==NULL)
                    free(NewBuffer);
                else
                {
                    (*CardInfo) = NewBuffer;
                    memset(NewBuffer[Index].IPAddr, 0, sizeof(NewBuffer[Index].IPAddr));
                    NewBuffer[Index].ControlPort = 0;
                }
            }
            else
            {
                NewBuffer[Index].Timeout = ZESTETM1_DEFAULT_TIMEOUT;
                (*CardInfo) = NewBuffer;
                (*NumCards)++;
            }
        }
    }
}


/***************************************************
* Multicasting functions to join and leave a group *
***************************************************/
static int ZestETM1_JoinGroup(SOCKET sd, uint32_t grpaddr,
                             uint32_t iaddr)
{
    struct ip_mreq imr; 

    imr.imr_multiaddr.s_addr  = grpaddr;
    imr.imr_interface.s_addr  = iaddr;
    return setsockopt(sd, IPPROTO_IP, IP_ADD_MEMBERSHIP,
                      (const char *)&imr, sizeof(imr));  
}
static int ZestETM1_LeaveGroup(SOCKET sd, uint32_t grpaddr, 
                              uint32_t iaddr)
{
    struct ip_mreq imr;

    imr.imr_multiaddr.s_addr  = grpaddr;
    imr.imr_interface.s_addr  = iaddr;
    return setsockopt(sd, IPPROTO_IP, IP_DROP_MEMBERSHIP, 
                      (const char *)&imr, sizeof(imr));
}

/*******************************************
* Get an array with all local IP addresses *
*******************************************/
static ZESTETM1_STATUS ZestETM1_GetAllAdapters(uint32_t *NumAdapters, struct sockaddr_in **Adapters)
{
#if defined(MSVC) || defined(WINGCC)
    SOCKET Socket;
    SOCKET_ADDRESS_LIST *AddressListPtr;
    DWORD BytesRequired;
    int i;
    int Count = 0;

    *NumAdapters = 0;
    *Adapters = NULL;

    Socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (Socket<0)
        return ZESTETM1_INTERNAL_ERROR;

    WSAIoctl(Socket, SIO_ADDRESS_LIST_QUERY, NULL, 0,
             NULL, 0, (LPDWORD)&BytesRequired, NULL, NULL);
    AddressListPtr = (SOCKET_ADDRESS_LIST *)malloc(BytesRequired);
    if (AddressListPtr==NULL)
    {
        closesocket(Socket);
        return ZESTETM1_OUT_OF_MEMORY;
    }
    if (WSAIoctl(Socket, SIO_ADDRESS_LIST_QUERY, NULL, 0,
                 AddressListPtr, BytesRequired, &BytesRequired, NULL, NULL)==SOCKET_ERROR)
    {
        free(AddressListPtr);
        closesocket(Socket);
        return ZESTETM1_INTERNAL_ERROR;
    }

    for (i=0; i<AddressListPtr->iAddressCount; i++)
    {
        if (AddressListPtr->Address[i].iSockaddrLength==sizeof(struct sockaddr_in))
        {
            Count++;
            (*Adapters) = (struct sockaddr_in *)realloc(*Adapters, Count*sizeof(struct sockaddr_in));
            if ((*Adapters)==NULL)
            {
                free(AddressListPtr);
                closesocket(Socket);
                return ZESTETM1_OUT_OF_MEMORY;
            }
            memcpy(&(*Adapters)[Count-1], AddressListPtr->Address[i].lpSockaddr, sizeof(struct sockaddr_in));
        }
    }
    *NumAdapters = Count;
    closesocket(Socket);
    free(AddressListPtr);

    return ZESTETM1_SUCCESS;
#else
    struct ifaddrs *Interfaces;
    struct ifaddrs *Ptr;
    uint32_t Count = 0;

    if (getifaddrs(&Interfaces)!=0)
        return ZESTETM1_INTERNAL_ERROR;

    *NumAdapters = 0;
    *Adapters = NULL;
    
    Ptr = Interfaces;
    while (Ptr!=NULL)
    {
        if (Ptr->ifa_addr!=NULL)
        {
            Count++;
            (*Adapters) = (struct sockaddr_in *)realloc(*Adapters, Count*sizeof(struct sockaddr_in));
            if ((*Adapters)==NULL)
            {
                freeifaddrs(Interfaces);
                return ZESTETM1_OUT_OF_MEMORY;
            }
            memcpy(&(*Adapters)[Count-1], Ptr->ifa_addr, sizeof(struct sockaddr_in));
        }
        Ptr = Ptr->ifa_next;
    }
    *NumAdapters = Count;
    freeifaddrs(Interfaces);

    return ZESTETM1_SUCCESS;
#endif
}

/******************************************************************************
* Scan networks for ZestETM1 cards and return the number of attached devices   *
* and details about each one                                                  *
******************************************************************************/
ZESTETM1_STATUS ZestETM1CountCards(unsigned long *NumCards,
                                 ZESTETM1_CARD_INFO **CardInfo, unsigned long Wait)
{
    SOCKET Socket;
    struct sockaddr_in DestIP;
    struct sockaddr_in SourceIP;
    int SourceIPLength;
    int Flag = 1;
    int Result;
    char Req[1024];
    char Response[1024];
    ZESTETM1_CARD_INFO *Cards = NULL;
    uint32_t CardCount = 0;
    int i;
    struct timeval Timeout;
    fd_set ReadFDS;
    uint32_t Interface;
    uint32_t NumAdapters;
    struct sockaddr_in *Adapters;
    ZESTETM1_STATUS Status;

    *NumCards = 0;
    *CardInfo = NULL;

    // Get a list of all adapters
    Status = ZestETM1_GetAllAdapters(&NumAdapters, &Adapters);
    if (Status!=ZESTETM1_SUCCESS)
        ZESTETM1_ERROR_GENERAL("ZestETM1CountCards", Status);
    if (NumAdapters==0)
    {
        *NumCards = 0;
        return ZESTETM1_SUCCESS;
    }

    // Send queries on all interfaces
    for (Interface=0; Interface<NumAdapters; Interface++)
    {
        if (Adapters[Interface].sin_family!=AF_INET)
            continue;

        // Open socket for search requests
        Socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (Socket<0)
        {
            continue;
        }

        // Set reuse port to on to allow multiple binds per host
        if (setsockopt(Socket, SOL_SOCKET, SO_REUSEADDR, (char *)&Flag,
                       sizeof(Flag))<0)
        {
            closesocket(Socket);
            continue;
        }

        // Bind to port for receiving responses
        SourceIP.sin_family = AF_INET;
        SourceIP.sin_addr.s_addr = htonl(INADDR_ANY);
        SourceIP.sin_port = 0;
        Result = bind(Socket, (const struct sockaddr *)(&Adapters[Interface]), sizeof(struct sockaddr_in));
        if (Result<0)
        {
            closesocket(Socket);
            continue;
        }

        // Join multicast group
        if (ZestETM1_JoinGroup(Socket, inet_addr(ZESTETM1_UPNP_ADDR), 
                              htonl(INADDR_ANY))<0)
        {
            closesocket(Socket);
            continue;
        }

        // Send M-SEARCH request
        // Send more than once as UDP is unreliable
        DestIP.sin_family = AF_INET;
        DestIP.sin_addr.s_addr = inet_addr(ZESTETM1_UPNP_ADDR);
        DestIP.sin_port = htons(1900);
        sprintf(Req, ZestETM1_SearchReq, (Wait+999)/1000);
        for (i=0; i<3; i++)
        {
            Result = sendto(Socket, ZestETM1_SearchReq, 
                            (int)strlen(ZestETM1_SearchReq),
                            0, (struct sockaddr *)&DestIP, sizeof(DestIP));
            if (Result!=strlen(ZestETM1_SearchReq))
            {
                ZestETM1_LeaveGroup(Socket, inet_addr(ZESTETM1_UPNP_ADDR), 
                                   htonl(INADDR_ANY));
                closesocket(Socket);
                continue;
            }
        }

        // Read responses
        Timeout.tv_sec = Wait/1000;
        Timeout.tv_usec = (Wait%1000)*1000;
        do
        {
            FD_ZERO(&ReadFDS);
            FD_SET(Socket, &ReadFDS);
            Result = select((int)Socket+1, &ReadFDS, NULL, NULL, &Timeout);
            if (Result<0)
            {
                break;
            }
            if (!FD_ISSET(Socket, &ReadFDS)) break;

            SourceIPLength = sizeof(SourceIP);
            Result = recvfrom(Socket, Response, sizeof(Response),
                              0, (struct sockaddr *)&SourceIP, &SourceIPLength);
            if (Result<0)
            {
                // Error!
                break;
            }
            else if (Result==0)
            {
                // Clean shut down
                break;
            }
            else
            {
                // Parse results
                if (_strnicmp("NOTIFY", Response, 6)==0 ||
                    _strnicmp("HTTP/1.1 200 OK", Response, 15)==0)
                {
                    // Check its a GigExpedite and request XML description
                    char *Server = strstr(Response, "GigExpedite2");
                    char *Location = strstr(Response, "LOCATION");
                    if (Server!=NULL && Location!=NULL)
                    {
                        char *c;
                        for (c=Location+10; *c!=0 && *c!='\n' && *c!='\r'; c++);
                        *c = 0;
                        ZestETM1_GetCardInfo(Location+10, &CardCount, &Cards, Wait);
                    }
                }
            }
        } while(1);

        // Leave multicast group
        ZestETM1_LeaveGroup(Socket, inet_addr(ZESTETM1_UPNP_ADDR), 
                           htonl(INADDR_ANY));

        // Close socket
        closesocket(Socket);
    }

    *NumCards = CardCount;
    *CardInfo = Cards;
    free(Adapters);

    return ZESTETM1_SUCCESS;
}

/*****************************************************
* Free data structures returned by ZestETM1CountCards *
*****************************************************/
ZESTETM1_STATUS ZestETM1FreeCards(ZESTETM1_CARD_INFO *CardInfo)
{
    if (CardInfo!=NULL)
        free(CardInfo);

    return ZESTETM1_SUCCESS;
}

/**********************************
* Fill in card information fields *
**********************************/
ZESTETM1_STATUS ZestETM1GetCardInfo(ZESTETM1_CARD_INFO *CardInfo)
{
    ZESTETM1_STATUS Status;
    
    Status = ZestETM1_ReadSettings(CardInfo);
    if (Status!=ZESTETM1_SUCCESS)
    {
        ZESTETM1_ERROR("ZestETM1GetCardInfo", Status);
    }

    return ZESTETM1_SUCCESS;
}

