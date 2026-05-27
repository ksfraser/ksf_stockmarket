<?php
require_once( 'candlesticksimple3days.class.php' );

        //go through technical analysis for this symbol,
        //using the identified candlesticks sell or buy
        //ALL stocks or all cash.
        //
        //DOES NOT CONSIDER CURRENCY (forex) EXCHANGES NOR DIVIDENDS
$symbol = "IBM";
$startingcash = "10000.00";
$startdate = "2011-01-02";
$enddate = "2011-12-25";
                $user = "cs_3days";
                $firstname = "Candlestick";
                $lastname = "Simple3days";
                $email = "fraser.ks@gmail.com";
                $currency = "CAD";
                $foreigncurrency = "CAD";
                $account = "TRADE";
        $candlesticksimple3days = new candlesticksimple3days( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple3days->AddUser( $firstname, $lastname, $email );
        $candlesticksimple3days->RunStrategy();
	exit();
//Change the averages for triggering buy/sell see if it makes any difference
        $candlesticksimple3days2 = new candlesticksimple3days( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple3days2->AddUser( $firstname, $lastname, $email );
	$candlesticksimple3days2->Setbuystockaverage( "55" );
	$candlesticksimple3days2->Setsellstockaverage( "45" );
        $candlesticksimple3days2->RunStrategy();
//Change the averages for triggering buy/sell see if it makes any difference
        $candlesticksimple3days3 = new candlesticksimple3days( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple3days3->AddUser( $firstname, $lastname, $email );
	$candlesticksimple3days3->Setbuystockaverage( "65" );
	$candlesticksimple3days3->Setsellstockaverage( "35" );
        $candlesticksimple3days3->RunStrategy();

?>
