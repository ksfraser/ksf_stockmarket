#include "stdlib.h"
#include "string.h"
#include "stdio.h"
#include "malloc_memset.h"

/*func*/ /*@only@*/ /*@null@*/ char * pcmalloc_memset( size_t t_memsize )
{
	char * pc_mem;
	pc_mem = (char *)malloc( t_memsize + 1);

        if( NULL != pc_mem )
                memset( pc_mem, 0, t_memsize + 1 );
	return pc_mem;
}

