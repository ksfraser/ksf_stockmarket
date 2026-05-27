#ifndef KSF_SQL
#define KSF_SQL

typedef struct symbollist
{
        char symbol[8];
	int count;
        /*@null@*/ struct symbollist *next; /*Last one must be NULL to indicate end of linked list*/
} SLIST;


/** getSymbolList.c */
/*func*/ /*@null@*/ char * build_SymbolList_select_query( /*@null@*/ FILE*, /*@NULL@*/ char * pcActive );
/*func*/ /*@null@*/ SLIST * extract_SymbolList_select_query ( /*@unused@*/ /*@null@*/ FILE* pfLogfile, MYSQL *pconn );
/*func*/ /*@null@*/ SLIST * getSymbolList( /*@null@*/ FILE* pfLogfile, MYSQL *pconn );


#endif

/** ksf_sql.c */
/*func*/ int update_mysql( /*@null@*/ FILE*, MYSQL *, char*, char*, char* );
/*func*/ /*@null@*/ char * build_stockdata_select_query( char *symbol, /*@null@*/ char *startdate, /*@null@*/ char *enddate );
/*func*/ int extract_stockdata_select_query ( /*@unused@*/ FILE* pfLogfile, MYSQL *conn, TA_DAT * dataarray, TA_Real *closePrice, TA_Real *openPrice, TA_Real *highPrice, TA_Real *lowPrice, TA_Real *tar_volume );
