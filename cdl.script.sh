#!/bin/sh

echo "/* */" > src/cdl/ksf_cdl.h
echo "#ifndef KSF_CDL" >> src/cdl/ksf_cdl.h
echo "#define KSF_CDL" >> src/cdl/ksf_cdl.h
echo "typedef struct candledatastruct {" >> src/cdl/ksf_cdl.h
echo -e "\tchar date[11];" >> src/cdl/ksf_cdl.h
echo -e "\tchar symbol[7];" >> src/cdl/ksf_cdl.h
echo -e "\tdouble closePrice;" >> src/cdl/ksf_cdl.h
echo -e "\tdouble highPrice;" >> src/cdl/ksf_cdl.h
echo -e "\tdouble lowPrice;" >> src/cdl/ksf_cdl.h
echo -e "\tdouble openPrice;" >> src/cdl/ksf_cdl.h
echo -e "\tdouble volume;" >> src/cdl/ksf_cdl.h
echo -e "\tfloat movavg;" >> src/cdl/ksf_cdl.h

for CDL in CDL2CROWS CDL3BLACKCROWS CDL3INSIDE CDL3LINESTRIKE CDL3OUTSIDE CDL3STARSINSOUTH CDL3WHITESOLDIERS CDLABANDONEDBABY CDLADVANCEBLOCK CDLBELTHOLD CDLBREAKAWAY CDLCLOSINGMARUBOZU CDLCONCEALBABYSWALL CDLCOUNTERATTACK CDLDARKCLOUDCOVER CDLDOJI CDLDOJISTAR CDLDRAGONFLYDOJI CDLENGULFING CDLEVENINGDOJISTAR CDLEVENINGSTAR CDLGAPSIDESIDEWHITE CDLGRAVESTONEDOJI CDLHAMMER CDLHANGINGMAN CDLHARAMICROSS CDLHARAMI CDLHIGHWAVE CDLHIKKAKEMOD CDLHIKKAKE CDLHOMINGPIGEON CDLIDENTICAL3CROWS CDLINNECK CDLINVERTEDHAMMER CDLKICKINGBYLENGTH CDLKICKING CDLLADDERBOTTOM CDLLONGLEGGEDDOJI CDLLONGLINE CDLMARUBOZU CDLMATCHINGLOW CDLMATHOLD CDLMORNINGDOJISTAR CDLMORNINGSTAR CDLONNECK CDLPIERCING CDLRICKSHAWMAN CDLRISEFALL3METHODS CDLSEPARATINGLINES CDLSHOOTINGSTAR CDLSHORTLINE CDLSPINNINGTOP CDLSTALLEDPATTERN CDLSTICKSANDWICH CDLTAKURI CDLTASUKIGAP CDLTHRUSTING CDLTRISTAR CDLUNIQUE3RIVER CDLUPSIDEGAP2CROWS CDLXSIDEGAP3METHODS
do
	echo -e "\tint $CDL; /*$CDL*/" >> src/cdl/ksf_cdl.h
	#echo -e "\tfloat $CDL; /*$CDL*/" >> src/cdl/ksf_cdl.h
done

echo "} TA_CDL_DAT;" >> src/cdl/ksf_cdl.h
echo "#endif" >> src/cdl/ksf_cdl.h



echo "/* */" > src/cdl/ksf_cdl.c
echo -e "#include \"ta-lib/c/include/ta_func.h\"" >> src/cdl/ksf_cdl.c
echo -e "#include \"ta-lib/c/include/ta_libc.h\"" >> src/cdl/ksf_cdl.c
echo -e "#include \"stdlib.h\"" >> src/cdl/ksf_cdl.c
echo -e "#include \"stdio.h\"" >> src/cdl/ksf_cdl.c
echo -e "#include \"string.h\"" >> src/cdl/ksf_cdl.c
echo -e "#include \"../../ta-lib.example.h\"" >> src/cdl/ksf_cdl.c
echo -e "#include \"ksf_cdl.h\"" >> src/cdl/ksf_cdl.c
echo "/* */" >> src/cdl/ksf_cdl.c
echo "/* */" >> src/cdl/ksf_cdl.c


