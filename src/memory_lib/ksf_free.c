#include "prog_param/prog_param.h"

void ksf_free(PROG_PARAM *pzPP,/*@null@*//*@only@*/ void *ptr, char *pcPlace)
/*@releases ptr@*//* @ensures isnull ptr@ *//*@modifies ptr@*/

{
#ifdef _Logging
(void) iyc010_lTrace( pzPP, TL_COMMONB, "MEMORY_LIB", __FILE__, __LINE__,
                "ksf_free");
#endif
/*(void) iyc000_free(pzPP, ptr, pcPlace);*/
	free( ptr );

/*ptr = NULL;*/ /*Pass by value makes this call useless*/
#ifdef _Logging
(void) iyc010_lTrace( pzPP, TL_COMMONB, "MEMORY_LIB", __FILE__, __LINE__,
                "ksf_free Exit");
#endif
return;
}

#ifdef OMA
long iyc000_free(PROG_PARM *pPP,/*@null@*//*@out@*//*@only@*/void *ptr, char *pcPlace)/*@modifies ptr@*//*@releases ptr@*/{
  long lRetValue,i;
  char *pcStart, *pcEnd;
  #ifdef MALLINFO
  struct mallinfo mi;
  #endif

if (ptr != NULL)
 {
  pcStart = (char *)ptr - MALLOC_HEADER_LENGTH - sizeof(long);

  if ( mallocCounter == 0){
    iyc010_lOMAERRprintf( pPP, "FREE", __FILE__, __LINE__,
            "Warning iyc000_free() called for mallocCounter=0: {%s}\n",pcPlace );
    printf("Warning iyc000_free() called for mallocCounter=0: {%s}\n",pcPlace);
    fflush( stdout );
    fprintf(pPP->pzErrorFID,"Warning iyc000_free() called for mallocCounter=0: {%s}\n",pcPlace);
    fflush( pPP->pzErrorFID );
  }

  if (memcmp(pcStart, MALLOC_FREE_TAG, MALLOC_FREE_LENGTH) == 0){
    iyc010_lOMAERRprintf( pPP, "FREE", __FILE__, __LINE__,
            "Attempting to free an already freed block of memory: Caller{%s} Ptr[%.12s]\n",pcPlace, ptr );
    printf("Attempting to free an already freed block of memory: {%s}[%.12s]\n",pcPlace, ptr);
    fflush( stdout );
    fprintf(pPP->pzErrorFID,"Attempting to free an already freed block of memory: {%s}[%.12s]\n",pcPlace, ptr);
    fflush( pPP->pzErrorFID );
    return IYWARNING;
  }

  lRetValue = iyc000_lHeapVerify( pPP, ptr, pcPlace);

  if (IYSUCCESS == lRetValue)
  { /*OK to free the memory*/
    memcpy( pcStart, MALLOC_FREE_TAG, MALLOC_FREE_LENGTH );
    free( (void *)pcStart );
    mallocCounter--;
  }
  /*Assumed else - heapverify logs why it returns IYWARNING*/

#ifdef DEBUG_ON
  for (i=0; i<mallocIndex; i++){
    if (aMallocList[i].lMemLoc==(long)pcStart){
      aMallocList[i].lMemLoc=0;
      break;
    }
  }
#endif
 }
 else
 /*ptr == NULL */
   lRetValue = IYSUCCESS;
  return lRetValue;
}

#endif
