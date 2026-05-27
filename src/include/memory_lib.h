#ifndef _PROG_PARAM
#include "prog_param/prog_param.h"
#endif

#ifdef BS
/*@null@*/ char * ksf_pc_malloc( size_t pcharsize );
void ksf_free(PROG_PARAM *pzPP,/*@null@*//*@only@*/ void *ptr, char *pcPlace);
#else
char * ksf_pc_malloc( int );
void ksf_free(PROG_PARAM *, void *, char *);
#endif

#include malloc_memset.h
