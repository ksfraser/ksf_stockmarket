#include "src/memory_lib/memory_lib.h"
#include "src/time_lib/time_lib.h"
#include "/usr/include/mysql/mysql.h"
#include "ta-lib/c/include/ta_func.h"
#include "ta-lib/c/include/ta_libc.h"
#include "ta-lib.example.h"

#include "ksf_sql.h"


#include "stdlib.h"
#include "stdio.h"
#include "string.h"


/******************************************************************************
*
* Name: build_SymbolList_select_query
*
* Function Description: Build the query to select data to do tech anaylsis upon
*
* Input Parameters:
        char *symbol,
        char *startdate,
        char *enddate
*
* Output Parameters:
*
* Return:
        char *querystring
*
* Notes:
*
* Code Reviewed YYYYMMDD XYZ
*
* MODIFICATIONS:
*   Name          Date        Description
*   ------------  ----------  ---------------------------------------
*   K. Fraser     2012.08.14  created
*
*******************************************************************************
*/
/*func*/ /*@null@*/ char * build_SymbolList_select_query( /*@null@*/ FILE* pfLogfile, /*@NULL@*/ char * pcActive )
{


        char query[10000]; /* = "select symbol from stockprices where active='"1"' order by stocksymbol asc";*/
        char query_select[] = "select stocksymbol from stockinfo";
        char query_selectwhere[] = " where active='";
        char query_selectorderby[] = " order by stocksymbol asc";
        char *querystring;

	/*Check params are valid*/
	if( NULL == pfLogfile )
	{
		/*do nothing */
	}
	if( NULL == pcActive )
	{
		pcActive = (char *) malloc(1);
		if( NULL == pcActive )
			return NULL;
		memset( pcActive, '1', 1 );
	}

        memset( query, 0, 10000 );
        strcat( query, query_select );
        strcat( query, query_selectwhere );
        strcat( query, pcActive );
        strcat( query, "'" );
        strcat( query, query_selectorderby );
        querystring = (char *) malloc( strlen( query ) + 1 );
        if( NULL == querystring )
        {
                /*ERROR*/
                return NULL;
        }
        memset( querystring, 0, strlen( query ) + 1 );
        querystring = strncpy( querystring, query, strlen( query ));
        return querystring;
}

/*func*/ /*@null@*/ SLIST * extract_SymbolList_select_query ( /*@unused@*/ /*@null@*/ FILE* pfLogfile, MYSQL *pconn )

{
	MYSQL_RES *result;
        MYSQL_ROW row;
        /*@unused@* / MYSQL_FIELD *field;*/
	SLIST * pSymbolList, *pFirst, *pNext;

	/*Check params are valid*/
	if( NULL == pfLogfile )
	{
		/*do nothing */
	}
	if( NULL == pconn )
	{
		/*nothing can be done without the pconnection to the DB*/
		return NULL;
	}

	pSymbolList = (SLIST *) malloc( sizeof( SLIST ) );
	if( NULL == pSymbolList )
		return NULL;
	pSymbolList->next = NULL;
	memset( pSymbolList, 0, sizeof( SLIST ) );
	memset( pSymbolList->symbol, 0, sizeof( pSymbolList->symbol ) );
	pFirst = pSymbolList;
	pFirst->count++;

	result = mysql_store_result( pconn );
        while   (
                   (
                     row = mysql_fetch_row( result )
                   ) != NULL
                )
        {
		strncpy( pSymbolList->symbol, (char*)row[1], MIN( sizeof( pSymbolList->symbol ), strlen( (char*)row[1] ) ) );
		pNext = (SLIST *) malloc( sizeof( SLIST ) );
		/*pSymbolList->next = (SLIST *) malloc( sizeof( SLIST ) );*/
		/*if( NULL == pSymbolList->next )*/
		if( NULL == pNext )
		{
			mysql_free_result( result );
			return pFirst;
		}
		pFirst->count++;
		pSymbolList->count = pFirst->count;
		pSymbolList->next = pNext;
		pSymbolList = pSymbolList->next;
		memset( pSymbolList, 0, sizeof( SLIST ) );
		memset( pSymbolList->symbol, 0, sizeof( pSymbolList->symbol ) );
		pSymbolList->next = NULL;
        }
	mysql_free_result( result );
	return pFirst;
}

/*func*/ /*@null@*/ SLIST * getSymbolList( /*@null@*/ FILE* pfLogfile, MYSQL *pconn )
{
	SLIST * pSymbolList;
	char * query;
	char *error;

	/*Check params are valid*/
	if( NULL == pfLogfile )
	{
		/*do nothing */
	}
	if( NULL == pconn )
	{
		/*nothing can be done without the pconnection to the DB*/
		return NULL;
	}

	pSymbolList = NULL;

	query = build_SymbolList_select_query( pfLogfile, NULL );
	if( NULL != query )
	{
		if( 0 != mysql_query( pconn, query  ) )
		{
			if( NULL != pfLogfile )
			{
				error = mysql_error( pconn );
				fprintf( pfLogfile, "Failed  query: %s\n", error );
				free( error );
			}
			else
			{
				error = mysql_error( pconn );
				printf( "Failed  query: %s\n", error );
				free( error );
			}
		}
		pSymbolList = extract_SymbolList_select_query ( pfLogfile, pconn );
		free( query );
	}
	return pSymbolList;
}

