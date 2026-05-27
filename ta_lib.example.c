#include "ta-lib/c/include/ta_func.h"
#include "ta-lib/c/include/ta_libc.h"
#include "/usr/include/mysql/mysql.h"
#include "stdlib.h"
#include "string.h"

/*
ta_ACOS.c            ta_CDLRICKSHAWMAN.c       ta_DIV.c                  ta_MACDFIX.c      ta_PLUS_DM.c   ta_TAN.c
ta_AD.c              ta_CDL3STARSINSOUTH.c     ta_CDLHARAMICROSS.c      ta_CDLRISEFALL3METHODS.c  ta_DX.c                   ta_MAMA.c         ta_PPO.c       ta_TANH.c
ta_ADD.c             ta_CDL3WHITESOLDIERS.c    ta_CDLHIGHWAVE.c         ta_CDLSEPARATINGLINES.c   ta_EMA.c                  ta_MAVP.c         ta_PVI.c       ta_TEMA.c
ta_ADOSC.c           ta_CDLABANDONEDBABY.c     ta_CDLHIKKAKE.c          ta_CDLSHOOTINGSTAR.c      ta_EXP.c                  ta_MAX.c          ta_TRANGE.c
ta_CDLADVANCEBLOCK.c      ta_CDLHIKKAKEMOD.c       ta_CDLSHORTLINE.c         ta_FLOOR.c                ta_MAXINDEX.c     ta_ROCP.c      ta_TRIMA.c
ta_CDLBELTHOLD.c          ta_CDLHOMINGPIGEON.c     ta_CDLSPINNINGTOP.c       ta_HT_DCPERIOD.c          ta_MEDPRICE.c     ta_ROCR100.c   ta_TRIX.c
ta_APO.c             ta_CDLBREAKAWAY.c         ta_CDLIDENTICAL3CROWS.c  ta_CDLSTALLEDPATTERN.c    ta_HT_DCPHASE.c           ta_ROCR.c      ta_TSF.c
ta_AROON.c           ta_CDLCLOSINGMARUBOZU.c   ta_CDLINNECK.c           ta_CDLSTICKSANDWICH.c     ta_HT_PHASOR.c            ta_MIDPOINT.c     ta_TYPPRICE.c
ta_AROONOSC.c        ta_CDLCONCEALBABYSWALL.c  ta_CDLTAKURI.c            ta_HT_SINE.c              ta_MIDPRICE.c     ta_SAR.c       ta_ULTOSC.c
ta_ASIN.c            ta_CDLKICKINGBYLENGTH.c  ta_CDLTASUKIGAP.c         ta_HT_TRENDLINE.c         ta_MIN.c          ta_SAREXT.c    ta_utility.c
ta_ATAN.c            ta_CDLDARKCLOUDCOVER.c    ta_CDLTHRUSTING.c         ta_HT_TRENDMODE.c         ta_MININDEX.c     ta_SIN.c       ta_VAR.c
ta_CDLLADDERBOTTOM.c     ta_CDLTRISTAR.c           ta_KAMA.c                 ta_MINMAX.c       ta_SINH.c      ta_WCLPRICE.c
ta_AVGPRICE.c        ta_CDLLONGLEGGEDDOJI.c   ta_CDLUNIQUE3RIVER.c      ta_LINEARREG_ANGLE.c      ta_MINMAXINDEX.c  ta_SMA.c       ta_WILLR.c
ta_BBANDS.c          ta_CDLDRAGONFLYDOJI.c     ta_CDLLONGLINE.c         ta_CDLUPSIDEGAP2CROWS.c   ta_LINEARREG.c            ta_MINUS_DI.c     ta_SQRT.c      ta_WMA.c
ta_BETA.c            ta_CDLMARUBOZU.c         ta_CDLXSIDEGAP3METHODS.c  ta_LINEARREG_INTERCEPT.c  ta_MINUS_DM.c     ta_STDDEV.c
ta_BOP.c             ta_CDLEVENINGDOJISTAR.c   ta_CDLMATCHINGLOW.c      ta_CEIL.c                 ta_LINEARREG_SLOPE.c      
ta_CCI.c             ta_CDLEVENINGSTAR.c       ta_CDLMATHOLD.c          ta_CMO.c                  ta_LN.c                   ta_MULT.c         ta_STOCHF.c
ta_CDLGAPSIDESIDEWHITE.c  ta_CDLMORNINGDOJISTAR.c  ta_CORREL.c               ta_LOG10.c                ta_NATR.c         ta_STOCHRSI.c
ta_CDLGRAVESTONEDOJI.c    ta_CDLMORNINGSTAR.c      ta_COS.c                  ta_NVI.c          ta_SUB.c
ta_CDL3INSIDE.c      ta_CDLHAMMER.c            ta_CDLONNECK.c           ta_COSH.c                      ta_SUM.c
ta_CDL3LINESTRIKE.c  ta_CDLPIERCING.c         ta_DEMA.c                 ta_MACDEXT.c              ta_PLUS_DI.c      ta_T3.c
*/

