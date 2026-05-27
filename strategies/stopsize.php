<?php

/***************************************************************
*
*       20111221 Money Management stop sizing for trade strategies
*
*       @file stopsize.php
*       @brief module for money management strategies in investing
*
*       Part of managing your risk is deciding how big a stop
*       delta between your purchase price and the stop loss price
*
*
*       USAGE:
*
***************************************************************/

/***************************************************************
*
*       Testing Results
*
***************************************************************/

echo __FILE__ . "\n";
require_once( 'data/generictable.php' );
require_once( '../local.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
require_once( 'strategiesConstants.php' );


/***************************************************************
*       BEGIN
***************************************************************/

/***************************************************************
*       @function stopStockPrice
*       @param string stocksymbol
*       @param date tradedate     
*       @see
*       @return float dollars delta
***************************************************************/
/*@float@*/ function stopStockPrice( $stocksymbol, $tradedate )
{
	if( !isset( $_SESSION[$stocksymbol][$tradedate]['day_close'] ))
	{
		require_once( MODELDIR . '/stockprices.class.php' );
		$stockprices = new stockprices();
		$stockprices->Setsymbol( $stocksymbol );
		$stockprices->Setdate( $tradedate );
		$stockprices->GetVARRow();
		$_SESSION[$stocksymbol][$tradedate]['day_close'] = $stockprices->Getday_close();
	}
	return $_SESSION[$stocksymbol][$tradedate]['day_close'];
}

/***************************************************************
*       @function stopTAValues
*       @param string stocksymbol
*       @param date tradedate     
*       @see
*       @return bool HARD CODED TRUE because of multiple values 
*	 being retrieved.
***************************************************************/
/*@bool@*/ function stopTAValues( $stocksymbol, $tradedate )
{
	if( !isset( $_SESSION[$stocksymbol][$tradedate]['truerange'] ))
	{
		require_once( MODELDIR . '/technicalanalysis.class.php' );
		$technicalanalysis = new technicalanalysis();
		$technicalanalysis->Setsymbol( $stocksymbol );
		$technicalanalysis->Setdate( $tradedate );
		$technicalanalysis->GetVARRow();
		$_SESSION[$stocksymbol][$tradedate]['truerange'] = $technicalanalysis->Gettruerange();
		$_SESSION[$stocksymbol][$tradedate]['support12'] = $technicalanalysis->Getsupport12();
		$_SESSION[$stocksymbol][$tradedate]['support26'] = $technicalanalysis->Getsupport26();
		$_SESSION[$stocksymbol][$tradedate]['annualrisk'] = $technicalanalysis->Getannualrisk();
	}
	return TRUE;
}

/***************************************************************
*       @function stopBreakEven
*       @param string stocksymbol
*       @param date tradedate     
*       @see
*       @return float dollars delta
***************************************************************/
/*@float@*/ function stopBreakEven( $stocksymbol, $tradedate )
{
	return 1; //Returning 0 will lead to a div by zero later.
}
/***************************************************************
*       @function stopFiftyPercent
*       @param string stocksymbol
*       @param date tradedate     
*       @see
*       @return float dollars delta
***************************************************************/
/*@float@*/ function stopFiftyPercent( $stocksymbol, $tradedate )
{
	$delta = stopStockPrice( $stocksymbol, $tradedate ) / 2;
	return $delta;
}
/***************************************************************
*       @function stopTwentyfivePercent
*       @param string stocksymbol
*       @param date tradedate     
*       @see
*       @return float dollars delta
***************************************************************/
/*@float@*/ function stopTwentyfivePercent( $stocksymbol, $tradedate )
{
	$delta = stopStockPrice( $stocksymbol, $tradedate ) / 4;
	return $delta;
}
/***************************************************************
*       @function stopActualTrueRange
*       @param string stocksymbol
*       @param date tradedate     
*       @see
*       @return float dollars delta
***************************************************************/
/*@float@*/ function stopActualTrueRange( $stocksymbol, $tradedate )
{
	if( stopTAValues( $stocksymbol, $tradedate ) )
		return $_SESSION[$stocksymbol][$tradedate]['truerange'];
	else
		return 0;
}
/***************************************************************
*       @function stopFiveDayLow
*       @param string stocksymbol
*       @param date tradedate     
*       @see
*       @return float dollars delta
***************************************************************/
/*@float@*/ function stopFiveDayLow( $stocksymbol, $tradedate )
{
	return 0;
}
/***************************************************************
*       @function stopSupport12
*       @param string stocksymbol
*       @param date tradedate     
*       @see
*       @return float dollars delta
***************************************************************/
/*@float@*/ function stopSupport12( $stocksymbol, $tradedate )
{
	if( stopTAValues( $stocksymbol, $tradedate ) )
		return $_SESSION[$stocksymbol][$tradedate]['support12'];
	else
		return 0;
}
/***************************************************************
*       @function stopSupport26
*       @param string stocksymbol
*       @param date tradedate     
*       @see
*       @return float dollars delta
***************************************************************/
/*@float@*/ function stopSupport26( $stocksymbol, $tradedate )
{
	if( stopTAValues( $stocksymbol, $tradedate ) )
		return $_SESSION[$stocksymbol][$tradedate]['support26'];
	else
		return 0;
	return 0;
}
/***************************************************************
*       @function stopAnnualRisk
*       @param string stocksymbol
*       @param date tradedate     
*       @see
*       @return float dollars delta
***************************************************************/
/*@float@*/ function stopAnnualRisk( $stocksymbol, $tradedate )
{
	if( stopTAValues( $stocksymbol, $tradedate ) )
		return $_SESSION[$stocksymbol][$tradedate]['annualrisk'];
	else
		return 0;
	return 0;
}


function stop_unittest()
{
	$stocksymbol = "IBM";
	$tradedate = "2011-11-30";

        $breakeven = stopBreakEven( $stocksymbol, $tradedate );
        $fifty = stopFiftyPercent( $stocksymbol, $tradedate );
        $twentyfive = stopTwentyfivePercent( $stocksymbol, $tradedate );
        $atr = stopActualTrueRange( $stocksymbol, $tradedate );
        $fivedaylow = stopFiveDayLow( $stocksymbol, $tradedate );
        $support12 = stopSupport12( $stocksymbol, $tradedate );
        $support26 = stopSupport26( $stocksymbol, $tradedate );
        $annualrisk = stopAnnualRisk( $stocksymbol, $tradedate );

	echo "Various stop price deltas are: \n";
	echo "Break Even " . $breakeven . "\n";
	echo "fifty percent " . $fifty . "\n";
	echo "twentyfive percent " . $twentyfive . "\n";
	echo "True Range " . $truerange . "\n";
	echo "Five Day Low " . $fivedaylow . "\n";
	echo "12 Day Support " . $support12 . "\n";
	echo "26 Day Support " . $support26 . "\n";
	echo "Annual Risk" . $annualrisk . "\n";

var_dump( $_SESSION );

}

stop_unittest();
?>
