<?php
require_once( 'candlesticksimpleAlert2days.class.php' );

        //go through technical analysis for this symbol,
        //using the identified candlesticks sell or buy
        //ALL stocks or all cash.
        //
        //DOES NOT CONSIDER CURRENCY (forex) EXCHANGES NOR DIVIDENDS
$symbol = "IBM";
$startingcash = "10000.00";
$startdate = "2011-01-02";
$enddate = "2011-12-25";
                $user = "cs_Alert2days";
                $firstname = "Candlestick";
                $lastname = "SimpleAlert2days";
                $email = "fraser.ks@gmail.com";
                $currency = "CAD";
                $foreigncurrency = "CAD";
                $account = "TRADE";
        $candlesticksimpleAlert2days = new candlesticksimpleAlert2days( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimpleAlert2days->AddUser( $firstname, $lastname, $email );
        $candlesticksimpleAlert2days->RunStrategy();
	exit();
//Change the averages for triggering buy/sell see if it makes any difference
        $candlesticksimpleAlert2days2 = new candlesticksimpleAlert2days( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimpleAlert2days2->AddUser( $firstname, $lastname, $email );
	$candlesticksimpleAlert2days2->Setbuystockaverage( "55" );
	$candlesticksimpleAlert2days2->Setsellstockaverage( "45" );
        $candlesticksimpleAlert2days2->RunStrategy();
//Change the averages for triggering buy/sell see if it makes any difference
        $candlesticksimpleAlert2days3 = new candlesticksimpleAlert2days( $user, $startingcash, $symbol, $startdate, $enddate, $currency, $foreigncurrency, $account );
        $candlesticksimpleAlert2days3->AddUser( $firstname, $lastname, $email );
	$candlesticksimpleAlert2days3->Setbuystockaverage( "65" );
	$candlesticksimpleAlert2days3->Setsellstockaverage( "35" );
        $candlesticksimpleAlert2days3->RunStrategy();

?>
