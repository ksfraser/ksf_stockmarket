<?php

//20090804 KF
//Backtest different strategies

//Get list of trade dates to test candlesticks
require_once( 'buildtradedatesarray.php' );
require_once( 'testcandlestickportfolio.php' );
require_once( 'testcandlesticksimple.php' );
require_once( 'testcandlesticksimple2day.php' );
require_once( 'testcandlesticksimplehalf.php' );
require_once( 'testcandlesticksimple2dayhalf.php' );
require_once( 'testcandlesticksimple2daytenth.php' );
require_once( '../scripts/candlestick/candlesticks2.php' );
$startdate = "2009-01-01";
$tradedatesarray = buildtradedatesarray( $startdate );
//Get list of stocks in (historical) stockprices

require_once( '../model/stockprices.class.php' );
$stockprices = new stockprices;
$stockprices->select = "distinct symbol";
$stockprices->Select();
var_dump( $stockprices->resultarray );

$startingcash = "1000.00";
//testcandlestickportfolio( $startdate, 100 * $startingcash, $tradedatesarray, $fcnaction );
//Take each symbol and send it through
foreach( $stockprices->resultarray as $row )
{
	testcandlesticksimple( $row['symbol'], $startingcash, $tradedatesarray, $fcnaction );
//	testcandlesticksimple2day( $row['symbol'], $startingcash, $tradedatesarray, $fcnaction );
//	testcandlesticksimplehalf( $row['symbol'], $startingcash, $tradedatesarray, $fcnaction );
//	testcandlesticksimple2dayhalf( $row['symbol'], $startingcash, $tradedatesarray, $fcnaction );
//	testcandlesticksimple2daytenth( $row['symbol'], $startingcash, $tradedatesarray, $fcnaction );
}

