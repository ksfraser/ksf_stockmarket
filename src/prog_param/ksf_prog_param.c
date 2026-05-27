#include "prog_param.h"
#include "stdio.h"
#include "string.h"
#include "stdlib.h"
#include "time_lib/time_lib.h"
#include "memory_lib/memory_lib.h"
#include "include/malloc_memset.h"
#include "include/env_ini_value.h"
#include "include/ksf_log.h"

/*func*/ int initProgParam( PROG_PARAM **ppzPP, char *pcIniFilename )
{
char *pcLogfileName, *pcErrorfileName, *pcErrorCodeFIDName;
char pcSite[] = "012345";
char pcAdminMailAddr[] = "kevin@defiant.silverdart.no-ip.org" ;
PROG_PARAM * pzPP;
char *pcDateTime;

	(void) iyc00004_ePutEnviroVar( pcIniFilename );

	pcLogfileName = pcmalloc_memset(LOGFILENAMELEN);
	pcErrorfileName = pcmalloc_memset(LOGFILENAMELEN);
	pcErrorCodeFIDName = pcmalloc_memset(LOGFILENAMELEN);
	
	pcLogfileName = getEnvVar( "LogfileName" );
	pcErrorfileName = getEnvVar( "ErrorfileName" );
	pcErrorCodeFIDName = getEnvVar( "ErrorCodeFIDName" );

	/*Should pass in a config file value*/
	pzPP = malloc( sizeof( PROG_PARAM ));
	if( NULL == pzPP )
	{
		free( pcLogfileName );
		free( pcErrorfileName );
		free( pcErrorCodeFIDName );

		return retFATAL;
	}
	memset( pzPP, 0, sizeof( PROG_PARAM ));
	if( NULL != pcLogfileName )
		pzPP->pfLogfile = fopen( pcLogfileName, "w" );
	if( NULL != pcErrorfileName )
		pzPP->pfErrorfile = fopen( pcErrorfileName, "w" );
	if( NULL != pcErrorCodeFIDName )
		pzPP->pzErrorCodeFID = fopen( pcErrorCodeFIDName, "w" );
	strncpy( pzPP->acSite, pcSite, 6 );
	pcDateTime = ksf_datetimestring();
	if( NULL != pcDateTime )
		strncpy( pzPP->cStartTime, pcDateTime, DATETIME_LEN );
	strncpy( pzPP->acAdminMailAddr, pcAdminMailAddr, strlen( pcAdminMailAddr ) );
	pzPP->sMode = 0;
	pzPP->lAuditLevel = atol( getenv( "LOGLEVEL" ) );
	pzPP->lMessages = 0;
	pzPP->lTimeOuts = 0;
	pzPP->lMaxMsgSize = 0;
	pzPP->hSession = NULL;
	pzPP->hRefMD = NULL;
	pzPP->hPendQCache = NULL;
	ppzPP = &pzPP;
	ksf_log( pzPP, 0, "initProgParam", __FILE__, __LINE__, "%s\n", "Initialization is complete" );

/*
	free( pcLogfileName );
	free( pcErrorfileName );
	free( pcErrorCodeFIDName );
	free( pcDateTime );
*/
	return retSUCCESS;
}

/*func*/ int freeProgParam( PROG_PARAM * pzPP )
/*@releases pzPP@*/
{
	if( NULL != pzPP )
	{
		if( NULL != pzPP->pfLogfile )
		{
			(void) fclose( pzPP->pfLogfile );
			pzPP->pfLogfile = NULL;
		}
		if( NULL != pzPP->pfErrorfile )
		{
			(void) fclose( pzPP->pfErrorfile );
			pzPP->pfErrorfile = NULL;
		}
		if( NULL != pzPP->pzErrorCodeFID )
		{
			(void) fclose( pzPP->pzErrorCodeFID );
			pzPP->pzErrorCodeFID = NULL;
		}
		if( NULL != pzPP->hSession )
		{
			free( pzPP->hSession );
			pzPP->hSession = NULL;
		}
		if( NULL != pzPP->hRefMD )
		{
			free( pzPP->hRefMD );
			pzPP->hRefMD = NULL;
		}
		if( NULL != pzPP->hPendQCache )
		{
			free( pzPP->hPendQCache );
			pzPP->hPendQCache = NULL;
		}
		free( pzPP );
	}
	return retSUCCESS;
}
