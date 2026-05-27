<?php

//require_once(dirname(__FILE__) . '/YahooFinanceAPI.php');

//require_once('data/YahooFinanceAPI/YahooFinanceAPI.php');
//spl_autoload_register(array('YahooFinanceAPI', 'autoload'));
//require_once("YahooCreateAPI.php");
 

/*************************************************
	Requires that the proper objects are passed in
*************************************************/

//require_once( '../local.php' );
//require_once( 'data/generictable.php' );
//Local_Init();
//require_once('security/genericsecurity.php');
//global $Security;
//include( $MODELDIR . '/stockinfo.class.php' );
//include( $MODELDIR . '/stockprices.class.php' );
//include( $MODELDIR . '/stockexchange.class.php' );
//include( $MODELDIR . '/technicalanalysis.class.php' );

/************************************************************************************************************************
************************************************************************************************************************
************************************************************************************************************************
				Called Functions
************************************************************************************************************************
************************************************************************************************************************
************************************************************************************************************************/

function updateStockinfo( $quote, $stockinfo )
{
	$stockinfo->corporatename = $quote->name;
	//$stockinfo->yearlow = $quote->52WeekLow;
	//$stockinfo->yearhigh = $quote->52WeekHigh;
	//$stockinfo->yearlow = $quote->get( YahooFinance_Options::52WEEKLOW );
	//$stockinfo->yearhigh = $quote->get( YahooFinance_Options::52WEEKLOW );
	$stockinfo->currentprice = $quote->lastTrade;
	$stockinfo->low = $quote->daysLow;
	$stockinfo->high = $quote->daysHigh;
	$stockinfo->dailyvolume = $quote->volume;
	$stockinfo->peratio = $quote->priceEarningsRatio;
	$stockinfo->averagevolume = $quote->averageDailyVolume;
	$stockinfo->EPS = $quote->earningsPerShare;
	$stockinfo->annualdividendpershare = $quote->dividendPerShare;
	$stockinfo->dailychange = $quote->change;
	$stockinfo->marketcap = $quote->marketCapitalization;
	$stockinfo->reviseduser = "YahooAPI";
	$stockinfo->InsertVAR();
}
function addStockinfo( $quote, $stockinfo )
{
	$stockinfo->corporatename = $quote->name;
	//$stockinfo->yearlow = $quote->52WeekLow;
	//$stockinfo->yearhigh = $quote->52WeekHigh;
	$stockinfo->currentprice = $quote->lastTrade;
	$stockinfo->low = $quote->daysLow;
	$stockinfo->high = $quote->daysHigh;
	$stockinfo->dailyvolume = $quote->volume;
	$stockinfo->peratio = $quote->priceEarningsRatio;
	$stockinfo->averagevolume = $quote->averageDailyVolume;
	$stockinfo->EPS = $quote->earningsPerShare;
	$stockinfo->annualdividendpershare = $quote->dividendPerShare;
	$stockinfo->dailychange = $quote->change;
	$stockinfo->marketcap = $quote->marketCapitalization;
	$stockinfo->reviseduser = "YahooAPI";
	$stockinfo->InsertVAR();
}

function addStockprices( $quote, $stockinfo )
{
	$stockprices = new stockprices();
	$stockprices->symbol = $stockinfo->stocksymbol;
	//$stockprices->idstockinfo = $stockinfo->idstockinfo;
	$stockprices->date = $quote->lastTradeDate;
	$stockprices->previous_close = $quote->previousClose;
	$stockprices->day_open = $quote->open;
	$stockprices->day_close = $quote->lastTrade;
	$stockprices->day_low = $quote->daysLow;
	$stockprices->day_high = $quote->daysHigh;
	$stockprices->day_change = $quote->change;
	$stockprices->volume = $quote->volume;
	$stockprices->stockExchange = $quote->stockExchange;
//	$stockprices->adjustedclose = $quote->stockExchange;
	$stockprices->reviseduser = "YahooAPI";
	$stockprices->InsertVAR();
	unset( $stockprices );

//$api->addOption("bookValue" ); 
//$api->addOption("shortRatio" ); 
//$api->addOption("PEGRatio" ); 
//$api->addOption("priceEarningsRatio" ); 
//$api->addOption("pricePerSales" ); 
//$api->addOption("pricePerBook" ); 
}

