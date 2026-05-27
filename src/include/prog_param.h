#ifndef _PROG_PARAM
#define _PROG_PARAM

#include "stdio.h"
#include "../time_lib/time_lib.h"

#define LOGFILENAMELEN 255

typedef struct prog_param_struct {
   FILE      *pfLogfile;
   FILE      *pfErrorfile;
   FILE      *pzErrorCodeFID;
   char       acSite[6];
   char       cStartTime[DATETIME_LEN + 1];
   char       acAdminMailAddr[64];
   short      sMode;
   long       lAuditLevel;
   long       lMessages;
   long       lTimeOuts;
   long       lMaxMsgSize;
   /*MSG_PARM  *zMsgBase;*/
   void      *hSession;
   void      *hRefMD;
   void      *hPendQCache;
} PROG_PARAM;

/*
 * Return Codes
 */
#define retSUCCESS           0
#define retWARNING           1
#define retBADMSG            2
#define retFATAL             3
#define retNOMSG             4
#define retSHIPMENTCOMPLETE  5 /*20021204 KF Shipment complete messages are rejected*/
#define retDUPMSG            6
#define retOLDMSG            7
#define retUNEXPECTEDMSG     8
#define retNOTTHISTERMINAL   9
#define retDATANOTFOUND     10
#define retNOPQMSG          11
#define retUNKNOWNMSG       12
#define retBADFILE          13
#define retFENCEPOST        14
#define retBADPTR           15
#define retBADSPEC          16
#define retMEMUNDER         17  /* 10001b*/
#define retMEMOVER          18  /* 10010b */
#define retMEMBOTH          35  /*100011b*/

/*
 * Sizing parameters
 */
#define MAXLINE 128
#define MAXMSG  4096000

/*
 * Running modes
 */
#define HALT    0
#define NORMAL  1
#define ONESHOT 2

/*
 * Message Types
 */
#define UNKNOWN 0
#define OASIS   1
#define EME     2
#define IIS     3
#define YARDS   4
#define ADMIN   5
#define UMLER   6


/*
 * Trace Log Level Defines
 */

 /* 2004 08 06 KF - Adding some meaning to these levels.  Intent is _now_:
  * level A - going in and out of routines (except malloc/free etc)
  * level B - what parameters were passed into the routine, logging of some of the more important variables
  * level C - Compares, End of Loops, Results
  * level D - Data Dump - step by step what is being done.
  */
#define TL_NONE      0x0
#define TL_TOPINOUT  0x2
#define TL_MODINOUT  0x3
#define TL_LOWINOUT  0x4
#define TL_LOOP      0x5
#define TL_LEVELMASK 0xf
#define TL_STREAMS   0xfffffff0
#define TL_ANAL      0xffffffff

#define TL_IISA      0x10
#define TL_IISB      0x20
#define TL_IISC      0x40
#define TL_IISD      0x80

#define TL_EMEA      0x100
#define TL_EMEB      0x200
#define TL_EMEC      0x400
#define TL_EMED      0x800

#define TL_OMAA      0x1000
#define TL_OMAB      0x2000
#define TL_OMAC      0x4000
#define TL_OMAD      0x8000

#define TL_OASISA    0x10000
#define TL_OASISB    0x20000
#define TL_OASISC    0x40000
#define TL_OASISD    0x80000

#define TL_YARDSA    0x100000
#define TL_YARDSB    0x200000
#define TL_YARDSC    0x400000
#define TL_YARDSD    0x800000

#define TL_COMMONA   0x1000000
#define TL_COMMONB   0x2000000
#define TL_COMMONC   0x4000000
#define TL_COMMOND   0x8000000


#endif
