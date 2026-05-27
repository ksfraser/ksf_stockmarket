<?php

//require_once(dirname(__FILE__) . '/YahooFinanceAPI.php');
require_once('data/YahooFinanceAPI/YahooFinanceAPI.php');
spl_autoload_register(array('YahooFinanceAPI', 'autoload'));
 
$api = new YahooFinanceAPI();
$api->addOption("symbol");		//ta, si
$api->addOption("open");
$api->addOption("previousClose");
$api->addOption("change");
$api->addOption("volume");
$api->addOption("averageDailyVolume");
$api->addOption("name");
$api->addOption("dividendPerShare");
$api->addOption("lastTradeDate");
$api->addOption("tradeDate");		//ta,si
$api->addOption("daysLow");
$api->addOption("daysHigh");
$api->addOption("52WeekLow");
$api->addOption("52WeekHigh");
$api->addOption("annualizedGain");
$api->addOption("changeFrom52WeekLow");
$api->addOption("50DayMovingAverage");	//ta
$api->addOption("200DayMovingAverage");	//ta
$api->addOption("marketCapitalization");
$api->addOption("EBITDA");
$api->addOption("earningsPerShare");
$api->addOption("EPSEstimateCurrentYear");
$api->addOption("EPSEstimateNextYear");
$api->addOption("EPSEstimateNextQuarter");
$api->addOption("stockExchange");
$api->addOption("dividendYeild");
$api->addOption("pricePerSales");
$api->addOption("pricePerBook");
$api->addOption("priceEarningsRatio");
$api->addOption("PEGRatio");

$api->addOption("ask");
$api->addOption("askSize");
$api->addOption("bid");
$api->addOption("bidSize");
$api->addOption("askRealTime");
$api->addOption("bidRealTime");
$api->addOption("changeRealTime");
$api->addOption("afterHoursChangeRealTime");
$api->addOption("errorIndication");
$api->addOption("floatShares");
$api->addOption("orderBookRealTime");
$api->addOption("marketCapitalizationRealTime");
$api->addOption("percentChangeFrom52WeekLow");
$api->addOption("lastTradeWithTimeRealTime");
$api->addOption("changePercentRealTime");
$api->addOption("lastTradeSize");
$api->addOption("changeFrom52WeekHigh");
$api->addOption("percentChangeFrom52WeekHigh");
$api->addOption("lastTradeWithTime");
$api->addOption("lastTrade");
$api->addOption("highLimit");
$api->addOption("lowLimit");
$api->addOption("daysRange");
$api->addOption("daysRangeRealTime");
$api->addOption("changeFrom200DayMovingAverage");
$api->addOption("percentChangeFrom200DayMovingAverage");
$api->addOption("changeFrom50DayMovingAverage");
$api->addOption("percentChangeFrom50DayMovingAverage");
$api->addOption("pricePaid");
$api->addOption("changeInPercent");
$api->addOption("exDividendDate");
$api->addOption("dividendPayDate");
$api->addOption("priceEarningsRatioRealTime");
$api->addOption("pricePerEPSEstimateCurrentYear");
$api->addOption("pricePerEPSEstimateNextYear");
$api->addOption("sharesOwned");
$api->addOption("shortRatio");
$api->addOption("lastTradeTime");
$api->addOption("tradeLinks");
$api->addOption("tickerTrend");
$api->addOption("1YrTargetPrice");
$api->addOption("holdingsValue");
$api->addOption("holdingsValueRealTime");
$api->addOption("52WeekRange");
$api->addOption("daysValueChange");
$api->addOption("daysValueChangeRealTime");
$api->addOption("changeAndPercentChange");
$api->addOption("notes");
$api->addOption("moreInfo");
$api->addOption("commision");
$api->addOption("bookValue");
$api->addOption("holdingsGain");
$api->addOption("holdingsGainPercentRealTime");
$api->addOption("holdingsGainRealTime");
$api->addOption("holdingsGainPercent");

/* Original Code */
$api->addSymbol("DELL" );
//$api->addSymbol("IBM" );
//$api->addSymbol("CNI" );
$result = $api->getQuotes();
if( $result->isSuccess() ) {
    $quotes = $result->data;
    foreach( $quotes as $quote ) {
	var_dump( $quote );
        $symbol = $quote->symbol;
        $lastTrade = $quote->lastTrade; // or $quote->get( YahooFinance_Options::LAST_TRADE );
        $daysLow = $quote->daysLow; // or $quote->get( YahooFinance_Options::DAYS_LOW );
    }
}
exit;
/*
*/

/*Taken from queryyahoo2.php */

require_once( '../local.php' );
require_once( 'data/generictable.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
include( $MODELDIR . '/stockinfo.class.php' );
$stock = new stockinfo();
$rowcount = $stock->CountAllRows();
$YahooLimit = 199; //Yahoo limits to 200 or less at a time
$lowlimit = 0;
$highlimit = $YahooLimit;
if( $rowcount > $YahooLimit )
{
	$stock->limit = $lowlimit . ", " . $highlimit; 
}
else
{
	$stock->limit = $lowlimit . ", " . $rowcount; 
}
while( $lowlimit < $rowcount )
{
	$stock->Select();
	foreach( $stock->resultarray as $key => $value )
	{
	        $symbol = $value['stocksymbol'];
	        if ( $symbol != 'CASH' )
	        {
			$api->addSymbol( $symbol );
		}
	}
	$result = $api->getQuotes();
	if( $result->isSuccess() ) 
	{
	    	$quotes = $result->data;
	    	foreach( $quotes as $quote ) 
		{
			var_dump( $quote );
	        	$stock->Setstocksymbol( $quote->symbol );
	        	 $stock->Setlow( $quote->daysLow );
	         	$stock->Sethigh( $quote->daysHigh );
	         	$stock->Setdailyvolume( $quote->volume );
	        	$stock->InsertVAR();
	        	$symbol = $quote->symbol;
	        	$lastTrade = $quote->lastTrade; // or $quote->get( YahooFinance_Options::LAST_TRADE );
	        	$daysLow = $quote->daysLow; // or $quote->get( YahooFinance_Options::DAYS_LOW );
	    	}
	}	
	$lowlimit += $YahooLimit;
	$highlimit += $YahooLimit;
}

?>