echo -e "/*func*/ TA_CDL_DAT * calcCandlesticks( FILE *pfLogfile, int startIdx, int endIdx, TA_Real *openPrice, TA_Real *highPrice, TA_Real *lowPrice, TA_Real *closePrice, /*@only@*/ TA_CDL_DAT *cdldataarray, const TA_DAT *dataarray ) {" >> src/cdl/ksf_cdl.c
echo -e "TA_CDL_DAT * calcCandlesticks( FILE *pfLogfile, int startIdx, int endIdx, TA_Real *openPrice, TA_Real *highPrice, TA_Real *lowPrice, TA_Real *closePrice, /*@only@*/ TA_CDL_DAT *cdldataarray, const TA_DAT *dataarray ); " >> src/cdl/ksf_cdl.h
echo -e "\tTA_RetCode retCode;" >> src/cdl/ksf_cdl.c
echo -e "\tint i;" >> src/cdl/ksf_cdl.c
echo -e "\tint outBeg;" >> src/cdl/ksf_cdl.c
echo -e "\tint outNbElement;" >> src/cdl/ksf_cdl.c
echo -e "\tint iout[MAXROWS];" >> src/cdl/ksf_cdl.c
echo -e "\tdouble doptInPenetration = 14;" >> src/cdl/ksf_cdl.c

for CDL in CDL2CROWS CDL3BLACKCROWS CDL3INSIDE CDL3LINESTRIKE CDL3OUTSIDE CDL3STARSINSOUTH CDL3WHITESOLDIERS CDLADVANCEBLOCK CDLBELTHOLD CDLBREAKAWAY CDLCLOSINGMARUBOZU CDLCONCEALBABYSWALL CDLCOUNTERATTACK CDLDOJI CDLDOJISTAR CDLDRAGONFLYDOJI CDLENGULFING CDLGAPSIDESIDEWHITE CDLGRAVESTONEDOJI CDLHAMMER CDLHANGINGMAN CDLHARAMICROSS CDLHARAMI CDLHIGHWAVE CDLHIKKAKEMOD CDLHIKKAKE CDLHOMINGPIGEON CDLIDENTICAL3CROWS CDLINNECK CDLINVERTEDHAMMER CDLKICKINGBYLENGTH CDLKICKING CDLLADDERBOTTOM CDLLONGLEGGEDDOJI CDLLONGLINE CDLMARUBOZU CDLMATCHINGLOW CDLONNECK CDLPIERCING CDLRICKSHAWMAN CDLRISEFALL3METHODS CDLSEPARATINGLINES CDLSHOOTINGSTAR CDLSHORTLINE CDLSPINNINGTOP CDLSTALLEDPATTERN CDLSTICKSANDWICH CDLTAKURI CDLTASUKIGAP CDLTHRUSTING CDLTRISTAR CDLUNIQUE3RIVER CDLUPSIDEGAP2CROWS CDLXSIDEGAP3METHODS
do

	echo -e "\tif( NULL != pfLogfile )" >> src/cdl/ksf_cdl.c
	echo -e "\t\t(void) fprintf( pfLogfile, \"%i TA_$CDL\\\n\", __LINE__ );" >> src/cdl/ksf_cdl.c
	echo -e "\tretCode = TA_$CDL( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], &outBeg, &outNbElement, &iout[0]); " >> src/cdl/ksf_cdl.c
	echo -e "\tfor( i=0; i < outNbElement; i++ )" >> src/cdl/ksf_cdl.c
	echo -e "\t{" >> src/cdl/ksf_cdl.c
	echo -e "\t\t(void) strncpy( cdldataarray[outBeg+i].symbol, dataarray[outBeg+i].symbol, 7);" >> src/cdl/ksf_cdl.c
	echo -e "\t\t(void) strncpy( cdldataarray[outBeg+i].date, dataarray[outBeg+i].date, 11);" >> src/cdl/ksf_cdl.c
	echo -e "\t\tcdldataarray[outBeg+i].$CDL = iout[i];" >> src/cdl/ksf_cdl.c
	echo -e "\t}" >> src/cdl/ksf_cdl.c
	echo -e "\t" >> src/cdl/ksf_cdl.c

done

for CDL in CDLABANDONEDBABY CDLDARKCLOUDCOVER CDLEVENINGDOJISTAR CDLEVENINGSTAR CDLMATHOLD CDLMORNINGDOJISTAR CDLMORNINGSTAR 
do

	echo -e "\tif( NULL != pfLogfile )" >> src/cdl/ksf_cdl.c
	echo -e "\t\t(void) fprintf( pfLogfile, \"%i TA_$CDL\\\n\", __LINE__ );" >> src/cdl/ksf_cdl.c
	echo -e "\tretCode = TA_$CDL( startIdx, endIdx, &openPrice[0], &highPrice[0], &lowPrice[0], &closePrice[0], doptInPenetration, &outBeg, &outNbElement, &iout[0]); " >> src/cdl/ksf_cdl.c
	echo -e "\tfor( i=0; i < outNbElement; i++ )" >> src/cdl/ksf_cdl.c
	echo -e "\t{" >> src/cdl/ksf_cdl.c
	echo -e "\t\tcdldataarray[outBeg+i].$CDL = iout[i];" >> src/cdl/ksf_cdl.c
	echo -e "\t}" >> src/cdl/ksf_cdl.c
	echo -e "\t" >> src/cdl/ksf_cdl.c

