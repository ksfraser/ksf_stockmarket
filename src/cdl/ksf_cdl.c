/* */
#include "ta-lib/c/include/ta_func.h"
#include "ta-lib/c/include/ta_libc.h"
#include "stdlib.h"
#include "stdio.h"
#include "string.h"
#include "../../ta-lib.example.h"
#include "ksf_cdl.h"
/* */
/* */
/*func*/ TA_CDL_DAT * calcCandlesticks(/*@null@*/ FILE *pfLogfile, int startIdx, int endIdx, TA_Real *openPrice, TA_Real *highPrice, TA_Real *lowPrice, TA_Real *closePrice, /*@only@*/ TA_CDL_DAT *cdldataarray, const TA_DAT *dataarray ) {
	TA_RetCode retCode;
	int i;
	int outBeg;
	int outNbElement;
	int iout[MAXROWS];
	double doptInPenetration = 14;
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDL2CROWS\n", __LINE__ );
	retCode = TA_CDL2CROWS( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDL2CROWS = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDL3BLACKCROWS\n", __LINE__ );
	retCode = TA_CDL3BLACKCROWS( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDL3BLACKCROWS = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDL3INSIDE\n", __LINE__ );
	retCode = TA_CDL3INSIDE( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDL3INSIDE = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDL3LINESTRIKE\n", __LINE__ );
	retCode = TA_CDL3LINESTRIKE( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDL3LINESTRIKE = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDL3OUTSIDE\n", __LINE__ );
	retCode = TA_CDL3OUTSIDE( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDL3OUTSIDE = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDL3STARSINSOUTH\n", __LINE__ );
	retCode = TA_CDL3STARSINSOUTH( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDL3STARSINSOUTH = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDL3WHITESOLDIERS\n", __LINE__ );
	retCode = TA_CDL3WHITESOLDIERS( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDL3WHITESOLDIERS = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLADVANCEBLOCK\n", __LINE__ );
	retCode = TA_CDLADVANCEBLOCK( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLADVANCEBLOCK = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLBELTHOLD\n", __LINE__ );
	retCode = TA_CDLBELTHOLD( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLBELTHOLD = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLBREAKAWAY\n", __LINE__ );
	retCode = TA_CDLBREAKAWAY( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLBREAKAWAY = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLCLOSINGMARUBOZU\n", __LINE__ );
	retCode = TA_CDLCLOSINGMARUBOZU( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLCLOSINGMARUBOZU = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLCONCEALBABYSWALL\n", __LINE__ );
	retCode = TA_CDLCONCEALBABYSWALL( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLCONCEALBABYSWALL = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLCOUNTERATTACK\n", __LINE__ );
	retCode = TA_CDLCOUNTERATTACK( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLCOUNTERATTACK = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLDOJI\n", __LINE__ );
	retCode = TA_CDLDOJI( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLDOJI = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLDOJISTAR\n", __LINE__ );
	retCode = TA_CDLDOJISTAR( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLDOJISTAR = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLDRAGONFLYDOJI\n", __LINE__ );
	retCode = TA_CDLDRAGONFLYDOJI( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLDRAGONFLYDOJI = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLENGULFING\n", __LINE__ );
	retCode = TA_CDLENGULFING( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLENGULFING = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLGAPSIDESIDEWHITE\n", __LINE__ );
	retCode = TA_CDLGAPSIDESIDEWHITE( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLGAPSIDESIDEWHITE = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLGRAVESTONEDOJI\n", __LINE__ );
	retCode = TA_CDLGRAVESTONEDOJI( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLGRAVESTONEDOJI = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLHAMMER\n", __LINE__ );
	retCode = TA_CDLHAMMER( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLHAMMER = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLHANGINGMAN\n", __LINE__ );
	retCode = TA_CDLHANGINGMAN( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLHANGINGMAN = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLHARAMICROSS\n", __LINE__ );
	retCode = TA_CDLHARAMICROSS( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLHARAMICROSS = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLHARAMI\n", __LINE__ );
	retCode = TA_CDLHARAMI( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLHARAMI = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLHIGHWAVE\n", __LINE__ );
	retCode = TA_CDLHIGHWAVE( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLHIGHWAVE = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLHIKKAKEMOD\n", __LINE__ );
	retCode = TA_CDLHIKKAKEMOD( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLHIKKAKEMOD = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLHIKKAKE\n", __LINE__ );
	retCode = TA_CDLHIKKAKE( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLHIKKAKE = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLHOMINGPIGEON\n", __LINE__ );
	retCode = TA_CDLHOMINGPIGEON( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLHOMINGPIGEON = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLIDENTICAL3CROWS\n", __LINE__ );
	retCode = TA_CDLIDENTICAL3CROWS( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLIDENTICAL3CROWS = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLINNECK\n", __LINE__ );
	retCode = TA_CDLINNECK( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLINNECK = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLINVERTEDHAMMER\n", __LINE__ );
	retCode = TA_CDLINVERTEDHAMMER( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLINVERTEDHAMMER = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLKICKINGBYLENGTH\n", __LINE__ );
	retCode = TA_CDLKICKINGBYLENGTH( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLKICKINGBYLENGTH = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLKICKING\n", __LINE__ );
	retCode = TA_CDLKICKING( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLKICKING = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLLADDERBOTTOM\n", __LINE__ );
	retCode = TA_CDLLADDERBOTTOM( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLLADDERBOTTOM = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLLONGLEGGEDDOJI\n", __LINE__ );
	retCode = TA_CDLLONGLEGGEDDOJI( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLLONGLEGGEDDOJI = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLLONGLINE\n", __LINE__ );
	retCode = TA_CDLLONGLINE( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLLONGLINE = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLMARUBOZU\n", __LINE__ );
	retCode = TA_CDLMARUBOZU( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLMARUBOZU = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLMATCHINGLOW\n", __LINE__ );
	retCode = TA_CDLMATCHINGLOW( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLMATCHINGLOW = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLONNECK\n", __LINE__ );
	retCode = TA_CDLONNECK( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLONNECK = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLPIERCING\n", __LINE__ );
	retCode = TA_CDLPIERCING( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLPIERCING = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLRICKSHAWMAN\n", __LINE__ );
	retCode = TA_CDLRICKSHAWMAN( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLRICKSHAWMAN = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLRISEFALL3METHODS\n", __LINE__ );
	retCode = TA_CDLRISEFALL3METHODS( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLRISEFALL3METHODS = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLSEPARATINGLINES\n", __LINE__ );
	retCode = TA_CDLSEPARATINGLINES( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLSEPARATINGLINES = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLSHOOTINGSTAR\n", __LINE__ );
	retCode = TA_CDLSHOOTINGSTAR( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLSHOOTINGSTAR = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLSHORTLINE\n", __LINE__ );
	retCode = TA_CDLSHORTLINE( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLSHORTLINE = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLSPINNINGTOP\n", __LINE__ );
	retCode = TA_CDLSPINNINGTOP( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLSPINNINGTOP = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLSTALLEDPATTERN\n", __LINE__ );
	retCode = TA_CDLSTALLEDPATTERN( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLSTALLEDPATTERN = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLSTICKSANDWICH\n", __LINE__ );
	retCode = TA_CDLSTICKSANDWICH( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLSTICKSANDWICH = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLTAKURI\n", __LINE__ );
	retCode = TA_CDLTAKURI( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLTAKURI = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLTASUKIGAP\n", __LINE__ );
	retCode = TA_CDLTASUKIGAP( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLTASUKIGAP = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLTHRUSTING\n", __LINE__ );
	retCode = TA_CDLTHRUSTING( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLTHRUSTING = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLTRISTAR\n", __LINE__ );
	retCode = TA_CDLTRISTAR( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLTRISTAR = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLUNIQUE3RIVER\n", __LINE__ );
	retCode = TA_CDLUNIQUE3RIVER( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLUNIQUE3RIVER = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLUPSIDEGAP2CROWS\n", __LINE__ );
	retCode = TA_CDLUPSIDEGAP2CROWS( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLUPSIDEGAP2CROWS = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLXSIDEGAP3METHODS\n", __LINE__ );
	retCode = TA_CDLXSIDEGAP3METHODS( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);
		(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);
		cdldataarray[outBeg+i].CDLXSIDEGAP3METHODS = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLABANDONEDBABY\n", __LINE__ );
	retCode = TA_CDLABANDONEDBABY( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], doptInPenetration, &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		cdldataarray[outBeg+i].CDLABANDONEDBABY = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLDARKCLOUDCOVER\n", __LINE__ );
	retCode = TA_CDLDARKCLOUDCOVER( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], doptInPenetration, &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		cdldataarray[outBeg+i].CDLDARKCLOUDCOVER = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLEVENINGDOJISTAR\n", __LINE__ );
	retCode = TA_CDLEVENINGDOJISTAR( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], doptInPenetration, &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		cdldataarray[outBeg+i].CDLEVENINGDOJISTAR = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLEVENINGSTAR\n", __LINE__ );
	retCode = TA_CDLEVENINGSTAR( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], doptInPenetration, &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		cdldataarray[outBeg+i].CDLEVENINGSTAR = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLMATHOLD\n", __LINE__ );
	retCode = TA_CDLMATHOLD( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], doptInPenetration, &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		cdldataarray[outBeg+i].CDLMATHOLD = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLMORNINGDOJISTAR\n", __LINE__ );
	retCode = TA_CDLMORNINGDOJISTAR( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], doptInPenetration, &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		cdldataarray[outBeg+i].CDLMORNINGDOJISTAR = iout[i];
	}
	
	if( NULL != pfLogfile )
		(void) fprintf( pfLogfile, "%i TA_CDLMORNINGSTAR\n", __LINE__ );
	retCode = TA_CDLMORNINGSTAR( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], doptInPenetration, &outBeg, &outNbElement, &iout[0]); 
	for( i=0; i < outNbElement; i++ )
	{
		cdldataarray[outBeg+i].CDLMORNINGSTAR = iout[i];
	}
	
	return cdldataarray;
}
/*func*/ char * createQueryCandlesticks( TA_CDL_DAT* cdldataarray, int icdlcount, /*@unique@*/ char *query_setfields, size_t setfields_size, /*@in@*/ /*@only@*/ char *query_setdata ) {
	int ifieldcount = 0;
		if( cdldataarray[icdlcount].CDL2CROWS != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDL2CROWS='%i'", cdldataarray[icdlcount].CDL2CROWS );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDL3BLACKCROWS != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDL3BLACKCROWS='%i'", cdldataarray[icdlcount].CDL3BLACKCROWS );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDL3INSIDE != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDL3INSIDE='%i'", cdldataarray[icdlcount].CDL3INSIDE );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDL3LINESTRIKE != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDL3LINESTRIKE='%i'", cdldataarray[icdlcount].CDL3LINESTRIKE );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDL3OUTSIDE != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDL3OUTSIDE='%i'", cdldataarray[icdlcount].CDL3OUTSIDE );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDL3STARSINSOUTH != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDL3STARSINSOUTH='%i'", cdldataarray[icdlcount].CDL3STARSINSOUTH );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDL3WHITESOLDIERS != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDL3WHITESOLDIERS='%i'", cdldataarray[icdlcount].CDL3WHITESOLDIERS );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLABANDONEDBABY != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLABANDONEDBABY='%i'", cdldataarray[icdlcount].CDLABANDONEDBABY );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLADVANCEBLOCK != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLADVANCEBLOCK='%i'", cdldataarray[icdlcount].CDLADVANCEBLOCK );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLBELTHOLD != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLBELTHOLD='%i'", cdldataarray[icdlcount].CDLBELTHOLD );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLBREAKAWAY != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLBREAKAWAY='%i'", cdldataarray[icdlcount].CDLBREAKAWAY );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLCLOSINGMARUBOZU != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLCLOSINGMARUBOZU='%i'", cdldataarray[icdlcount].CDLCLOSINGMARUBOZU );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLCONCEALBABYSWALL != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLCONCEALBABYSWALL='%i'", cdldataarray[icdlcount].CDLCONCEALBABYSWALL );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLCOUNTERATTACK != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLCOUNTERATTACK='%i'", cdldataarray[icdlcount].CDLCOUNTERATTACK );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLDARKCLOUDCOVER != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLDARKCLOUDCOVER='%i'", cdldataarray[icdlcount].CDLDARKCLOUDCOVER );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLDOJI != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLDOJI='%i'", cdldataarray[icdlcount].CDLDOJI );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLDOJISTAR != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLDOJISTAR='%i'", cdldataarray[icdlcount].CDLDOJISTAR );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLDRAGONFLYDOJI != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLDRAGONFLYDOJI='%i'", cdldataarray[icdlcount].CDLDRAGONFLYDOJI );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLENGULFING != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLENGULFING='%i'", cdldataarray[icdlcount].CDLENGULFING );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLEVENINGDOJISTAR != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLEVENINGDOJISTAR='%i'", cdldataarray[icdlcount].CDLEVENINGDOJISTAR );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLEVENINGSTAR != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLEVENINGSTAR='%i'", cdldataarray[icdlcount].CDLEVENINGSTAR );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLGAPSIDESIDEWHITE != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLGAPSIDESIDEWHITE='%i'", cdldataarray[icdlcount].CDLGAPSIDESIDEWHITE );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLGRAVESTONEDOJI != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLGRAVESTONEDOJI='%i'", cdldataarray[icdlcount].CDLGRAVESTONEDOJI );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLHAMMER != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLHAMMER='%i'", cdldataarray[icdlcount].CDLHAMMER );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLHANGINGMAN != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLHANGINGMAN='%i'", cdldataarray[icdlcount].CDLHANGINGMAN );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLHARAMICROSS != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLHARAMICROSS='%i'", cdldataarray[icdlcount].CDLHARAMICROSS );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLHARAMI != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLHARAMI='%i'", cdldataarray[icdlcount].CDLHARAMI );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLHIGHWAVE != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLHIGHWAVE='%i'", cdldataarray[icdlcount].CDLHIGHWAVE );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLHIKKAKEMOD != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLHIKKAKEMOD='%i'", cdldataarray[icdlcount].CDLHIKKAKEMOD );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLHIKKAKE != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLHIKKAKE='%i'", cdldataarray[icdlcount].CDLHIKKAKE );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLHOMINGPIGEON != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLHOMINGPIGEON='%i'", cdldataarray[icdlcount].CDLHOMINGPIGEON );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLIDENTICAL3CROWS != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLIDENTICAL3CROWS='%i'", cdldataarray[icdlcount].CDLIDENTICAL3CROWS );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLINNECK != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLINNECK='%i'", cdldataarray[icdlcount].CDLINNECK );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLINVERTEDHAMMER != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLINVERTEDHAMMER='%i'", cdldataarray[icdlcount].CDLINVERTEDHAMMER );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLKICKINGBYLENGTH != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLKICKINGBYLENGTH='%i'", cdldataarray[icdlcount].CDLKICKINGBYLENGTH );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLKICKING != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLKICKING='%i'", cdldataarray[icdlcount].CDLKICKING );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLLADDERBOTTOM != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLLADDERBOTTOM='%i'", cdldataarray[icdlcount].CDLLADDERBOTTOM );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLLONGLEGGEDDOJI != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLLONGLEGGEDDOJI='%i'", cdldataarray[icdlcount].CDLLONGLEGGEDDOJI );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLLONGLINE != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLLONGLINE='%i'", cdldataarray[icdlcount].CDLLONGLINE );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLMARUBOZU != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLMARUBOZU='%i'", cdldataarray[icdlcount].CDLMARUBOZU );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLMATCHINGLOW != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLMATCHINGLOW='%i'", cdldataarray[icdlcount].CDLMATCHINGLOW );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLMATHOLD != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLMATHOLD='%i'", cdldataarray[icdlcount].CDLMATHOLD );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLMORNINGDOJISTAR != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLMORNINGDOJISTAR='%i'", cdldataarray[icdlcount].CDLMORNINGDOJISTAR );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLMORNINGSTAR != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLMORNINGSTAR='%i'", cdldataarray[icdlcount].CDLMORNINGSTAR );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLONNECK != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLONNECK='%i'", cdldataarray[icdlcount].CDLONNECK );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLPIERCING != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLPIERCING='%i'", cdldataarray[icdlcount].CDLPIERCING );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLRICKSHAWMAN != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLRICKSHAWMAN='%i'", cdldataarray[icdlcount].CDLRICKSHAWMAN );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLRISEFALL3METHODS != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLRISEFALL3METHODS='%i'", cdldataarray[icdlcount].CDLRISEFALL3METHODS );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLSEPARATINGLINES != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLSEPARATINGLINES='%i'", cdldataarray[icdlcount].CDLSEPARATINGLINES );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLSHOOTINGSTAR != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLSHOOTINGSTAR='%i'", cdldataarray[icdlcount].CDLSHOOTINGSTAR );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLSHORTLINE != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLSHORTLINE='%i'", cdldataarray[icdlcount].CDLSHORTLINE );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLSPINNINGTOP != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLSPINNINGTOP='%i'", cdldataarray[icdlcount].CDLSPINNINGTOP );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLSTALLEDPATTERN != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLSTALLEDPATTERN='%i'", cdldataarray[icdlcount].CDLSTALLEDPATTERN );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLSTICKSANDWICH != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLSTICKSANDWICH='%i'", cdldataarray[icdlcount].CDLSTICKSANDWICH );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLTAKURI != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLTAKURI='%i'", cdldataarray[icdlcount].CDLTAKURI );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLTASUKIGAP != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLTASUKIGAP='%i'", cdldataarray[icdlcount].CDLTASUKIGAP );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLTHRUSTING != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLTHRUSTING='%i'", cdldataarray[icdlcount].CDLTHRUSTING );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLTRISTAR != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLTRISTAR='%i'", cdldataarray[icdlcount].CDLTRISTAR );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLUNIQUE3RIVER != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLUNIQUE3RIVER='%i'", cdldataarray[icdlcount].CDLUNIQUE3RIVER );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLUPSIDEGAP2CROWS != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLUPSIDEGAP2CROWS='%i'", cdldataarray[icdlcount].CDLUPSIDEGAP2CROWS );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
		if( cdldataarray[icdlcount].CDLXSIDEGAP3METHODS != 0 )
		{
			if( ifieldcount > 0 )
				(void) strcat( query_setdata,  ", " );
			memset( query_setfields, 0, setfields_size );
			(void) snprintf( query_setfields, setfields_size, "CDLXSIDEGAP3METHODS='%i'", cdldataarray[icdlcount].CDLXSIDEGAP3METHODS );
			(void) strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
		
	return query_setdata;
}