#define MAXROWS 5000 /*260 work days a year, subtract a dozen bank holidays times 20 years worth...*/
#define STOCHKFAST 14
#define STOCHKSLOW 26
#define STOCHKSLOWTYPE TA_MAType_SMA
#define STOCHDSLOW 26
#define STOCHDSLOWTYPE TA_MAType_SMA
#define MFITIMEPERIOD 14
#define RSITIMEPERIOD 14
#define MOMTIMEPERIOD 14
#define ROCTIMEPERIOD 14
#define OBVTIMEPERIOD 14
#define DOJIPEN 14
#define MACDFAST 12  /* Common values are 12/26/9.  More volatile stocks would have shorter periods where as less volatile would have longer*/
#define MACDSLOW 26
#define MACDSIGNAL 9
#define ADXTIMEPERIOD 14
#define ADXRTIMEPERIOD 14

typedef enum
{
  STOCH,
  STOCHF,
  STOCHRSI,
  MA50,
  MA200,
  MA260,
  ATR
} TypeId;
typedef struct
{
   TypeId testId;
	char funcname[30];

   TA_Integer startIdx;
   TA_Integer endIdx;

   TA_Integer    optInPeriod_1;
   TA_Integer    optInMAType_1;
   TA_Integer    optInPeriod_2;
   TA_Integer    optInMAType_2;

   TA_RetCode expectedRetCode;
/*
   	TA_Integer expectedBegIdx;
   	TA_Integer expectedNbElement;
	TA_Real    closePrice[MAXROWS];
	TA_Real    out[MAXROWS];
	int        iout[MAXROWS];
	int        iout1[MAXROWS];
	int        iout2[MAXROWS];
	TA_Integer outBeg;
	TA_Integer outNbElement;
   	TA_Integer unstablePeriod;
*/

} TA_PARAMS;
/*
static TA_PARAMS ta_params[] = 
{
	{ MA50, TA_MA, 0, MAXROWS, 50, TA_MAType_SMA, 50, TA_MAType_SMA, TA_SUCCESS },
	{ MA200, TA_MA, 0, MAXROWS, 200, TA_MAType_SMA, 200, TA_MAType_SMA, TA_SUCCESS },
	{ MA260, TA_MA, 0, MAXROWS, 260, TA_MAType_SMA, 260, TA_MAType_SMA, TA_SUCCESS },
	{ EMA260, TA_MA, 0, MAXROWS, 260, TA_MAType_EMA, 260, TA_MAType_EMA, TA_SUCCESS },
	{ DEMA260, TA_MA, 0, MAXROWS, 260, TA_MAType_DEMA, 260, TA_MAType_DEMA, TA_SUCCESS },
	{ TEMA260, TA_MA, 0, MAXROWS, 260, TA_MAType_TEMA, 260, TA_MAType_TEMA, TA_SUCCESS },
	{ TRIMA260, TA_MA, 0, MAXROWS, 260, TA_MAType_TRIMA, 260, TA_MAType_TRIMA, TA_SUCCESS },
	{ KAMA260, TA_MA, 0, MAXROWS, 260, TA_MAType_KAMA, 260, TA_MAType_KAMA, TA_SUCCESS },
	{ MAMA260, TA_MA, 0, MAXROWS, 260, TA_MAType_MAMA, 260, TA_MAType_MAMA, TA_SUCCESS },
	{ T3_260, TA_MA, 0, MAXROWS, 260, TA_MAType_T3, 260, TA_MAType_T3, TA_SUCCESS },
	{ ATR10, TA_ATR, 0, MAXROWS, 10, TA_MAType_SMA, 10, TA_MAType_SMA, TA_SUCCESS }
};

*/
	/*retCode = TA_MA( 0, rowsmax, &closePrice[0], 200,TA_MAType_SMA, &outBeg, &outNbElement, &out[0] );*/
	/*retCode = TA_MA( 0, rowsmax, &closePrice[0], 200,TA_MAType_SMA, &outBeg, &outNbElement, &out[0] );*/
	/*retCode = TA_ATR( startIdx, endIdx, &highPrice[0], &lowPirce[0], &closePrice[0], 10, &outBeg, &outNbElement, &out[0] );*/
/* switch( test->testId )
   {
   case TEST_STOCH:
      retCode = TA_STOCH( test->startIdx, test->endIdx, gBuffer[0].in, gBuffer[1].in, gBuffer[2].in, test->optInPeriod_0, test->optInPeriod_1,
                          (TA_MAType)test->optInMAType_1, test->optInPeriod_2, (TA_MAType)test->optInMAType_2, &outBegIdx, &outNbElement, gBuffer[0].in, gBuffer[1].in );
      break;
   case TEST_STOCHF:
      retCode = TA_STOCHF( test->startIdx, test->endIdx, gBuffer[0].in, gBuffer[1].in, gBuffer[2].in, test->optInPeriod_0, test->optInPeriod_1,
                           (TA_MAType)test->optInMAType_1, &outBegIdx, &outNbElement, gBuffer[0].in, gBuffer[1].in );
      break;
   case TEST_STOCHRSI:
      retCode = TA_STOCHRSI( test->startIdx, test->endIdx, gBuffer[2].in, test->optInPeriod_0, test->optInPeriod_1, test->optInPeriod_2, (TA_MAType)test->optInMAType_2,
                             &outBegIdx, &outNbElement, gBuffer[0].in, gBuffer[1].in );
      break;
   
   }
*/

