#include <stdlib.h>
#include <string.h>
#include <time.h>


/*@only@*/ /*@null@*/  struct tm * get_localtime( )
{
  	time_t curtime;
  	/*@out@*/ struct tm *loctime;

  	/* Get the current time.  */
  	curtime = time (NULL);

  	/* Convert it to local time representation.  */
  	loctime = localtime (&curtime);
	return loctime;
}


/*@only@*/ /*@null@*/ char * ksf_datestring( /*void*/ )
{
	char *buffer;
  	struct tm *loctime;
	loctime = get_localtime();
	if( NULL == loctime )
		return NULL;
	buffer = (char *) malloc( 257 );
	if( NULL == buffer )
	{
		free( loctime );
		return NULL;
	}
	memset( buffer, 0, 257 );
	(void) strftime( buffer, 256, "%Y-%m-%d", loctime );
	/*free( loctime );*/
	return buffer;	
}

/*@only@*/ /*@null@*/ char * ksf_datetimestring( /*void*/ )
{
	char *buffer;
  	struct tm *loctime;
	loctime = get_localtime();
	if( NULL == loctime )
		return NULL;
	buffer = (char *) malloc( 257 );
	if( NULL == buffer )
	{
		free( loctime );
		return NULL;
	}
	memset( buffer, 0, 257 );
	(void) strftime( buffer, 256, "%Y-%m-%d %I:%M:%s", loctime );
	/*free( loctime );*/
	return buffer;	
}

#ifdef example_from_web
  /* Print out the date and time in the standard format.  */
  fputs (asctime (loctime), stdout);

  /* Print it out in a nice format.  */
  strftime (buffer, 256, "Today is %A, %B %d.\n", loctime);
  fputs (buffer, stdout);

/*HH:MM*/
  strftime (buffer, 256, "The time is %I:%M %p.\n", loctime);
  fputs (buffer, stdout);
#endif
