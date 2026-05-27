#include "iyc00004.h"
#include "stdio.h"
#include "prog_param.h"
#include "stdlib.h"
#include "string.h"

/*=============================================================================
*    $Archive:   J:\R1.0.0\Archives\iyc00004.c_v  $  $Revision:   1.0  $
*       FILE    :       iyc00004.c
*       DESCRIPTION :   This file is not part of the OASIS API. It contains
*			the functions I needed to test the API by writting
*			my own executable. Such functions would be handy in 
*			a corporate library. 
*
*                       Liam Alton      29/10/98
* (tabstop=8)
===============================================================================*/

/********************************************************************************
*	NAME		: iyc00004_pcStrip
*	DESCRIPTION	: Ignore unwanted blanks.
*  			  On exit the return value points to the input string
*  			  with all leading and trailing blanks removed.
*
*	INPUT		: s	char *Input string
*	RETURN		: s	char *output string
*	NOTE		:
*
*
*	MODIFICATION HISTORY
*	NAME		DATE		DESCRIPTION
*	-------------------------------------------
*	Liam Alton	12/01/98	Created
*
********************************************************************************/
char *iyc00004_pcStrip(char *pcInString) 
{
	/*
	* invoke StripLeading and StripTrailing
	*/
    	return iyc00004_pcStripTrailing(iyc00004_pcStripLeading(pcInString));
}

/********************************************************************************
*       NAME            : iyc00004_pcStripLeading
*       DESCRIPTION     : Remove unwanted blanks from strings
*                         On exit the return value points to the input string
*                         with all leading blanks removed.
*
*       INPUT           : s     char *          Input string
*       RETURN          : s     char *          output string
*       NOTE            :
*
*
*       MODIFICATION HISTORY
*       NAME            DATE            DESCRIPTION
*       -------------------------------------------
*       Liam Alton      12/01/98        Created
********************************************************************************/
char *iyc00004_pcStripLeading(char *pcInString) 
{

	char *pcString;

	/*
	*       Search for first non blank
	*/
	for (pcString = pcInString; *pcString; pcString++)
	{
		if (!isspace(*pcString))
		{
			break;
		}
	}
	/*
	*       Return pointer to first non blank
	*/
	return pcString;
}

/********************************************************************************
*       NAME            : iyc00004_pcStripTrailing
*       DESCRIPTION     : Remove unwanted blanks from strings
*                         On exit the return value points to the input string
*                         with all trailing blanks removed.
*
*       INPUT           : s     char *          Input string
*       RETURN          : s     char *          output string
*       NOTE            :
*
*
*       MODIFICATION HISTORY
*       NAME            DATE            DESCRIPTION
*       -------------------------------------------
*       Liam Alton      12/01/98        Created
*
********************************************************************************/
char *iyc00004_pcStripTrailing(char *pcInString) 
{
	char *pcString;
	int i;
	int j;
	int l;

	/*
	* get length of input string
	*/
	l = strlen(pcInString);
	pcString = pcInString;

	/*
	* loop backwards over string
	*/
	for (i = l; i > 0; i--) 
	{
		/*
		* exit loop if non blank
		*/
		if (pcString[i])
		{
			break;
		}
		/*
		* index of last byte
        	*/
		j = i - 1;
		/*
		* if white space, change to NULL byte
		*/
		if (isspace(pcString[j]))
		{
			pcString[j] = '\0';
		}
	}
	/*
	* return starting address of string
	*/
	return pcString;
}

/*******************************************************************************
*       NAME            : iyc00004_iPutEnviroVar
*       DESCRIPTION     : Open an environment file containing the program variables.
*                         For each variable create an environment variable.
*			  Close the environment file.
*
*       INPUT           : pcEnvFile    char *          Environment File
*       RETURN          : 
*       NOTE            :
*
*
*
*       MODIFICATION HISTORY
*       NAME            DATE            DESCRIPTION
*       -------------------------------------------
*       Liam Alton      12/01/98        Created
*
********************************************************************************/
int iyc00004_ePutEnviroVar(char *pcEnvFile) 
{

	FILE *pFile;
	char acLine[LINESIZE];
	char *pcBuffer;

	/*
	* Open the file containing the values for the ENVIRONMENT variables.
	*/
	if ((pFile = fopen(pcEnvFile,"r"))==NULL){
		fprintf(stdout, "Unable to Open Environment File\n");
		return retBADPTR;
	}
	/*
	* For each VARIABLE=VALUE in the file create an ENVIRONMENT variable
	*/
	while (fgets(acLine,LINESIZE,pFile) != NULL){
		iyc00004_pcStrip(acLine);
		if (acLine[0] != '\0'){
		pcBuffer = (char *) malloc (strlen(acLine));
		strcpy(pcBuffer,acLine);
		putenv(pcBuffer);
	}
	}
	if (fclose (pFile) != 0)
	{
		fprintf(stdout, "Unable to Close Environment File\n");
		return retBADPTR;
	}
	return retSUCCESS;
}
