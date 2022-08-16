/**********************************************************
*                                                         *
* (c) 2012 Orange Tree Technologies Ltd                   *
*                                                         *
* ZestETM1.h                                              *
* Version 1.0                                             *
*                                                         *
* Header file for ZestETM1 Ethernet module                *
*                                                         *
**********************************************************/

#ifndef __ZESTETM1_H__
#define __ZESTETM1_H__

#ifdef __cplusplus
extern "C"
{
#endif


/*********************************
* Handle for referencing modules *
*********************************/
typedef void *ZESTETM1_HANDLE;


/*****************************
* Card information structure *
*****************************/
typedef struct
{
    // These must be filled in before calling functions
    unsigned char IPAddr[4];
    unsigned short ControlPort;
    unsigned long Timeout;

    // These are for information purposes only
    unsigned short HTTPPort;
    unsigned char MACAddr[6];
    unsigned char SubNet[4];
    unsigned char Gateway[4];
    unsigned long SerialNumber;
    unsigned long FirmwareVersion;
    unsigned long HardwareVersion;
} ZESTETM1_CARD_INFO;

// Fallback mask
// This will be set if the GigExpedite is operating in firmware version fallback mode
// due to a failed upload of firmware
#define ZESTETM1_VERSION_FALLBACK 0x8000

/****************************
* Data transfer definitions *
****************************/
typedef void *ZESTETM1_CONNECTION;
typedef enum
{
    ZESTETM1_TYPE_TCP,
    ZESTETM1_TYPE_UDP
} ZESTETM1_CONNECTION_TYPE;

/*************************
* Master SPI clock rates *
*************************/
typedef enum
{
    ZESTETM1_SPI_RATE_35,
    ZESTETM1_SPI_RATE_17_5,
    ZESTETM1_SPI_RATE_8_75,
} ZESTETM1_SPI_RATE;

/************************
* Function return codes *
************************/
#define ZESTETM1_INFO_BASE 0
#define ZESTETM1_WARNING_BASE 0x4000
#define ZESTETM1_ERROR_BASE 0x8000
typedef enum
{
    ZESTETM1_SUCCESS = ZESTETM1_INFO_BASE,
    ZESTETM1_MAX_INFO,

    ZESTETM1_MAX_WARNING = ZESTETM1_WARNING_BASE,

    ZESTETM1_SOCKET_ERROR = ZESTETM1_ERROR_BASE,
    ZESTETM1_INTERNAL_ERROR,
    ZESTETM1_ILLEGAL_STATUS_CODE,
    ZESTETM1_NULL_PARAMETER,
    ZESTETM1_OUT_OF_MEMORY,
    ZESTETM1_INVALID_CONNECTION_TYPE,
    ZESTETM1_ILLEGAL_CONNECTION,
    ZESTETM1_SOCKET_CLOSED,
    ZESTETM1_TIMEOUT,
    ZESTETM1_ILLEGAL_PARAMETER,

    ZESTETM1_MAX_ERROR
} ZESTETM1_STATUS;
typedef void (*ZESTETM1_ERROR_FUNC)(const char *Function, 
                                   ZESTETM1_CARD_INFO *CardInfo,
                                   ZESTETM1_STATUS Status,
                                   const char *Msg);


/**********************
* Function prototypes *
**********************/
ZESTETM1_STATUS ZestETM1Init(void);
ZESTETM1_STATUS ZestETM1Close(void);
ZESTETM1_STATUS ZestETM1CountCards(unsigned long *NumCards,
                                 ZESTETM1_CARD_INFO **CardInfo,
                                 unsigned long Wait);
ZESTETM1_STATUS ZestETM1GetCardInfo(ZESTETM1_CARD_INFO *CardInfo);
ZESTETM1_STATUS ZestETM1FreeCards(ZESTETM1_CARD_INFO *CardInfo);

ZESTETM1_STATUS ZestETM1RegisterErrorHandler(ZESTETM1_ERROR_FUNC Function);
ZESTETM1_STATUS ZestETM1GetErrorMessage(ZESTETM1_STATUS Status,
                                      char **Buffer);

ZESTETM1_STATUS ZestETM1OpenConnection(ZESTETM1_CARD_INFO *CardInfo,
                                     ZESTETM1_CONNECTION_TYPE Type,
                                     unsigned short Port,
                                     unsigned short LocalPort,
                                     ZESTETM1_CONNECTION *Connection);
ZESTETM1_STATUS ZestETM1CloseConnection(ZESTETM1_CONNECTION Connection);
ZESTETM1_STATUS ZestETM1WriteData(ZESTETM1_CONNECTION Connection,
                                void *Buffer,
                                unsigned long Length,
                                unsigned long *Written,
                                unsigned long Timeout);
ZESTETM1_STATUS ZestETM1ReadData(ZESTETM1_CONNECTION Connection,
                               void *Buffer,
                               unsigned long Length,
                               unsigned long *Read,
                               unsigned long Timeout);

ZESTETM1_STATUS ZestETM1SPIReadWrite(ZESTETM1_CARD_INFO *CardInfo, ZESTETM1_SPI_RATE Rate,
                                     int WordLen, void *WriteData,
                                     void *ReadData, unsigned long Length,
                                     int ReleaseCS);

ZESTETM1_STATUS ZestETM1WriteRegister(ZESTETM1_CARD_INFO *CardInfo, unsigned long Addr, unsigned short Data);
ZESTETM1_STATUS ZestETM1ReadRegister(ZESTETM1_CARD_INFO *CardInfo, unsigned long Addr, unsigned short *Data);
ZESTETM1_STATUS ZestETM1SetInterrupt(ZESTETM1_CARD_INFO *CardInfo);

#ifdef __cplusplus
}
#endif

#endif // __ZESTETM1_H__

