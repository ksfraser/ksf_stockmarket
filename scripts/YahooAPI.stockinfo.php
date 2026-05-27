<?php

//require_once(dirname(__FILE__) . '/YahooFinanceAPI.php');
require_once('data/YahooFinanceAPI/YahooFinanceAPI.php');
require_once( 'common/Yahoo2MySql_Date.php' );
spl_autoload_register(array('YahooFinanceAPI', 'autoload'));
 
$api = new YahooFinanceAPI();
 
$api->addOption("symbol"); // or $api->addOption( YahooFinance_Options::SYMBOL );
$api->addOption("previousClose"); // or $api->addOption( YahooFinance_Options::PREVIOUS_CLOSE);
$api->addOption("open"); // or $api->addOption( YahooFinance_Options::OPEN );
$api->addOption("lastTrade"); // or $api->addOption( YahooFinance_Options:LAST_TRADE );
$api->addOption("lastTradeTime"); // or $api->addOption( YahooFinance_Options::LAST_TRADE_TIME );
$api->addOption("change" ); // or $api->addOption( YahooFinance_Options::CHANGE );
$api->addOption("daysLow" ); // or $api->addOption( YahooFinance_Options::DAYS_LOW );
$api->addOption("daysHigh" ); // or $api->addOption( YahooFinance_Options::DAYS_HIGH );
$api->addOption("volume" ); // or $api->addOption( YahooFinance_Options::VOLUME );
$api->addOption("averageDailyVolume" );
$api->addOption("52WeekLow" ); 
$api->addOption("52WeekHigh" ); 
$api->addOption("earningsPerShare" ); 
$api->addOption("dividendPerShare" ); 
$api->addOption("lastTrade" ); //currentprice
$api->addOption("lastTradeDate" ); //asofdate 
$api->addOption("change" ); //dailychange?
$api->addOption("marketCapitalization" );
$api->addOption("priceEarningsRatio" ); 
$api->addOption("name" ); 

/* Original Code
$api->addSymbol("DELL" );
$api->addSymbol("IBM" );
$api->addSymbol("CNI" );
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
*/

/*Taken from queryyahoo2.php */

require_once( '../local.php' );
require_once( 'data/generictable.php' );
Local_Init();
require_once('security/genericsecurity.php');
global $Security;
include( $MODELDIR . '/stockexchange.class.php' );
$stockexchange = new stockexchange();
include( $MODELDIR . '/stockinfo.class.php' );
$stock = new stockinfo();
$stock_insert = new stockinfo();
$stock_insert->fieldspec['idstockinfo']['prikey'] = 'N';
$stock_insert->fieldspec['stocksymbol']['prikey'] = 'Y';

//Do this by locale....YahooCountry in stockexchange
$stockexchange->select = "distinct(YahooCountry)";
//$stockexchange->limit = "1";
$stockexchange->Select();
echo $stockexchange->querystring . "\n";
foreach ( $stockexchange->resultarray as $row )
{
	$country = $row['YahooCountry'];
	//$api->local = $country;
	$rowcount = $stock->CountAllRows();
	$YahooLimit = 199; //Yahoo limits to 200 or less at a time
	$lowlimit = 0;
	$highlimit = $YahooLimit;
	$count = 0;
	if( $rowcount > $YahooLimit )
	{
		$highlimit = $YahooLimit;
	}
	else
	{
		$highlimit = $rowcount;
	}
	while( $lowlimit < $rowcount )
	{
		$stock->limit = $lowlimit . ", " . $highlimit; 
		$stock->where = "active='1' and stockexchange in (select idstockexchange from stockexchange where YahooCountry='$country')";
		$stock->Select();
		echo $stock->querystring . "\n";
		//$stock->fieldspec['active']['extra_sql'] = '';
		$api->clear_symbols();
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
				//var_dump( $quote );
		        	$stock_insert->Setstocksymbol( $quote->symbol );
				if( strncmp( "N/A", $quote->daysLow, 3 ) ) 
		        		$stock_insert->Setlow( $quote->daysLow );
				if( strncmp( "N/A", $quote->daysHigh, 3 ) ) 
		         		$stock_insert->Sethigh( $quote->daysHigh );
				if( strncmp( "N/A", $quote->volume, 3 ) ) 
		         		$stock_insert->Setdailyvolume( $quote->volume );
				if( strncmp( "N/A", $quote->averageDailyVolume, 3 ) ) 
					$stock_insert->Setaveragevolume( $quote->averageDailyVolume );
				if( strncmp( "N/A", $quote->get( YahooFinance_Options::FIFTY_TWO_WEEK_LOW ), 3 ) ) 
					$stock_insert->Setyearlow( $quote->get( YahooFinance_Options::FIFTY_TWO_WEEK_LOW ) ); 
				if( strncmp( "N/A", $quote->get( YahooFinance_Options::FIFTY_TWO_WEEK_HIGH ), 3 ) ) 
					$stock_insert->Setyearhigh( $quote->get( YahooFinance_Options::FIFTY_TWO_WEEK_HIGH ) ); 
				if( strncmp( "N/A", $quote->earningsPerShare, 3 ) ) 
					$stock_insert->SetEPS( $quote->earningsPerShare ); 
				if( strncmp( "N/A", $quote->dividendPerShare, 3 ) ) 
					$stock_insert->Setannualdividendpershare( $quote->dividendPerShare ); 
				if( strncmp( "N/A", $quote->lastTrade, 3 ) ) 
					$stock_insert->Setcurrentprice( $quote->lastTrade ); //currentprice
				if( strncmp( "N/A", $quote->lastTradeDate, 3 ) ) 
					$stock_insert->Setasofdate( Yahoo2MySql_Date( $quote->lastTradeDate ) ); //asofdate 
				if( strncmp( "N/A", $quote->change, 3 ) ) 
					$stock_insert->Setdailychange( $quote->change ); //dailychange?
				if( strncmp( "N/A", $quote->marketCapitalization, 3 ) ) 
					$stock_insert->Setmarketcap( $quote->marketCapitalization );
				if( strncmp( "N/A", $quote->name, 3 ) ) 
					$stock_insert->Setcorporatename( $quote->name ); 
				if( strncmp( "N/A", $quote->priceEarningsRatio, 3 ) ) 
					$stock_insert->Setperatio( $quote->priceEarningsRatio ); 
		        	//$stock_insert->InsertVAR();
				$stock_insert->Setreviseduser( "YahooAPI-stockinfo" );
		        	$stock_insert->UpdateVAR();
				echo $stock_insert->querystring . "\n";
				$stock_insert->UnsetVAR();
				$count++;
		    	}
		}	
		$lowlimit += $YahooLimit;
		$highlimit += $YahooLimit;
	
	}
}
echo "Yahoo returned $count results when we queried for $rowcount\n";

/*
    ["change"]=>
    string(5) "-0.63"
    ["earningsPerShare"]=>
    string(4) "2.94"
    ["priceEarningsRatio"]=>
    string(4) "7.84"
*/
?>

