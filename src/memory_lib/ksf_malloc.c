#include <stdlib.h>
#include <string.h>

/*@null@*/ char * ksf_pc_malloc( size_t pcharsize )
{
	char * pchar; 
 	pchar = (char *) malloc( pcharsize + 1 );
	if( NULL == pchar )
	{
		/*ERROR Condition*/
		
	}
	else
	{
        	memset( pchar, 0, pcharsize + 1 );
	}
	return pchar;
}