done

echo -e "\treturn cdldataarray;" >> src/cdl/ksf_cdl.c
echo -e "}" >> src/cdl/ksf_cdl.c


echo -e "/*func*/ char * createQueryCandlesticks( TA_CDL_DAT* cdldataarray, int icdlcount, /*@unique@*/ char *query_setfields, size_t setfields_size, /*@in@*/ /*@only@*/ char *query_setdata ) {" >> src/cdl/ksf_cdl.c
echo -e "/*func*/ char * createQueryCandlesticks( TA_CDL_DAT* cdldataarray, int icdlcount, /*@unique@*/ char *query_setfields, size_t setfields_size, /*@in@*/ /*@only@*/ char *query_setdata ); " >> src/cdl/ksf_cdl.h
echo -e "\tint ifieldcount = 0;" >> src/cdl/ksf_cdl.c

for CDL in CDL2CROWS CDL3BLACKCROWS CDL3INSIDE CDL3LINESTRIKE CDL3OUTSIDE CDL3STARSINSOUTH CDL3WHITESOLDIERS CDLABANDONEDBABY CDLADVANCEBLOCK CDLBELTHOLD CDLBREAKAWAY CDLCLOSINGMARUBOZU CDLCONCEALBABYSWALL CDLCOUNTERATTACK CDLDARKCLOUDCOVER CDLDOJI CDLDOJISTAR CDLDRAGONFLYDOJI CDLENGULFING CDLEVENINGDOJISTAR CDLEVENINGSTAR CDLGAPSIDESIDEWHITE CDLGRAVESTONEDOJI CDLHAMMER CDLHANGINGMAN CDLHARAMICROSS CDLHARAMI CDLHIGHWAVE CDLHIKKAKEMOD CDLHIKKAKE CDLHOMINGPIGEON CDLIDENTICAL3CROWS CDLINNECK CDLINVERTEDHAMMER CDLKICKINGBYLENGTH CDLKICKING CDLLADDERBOTTOM CDLLONGLEGGEDDOJI CDLLONGLINE CDLMARUBOZU CDLMATCHINGLOW CDLMATHOLD CDLMORNINGDOJISTAR CDLMORNINGSTAR CDLONNECK CDLPIERCING CDLRICKSHAWMAN CDLRISEFALL3METHODS CDLSEPARATINGLINES CDLSHOOTINGSTAR CDLSHORTLINE CDLSPINNINGTOP CDLSTALLEDPATTERN CDLSTICKSANDWICH CDLTAKURI CDLTASUKIGAP CDLTHRUSTING CDLTRISTAR CDLUNIQUE3RIVER CDLUPSIDEGAP2CROWS CDLXSIDEGAP3METHODS
do


	echo -e "\t\tif( cdldataarray[icdlcount].$CDL != 0 )" >> src/cdl/ksf_cdl.c
	echo -e "\t\t{" >> src/cdl/ksf_cdl.c
	echo -e "\t\t\tif( ifieldcount > 0 )" >> src/cdl/ksf_cdl.c
	echo -e "\t\t\t\t(void) strcat( query_setdata,  \", \" );" >> src/cdl/ksf_cdl.c
	echo -e "\t\t\tmemset( query_setfields, 0, setfields_size );" >> src/cdl/ksf_cdl.c
	echo -e "\t\t\t(void) snprintf( query_setfields, setfields_size, \"$CDL='%i'\", cdldataarray[icdlcount].$CDL );" >> src/cdl/ksf_cdl.c
	echo -e "\t\t\t(void) strcat( query_setdata, query_setfields );" >> src/cdl/ksf_cdl.c
	echo -e "\t\t\tifieldcount++;" >> src/cdl/ksf_cdl.c
	echo -e "\t\t}" >> src/cdl/ksf_cdl.c
	echo -e "\t\t" >> src/cdl/ksf_cdl.c

done

echo -e "\treturn query_setdata;" >> src/cdl/ksf_cdl.c
echo -e "}" >> src/cdl/ksf_cdl.c
