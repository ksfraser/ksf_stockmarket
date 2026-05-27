
#define LOG(st) if( NULL != pfLogFile ) fprintf( pfLogFile, "%s %3.3d %s\n", __FILE__, __LINE__, st ); fflush( pfLogFile );
#define LOGI( it) if( NULL != pfLogFile ) fprintf( pfLogFile, "%s %3.3d %d\n", __FILE__, __LINE__, it ); fflush( pfLogFile );

