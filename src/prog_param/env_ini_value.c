#include "stdlib.h"
#include "stdio.h"

/*******************************************************************
*
*	Using the environment to pass values
*
*******************************************************************/

/*func*/ char *getEnvVar( char *envVariable )
{
	char *envValue;

        envValue = getenv( envVariable ) ;
	/* if envValue is NULL the environment variable wasn't set */
	return envValue;
}

/*func*/ FILE * fpFromEnv( char *pcEnvVariable )
{
	FILE *pfEnv;
	pfEnv = fopen( getEnvVar( pcEnvVariable ), "w" );
	return pfEnv;
}