function addTechnicalanalysis( $quote, $stockinfo )
{
	$technicalanalysis = new technicalanalysis();
	$technicalanalysis->symbol = $stockinfo->stocksymbol;
	$technicalanalysis->idstockinfo = $stockinfo->idstockinfo;
	$technicalanalysis->date = $quote->lastTradeDate;
	$technicalanalysis->reviseduser = "YahooAPI";

//	//$technicalanalysis->dayclose = $quote->lastTradeDate;			//
//	//$technicalanalysis->typicalprice = $quote->lastTradeDate;		//
//	$technicalanalysis->movingaverage50 = $quote->50DayMovingAverage;
//	$technicalanalysis->movingaverage200 = $quote->200DayMovingAverage;
//	//$technicalanalysis->expmovingaverage9 = $quote->lastTradeDate;		//
//	//$technicalanalysis->expmovingaverage12 = $quote->lastTradeDate;		//
//	//$technicalanalysis->expmovingaverage26 = $quote->lastTradeDate;		//
//	$technicalanalysis->macd = $quote->lastTradeDate;			
//	//$technicalanalysis->macd_histogram = $quote->lastTradeDate;		//
//	//$technicalanalysis->momentumoscilator = $quote->lastTradeDate;		//
//	$technicalanalysis->mamomentum = $quote->lastTradeDate;
//	$technicalanalysis->macrossover = $quote->lastTradeDate;
//	$technicalanalysis->macenterlinecrossover = $quote->lastTradeDate;
//	//$technicalanalysis->priceoscilator = $quote->lastTradeDate;		//
//	$technicalanalysis->linearregression = $quote->lastTradeDate;
//	$technicalanalysis->linearregressionangle = $quote->lastTradeDate;
//	$technicalanalysis->linearregressionslope = $quote->lastTradeDate;
//	$technicalanalysis->linearregressionintercept = $quote->lastTradeDate;
//	$technicalanalysis->stochastic = $quote->lastTradeDate;
//	//$technicalanalysis->relativestrenghtindex = $quote->lastTradeDate;	//
//	$technicalanalysis->rsioscilator = $quote->lastTradeDate;
//	//$technicalanalysis->commoditychannelindex = $quote->lastTradeDate;	//
//	//$technicalanalysis->pricechangepercent = $quote->lastTradeDate;		//
//	$technicalanalysis->volume12 = $quote->lastTradeDate;
//	$technicalanalysis->volume26 = $quote->lastTradeDate;
//	$technicalanalysis->volume90 = $quote->lastTradeDate;
//	//$technicalanalysis->support12 = $quote->lastTradeDate;			//
//	//$technicalanalysis->support26 = $quote->lastTradeDate;			//
//	//$technicalanalysis->resistence12 = $quote->lastTradeDate;		//
//	//$technicalanalysis->resistence26 = $quote->lastTradeDate;		//
//	$technicalanalysis->annualreturn = $quote->lastTradeDate;
//	$technicalanalysis->annualrisk = $quote->lastTradeDate;
//$api->addOption("changeFrom200DayMovingAverage" ); 
//$api->addOption("percentChangeFrom200DayMovingAverage" ); 
//$api->addOption("changeFrom50DayMovingAverage" ); 
//$api->addOption("percentChangeFrom50DayMovingAverage" ); 
//$api->addOption("marketCapitalization" ); 
//$api->addOption("changeFrom52WeekLow" ); 
//$api->addOption("percentChangeFrom52WeekLow" ); 
//$api->addOption("changeFrom52WeekHigh" ); 
//$api->addOption("percentChangeFrom52WeekHigh" ); 
//$api->addOption("shortRatio" ); 
//$api->addOption("1YrTargetPrice" ); 
//$api->addOption("PEGRatio" ); 
//$api->addOption("priceEarningsRatio" ); 
//$api->addOption("pricePerSales" ); 
//$api->addOption("pricePerBook" ); 
	$technicalanalysis->InsertVAR();
	unset( $technicalanalysis  );
}


?>
