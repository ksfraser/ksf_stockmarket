#include "src/memory_lib/memory_lib.h"
#include "src/time_lib/time_lib.h"
#include "/usr/include/mysql/mysql.h"
#include "ta-lib/c/include/ta_func.h"
#include "ta-lib/c/include/ta_libc.h"
#include "ta-lib.example.h"


#include "stdlib.h"
#include "stdio.h"
#include "string.h"


/*
*****************************************************************************
*
* Name: update_mysql
*
* Function Description: take query components and update mysql
*
* Input Parameters:
        pfLogfile,
        conn,
        tablename
        query_setdata,
        query_where
*
* Output Parameters:
*
* Return:
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
/*func*/ int update_mysql( /*@null@*/ FILE* pfLogfile, MYSQL *pconn, char* tablename, char* query_setdata, char* query_where )
{
/*
                sprintf( query_update, "update technicalanalysis set " );
                sprintf( query_where, " where symbol = '%s' and date = '%s'\n", dataarray[i].symbol, dataarray[i].date );
*/
        char query_update[1000];
        char query_update_mysql[10000];
	char *error;

        memset( query_update, 0, 1000 );
        (void) snprintf( query_update, 999, "update %s set ", tablename );
        memset( query_update_mysql, 0, 10000 );
        strcat( query_update_mysql, query_update );
        strcat( query_update_mysql, query_setdata );
        strcat( query_update_mysql, query_where );
        printf( "%s\n", query_update_mysql );
	if( NULL != pfLogfile )
        	fprintf( pfLogfile, "%s\n", query_update_mysql );
/*Update technicalanalysis*/
        if( mysql_query( pconn, query_update_mysql  ) )
        {
		error =  mysql_error( pconn );
		if( NULL != pfLogfile )
                	fprintf( pfLogfile, "Failed  query: %s\n", error );
		else
                	printf( "Failed  query: %s\n", error );
		free( error );
        }
        else
        {
                /*res_count = mysql_field_count( pconn );*/
        }
        return 1;
}


/******************************************************************************
*
* Name: build_stockdata_select_query
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
/*func*/ /*@null@*/ char * build_stockdata_select_query( char *symbol, /*@null@*/ char *startdate, /*@null@*/ char *enddate )
{


        char query[10000]; /* = "select date, symbol, day_close, day_high, day_low, day_open, volume from stockprices where symbol='IBM' and date > '2009-06-30' order by date asc";*/
        char query_select[] = "select date, symbol, day_close, day_high, day_low, day_open, volume from stockprices";
        char query_selectwhere[] = " where symbol='";
        char query_selectorderby[] = " order by date asc";
        char *querystring;
/*Confirm that the variables are set...*/
        if( NULL == symbol )
                return NULL;
        if( NULL == startdate )
        {
                startdate = ksf_pc_malloc( 10 );
                if( NULL == startdate )
                        return NULL;
                else
                        strcpy( startdate, "2011-01-01" );
        }
        if( NULL == enddate )
        {
                enddate = ksf_datestring();
                if( NULL == enddate )
                        return NULL;
        }

        memset( query, 0, 10000 );
        strcat( query, query_select );
        strcat( query, query_selectwhere );
        strcat( query, symbol );
        strcat( query, "' and date > '" );
        strcat( query, startdate );
        strcat( query, "' and date < '" );
        strcat( query, enddate );
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

/*func*/ int extract_stockdata_select_query ( /*@unused@*/ FILE* pfLogfile, MYSQL *conn, TA_DAT * dataarray, TA_Real *closePrice, TA_Real *openPrice, TA_Real *highPrice, TA_Real *lowPrice, TA_Real *tar_volume )

{
	MYSQL_RES *result;
        MYSQL_ROW row;
        /* /*@unused@* / MYSQL_FIELD *field; */
	int resultcount = 0;
	float price = 0;

	result = mysql_store_result( conn );
        while   (
                   (
                     row = mysql_fetch_row( result )
                   ) != NULL
                )
        {
/*
	        	mysql_field_seek( result, 1 );
        	        field = mysql_fetch_field( result );
                        fprintf( pfLogfile, "Field details: %s is %lu long, type: %i value: %s\n", field->name, field->length, field->type, (char*)row[1] );
                        fprintf( pfLogfile, "%s: %s\n ", (char*)row[0], (char*)row[1] );
*/
		price = strtof( (char*)row[2], NULL );
		closePrice[resultcount] = price;
		price = strtof( (char*)row[3], NULL );
		highPrice[resultcount] = price;
		price = strtof( (char*)row[4], NULL );
		lowPrice[resultcount] = price;
		price = strtof( (char*)row[5], NULL );
		openPrice[resultcount] = price;
		price = strtof( (char*)row[6], NULL );
		tar_volume[resultcount] = price;
		strcpy( dataarray[resultcount].date, (char*)row[0] );
		strcpy( dataarray[resultcount].symbol, (char*)row[1] );
		dataarray[resultcount].closePrice =  closePrice[resultcount];
		dataarray[resultcount].highPrice =  highPrice[resultcount];
		dataarray[resultcount].lowPrice =  lowPrice[resultcount];
		dataarray[resultcount].openPrice =  openPrice[resultcount];
		dataarray[resultcount].volume =  tar_volume[resultcount];
		resultcount++;

                }
	mysql_free_result( result );
	return resultcount;
}

