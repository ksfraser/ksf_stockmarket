<?php

//require_once(dirname(__FILE__) . '/YahooFinanceAPI.php');
require_once('data/YahooFinanceAPI/YahooFinanceAPI.php');
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
include( $MODELDIR . '/stockinfo.class.php' );
$stock = new stockinfo();
$stock->limit = 199; //Yahoo limits to 200 or less at a time
$stock->Select();
foreach( $stock->resultarray as $key => $value )
{
        $symbol = $value['stocksymbol'];
        if ( $symbol != 'CASH' )
        {
		$api->addSymbol( $symbol );
	}
}

/* END queryyahoo2.php */ 
 
$result = $api->getQuotes();
if( $result->isSuccess() ) {
    $quotes = $result->data;
    foreach( $quotes as $quote ) {
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


/* queryyahoo2.php would then insert,
   using newer API in generictable */
    $quotes = $result->data;
    foreach( $quotes as $quote ) {
        $stock->Setstocksymbol( $quote->symbol );
         $stock->Setlow( $quote->daysLow );
         $stock->Sethigh( $quote->daysHigh );
         $stock->Setdailyvolume( $quote->volume );
         //$stock->Setclose( $quote->lastTrade );
         //$stock->Setopen( $quote->open );
	$stock->InsertVAR();
  }


?>
