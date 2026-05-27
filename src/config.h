typedef struct connectiondetails_struct
{
   char *server;
   char *user;
   char *password;
   char *database;
} connectiondetails;

extern connectiondetails * psReadConfig( FILE *pfLogFile, char * pcConfigFileName );

