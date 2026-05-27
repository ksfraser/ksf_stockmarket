<?php
require_once( 'candlesticksimple.class.php' );

        //go through technical analysis for this symbol,
        //using the identified candlesticks sell or buy
        //ALL stocks or all cash.
        //
        //DOES NOT CONSIDER CURRENCY (forex) EXCHANGES NOR DIVIDENDS
$symbol = "IBM";
$startingcash = "10000.00";
$startdate = "2011-01-02";
$enddate = "2011-12-25";
                $user = "candlestick_simple";
                $firstname = "Candlestick";
                $lastname = "Simple";
                $email = "fraser.ks@gmail.com";
                $currency = "CAD";
                $foreigncurrency = "CAD";
                $account = "TRADE";
        $candlesticksimple = new candlesticksimple( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple->AddUser( $firstname, $lastname, $email );
        $candlesticksimple->RunStrategy();
//Change the averages for triggering buy/sell see if it makes any difference
        $candlesticksimple2 = new candlesticksimple( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple2->AddUser( $firstname, $lastname, $email );
	$candlesticksimple2->Setbuystockaverage( "55" );
	$candlesticksimple2->Setsellstockaverage( "45" );
        $candlesticksimple2->RunStrategy();
//Change the averages for triggering buy/sell see if it makes any difference
        $candlesticksimple3 = new candlesticksimple( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple3->AddUser( $firstname, $lastname, $email );
	$candlesticksimple3->Setbuystockaverage( "65" );
	$candlesticksimple3->Setsellstockaverage( "35" );
        $candlesticksimple3->RunStrategy();

?>
