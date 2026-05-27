<?php

//require_once(dirname(__FILE__) . '/YahooFinanceAPI.php');
require_once('data/YahooFinanceAPI/YahooFinanceAPI.php');
spl_autoload_register(array('YahooFinanceAPI', 'autoload'));
 
function createAPI()
{
	$api = new YahooFinanceAPI();

/*
				ask
                              "askSize" => "a5",
                              "bid" => "b",
                              "askRealTime" => "b2",
                              "bidRealTime" => "b3",
                              "bidSize" => "b6",
                              "changeAndPercentChange" => "c",
                              "change" => "c1",
                              "changeRealTime" => "c6",
                              "afterHoursChangeRealTime" => "c8",
                              "errorIndication" => "e1",
                              "EPSEstimateCurrentYear" => "e7",
                              "EPSEstimateNextYear" => "e8",
                              "EPSEstimateNextQuarter" => "e9",
                              "floatShares" => "f6",
                              "holdingsGainPercent" => "g1",
                              "annualizedGain" => "g3",
                              "holdingsGain" => "g4",
                              "holdingsGainPercentRealTime" => "g5",
                              "holdingsGainRealTime" => "g6",
                              "moreInfo" => "i",
                              "orderBookRealTime" => "i5",
                              "marketCapitalizationRealTime" => "j3",
                              "EBITDA" => "j4",
                              "lastTradeWithTimeRealTime" => "k1",
                              "changePercentRealTime" => "k2",
                              "lastTradeSize" => "k3",
                              "lastTradeWithTime" => "l",
				lasttrade
			 "highLimit" => "l2",
                              "lowLimit" => "l3",
                              "daysRange" => "m",
                              "daysRangeRealTime" => "m2",
                              "notes" => "n4",
                              "pricePaid" => "p1",
                              "changeInPercent" => "p2",
                              //"changeInPercent" => "c2",  original library value but looks to be a typo
                              "priceEarningsRatioRealTime" => "r2",
                              "sharesOwned" => "s1",
                              "lastTradeTime" => "t1",
                              "tradeLinks" => "t6",
                              "tickerTrend" => "t7",
                              "holdingsValue" => "v1",
                              "holdingsValueRealTime" => "v7",
                              "52WeekRange" => "w",
                              "daysValueChange" => "w1",
                              "daysValueChangeRealTime" => "w4",

*/
	$api->addOption("symbol"); // or $api->addOption( YahooFinance_Options::SYMBOL );
	$api->addOption("previousClose"); // or $api->addOption( YahooFinance_Options::PREVIOUS_CLOSE);
	$api->addOption("open"); // or $api->addOption( YahooFinance_Options::OPEN );
	$api->addOption("lastTrade"); // or $api->addOption( YahooFinance_Options:LAST_TRADE );
	$api->addOption("lastTradeTime"); // or $api->addOption( YahooFinance_Options::LAST_TRADE_TIME );
	$api->addOption("lastTradeDate"); // or $api->addOption( YahooFinance_Options::LAST_TRADE_TIME );
	$api->addOption("change" ); // or $api->addOption( YahooFinance_Options::CHANGE );
	$api->addOption("daysLow" ); // or $api->addOption( YahooFinance_Options::DAYS_LOW );
	$api->addOption("daysHigh" ); // or $api->addOption( YahooFinance_Options::DAYS_HIGH );
	$api->addOption("volume" ); // or $api->addOption( YahooFinance_Options::VOLUME );
	$api->addOption("name" ); 
	$api->addOption("stockExchange" ); 
	$api->addOption("dividendPerShare" ); 
	$api->addOption("dividendYeild" ); 
	$api->addOption("earningsPerShare" ); 
	$api->addOption("averageDailyVolume" ); 
	$api->addOption("bookValue" ); 
	$api->addOption("52WeekLow" ); 
	$api->addOption("52WeekHigh" ); 
	$api->addOption("50DayMovingAverage" ); 
	$api->addOption("200DayMovingAverage" ); 
	$api->addOption("changeFrom200DayMovingAverage" ); 
	$api->addOption("percentChangeFrom200DayMovingAverage" ); 
	$api->addOption("changeFrom50DayMovingAverage" ); 
	$api->addOption("percentChangeFrom50DayMovingAverage" ); 
	$api->addOption("marketCapitalization" ); 
	$api->addOption("changeFrom52WeekLow" ); 
	$api->addOption("percentChangeFrom52WeekLow" ); 
	$api->addOption("changeFrom52WeekHigh" ); 
	$api->addOption("percentChangeFrom52WeekHigh" ); 
	$api->addOption("shortRatio" ); 
	$api->addOption("1YrTargetPrice" ); 
	$api->addOption("PEGRatio" ); 
	$api->addOption("pricePerEPSEstimateCurrentYear" ); 
	$api->addOption("pricePerEPSEstimateNextYear" ); 
	$api->addOption("priceEarningsRatio" ); 
	$api->addOption("pricePerSales" ); 
	$api->addOption("pricePerBook" ); 
	$api->addOption("exDividendDate" ); 
	$api->addOption("dividendPayDate" ); 
	//$api->addOption("tradeDate"); // or $api->addOption( YahooFinance_Options::LAST_TRADE_TIME );
	return $api;
}
?>
