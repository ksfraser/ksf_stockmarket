<?php
require_once( 'candlesticksimple2days.class.php' );

        //go through technical analysis for this symbol,
        //using the identified candlesticks sell or buy
        //ALL stocks or all cash.
        //
        //DOES NOT CONSIDER CURRENCY (forex) EXCHANGES NOR DIVIDENDS
$symbol = "IBM";
$startingcash = "10000.00";
$startdate = "2011-01-02";
$enddate = "2011-12-25";
                $user = "cs_2days";
                $firstname = "Candlestick";
                $lastname = "Simple2days";
                $email = "fraser.ks@gmail.com";
                $currency = "CAD";
                $foreigncurrency = "CAD";
                $account = "TRADE";
        $candlesticksimple2days = new candlesticksimple2days( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple2days->AddUser( $firstname, $lastname, $email );
        $candlesticksimple2days->RunStrategy();
	exit();
//Change the averages for triggering buy/sell see if it makes any difference
        $candlesticksimple2days2 = new candlesticksimple2days( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple2days2->AddUser( $firstname, $lastname, $email );
	$candlesticksimple2days2->Setbuystockaverage( "55" );
	$candlesticksimple2days2->Setsellstockaverage( "45" );
        $candlesticksimple2days2->RunStrategy();
//Change the averages for triggering buy/sell see if it makes any difference
        $candlesticksimple2days3 = new candlesticksimple2days( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimple2days3->AddUser( $firstname, $lastname, $email );
	$candlesticksimple2days3->Setbuystockaverage( "65" );
	$candlesticksimple2days3->Setsellstockaverage( "35" );
        $candlesticksimple2days3->RunStrategy();

?>
