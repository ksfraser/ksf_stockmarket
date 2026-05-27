#include "src/include/prog_param.h"
#include "stdarg.h"
#include "stdlib.h"
#include "string.h"
#include "unistd.h"

/*
******************************************************************************
*
*    NAME         :  ksf_log()
*    DESCRIPTION  :  Trace routine that checks audit level and uses varargs
*
*    INPUT        :  PROG_PARM *
*                    long iTraceLevel
*                    char *pcProcess (e.g., "EME ")
*                    char *pcFile    (always use __FILE__ )
*                    long lLine      (always use __LINE__ )
*                    char *pcFormat  (e.g., "%s %d")
*                    more arguments as needed by format string
*
*
*    RETURN       :  retSUCCESS if successful
*                    retFAILURE if not successful
*
*    NOTE         :
*
*    MODIFICATIONS:
*    Name           Date          Description
*    ----------------------------------------------------------
*    F. Berg        98/12/02      Initial coding.
*	KSF		2012/08/29	Modified to fit framework
*
******************************************************************************
*/

/*func*/ int ksf_log( PROG_PARAM *pzPP, unsigned int iLoggingLevel, char *pcProcess, char *pcFile, long lLine, char *pcFormat, ... )
{
  va_list args;
	char *pcTimeString;
  FILE *pzFD=stdout;

  if ( pzPP == NULL )
  {
    printf( "******ERROR PROG_PARM pointer is NULL!!!\n");
    return( retFATAL );
  }

  if ( pzPP->pfLogfile != NULL )
  {
    pzFD = pzPP->pfLogfile;
  }
    if( (pzPP->lAuditLevel & iLoggingLevel & TL_STREAMS) ||
      ( iLoggingLevel == 0 ) ||
      (((iLoggingLevel & TL_LEVELMASK) > 0 ) &&
       ((pzPP->lAuditLevel & TL_LEVELMASK) >=
       (iLoggingLevel & TL_LEVELMASK))))
  {
    pcTimeString = ksf_datetimestring();

    fprintf( pzFD, "+%19.19s %08x %-8.16s %-8.16s%5d>", pcTimeString,
                     iLoggingLevel, pcProcess, pcFile, lLine );
	free( pcTimeString );

    va_start( args, pcFormat );

    (void)vfprintf( pzFD, pcFormat, args );

    va_end( args );

    if( pcFormat[ strlen( pcFormat ) - 1 ] != '\n' )
    {
      fprintf( pzFD, "<\n" );
    }

    fflush( pzFD );

  }
  return( retSUCCESS );

}