int main( void )
{
	TA_Real    closePrice[MAXROWS];
	TA_Real    openPrice[MAXROWS];
	TA_Real    highPrice[MAXROWS];
	TA_Real    lowPrice[MAXROWS];
	TA_Real    tar_volume[MAXROWS];
	TA_Real    out[MAXROWS];
	int	   iout[MAXROWS];
	double	   dout[MAXROWS];
	double	   dout1[MAXROWS];
	double	   dout2[MAXROWS];
	TA_Integer outBeg;
	TA_Integer outNbElement;
	int i = 0;
	/*int val = 100;*/
	TA_RetCode retCode;
	int resultcount;
	/*int rowsmax;*/
	int ifieldcount;

	FILE *pfLogfile;
	pfLogfile = fopen( "logfile.txt", 'w' );
	typedef struct datastruct
	{
		char date[11];
		char symbol[7];
		double closePrice;
		double highPrice;
		double lowPrice;
		double openPrice;
		double volume;
		float movavg;
		float ma50;
		float ma200;
		float ma260;
		float sd260;
		float expma9;
		float expma12;
		float expma26;
		float expma90;
		float macd;
		float macd_histogram; /*Diff between the MACD and the Signal.  Higher the bars the more momentum*/
		float macd_signal;  /*When MACD crosses above signal line is a BUY signal, and MACD crosses below is a SELL signal*/
		float mamomentum;
		float macrossover;
		float macenterlinecrossover;
		float momentumoscillator;
		float priceoscillator;
		float linearregression;
		float linearregressionangle;
		float linearregressionslope;
		float linearregressionintercept;
		float stochasticK; /*80 is oversold, 20 undersold. %K is raw, %D is moving average (usually 14 days)*/
		float stochasticD; /*80 is oversold, 20 undersold. %K is raw, %D is moving average (usually 14 days)*/
		float relativestrengthindex; /*Above 70 is overbought and below 30 is oversold.  Shorter period is more volatile*/
		float rsioscillator;
		float commoditychannelindex;
		float pricechangepercent;
		float support12;
		float support26;
		float resistance12;
		float resistance26;
		float bollingerbandupper;
		float bollingerbandmiddle;
		float bollingerbandlower;
		float bollingerbandpercent;
		float bollingerbandbandwidth;
		float coeffecientofvariation;
		float annualreturn;
		float annualrisk;
		float truerange;
		float voltrendind90;
		float voltrendind26;
		float voltrendind260;
		float volume260;
		float cdl2crows;
		float cdl3blackcrows;
		float cdl3inside;
		float cdl3outside; /* -100  Usually 1 day behind Engulfing*/
		float cdl3linestrike;
		float cdlcounterattack;
		float cdldoji; 		/* Perfect Doji indicates uncertainty and a likely trend change*/
					/* Double Doji indicates uncertainty and a large move - buy straddles*/
					/* White Doji indicates end of an uptrend*/
		float cdldojistar;
		float cdlgravestonedoji;
		float cdldragonflydoji;
		float cdleveningdojistar;/*End of uptrend?*/
		float cdllongleggeddoji;
		float cdlengulfing; 	/*Bullish Engulfing indicates end of downtrend*/  /* +- 100 */
					/*Bearish Engulfing indicates end of uptrend*/
		float cdlhangingman;	/*Hanging man indicates testing top of run*/
		float cdlinvertedhammer; /*hammer indicates end of uptrend*/
		float cdlshootingstar;	/*Indicates top is near*/
		float cdleveningstar;	/*End of uptrend*/
		float cdlharami;	/*Trend reversal*/
		float cdlkicking; 	/* Kicker indicates a strong change of direction*/
		float cdlhammer;  	/*Hammer indicates end of a downtrend*/
		float cdlmorningstar;	/*Bottom reversal*/
		float cdlmorningdojistar;
		float mfi;
		float mom;
		float roc;
		float obv; 		/*On Balance Volume - trend/price indicator.  More important to look at trend*/
		float adx; 		/*average directional index measures the strength of a trend*/
		float adxr;
		float aroon;
		float cdlrickshawman;
		float cdltasukigap;
		float cdlclosingmarubozu;
		float cdlhikkakemod;
		float cdllongline;
		float cdlrisefall3methods;
		float cdlthrusting;
		float cdlconcealbabyswall;
		float cdlgapsidesidewhite;
		float cdlhomingpigeon;
		float cdlmarubozu;
		float cdlseparatinglines; /*100 seen */
		float cdltristar;
		float cdlidentical3crows;
		float cdlmatchinglow;
		float cdlunique3river;
		float cdl3starsinsouth;
		float cdldarkcloudcover;
		float cdlinneck;
		float cdlmathold;
		float cdlshortline;
		float cdlupsidegap2crows;
		float cdlspinningtop;
		float cdlxsidefap3methods;
		float cdlabandonedbaby;
		float cdlkickingbylength;
		float cdlsticksandwich;
		float cdlharamicross;
		float cdladvanceblock;
		float cdlstalledpattern;
		float cdlbelthold;
		float cdlhighwave;
		float cdlladderbottom;
		float cdlpiercing;
		float cdltakuri;
		float cdlbreakaway;
		float cdlhikkake; /* -[12]00 seen*/
		float cdl3whitesoldiers;

} DAT;
	DAT dataarray[MAXROWS];

	MYSQL conn;
	char host[] = "192.168.1.14";
	char user[] = "finance";
	char password[] = "finance";
	char db[] = "finance";
	float price;
	/*char rowstring[200];*/
	/*int res_count;*/
	/*char **end;*/
	MYSQL_RES *result;
	MYSQL_ROW *row;
	MYSQL_FIELD *field;
	int iMFITimePeriod;
	int iMOMTimePeriod;
	int iROCTimePeriod;
	int iOBVTimePeriod;
	int iADXTimePeriod, iADXRTimePeriod;
	int iMACDFastTimePeriod, iMACDSlowTimePeriod, iMACDSignalTimePeriod;
	int iDojiPen;
	int iEveningPen;
	int iDarkCloudPen;
	int iMatHoldPen;
	int iAbandonPen;
	/*int num_fields;*/
	/*
	int port = 3306;
	*/

	int startIdx;
	int endIdx;

	startIdx = 0;
	endIdx = MAXROWS;
	iMFITimePeriod = MFITIMEPERIOD;
	iMOMTimePeriod = MOMTIMEPERIOD;
	iROCTimePeriod = ROCTIMEPERIOD;
	iOBVTimePeriod = OBVTIMEPERIOD;
	iMACDFastTimePeriod = MACDFAST;
	iMACDSlowTimePeriod = MACDSLOW;
	iMACDSignalTimePeriod = MACDSIGNAL;
	iADXTimePeriod = ADXTIMEPERIOD;
	iADXRTimePeriod = ADXRTIMEPERIOD;
	iDojiPen = DOJIPEN;
	iEveningPen = DOJIPEN;
	iDarkCloudPen = DOJIPEN;
	iMatHoldPen = DOJIPEN;
	iAbandonPen = DOJIPEN;

	resultcount = 0;
	char query[] = "select date, symbol, day_close, day_high, day_low, day_open, volume from stockprices where symbol='IBM' and date > '2009-06-30' order by date asc";
	char query_update[1000];
	char query_setfields[1000];
	char query_setdata[1000];
	char query_where[1000];
	mysql_init( &conn );
	if ( !mysql_real_connect( &conn, host, user, password, db, 0, NULL, 0 ) )
	{
		sprintf( pfLogfile, "Failed to connect: %s\n", mysql_error( &conn ) );
	}
	else if( mysql_query( &conn, query  ) )
	{
		sprintf( pfLogfile, "Failed  query: %s\n", mysql_error( &conn ) );
	}
	else
	{
		/*res_count = mysql_field_count( &conn );*/
		result = mysql_store_result( &conn );
		while 	( 
				( 
					row = mysql_fetch_row( result ) 
				) != NULL 
			)
		{
			mysql_field_seek( result, 1 );
			field = mysql_fetch_field( result );
/*
			sprintf( pfLogfile, "Field details: %s is %lu long, type: %i value: %s\n", field->name, field->length, field->type, (char*)row[1] );
			sprintf( pfLogfile, "%s: %s\n ", (char*)row[0], (char*)row[1] );
*/
			price = strtod( (char*)row[2], NULL );
			closePrice[resultcount] = price;
			price = strtod( (char*)row[3], NULL );
			highPrice[resultcount] = price;
			price = strtod( (char*)row[4], NULL );
			lowPrice[resultcount] = price;
			price = strtod( (char*)row[5], NULL );
			openPrice[resultcount] = price;
			price = strtod( (char*)row[6], NULL );
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
	}
	
	/* ... initialize your closing price here... */
	/* istart, iend, inReal, InTimePeriod, InMAType, ioutBeg, ioutNbElement, outReal*/

	if ( resultcount < MAXROWS )
		endIdx = resultcount;
	else
		endIdx = MAXROWS;

	sprintf( pfLogfile, "%i TA_MA50\n", __LINE__ );
	retCode = TA_MA( startIdx, endIdx, &closePrice[0], 50,TA_MAType_SMA, &outBeg, &outNbElement, &out[0] );
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].ma50 = out[i];
	}

	sprintf( pfLogfile, "%i TA_MA200\n", __LINE__ );
	retCode = TA_MA( startIdx, endIdx, &closePrice[0], 200,TA_MAType_SMA, &outBeg, &outNbElement, &out[0] );
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].ma200 = out[i];
	}

	sprintf( pfLogfile, "%i TA_MA260\n", __LINE__ );
	retCode = TA_MA( startIdx, endIdx, &closePrice[0], 260,TA_MAType_SMA, &outBeg, &outNbElement, &out[0] );
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].ma260 = out[i];
	}

	sprintf( pfLogfile, "%i TA_ATR\n", __LINE__ );
	retCode = TA_ATR( startIdx, endIdx, &highPrice[0], &lowPrice[0], &closePrice[0], 2, &outBeg, &outNbElement, &out[0] );
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].truerange = out[i];
	}
	sprintf( pfLogfile, "%i TA_Cdl2Crows\n", __LINE__ );
	retCode = TA_CDL2CROWS( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdl2crows = iout[i];
	}
	sprintf( pfLogfile, "%i TA_Cdl3BlackCrows\n", __LINE__ );
	retCode = TA_CDL3BLACKCROWS( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdl3blackcrows = iout[i];
	}
	sprintf( pfLogfile, "%i TA_Cdl3Inside\n", __LINE__ );
	retCode = TA_CDL3INSIDE( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdl3inside = iout[i];
	}
	sprintf( pfLogfile, "%i TA_Cdl3LineStrike\n", __LINE__ );
	retCode = TA_CDL3LINESTRIKE( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdl3linestrike = iout[i];
	}
	sprintf( pfLogfile, "%i TA_Cdl3Outside\n", __LINE__ );
	retCode = TA_CDL3OUTSIDE( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdl3outside = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlCounterattack\n", __LINE__ );
	retCode = TA_CDLCOUNTERATTACK( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlcounterattack = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlDoji\n", __LINE__ );
	retCode = TA_CDLDOJI( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdldoji = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlDojiStar\n", __LINE__ );
	retCode = TA_CDLDOJISTAR( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdldojistar = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlEngulfing\n", __LINE__ );
	retCode = TA_CDLENGULFING( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlengulfing = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlHangingman\n", __LINE__ );
	retCode = TA_CDLHANGINGMAN( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlhangingman = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlHarami\n", __LINE__ );
	retCode = TA_CDLHARAMI( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlharami = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlKicking\n", __LINE__ );
	retCode = TA_CDLKICKING( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlkicking = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlInvertedHammer\n", __LINE__ );
	retCode = TA_CDLINVERTEDHAMMER( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlinvertedhammer = iout[i];
	}
/* */
	sprintf( pfLogfile, "%i TA_MFI\n", __LINE__ );
	retCode = TA_MFI( startIdx, endIdx,
				&highPrice[0], &lowPrice[0], &closePrice[0], &tar_volume[0], 
				iMFITimePeriod,
				&outBeg, &outNbElement, &dout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].mfi = dout[i];
	}
	sprintf( pfLogfile, "%i TA_MOM\n", __LINE__ );
	retCode = TA_MOM( startIdx, endIdx,
				&closePrice[0], iMOMTimePeriod,
				&outBeg, &outNbElement, &dout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].mom = dout[i];
	}
	sprintf( pfLogfile, "%i TA_ROC\n", __LINE__ );
	retCode = TA_ROC( startIdx, endIdx,
				&closePrice[0], iROCTimePeriod,
				&outBeg, &outNbElement, &dout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].roc = dout[i];
	}
/* */
	sprintf( pfLogfile, "%i TA_MACD\n", __LINE__ );
	retCode = TA_MACD( startIdx, endIdx,
				&closePrice[0], iMACDFastTimePeriod, iMACDSlowTimePeriod, iMACDSignalTimePeriod,
				&outBeg, &outNbElement, &dout[0], &dout1[0], &dout2[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].macd = dout[i];
		dataarray[outBeg+i].macd_signal = dout1[i];
		dataarray[outBeg+i].macd_histogram = dout2[i];
	}

	sprintf( pfLogfile, "%i TA_RSI\n", __LINE__ );
	retCode = TA_RSI( startIdx, endIdx,
				&closePrice[0], iMOMTimePeriod,
				&outBeg, &outNbElement, &dout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].relativestrengthindex = dout[i];
	}

/*
	sprintf( pfLogfile, "%i TA_OBV\n", __LINE__ );
	retCode = TA_OBV( startIdx, endIdx,
				&closePrice[0], (double*)&tar_volume[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].obv = iout[i];
	}
*/
/* */
	sprintf( pfLogfile, "%i TA_STOCH\n", __LINE__ );
	retCode = TA_STOCH( startIdx, endIdx,
				&highPrice[0], &lowPrice[0], &closePrice[0], 
				STOCHKFAST, STOCHKSLOW, STOCHKSLOWTYPE, STOCHDSLOW, STOCHDSLOWTYPE,
				&outBeg, &outNbElement, &dout[0], &dout1[0]
		);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].stochasticK = dout[i];
		dataarray[outBeg+i].stochasticD = dout1[i];
	}
/* */
	sprintf( pfLogfile, "%i TA_ADX\n", __LINE__ );
	retCode = TA_ADX( startIdx, endIdx,
				&highPrice[0], &lowPrice[0], &closePrice[0], 
				iADXTimePeriod,
				&outBeg, &outNbElement, &dout[0]
		);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].adx = dout[i];
	}
	sprintf( pfLogfile, "%i TA_ADXR\n", __LINE__ );
	retCode = TA_ADXR( startIdx, endIdx,
				&highPrice[0], &lowPrice[0], &closePrice[0], 
				iADXRTimePeriod,
				&outBeg, &outNbElement, &dout[0]
		);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].adxr = dout[i];
	}




	sprintf( pfLogfile, "%i TA_CdlStickSandwhich\n", __LINE__ );
	retCode = TA_CDLSTICKSANDWICH( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlsticksandwich = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlHaramiCross\n", __LINE__ );
	retCode = TA_CDLHARAMICROSS( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlharamicross = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlDragonFlyDoji\n", __LINE__ );
	retCode = TA_CDLDRAGONFLYDOJI( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdldragonflydoji = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlAdvanceBlock\n", __LINE__ );
	retCode = TA_CDLADVANCEBLOCK( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdladvanceblock = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlStalledPattern\n", __LINE__ );
	retCode = TA_CDLSTALLEDPATTERN( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlstalledpattern = iout[i];
	}


	sprintf( pfLogfile, "%i TA_CdlBelthold\n", __LINE__ );
	retCode = TA_CDLBELTHOLD( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlbelthold = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlHighWave\n", __LINE__ );
	retCode = TA_CDLHIGHWAVE( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlhighwave = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlLadderBottom\n", __LINE__ );
	retCode = TA_CDLLADDERBOTTOM( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlladderbottom = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlPiercing\n", __LINE__ );
	retCode = TA_CDLPIERCING( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlpiercing = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlTakuri\n", __LINE__ );
	retCode = TA_CDLTAKURI( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdltakuri = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlBreakaway\n", __LINE__ );
	retCode = TA_CDLBREAKAWAY( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlbreakaway = iout[i];
	}


	sprintf( pfLogfile, "%i TA_CdlEveningDojiStar\n", __LINE__ );
	retCode = TA_CDLEVENINGDOJISTAR( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], iDojiPen,
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdleveningdojistar = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlHikkake\n", __LINE__ );
	retCode = TA_CDLHIKKAKE( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlhikkake = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlLongLeggedDoji\n", __LINE__ );
	retCode = TA_CDLLONGLEGGEDDOJI( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdllongleggeddoji = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlRickshawman\n", __LINE__ );
	retCode = TA_CDLRICKSHAWMAN( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlrickshawman = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlAsukigap\n", __LINE__ );
	retCode = TA_CDLTASUKIGAP( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdltasukigap = iout[i];
	}


	sprintf( pfLogfile, "%i TA_CdlClosingMarubizu\n", __LINE__ );
	retCode = TA_CDLCLOSINGMARUBOZU( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlclosingmarubozu = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlEveningStar\n", __LINE__ );
	retCode = TA_CDLEVENINGSTAR( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], iEveningPen,
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdleveningstar = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlHikkakemod\n", __LINE__ );
	retCode = TA_CDLHIKKAKEMOD( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlhikkakemod = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlLongLine\n", __LINE__ );
	retCode = TA_CDLLONGLINE( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdllongline = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlRiseFall3Methods\n", __LINE__ );
	retCode = TA_CDLRISEFALL3METHODS( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlrisefall3methods = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlThrusting\n", __LINE__ );
	retCode = TA_CDLTHRUSTING( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlthrusting = iout[i];
	}

	sprintf( pfLogfile, "%i TA_CdlConcealBabysWall\n", __LINE__ );
	retCode = TA_CDLCONCEALBABYSWALL( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlconcealbabyswall = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlGapSideSideWhite\n", __LINE__ );
	retCode = TA_CDLGAPSIDESIDEWHITE( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlgapsidesidewhite = iout[i];
	}
	sprintf( pfLogfile, "%i TA_Cdlhomingpigeon\n", __LINE__ );
	retCode = TA_CDLHOMINGPIGEON( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlhomingpigeon = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlMarubozu\n", __LINE__ );
	retCode = TA_CDLMARUBOZU( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlmarubozu = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlSeparatingLine\n", __LINE__ );
	retCode = TA_CDLSEPARATINGLINES( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlseparatinglines = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlTriStar\n", __LINE__ );
	retCode = TA_CDLTRISTAR( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdltristar = iout[i];
	}

	sprintf( pfLogfile, "%i TA_CdlGraveStoneDoji\n", __LINE__ );
	retCode = TA_CDLGRAVESTONEDOJI( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlgravestonedoji = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlIdentical3Crows\n", __LINE__ );
	retCode = TA_CDLIDENTICAL3CROWS( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlidentical3crows = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlMatchLow\n", __LINE__ );
	retCode = TA_CDLMATCHINGLOW( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlmatchinglow = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlShootingStar\n", __LINE__ );
	retCode = TA_CDLSHOOTINGSTAR( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlshootingstar = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlUnique3River\n", __LINE__ );
	retCode = TA_CDLUNIQUE3RIVER( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlunique3river = iout[i];
	}

	sprintf( pfLogfile, "%i TA_Cdl3StarInSouth\n", __LINE__ );
	retCode = TA_CDL3STARSINSOUTH( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdl3starsinsouth = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlDarkCloudCover\n", __LINE__ );
	retCode = TA_CDLDARKCLOUDCOVER( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], iDarkCloudPen,
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdldarkcloudcover = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlHammer\n", __LINE__ );
	retCode = TA_CDLHAMMER( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlhammer = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlInneck\n", __LINE__ );
	retCode = TA_CDLINNECK( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlinneck = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlMathold\n", __LINE__ );
	retCode = TA_CDLMATHOLD( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], iMatHoldPen,
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlmathold = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlShortLine\n", __LINE__ );
	retCode = TA_CDLSHORTLINE( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlshortline = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlUpsideGap2Crows\n", __LINE__ );
	retCode = TA_CDLUPSIDEGAP2CROWS( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlupsidegap2crows = iout[i];
	}

	sprintf( pfLogfile, "%i TA_Cdl3WhiteSoldiers\n", __LINE__ );
	retCode = TA_CDL3WHITESOLDIERS( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdl3whitesoldiers = iout[i];
	}
	sprintf( pfLogfile, "%i TA_MorningDojiStar\n", __LINE__ );
	retCode = TA_CDLMORNINGDOJISTAR( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], iDojiPen,
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlmorningdojistar = iout[i];
	}
	sprintf( pfLogfile, "%i TA_SpingTop\n", __LINE__ );
	retCode = TA_CDLSPINNINGTOP( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlspinningtop = iout[i];
	}
	sprintf( pfLogfile, "%i TA_SideGap3Method\n", __LINE__ );
	retCode = TA_CDLXSIDEGAP3METHODS( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlxsidefap3methods = iout[i];
	}


	sprintf( pfLogfile, "%i TA_CdlAbandonBaby\n", __LINE__ );
	retCode = TA_CDLABANDONEDBABY( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], iAbandonPen,
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlabandonedbaby = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CdlKickingByLength\n", __LINE__ );
	retCode = TA_CDLKICKINGBYLENGTH( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0],
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlkickingbylength = iout[i];
	}
	sprintf( pfLogfile, "%i TA_CDLMorningStar\n", __LINE__ );
	retCode = TA_CDLMORNINGSTAR( startIdx, endIdx,
				&openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], iDojiPen,
				&outBeg, &outNbElement, &iout[0]);
	for( i=0; i < outNbElement; i++ )
	{
		dataarray[outBeg+i].cdlmorningstar = iout[i];
	}

		printf ("\n" );
	for( i=0; i < resultcount; i++ )
	{
	   	sprintf( pfLogfile, "Day %d Date %s \tSymbol %s \tOpen %.2f \tClose %.2f \tHigh %.2f \tLow %.2f \tVolume %.1f\n", i, dataarray[i].date , dataarray[i].symbol, dataarray[i].openPrice, dataarray[i].closePrice, dataarray[i].highPrice, dataarray[i].lowPrice, dataarray[i].volume);
	   	sprintf( pfLogfile, "Day %d                                    \tMFI       \t%.1f \tMomentum \t%.1f \tROC      \t %.1f \tOBV \t%.1f\n", i, dataarray[i].mfi, dataarray[i].mom, dataarray[i].roc, dataarray[i].obv );
	   	sprintf( pfLogfile, "Day %d                                    \tTrueRange \t%.2f \tMA50     \t%.2f \tMA200     \t%.2f \tMA260 \t\t%.2f \n", i, dataarray[i].truerange , dataarray[i].ma50, dataarray[i].ma200, dataarray[i].ma260);
	   	sprintf( pfLogfile, "Day %d Oscillators Oversold/bought 80/20: \tStochastic K \t%.1f \tStochastic D \t%.1f  \tRSI 70/30 \t%.1f \n", i, dataarray[i].stochasticK, dataarray[i].stochasticD, dataarray[i].relativestrengthindex );
	   	sprintf( pfLogfile, "Day %d MACD Ind                         : \tMACD        \t%.1f \tMACD Histogram \t%.1f \tMACD Signal \t%.1f\n", i, dataarray[i].macd, dataarray[i].macd_histogram, dataarray[i].macd_signal );
	   	sprintf( pfLogfile, "Day %d Candle                           \t2Crows        \t%.1f \tXXXXXXXXX \t%.1f \tKicking   \t%.1f \tHarami      \t%.1f\n", i, dataarray[i].cdl2crows, dataarray[i].cdlinvertedhammer, dataarray[i].cdlkicking, dataarray[i].cdlharami );
	   	sprintf( pfLogfile, "Day %d Candle                           \t3BlackCrows   \t%.1f \t3Inside   \t%.1f \t3outside  \t%.1f \t3lineStrike \t%.1f\n", i, dataarray[i].cdl3blackcrows, dataarray[i].cdl3inside, dataarray[i].cdl3outside, dataarray[i].cdl3linestrike );
	   	sprintf( pfLogfile, "Day %d Candle                           \tCounterattack \t%.1f \tDoji      \t%.1f \tDoji Star \t%.1f \tEngulfing   \t%.1f\n", i, dataarray[i].cdlcounterattack, dataarray[i].cdldoji, dataarray[i].cdldojistar, dataarray[i].cdlengulfing );
	   	sprintf( pfLogfile, "Day %d Candle Uptrend End Ind           : \tHanging Man  \t%.1f \tShooting Star \t%.1f \tEvening Star \t%.1f \tHarami \t%.1f \tInverted Hammer %.1f\n", i, dataarray[i].cdlhangingman, dataarray[i].cdlshootingstar, dataarray[i].cdleveningstar, dataarray[i].cdlharami, dataarray[i].cdlinvertedhammer );
	   	sprintf( pfLogfile, "Day %d Candle Downtrend End Ind         : \tHammer       \t%.1f \tMorning Star \t%.1f  \tMorning Doji Star \t%.1f\n", i, dataarray[i].cdlhammer, dataarray[i].cdlmorningstar, dataarray[i].cdlmorningdojistar );

		sprintf( pfLogfile, "Day %d Candle \t %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdlrickshawman, dataarray[i].cdltasukigap, dataarray[i].cdlclosingmarubozu, dataarray[i].cdleveningstar ); 
		sprintf( pfLogfile, "Day %d Candle \t %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdlhikkakemod, dataarray[i].cdllongline, dataarray[i].cdlrisefall3methods, dataarray[i].cdlthrusting ); 
		sprintf( pfLogfile, "Day %d Candle \t %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdlconcealbabyswall, dataarray[i].cdlgapsidesidewhite, dataarray[i].cdlhomingpigeon, dataarray[i].cdlmarubozu ); 
		sprintf( pfLogfile, "Day %d Candle \t %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdlseparatinglines, dataarray[i].cdltristar, dataarray[i].cdlgravestonedoji, dataarray[i].cdlidentical3crows ); 
		sprintf( pfLogfile, "Day %d Candle \tMatching Low %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdlmatchinglow, dataarray[i].cdlshootingstar, dataarray[i].cdlunique3river, dataarray[i].cdl3starsinsouth ); 
		sprintf( pfLogfile, "Day %d Candle \t %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdldarkcloudcover, dataarray[i].cdlhammer, dataarray[i].cdlinneck, dataarray[i].cdlmathold ); 
		sprintf( pfLogfile, "Day %d Candle \t %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdlshortline, dataarray[i].cdlupsidegap2crows, dataarray[i].cdlmorningdojistar, dataarray[i].cdlspinningtop ); 
		sprintf( pfLogfile, "Day %d Candle \t %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdlxsidefap3methods, dataarray[i].cdlabandonedbaby, dataarray[i].cdlkickingbylength, dataarray[i].cdlmorningstar ); 
		sprintf( pfLogfile, "Day %d Candle \t %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdlsticksandwich, dataarray[i].cdlharamicross, dataarray[i].cdldragonflydoji, dataarray[i].cdladvanceblock ); 
		sprintf( pfLogfile, "Day %d Candle \t %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdlstalledpattern, dataarray[i].cdlbelthold, dataarray[i].cdlhighwave, dataarray[i].cdlladderbottom ); 
		sprintf( pfLogfile, "Day %d Candle \t %.1f \t %.1f \t %.1f \t %.1f \n", i, dataarray[i].cdlpiercing, dataarray[i].cdltakuri, dataarray[i].cdlbreakaway, dataarray[i].cdleveningdojistar ); 
		sprintf( pfLogfile, "Day %d Candle \t Hikkake %.1f \t %.1f \t %.1f \t \n", i, dataarray[i].cdlhikkake, dataarray[i].cdllongleggeddoji, dataarray[i].cdl3whitesoldiers );

		printf ("\n" );

	/*	
		char query_update[1000];
		char query_setfields[1000];
		char query_setdata[1000];
		char query_where[1000];
	*/
		ifieldcount = 0;
		memset( query_update, 0, 1000 );
		memset( query_setfields, 0, 1000 );
		memset( query_setdata, 0, 1000 );
		memset( query_where, 0, 1000 );
		sprintf( query_update, "update technicalanalysis set \n" );
		sprintf( query_where, "where symbol = '%s' and date = '%s'\n", dataarray[i].symbol, dataarray[i].date );

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   "," );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "day_close='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "typical_price='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "movingaverage50='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "movingaverage200='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "expmovingaverage9='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "expmovingaverage12='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "expmovingaverage26='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "expmovingaverage90='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}


		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "macd='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "momentumoscillator='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "imamomentum='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "macrossover='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "macenterlinecrossover='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "priceoscillator='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "macd_histogram='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "linearregression='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "linearregressionangle='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "linearregressionslope='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "linearregressionintercept='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "stochastic='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "relativestrengthindex='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "rsioscillator='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "commoditychannelindex='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "pricechangepercent='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "volume12='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "volume26='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "volume90='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "support12='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "support26='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "resistance12='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "resistance26='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "bollingerbandmiddle='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "bollingerbandupper='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "bollingerbandlower='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "bollingerpercentb='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "bollingerbandwidth='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "coefficientofvariation='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "movingaverage260='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "standarddeviation260='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "annualreturn='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "annualrisk='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "truerange='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "voltrend90='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "voltrend26='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "voltrend260='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}

		if( dataarray[i].closePrice > 0 )
		{
			if( ifieldcount > 0 )
				strcat( query_setdata,   ","  );
			memset( query_setfields, 0, 1000 );
			sprintf( query_setfields, "volume260='%f'", dataarray[i].closePrice );
			strcat( query_setdata, query_setfields );
			ifieldcount++;
		}
	printf( "%s\n", query_setdata );
	fprintf( pfLogfile, "%s\n", query_setdata );
	}
fclose( pfLogfile );	
exit(0);
}

/*
Open 192.91     High 194.87     Low 192.40      Volume 4847900.0
Day 617                                         MFI             64.1    Momentum        9.3     ROC              5.0    OBV     0.0
Day 617                                         TrueRange       3.26    MA50            184.31  MA200           172.34  MA260           167.95
Day 617 Oscillators Oversold/bought 80/20:      Stochastic K    64.8    Stochastic D    62.6    RSI 70/30       63.8
Day 617 MACD Ind                         :      MACD            2.7     MACD Histogram  1.0     MACD Signal     1.7
Day 617 Candle                                  2Crows          0.0     XXXXXXXXX       0.0     Kicking         0.0     Harami          0.0
Day 617 Candle                                  3BlackCrows     0.0     3Inside         0.0     3outside        0.0     3lineStrike     0.0
Day 617 Candle                                  Counterattack   0.0     Doji            0.0     Doji Star       0.0     Engulfing       0.0
Day 617 Candle Uptrend End Ind           :      Hanging Man     0.0     Shooting Star   0.0     Evening Star    0.0     Harami  0.0     Inverted Hammer 0.0
Day 617 Candle Downtrend End Ind         :      Hammer          0.0     Morning Star    0.0     Morning Doji Star       0.0
Day 617 Candle   0.0     0.0     0.0     0.0
Day 617 Candle   0.0     0.0     0.0     0.0
Day 617 Candle   0.0     0.0     0.0     0.0
Day 617 Candle   0.0     0.0     0.0     0.0
Day 617 Candle  Matching Low 0.0         0.0     0.0     0.0
Day 617 Candle   0.0     0.0     0.0     0.0
Day 617 Candle   0.0     0.0     0.0     0.0
Day 617 Candle   0.0     0.0     0.0     0.0
Day 617 Candle   0.0     0.0     0.0     0.0
Day 617 Candle   0.0     0.0     0.0     0.0
Day 617 Candle   0.0     0.0     0.0     0.0
Day 617 Candle   Hikkake 0.0     0.0     0.0
*/
